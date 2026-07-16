"""Fail-closed verifiers for Context Bundle attachment."""

from cognitive_os.context.tokenization import ConservativeUtf8TokenEstimator
from cognitive_os.domain.context import (
    ContextBundleRevision,
    ContextRequest,
    ContextRetrievalTrace,
)
from cognitive_os.domain.enums import RiskLevel, VerifierStatus
from cognitive_os.domain.problems import CriterionType, ProblemDomain
from cognitive_os.domain.verification import VerifierResult
from cognitive_os.domain.verifiers import (
    VerificationRequest,
    VerificationSubjectType,
    VerifierCapability,
    VerifierDescriptor,
    VerifierDeterminism,
    VerifierKind,
)
from cognitive_os.memory.governance import contains_secret
from cognitive_os.verification.base import BaseVerifier

REQUIRED_CONTEXT_CAPABILITIES = (
    "provenance_integrity",
    "token_budget",
    "trust_integrity",
    "sensitivity",
    "required_coverage",
    "trace_integrity",
    "safety",
    "source_snapshot",
)


def build_context_verification_snapshot(
    bundle: ContextBundleRevision,
    trace: ContextRetrievalTrace,
    request: ContextRequest,
    rendered_context: str,
) -> dict[str, bool]:
    section_candidates = {
        candidate_id for section in bundle.sections for candidate_id in section.candidate_references
    }
    selected = set(trace.selected_candidate_ids)
    task_sources = {
        source.source_type for section in bundle.sections for source in section.source_references
    }
    estimator = ConservativeUtf8TokenEstimator(
        bytes_per_token=bundle.token_estimator_profile.bytes_per_token,
        per_message_overhead=bundle.token_estimator_profile.per_message_overhead,
    )
    return {
        "provenance_integrity": all(
            section.source_references and section.candidate_references
            for section in bundle.sections
        ),
        "token_budget": (
            bundle.total_token_estimate <= request.budget.provider_context_limit
            and estimator.estimate_text(rendered_context) + request.budget.system_instruction_tokens
            <= request.budget.provider_context_limit - request.budget.reserved_output_tokens
        ),
        "trust_integrity": all(section.trust_class.value for section in bundle.sections),
        "sensitivity": all(
            exclusion.reason.value != "sensitivity_exceeded"
            or exclusion.candidate_id not in selected
            for exclusion in trace.exclusions
        ),
        "required_coverage": (
            {"task_state", "execution_plan"} <= {source_type.value for source_type in task_sources}
        ),
        "trace_integrity": (
            selected == section_candidates
            and all(exclusion.reason.value for exclusion in trace.exclusions)
            and trace.context_request_id == bundle.context_request_id
        ),
        "safety": (
            not contains_secret(rendered_context)
            and all("----- END RETRIEVED DATA" in section.content for section in bundle.sections)
        ),
        "source_snapshot": (
            bundle.source_snapshot.snapshot_hash
            == trace.source_snapshot.snapshot_hash
            == request.source_snapshot.snapshot_hash
        ),
    }


class ContextInvariantVerifier(BaseVerifier):
    def __init__(self, capability: str) -> None:
        if capability not in REQUIRED_CONTEXT_CAPABILITIES:
            raise ValueError(f"unknown Context verifier capability: {capability}")
        verifier_id = f"context.{capability}"
        super().__init__(
            VerifierDescriptor(
                verifier_id=verifier_id,
                version="1",
                display_name=verifier_id.replace(".", " ").replace("_", " ").title(),
                description=f"Deterministically verify Context Bundle {capability}.",
                kind=VerifierKind.CONTEXT,
                capabilities=(
                    VerifierCapability(
                        capability_id=verifier_id,
                        subject_type=VerificationSubjectType.CONTEXT_BUNDLE,
                        problem_domains=(ProblemDomain.GENERIC,),
                        criterion_types=(CriterionType.DOMAIN_VERIFIER,),
                    ),
                ),
                determinism=VerifierDeterminism.DETERMINISTIC,
                risk_level=RiskLevel.LOW,
                default_timeout_seconds=10,
                maximum_input_bytes=1_048_576,
                configuration_schema={"type": "object", "additionalProperties": False},
            )
        )
        self._capability = capability

    async def verify(self, request: VerificationRequest) -> VerifierResult:
        value = request.subject.inline_value
        passed = (
            request.subject.subject_type is VerificationSubjectType.CONTEXT_BUNDLE
            and isinstance(value, dict)
            and value.get(self._capability) is True
        )
        return self.result(
            request,
            VerifierStatus.PASSED if passed else VerifierStatus.FAILED,
            code=f"context.{self._capability}.failed",
            message=f"Context Bundle {self._capability} did not pass",
            score=1.0 if passed else 0.0,
        )


def build_context_verifiers() -> tuple[ContextInvariantVerifier, ...]:
    return tuple(
        ContextInvariantVerifier(capability) for capability in REQUIRED_CONTEXT_CAPABILITIES
    )
