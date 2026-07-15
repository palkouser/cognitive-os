"""Registered fail-closed verifiers for semantic promotion and Wiki integrity."""

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

from ..base import BaseVerifier

SEMANTIC_CAPABILITIES = (
    "source_integrity",
    "source_grounding",
    "observation_schema",
    "predicate_schema",
    "valid_interval",
    "revision_continuity",
    "relation_integrity",
    "supersession_acyclic",
    "evidence_minimum",
    "evidence_integrity",
    "critical_contradiction",
    "belief_policy",
    "wiki_lineage",
    "wiki_content_hash",
    "wiki_snapshot",
    "wiki_sensitivity",
)


class SemanticInvariantVerifier(BaseVerifier):
    def __init__(self, capability: str) -> None:
        if capability not in SEMANTIC_CAPABILITIES:
            raise ValueError(f"unknown semantic verifier capability: {capability}")
        verifier_id = f"semantic.{capability}"
        super().__init__(
            VerifierDescriptor(
                verifier_id=verifier_id,
                version="1",
                display_name=verifier_id.replace(".", " ").replace("_", " ").title(),
                description=f"Deterministically verify semantic {capability} evidence.",
                kind=VerifierKind.SEMANTIC,
                capabilities=(
                    VerifierCapability(
                        capability_id=verifier_id,
                        subject_type=VerificationSubjectType.SEMANTIC_SNAPSHOT,
                        problem_domains=(ProblemDomain.SEMANTIC,),
                        criterion_types=(CriterionType.DOMAIN_VERIFIER,),
                    ),
                ),
                determinism=VerifierDeterminism.DETERMINISTIC,
                risk_level=RiskLevel.LOW,
                default_timeout_seconds=10,
                maximum_input_bytes=262_144,
                configuration_schema={"type": "object", "additionalProperties": False},
            )
        )
        self._capability = capability

    async def verify(self, request: VerificationRequest) -> VerifierResult:
        value = request.subject.inline_value
        passed = (
            request.subject.subject_type is VerificationSubjectType.SEMANTIC_SNAPSHOT
            and isinstance(value, dict)
            and value.get(self._capability) is True
        )
        return self.result(
            request,
            VerifierStatus.PASSED if passed else VerifierStatus.FAILED,
            code=f"semantic.{self._capability}.failed",
            message=f"semantic {self._capability} evidence did not pass",
            score=1.0 if passed else 0.0,
        )
