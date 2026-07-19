"""Fail-closed invariant verifiers for procedural skill promotion."""

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

SKILL_CAPABILITIES = (
    "package_integrity",
    "package_schema",
    "precondition_determinism",
    "tool_requirements",
    "verifier_requirements",
    "path_safety",
    "execution_conformance",
    "output_schema",
    "regression_suite",
    "no_permission_expansion",
)

_SUBJECTS = {
    "package_integrity": VerificationSubjectType.SKILL_PACKAGE,
    "package_schema": VerificationSubjectType.SKILL_PACKAGE,
    "precondition_determinism": VerificationSubjectType.SKILL_REVISION,
    "tool_requirements": VerificationSubjectType.SKILL_REVISION,
    "verifier_requirements": VerificationSubjectType.SKILL_REVISION,
    "path_safety": VerificationSubjectType.SKILL_PACKAGE,
    "execution_conformance": VerificationSubjectType.SKILL_EXECUTION,
    "output_schema": VerificationSubjectType.SKILL_EXECUTION,
    "regression_suite": VerificationSubjectType.SKILL_REGRESSION,
    "no_permission_expansion": VerificationSubjectType.SKILL_REVISION,
}


class SkillInvariantVerifier(BaseVerifier):
    def __init__(self, capability: str) -> None:
        if capability not in SKILL_CAPABILITIES:
            raise ValueError(f"unknown skill verifier capability: {capability}")
        verifier_id = f"skill.{capability}"
        subject_type = _SUBJECTS[capability]
        super().__init__(
            VerifierDescriptor(
                verifier_id=verifier_id,
                version="1",
                display_name=verifier_id.replace(".", " ").replace("_", " ").title(),
                description=f"Deterministically verify skill {capability}.",
                kind=VerifierKind.SKILL,
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
            code=f"skill.{self._capability}.failed",
            message=f"Skill {self._capability} did not pass",
            score=1.0 if passed else 0.0,
        )


def build_skill_verifiers() -> tuple[SkillInvariantVerifier, ...]:
    return tuple(SkillInvariantVerifier(item) for item in SKILL_CAPABILITIES)
