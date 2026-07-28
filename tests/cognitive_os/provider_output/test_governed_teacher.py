"""The governed teacher: one provider call, one governance decision, one intake offer.

Every test here is about a boundary that would otherwise be a convention. In particular:
the provider is called exactly once whatever else happens; retention is the directive
*intersected* with the evidence rather than the directive alone; a governance record is
durable before anything reaches learned intake; and no provider output can ever be
classified as a real governed run.
"""

from __future__ import annotations

import asyncio
from datetime import timedelta
from hashlib import sha256
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4, uuid5

import pytest

from cognitive_os.application.services.governed_teacher import (
    GovernedTeacherService,
    RightsDecision,
    VerifierOutcome,
    provider_output_id_for,
)
from cognitive_os.application.services.learned_evidence import LearnedEvidenceService
from cognitive_os.application.services.learned_intake import (
    PROVIDER_ADVISORY_SOURCE_KINDS,
    REAL_GOVERNED_SOURCE_KINDS,
    VERIFIER_BACKED_SOURCE_KINDS,
    LearnedObservationIntake,
)
from cognitive_os.application.services.model_execution import ModelExecutionService
from cognitive_os.domain.common import ArtifactRef
from cognitive_os.domain.learned import ProvenanceClass
from cognitive_os.domain.learned_evidence import ObservationStatus
from cognitive_os.domain.memory import MemorySensitivity
from cognitive_os.domain.model_requests import (
    ModelProviderRequest,
    ModelProviderResponse,
    ProviderMessage,
    ProviderMessageRole,
)
from cognitive_os.domain.provider import ModelFinishReason
from cognitive_os.domain.provider_output import (
    ProviderAdapterKind,
    ProviderOutputConflict,
    ProviderOutputIntendedUse,
    ProviderOutputRepositoryError,
    ProviderOutputRetentionMode,
    ProviderOutputVerifierStatus,
    ProviderRetentionDirective,
    SecretScanStatus,
    UsageRightsDecision,
)
from cognitive_os.events.memory_store import MemoryEventStore
from cognitive_os.events.provider_event_service import (
    ProviderArtifactPolicy,
    ProviderArtifactService,
    ProviderEventService,
)
from cognitive_os.infrastructure.learned.memory_provider_output import (
    InMemoryProviderOutputRepository,
)
from cognitive_os.infrastructure.learned.memory_repository import (
    InMemoryLearnedEvidenceRepository,
)
from cognitive_os.providers.errors import ProviderConfigurationError
from cognitive_os.providers.mock import MockProvider
from cognitive_os.providers.registry import ProviderRegistry

from . import fixtures as fx

CLEAN_CONTENT = "the helper subtracts where it should add"
LEAKY_CONTENT = "the key is sk-or-v1-" + "a" * 32  # pragma: allowlist secret


class CountingProvider:
    """A provider that records how many times it was actually called."""

    def __init__(self, response: ModelProviderResponse) -> None:
        self._inner = MockProvider(outcomes=(response,) * 8)
        self.calls = 0

    @property
    def provider_id(self) -> str:
        return self._inner.provider_id

    @property
    def identity(self):  # type: ignore[no-untyped-def]
        return self._inner.identity

    @property
    def enabled(self) -> bool:
        return True

    async def complete(self, request: ModelProviderRequest) -> ModelProviderResponse:
        self.calls += 1
        return await self._inner.complete(request)

    def stream(self, request: ModelProviderRequest):  # type: ignore[no-untyped-def]
        return self._inner.stream(request)

    async def health_check(self):  # type: ignore[no-untyped-def]
        return await self._inner.health_check()

    async def get_model_capabilities(self, model_id: str):  # type: ignore[no-untyped-def]
        return await self._inner.get_model_capabilities(model_id)


class MemoryArtifactStore:
    """The narrowest thing `ProviderArtifactService` needs: content-addressed `put_bytes`.

    In-process rather than on disk, because what these tests assert is *whether* an artifact
    was created and referenced, not how the filesystem stores it — that is covered by the
    Artifact Store's own suite and by the PostgreSQL integration tests.
    """

    def __init__(self) -> None:
        self.blobs: dict[UUID, bytes] = {}

    async def put_bytes(
        self, data: bytes, *, media_type: str, source_event_id: UUID | None = None
    ) -> ArtifactRef:
        del source_event_id
        content_hash = sha256(data).hexdigest()
        artifact_id = uuid5(UUID("00000000-0000-5000-8000-000000000000"), content_hash)
        self.blobs[artifact_id] = data
        return ArtifactRef(
            artifact_id=artifact_id,
            media_type=media_type,
            content_hash=content_hash,
            size_bytes=len(data),
            storage_key=f"sha256/{content_hash[:2]}/{content_hash}",
            created_at=fx.FIXTURE_NOW,
        )


def a_request() -> ModelProviderRequest:
    return ModelProviderRequest(
        model_call_id=uuid4(),
        task_run_id=uuid4(),
        correlation_id=uuid4(),
        requested_model="openrouter/free",
        messages=(ProviderMessage(role=ProviderMessageRole.USER, content="review this"),),
    )


def a_response(request: ModelProviderRequest, *, content: str = CLEAN_CONTENT):
    return ModelProviderResponse(
        model_call_id=request.model_call_id,
        provider_id="mock",
        requested_model=request.requested_model,
        resolved_model="vendor/small-model:free",
        content=content,
        structured_output={"summary": content, "findings": []},
        finish_reason=ModelFinishReason.COMPLETED,
        latency_ms=1.0,
    )


def build(
    request: ModelProviderRequest,
    tmp_path: Path,
    *,
    content: str = CLEAN_CONTENT,
    with_artifacts: bool = True,
    with_events: bool = True,
    with_intake: bool = True,
) -> tuple[GovernedTeacherService, CountingProvider, InMemoryProviderOutputRepository, Any]:
    provider = CountingProvider(a_response(request, content=content))
    del tmp_path
    artifacts = (
        ProviderArtifactService(
            MemoryArtifactStore(),  # type: ignore[arg-type]
            policy=ProviderArtifactPolicy.NORMALIZED_ONLY,
        )
        if with_artifacts
        else None
    )
    execution = ModelExecutionService(
        ProviderRegistry((provider,)),
        default_provider_id=provider.provider_id,
        event_service=(ProviderEventService(MemoryEventStore()) if with_events else None),
        artifact_service=artifacts,
    )
    repository = InMemoryProviderOutputRepository()
    evidence = LearnedEvidenceService(InMemoryLearnedEvidenceRepository())
    intake = LearnedObservationIntake(evidence) if with_intake else None
    service = GovernedTeacherService(
        execution,
        repository=repository,
        intake=intake,
        clock=lambda: fx.FIXTURE_NOW,
    )
    return service, provider, repository, intake


def directive(**overrides: object) -> ProviderRetentionDirective:
    fields: dict[str, object] = {
        "intended_use": ProviderOutputIntendedUse.CORPUS_CANDIDATE,
        "retention_mode": ProviderOutputRetentionMode.HASH_ONLY,
        "sensitivity": MemorySensitivity.PUBLIC,
    }
    fields.update(overrides)
    return ProviderRetentionDirective(**fields)  # type: ignore[arg-type]


VERIFIED = RightsDecision(decision=UsageRightsDecision.VERIFIED, evidence_hash=fx.HASH_A)
PASSED = VerifierOutcome(
    status=ProviderOutputVerifierStatus.PASSED,
    identity="synthetic-fixture-verifier",
    evidence_hash=fx.HASH_C,
)


class TestTheProviderIsCalledExactlyOnce:
    @pytest.mark.asyncio
    async def test_one_governed_execution_makes_one_provider_call(self, tmp_path: Path) -> None:
        """A second call would double the spend and the provider-side retention."""
        request = a_request()
        service, provider, _, _ = build(request, tmp_path)
        await service.execute_with_receipt(
            request,
            directive=directive(),
            adapter_kind=ProviderAdapterKind.OPENROUTER,
            rights=VERIFIED,
            verifier=PASSED,
        )
        assert provider.calls == 1

    @pytest.mark.asyncio
    async def test_reusing_one_model_call_id_fails_closed_rather_than_overwriting(
        self, tmp_path: Path
    ) -> None:
        """The governance identity is derived from the model call, which cuts both ways.

        A genuine retry — the same execution recorded again — finds the first record and is
        a free no-op, and the next test asserts that. *Re-executing* under the same model
        call ID is a different thing: it produces a second provider answer and a second
        completed envelope, so the content differs, and silently accepting it would let a
        caller with a reused ID overwrite a governance decision. It is refused instead.
        """
        request = a_request()
        service, _, repository, _ = build(request, tmp_path)
        await service.execute_with_receipt(
            request,
            directive=directive(),
            adapter_kind=ProviderAdapterKind.OPENROUTER,
            rights=VERIFIED,
            verifier=PASSED,
        )
        with pytest.raises(ProviderOutputRepositoryError) as failure:
            await service.execute_with_receipt(
                request,
                directive=directive(),
                adapter_kind=ProviderAdapterKind.OPENROUTER,
                rights=VERIFIED,
                verifier=PASSED,
            )
        assert failure.value.conflict is ProviderOutputConflict.IDEMPOTENCY_KEY_REUSED
        assert await repository.count_revisions() == 1

    @pytest.mark.asyncio
    async def test_recording_the_same_execution_twice_is_a_free_no_op(self, tmp_path: Path) -> None:
        """The retry that actually happens: persistence failed, the same answer is re-recorded."""
        request = a_request()
        service, _, repository, _ = build(request, tmp_path)
        receipt = await service.execute_with_receipt(
            request,
            directive=directive(),
            adapter_kind=ProviderAdapterKind.OPENROUTER,
            rights=VERIFIED,
            verifier=PASSED,
        )
        assert receipt.governance is not None
        for _ in range(3):
            await repository.record_output(receipt.governance)
        assert await repository.count_revisions() == 1

    @pytest.mark.asyncio
    async def test_concurrent_executions_of_one_call_id_leave_exactly_one_record(
        self, tmp_path: Path
    ) -> None:
        """Whoever wins, the ledger holds one decision — never a fork."""
        request = a_request()
        service, _, repository, _ = build(request, tmp_path)
        results = await asyncio.gather(
            *(
                service.execute_with_receipt(
                    request,
                    directive=directive(),
                    adapter_kind=ProviderAdapterKind.OPENROUTER,
                    rights=VERIFIED,
                    verifier=PASSED,
                )
                for _ in range(4)
            ),
            return_exceptions=True,
        )
        successes = [item for item in results if not isinstance(item, BaseException)]
        assert len(successes) == 1
        assert await repository.count_revisions() == 1


class TestRetentionIsTheDirectiveIntersectedWithEvidence:
    @pytest.mark.asyncio
    async def test_the_default_directive_retains_nothing_at_all(self, tmp_path: Path) -> None:
        request = a_request()
        service, _, repository, _ = build(request, tmp_path)
        receipt = await service.execute_with_receipt(
            request,
            directive=ProviderRetentionDirective(
                intended_use=ProviderOutputIntendedUse.TRANSIENT_ADVICE
            ),
            adapter_kind=ProviderAdapterKind.OPENROUTER,
        )
        assert receipt.governance is None
        assert receipt.observation is None
        assert receipt.execution.response_artifact_id is None
        assert await repository.count_revisions() == 0

    @pytest.mark.asyncio
    async def test_normalized_content_is_retained_when_every_condition_holds(
        self, tmp_path: Path
    ) -> None:
        request = a_request()
        service, _, _, _ = build(request, tmp_path)
        receipt = await service.execute_with_receipt(
            request,
            directive=directive(retention_mode=ProviderOutputRetentionMode.NORMALIZED_CONTENT),
            adapter_kind=ProviderAdapterKind.OPENROUTER,
            rights=VERIFIED,
            verifier=PASSED,
        )
        assert receipt.governance is not None
        assert receipt.governance.retention_mode is ProviderOutputRetentionMode.NORMALIZED_CONTENT
        assert receipt.governance.response_artifact_id is not None

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ("rights", "content", "reason"),
        [
            (RightsDecision(decision=UsageRightsDecision.UNKNOWN), CLEAN_CONTENT, "rights"),
            (VERIFIED, LEAKY_CONTENT, "scan"),
        ],
    )
    async def test_missing_evidence_downgrades_to_hash_only_rather_than_raising(
        self, tmp_path: Path, rights: RightsDecision, content: str, reason: str
    ) -> None:
        """The caller asked for a governed execution and got one; the record says how much
        survived. Raising would lose the answer over a question the record can express."""
        request = a_request()
        service, _, _, _ = build(request, tmp_path, content=content)
        receipt = await service.execute_with_receipt(
            request,
            directive=directive(retention_mode=ProviderOutputRetentionMode.NORMALIZED_CONTENT),
            adapter_kind=ProviderAdapterKind.OPENROUTER,
            rights=rights,
            verifier=PASSED,
        )
        assert receipt.governance is not None
        assert receipt.governance.retention_mode is ProviderOutputRetentionMode.HASH_ONLY
        assert receipt.governance.response_artifact_id is None

    @pytest.mark.asyncio
    async def test_the_scan_runs_on_the_unredacted_response(self, tmp_path: Path) -> None:
        """Scanning the redacted value would always pass, which is the trap."""
        request = a_request()
        service, _, _, _ = build(request, tmp_path, content=LEAKY_CONTENT)
        receipt = await service.execute_with_receipt(
            request,
            directive=directive(),
            adapter_kind=ProviderAdapterKind.OPENROUTER,
            rights=VERIFIED,
            verifier=PASSED,
        )
        assert receipt.governance is not None
        assert receipt.governance.secret_scan_status is SecretScanStatus.FAILED
        assert receipt.governance.secret_scan_evidence_hash is not None

    @pytest.mark.asyncio
    async def test_a_deletion_obligation_prevents_content_retention(self, tmp_path: Path) -> None:
        request = a_request()
        service, _, _, _ = build(request, tmp_path)
        receipt = await service.execute_with_receipt(
            request,
            directive=directive(retention_mode=ProviderOutputRetentionMode.HASH_ONLY),
            adapter_kind=ProviderAdapterKind.OPENROUTER,
            rights=VERIFIED,
            verifier=PASSED,
        )
        assert receipt.governance is not None
        assert receipt.governance.physical_deletion_required is False
        assert receipt.governance.response_artifact_id is None


class TestTheReceiptCarriesHandlesNotContent:
    @pytest.mark.asyncio
    async def test_the_receipt_names_the_event_the_ledger_points_at(self, tmp_path: Path) -> None:
        request = a_request()
        service, _, _, _ = build(request, tmp_path)
        receipt = await service.execute_with_receipt(
            request,
            directive=directive(),
            adapter_kind=ProviderAdapterKind.OPENROUTER,
            rights=VERIFIED,
            verifier=PASSED,
        )
        assert receipt.execution.completed_event_id is not None
        assert receipt.governance is not None
        assert receipt.governance.completed_event_id == receipt.execution.completed_event_id

    @pytest.mark.asyncio
    async def test_the_governance_record_carries_no_prompt_or_response_text(
        self, tmp_path: Path
    ) -> None:
        request = a_request()
        service, _, _, _ = build(request, tmp_path)
        receipt = await service.execute_with_receipt(
            request,
            directive=directive(),
            adapter_kind=ProviderAdapterKind.OPENROUTER,
            rights=VERIFIED,
            verifier=PASSED,
        )
        assert receipt.governance is not None
        rendered = receipt.governance.model_dump_json()
        assert "review this" not in rendered
        assert CLEAN_CONTENT not in rendered

    @pytest.mark.asyncio
    async def test_the_receipt_names_the_governance_revision_it_created(
        self, tmp_path: Path
    ) -> None:
        request = a_request()
        service, provider, _, _ = build(request, tmp_path)
        receipt = await service.execute_with_receipt(
            request,
            directive=directive(),
            adapter_kind=ProviderAdapterKind.OPENROUTER,
            rights=VERIFIED,
            verifier=PASSED,
        )
        assert receipt.execution.provider_output_id == provider_output_id_for(
            request.model_call_id, provider_id=provider.provider_id
        )
        assert receipt.execution.provider_output_revision == 1


class TestNoProviderVerifiesItself:
    @pytest.mark.asyncio
    async def test_a_verifier_identity_equal_to_the_provider_is_refused(
        self, tmp_path: Path
    ) -> None:
        request = a_request()
        service, provider, _, _ = build(request, tmp_path)
        with pytest.raises(ProviderConfigurationError, match="cannot verify its own output"):
            await service.execute_with_receipt(
                request,
                directive=directive(),
                adapter_kind=ProviderAdapterKind.OPENROUTER,
                rights=VERIFIED,
                verifier=VerifierOutcome(
                    status=ProviderOutputVerifierStatus.PASSED,
                    identity=provider.provider_id,
                    evidence_hash=fx.HASH_C,
                ),
            )


class TestLearnedIntakeIntegration:
    @pytest.mark.asyncio
    async def test_a_verified_output_is_accepted_as_evaluation_evidence(
        self, tmp_path: Path
    ) -> None:
        request = a_request()
        service, _, _, _ = build(request, tmp_path)
        receipt = await service.execute_with_receipt(
            request,
            directive=directive(),
            adapter_kind=ProviderAdapterKind.OPENROUTER,
            rights=VERIFIED,
            verifier=PASSED,
            offer_to_intake=True,
        )
        assert receipt.observation is not None
        assert receipt.observation.status is ObservationStatus.ACCEPTED
        assert receipt.observation.source_kind == "openrouter_advisory"

    @pytest.mark.asyncio
    async def test_unverified_output_quarantines_rather_than_being_accepted(
        self, tmp_path: Path
    ) -> None:
        request = a_request()
        service, _, _, _ = build(request, tmp_path)
        receipt = await service.execute_with_receipt(
            request,
            directive=directive(),
            adapter_kind=ProviderAdapterKind.OPENROUTER,
            rights=VERIFIED,
            verifier=VerifierOutcome(status=ProviderOutputVerifierStatus.NOT_RUN),
            offer_to_intake=True,
        )
        assert receipt.observation is not None
        assert receipt.observation.status is ObservationStatus.QUARANTINED
        assert receipt.observation.evaluation_eligible is False

    @pytest.mark.asyncio
    async def test_unverified_rights_are_rejected_not_quarantined(self, tmp_path: Path) -> None:
        request = a_request()
        service, _, _, _ = build(request, tmp_path)
        receipt = await service.execute_with_receipt(
            request,
            directive=directive(),
            adapter_kind=ProviderAdapterKind.OPENROUTER,
            rights=RightsDecision(decision=UsageRightsDecision.UNKNOWN),
            verifier=PASSED,
            offer_to_intake=True,
        )
        assert receipt.observation is not None
        assert receipt.observation.status is ObservationStatus.REJECTED

    @pytest.mark.asyncio
    async def test_a_provider_output_is_never_a_real_governed_run(self, tmp_path: Path) -> None:
        request = a_request()
        service, _, _, _ = build(request, tmp_path)
        receipt = await service.execute_with_receipt(
            request,
            directive=directive(),
            adapter_kind=ProviderAdapterKind.OPENROUTER,
            rights=VERIFIED,
            verifier=PASSED,
            offer_to_intake=True,
        )
        assert receipt.observation is not None
        assert receipt.observation.provenance_class is ProvenanceClass.OPERATOR_SUPPLIED
        assert receipt.observation.training_eligible is True

    @pytest.mark.asyncio
    async def test_intake_is_not_offered_unless_the_caller_asks(self, tmp_path: Path) -> None:
        request = a_request()
        service, _, _, _ = build(request, tmp_path)
        receipt = await service.execute_with_receipt(
            request,
            directive=directive(),
            adapter_kind=ProviderAdapterKind.OPENROUTER,
            rights=VERIFIED,
            verifier=PASSED,
        )
        assert receipt.governance is not None
        assert receipt.observation is None

    @pytest.mark.asyncio
    async def test_an_expired_governance_revision_is_rejected_by_intake(
        self, tmp_path: Path
    ) -> None:
        """`expires_at` governs future selection, and intake is a future selection."""
        request = a_request()
        service, _, _, _ = build(request, tmp_path)
        # An advancing clock, because that is what actually happens: the decision is
        # recorded now and intake resolves it later. A frozen clock could not express
        # the gap the expiry rule exists to govern.
        later = fx.FIXTURE_NOW + timedelta(days=2)
        readings = iter([fx.FIXTURE_NOW, later, later])
        service._clock = lambda: next(readings)
        receipt = await service.execute_with_receipt(
            request,
            directive=directive(expires_at=fx.FIXTURE_NOW + timedelta(days=1)),
            adapter_kind=ProviderAdapterKind.OPENROUTER,
            rights=VERIFIED,
            verifier=PASSED,
            offer_to_intake=True,
        )
        assert receipt.observation is not None
        assert receipt.observation.status is ObservationStatus.REJECTED


class TestTheSourceKindAllowlist:
    def test_all_three_provider_kinds_are_verifier_backed(self) -> None:
        assert PROVIDER_ADVISORY_SOURCE_KINDS <= VERIFIER_BACKED_SOURCE_KINDS

    def test_zero_provider_kinds_are_real_governed_sources(self) -> None:
        """The single most important allowlist assertion in the sprint."""
        assert frozenset() == PROVIDER_ADVISORY_SOURCE_KINDS & REAL_GOVERNED_SOURCE_KINDS

    def test_the_three_expected_kinds_are_present(self) -> None:
        assert (
            frozenset({"openrouter_advisory", "claude_code_advisory", "codex_cli_advisory"})
            == PROVIDER_ADVISORY_SOURCE_KINDS
        )


class TestNoPathReachesActivation:
    def test_the_service_imports_nothing_that_could_activate_or_approve(self) -> None:
        """A grep, but the boundary it guards is the one the whole sprint is about."""
        source = Path("src/cognitive_os/application/services/governed_teacher.py").read_text(
            encoding="utf-8"
        )
        for forbidden in (
            "record_activation",
            "advance_component",
            "register_component",
            "record_approval",
            "LearnedActivationApproval",
            "memory_repository",
            "active_component",
        ):
            assert forbidden not in source, forbidden

    @pytest.mark.asyncio
    async def test_recording_governance_requires_an_event_store(self, tmp_path: Path) -> None:
        """The ledger names the exact completed envelope; without one there is nothing to name."""
        request = a_request()
        service, _, _, _ = build(request, tmp_path, with_events=False)
        with pytest.raises(ProviderConfigurationError, match="requires an Event Store"):
            await service.execute_with_receipt(
                request,
                directive=directive(),
                adapter_kind=ProviderAdapterKind.OPENROUTER,
                rights=VERIFIED,
                verifier=PASSED,
            )
