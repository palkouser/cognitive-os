"""One service from a provider call to a governance revision to learned intake.

The order matters, and it is the order a failure would otherwise let you get wrong:

1. **execute exactly once.** The provider call and the governance record share one
   execution; a retry above this service must not be able to produce two governance
   revisions or two learned observations for one answer, so the idempotency key is derived
   from the model call rather than generated;
2. **scan before deciding, decide before retaining.** Secret scanning runs on the
   *unredacted* normalized response, because scanning the redacted value would always pass.
   Retention is then whatever the directive asked for *and* the evidence permits — never
   the directive alone;
3. **retain only what policy allows.** `normalized_content` needs verified rights, a passed
   scan, a storable sensitivity and no deletion obligation. Any of them missing downgrades
   to `hash_only`, which is a recorded decision rather than a silent failure;
4. **record the governance revision before offering anything to intake.** A learned
   observation whose governance record failed to persist would be an observation nobody can
   trace back, which is exactly what C1 intake exists to refuse;
5. **never touch active memory, activation or approval.** There is no code path from here to
   any of them, and a test asserts the module contains no import that could reach one.

The verifier is supplied by the caller and must not be the provider. See ADR 0087.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256
from uuid import UUID, uuid5

from cognitive_os.application.ports.provider_output import ProviderOutputRepositoryPort
from cognitive_os.application.services.learned_intake import LearnedObservationIntake
from cognitive_os.application.services.model_execution import ModelExecutionService
from cognitive_os.domain.common import utc_now
from cognitive_os.domain.learned_evidence import LearnedObservationRecord
from cognitive_os.domain.model_requests import ModelProviderRequest, ModelProviderResponse
from cognitive_os.domain.provider_output import (
    STORABLE_SENSITIVITIES,
    GovernedExecutionReceipt,
    ProviderAdapterKind,
    ProviderOutputRecord,
    ProviderOutputRetentionMode,
    ProviderOutputVerifierStatus,
    ProviderRetentionDirective,
    SecretScanStatus,
    UsageRightsDecision,
)
from cognitive_os.providers.errors import ProviderConfigurationError
from cognitive_os.providers.redaction import REDACTION_RULESET_VERSION, scan_for_secrets

#: Fixed forever. Changing it would give an already-recorded governance decision a second
#: identity, and the whole point of deriving the ID is that a retry finds the first one.
PROVIDER_OUTPUT_NAMESPACE = UUID("2b7c9a14-5f83-5d61-9c02-7e4a1d6b8f35")


@dataclass(frozen=True, slots=True)
class RightsDecision:
    """What the operator determined about usage rights, and the evidence for it.

    An explicit input rather than something this service infers: the rights question is
    about terms of service and intended use, and a system that answered it for itself would
    be marking its own homework.
    """

    decision: UsageRightsDecision
    evidence_hash: str | None = None


@dataclass(frozen=True, slots=True)
class VerifierOutcome:
    """An *independent* verdict on the content, with the identity that produced it."""

    status: ProviderOutputVerifierStatus
    identity: str | None = None
    evidence_hash: str | None = None


@dataclass(frozen=True, slots=True)
class GovernedTeacherReceipt:
    """Everything one governed execution produced, by identity and hash."""

    execution: GovernedExecutionReceipt
    governance: ProviderOutputRecord | None
    observation: LearnedObservationRecord | None


def provider_output_id_for(model_call_id: UUID, *, provider_id: str) -> UUID:
    """Derived from the call, so re-recording the same execution is genuinely idempotent."""
    return uuid5(PROVIDER_OUTPUT_NAMESPACE, f"{provider_id}|{model_call_id}")


def canonical_hash(value: object) -> str:
    return sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()
    ).hexdigest()


def parameter_hash_for(request: ModelProviderRequest) -> str:
    """The parameters that shape an answer, without the prompt that asked for it."""
    return canonical_hash(
        {
            "temperature": request.temperature,
            "max_output_tokens": request.max_output_tokens,
            "response_format": request.response_format.value,
            "tool_choice": request.tool_choice.value,
            "context_budget": request.context_budget,
        }
    )


def request_hash_for(request: ModelProviderRequest) -> str:
    """Identity of the request, by content hash. The content itself is never stored."""
    return canonical_hash(
        {
            "requested_model": request.requested_model,
            "system_instructions": request.system_instructions,
            "messages": [
                {"role": message.role.value, "content": message.content}
                for message in request.messages
            ],
            "parameters": parameter_hash_for(request),
        }
    )


def normalized_response_hash_for(response: ModelProviderResponse) -> str:
    """Hash of the *normalized* response only. Raw provider payloads are never hashed here
    because they are never held long enough to hash."""
    return canonical_hash(
        {
            "resolved_model": response.resolved_model,
            "content": response.content,
            "structured_output": response.structured_output,
            "finish_reason": response.finish_reason.value,
        }
    )


class GovernedTeacherService:
    """Executes an advisory provider under an explicit retention and intended-use directive."""

    def __init__(
        self,
        execution: ModelExecutionService,
        *,
        repository: ProviderOutputRepositoryPort,
        intake: LearnedObservationIntake | None = None,
        surface: str = "provider-advisory",
        recorded_by: str = "governed-teacher",
        clock: Callable[[], datetime] = utc_now,
    ) -> None:
        self._execution = execution
        self._repository = repository
        self._intake = intake
        self._surface = surface
        self._recorded_by = recorded_by
        self._clock = clock

    async def execute_with_receipt(
        self,
        request: ModelProviderRequest,
        *,
        provider_id: str | None = None,
        directive: ProviderRetentionDirective,
        adapter_kind: ProviderAdapterKind,
        rights: RightsDecision | None = None,
        verifier: VerifierOutcome | None = None,
        offer_to_intake: bool = False,
    ) -> GovernedTeacherReceipt:
        rights = rights or RightsDecision(decision=UsageRightsDecision.UNKNOWN)
        verifier = verifier or VerifierOutcome(status=ProviderOutputVerifierStatus.NOT_RUN)

        response, handles = await self._execution.execute_for_governance(
            request, provider_id=provider_id
        )
        self._refuse_self_verification(handles.provider_id, verifier)

        response_hash = normalized_response_hash_for(response)
        scan = scan_for_secrets(
            {
                "content": response.content,
                "structured_output": response.structured_output,
                "warnings": list(response.warnings),
            }
        )
        retention = self._permitted_retention(
            directive,
            rights=rights,
            scan_status=scan.status,
            has_response_artifact=handles.response_artifact is not None,
        )

        execution_receipt = GovernedExecutionReceipt(
            response=response,
            provider_id=handles.provider_id,
            adapter_kind=adapter_kind,
            requested_model=request.requested_model,
            resolved_model=response.resolved_model,
            request_hash=request_hash_for(request),
            normalized_response_hash=response_hash,
            model_call_id=request.model_call_id,
            completed_event_id=handles.completed_event_id,
            request_artifact_id=(
                handles.request_artifact.artifact_id if handles.request_artifact else None
            ),
            response_artifact_id=(
                handles.response_artifact.artifact_id
                if handles.response_artifact
                and retention is ProviderOutputRetentionMode.NORMALIZED_CONTENT
                else None
            ),
            retention_mode=retention,
        )

        if retention is ProviderOutputRetentionMode.NONE:
            # The default. Nothing is recorded, nothing is offered, and the caller gets the
            # answer it asked for and no durable trace beyond the Event Store lifecycle.
            return GovernedTeacherReceipt(
                execution=execution_receipt, governance=None, observation=None
            )

        if handles.completed_event_id is None:
            raise ProviderConfigurationError(
                provider_id=handles.provider_id,
                error_code="governance_requires_event_store",
                message=(
                    "recording provider-output governance requires an Event Store: the "
                    "ledger names the exact completed model-call envelope"
                ),
            )

        record = await self._record_governance(
            request,
            response_hash=response_hash,
            execution_receipt=execution_receipt,
            directive=directive,
            rights=rights,
            verifier=verifier,
            scan_status=scan.status,
            scan_evidence_hash=scan.evidence_hash,
            retention=retention,
            handles_response_artifact=execution_receipt.response_artifact_id,
        )
        execution_receipt = execution_receipt.model_copy(
            update={
                "provider_output_id": record.provider_output_id,
                "provider_output_revision": record.revision,
            }
        )

        observation = None
        if offer_to_intake and self._intake is not None:
            # Only after the governance record is durable. An observation whose governance
            # record failed to persist would be untraceable, and reporting the intake as a
            # success would make a persistence failure look like a learned result.
            reference = await self._repository.resolve_source(
                record.provider_output_id, surface=self._surface, moment=self._clock()
            )
            observation = await self._intake.offer(reference, correlation_id=request.correlation_id)

        return GovernedTeacherReceipt(
            execution=execution_receipt, governance=record, observation=observation
        )

    # ---------------------------------------------------------------------- policy

    @staticmethod
    def _refuse_self_verification(provider_id: str, verifier: VerifierOutcome) -> None:
        if verifier.identity is not None and verifier.identity == provider_id:
            raise ProviderConfigurationError(
                provider_id=provider_id,
                error_code="provider_verified_itself",
                message=(
                    "a provider cannot verify its own output: schema validity proves shape, "
                    "not correctness"
                ),
            )

    @staticmethod
    def _permitted_retention(
        directive: ProviderRetentionDirective,
        *,
        rights: RightsDecision,
        scan_status: SecretScanStatus,
        has_response_artifact: bool,
    ) -> ProviderOutputRetentionMode:
        """What may actually be retained, which is the directive *intersected* with evidence.

        Downgrading rather than raising: the caller asked for a governed execution and got
        one, and the record says exactly how much survived. Raising would lose the answer
        over a retention question the record is designed to express.
        """
        requested = directive.retention_mode
        if requested is not ProviderOutputRetentionMode.NORMALIZED_CONTENT:
            return requested
        permitted = (
            rights.decision is UsageRightsDecision.VERIFIED
            and scan_status is SecretScanStatus.PASSED
            and not directive.physical_deletion_required
            and directive.sensitivity in STORABLE_SENSITIVITIES
            and has_response_artifact
        )
        return (
            ProviderOutputRetentionMode.NORMALIZED_CONTENT
            if permitted
            else ProviderOutputRetentionMode.HASH_ONLY
        )

    async def _record_governance(
        self,
        request: ModelProviderRequest,
        *,
        response_hash: str,
        execution_receipt: GovernedExecutionReceipt,
        directive: ProviderRetentionDirective,
        rights: RightsDecision,
        verifier: VerifierOutcome,
        scan_status: SecretScanStatus,
        scan_evidence_hash: str,
        retention: ProviderOutputRetentionMode,
        handles_response_artifact: UUID | None,
    ) -> ProviderOutputRecord:
        output_id = provider_output_id_for(
            request.model_call_id, provider_id=execution_receipt.provider_id
        )
        completed_event_id = execution_receipt.completed_event_id
        if completed_event_id is None:
            # A real check, not an `assert`: under `python -O` an assertion disappears, and
            # what would be left is a contract validation error several frames away from the
            # cause.
            raise ProviderConfigurationError(
                provider_id=execution_receipt.provider_id,
                error_code="governance_requires_event_store",
                message="a governance revision must name the completed model-call envelope",
            )
        record = ProviderOutputRecord(
            provider_output_revision_id=uuid5(PROVIDER_OUTPUT_NAMESPACE, f"{output_id}|1"),
            provider_output_id=output_id,
            revision=1,
            model_call_id=request.model_call_id,
            provider_id=execution_receipt.provider_id,
            adapter_kind=execution_receipt.adapter_kind,
            requested_model=request.requested_model,
            resolved_model=execution_receipt.resolved_model,
            request_hash=execution_receipt.request_hash,
            normalized_response_hash=response_hash,
            completed_event_id=completed_event_id,
            response_artifact_id=handles_response_artifact,
            response_artifact_hash=(
                execution_receipt.normalized_response_hash
                if handles_response_artifact is not None
                else None
            ),
            prompt_template_id=directive.prompt_template_id,
            prompt_template_version=directive.prompt_template_version,
            parameter_hash=parameter_hash_for(request),
            intended_use=directive.intended_use,
            rights_decision=rights.decision,
            rights_evidence_hash=rights.evidence_hash,
            sensitivity=directive.sensitivity,
            secret_scan_status=scan_status,
            secret_scan_evidence_hash=scan_evidence_hash,
            secret_scan_ruleset_version=REDACTION_RULESET_VERSION,
            retention_mode=retention,
            expires_at=directive.expires_at,
            physical_deletion_required=directive.physical_deletion_required,
            verifier_status=verifier.status,
            verifier_identity=verifier.identity,
            verifier_evidence_hash=verifier.evidence_hash,
            recorded_by=self._recorded_by,
            recorded_at=self._clock(),
            # Derived from the call, not generated: a retry finds the first record rather
            # than appending a second governance decision for one answer.
            idempotency_key=f"provider-output:{output_id}:1",
        )
        return await self._repository.record_output(record)
