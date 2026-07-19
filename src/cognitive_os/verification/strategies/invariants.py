"""Fail-closed mandatory Strategy Engine invariant verifiers."""

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
from cognitive_os.verification.base import BaseVerifier

STRATEGY_CAPABILITIES = (
    "schema_conformance",
    "phase_structure",
    "graph_integrity",
    "edge_targets",
    "applicability_determinism",
    "skill_integrity",
    "capability_integrity",
    "fallback_acyclic",
    "budget_conformance",
    "plan_instantiation_conformance",
    "outcome_lineage",
    "statistics_reproducibility",
    "no_permission_expansion",
)

_SUBJECTS = {
    "schema_conformance": VerificationSubjectType.STRATEGY_REVISION,
    "phase_structure": VerificationSubjectType.STRATEGY_REVISION,
    "graph_integrity": VerificationSubjectType.STRATEGY_GRAPH,
    "edge_targets": VerificationSubjectType.STRATEGY_GRAPH,
    "applicability_determinism": VerificationSubjectType.STRATEGY_REVISION,
    "skill_integrity": VerificationSubjectType.STRATEGY_REVISION,
    "capability_integrity": VerificationSubjectType.STRATEGY_REVISION,
    "fallback_acyclic": VerificationSubjectType.STRATEGY_GRAPH,
    "budget_conformance": VerificationSubjectType.STRATEGY_PLAN,
    "plan_instantiation_conformance": VerificationSubjectType.STRATEGY_PLAN,
    "outcome_lineage": VerificationSubjectType.STRATEGY_OUTCOME,
    "statistics_reproducibility": VerificationSubjectType.STRATEGY_STATISTICS,
    "no_permission_expansion": VerificationSubjectType.STRATEGY_REVISION,
}


class StrategyInvariantVerifier(BaseVerifier):
    def __init__(self, capability: str) -> None:
        if capability not in STRATEGY_CAPABILITIES:
            raise ValueError(f"unknown strategy verifier capability: {capability}")
        verifier_id = f"strategy.{capability}"
        subject_type = _SUBJECTS[capability]
        super().__init__(
            VerifierDescriptor(
                verifier_id=verifier_id,
                version="1",
                display_name=verifier_id.replace(".", " ").replace("_", " ").title(),
                description=f"Deterministically verify strategy {capability}.",
                kind=VerifierKind.STRATEGY,
                capabilities=(
                    VerifierCapability(
                        capability_id=verifier_id,
                        subject_type=subject_type,
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
        self._subject_type = subject_type

    async def verify(self, request: VerificationRequest) -> VerifierResult:
        value = request.subject.inline_value
        passed = (
            request.subject.subject_type is self._subject_type
            and isinstance(value, dict)
            and value.get(self._capability) is True
        )
        return self.result(
            request,
            VerifierStatus.PASSED if passed else VerifierStatus.FAILED,
            code=f"strategy.{self._capability}.failed",
            message=f"Strategy {self._capability} did not pass",
            score=1.0 if passed else 0.0,
        )


def build_strategy_verifiers() -> tuple[StrategyInvariantVerifier, ...]:
    return tuple(StrategyInvariantVerifier(item) for item in STRATEGY_CAPABILITIES)
