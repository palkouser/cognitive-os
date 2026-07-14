"""Coding verifier descriptor factory."""

from cognitive_os.domain.enums import RiskLevel
from cognitive_os.domain.problems import CriterionType, ProblemDomain
from cognitive_os.domain.verifiers import (
    VerificationSubjectType,
    VerifierCapability,
    VerifierDescriptor,
    VerifierDeterminism,
    VerifierKind,
)


def coding_descriptor(verifier_id: str, *, sandbox: bool) -> VerifierDescriptor:
    return VerifierDescriptor(
        verifier_id=verifier_id,
        version="1",
        display_name=verifier_id.replace(".", " ").title(),
        description=(
            "Verify bounded Python workspace evidence without modifying the source workspace."
        ),
        kind=VerifierKind.CODING,
        capabilities=(
            VerifierCapability(
                capability_id=f"{verifier_id}.v1",
                subject_type=VerificationSubjectType.WORKSPACE
                if sandbox
                else VerificationSubjectType.STRUCTURED_VALUE,
                problem_domains=(ProblemDomain.CODING,),
                criterion_types=(CriterionType.DOMAIN_VERIFIER,),
                requires_sandbox=sandbox,
            ),
        ),
        determinism=VerifierDeterminism.DETERMINISTIC,
        requires_sandbox=sandbox,
        risk_level=RiskLevel.MEDIUM if sandbox else RiskLevel.LOW,
        default_timeout_seconds=300 if sandbox else 10,
        maximum_input_bytes=1_048_576,
        configuration_schema={"type": "object"},
    )
