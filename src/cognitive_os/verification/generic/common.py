"""Descriptor helpers for generic verifiers."""

from cognitive_os.domain.common import JsonValue
from cognitive_os.domain.enums import RiskLevel
from cognitive_os.domain.problems import CriterionType, ProblemDomain
from cognitive_os.domain.verifiers import (
    VerificationSubjectType,
    VerifierCapability,
    VerifierDescriptor,
    VerifierDeterminism,
    VerifierKind,
)


def generic_descriptor(
    verifier_id: str,
    subject_type: VerificationSubjectType,
    criterion_type: CriterionType,
    *,
    configuration_schema: dict[str, JsonValue] | None = None,
) -> VerifierDescriptor:
    return VerifierDescriptor(
        verifier_id=verifier_id,
        version="1",
        display_name=verifier_id.replace(".", " ").title(),
        description=f"Deterministically evaluate {criterion_type.value} evidence.",
        kind=VerifierKind.GENERIC,
        capabilities=(
            VerifierCapability(
                capability_id=f"{verifier_id}.v1",
                subject_type=subject_type,
                problem_domains=tuple(ProblemDomain),
                criterion_types=(criterion_type,),
            ),
        ),
        determinism=VerifierDeterminism.DETERMINISTIC,
        risk_level=RiskLevel.LOW,
        default_timeout_seconds=10,
        maximum_input_bytes=1_048_576,
        configuration_schema=configuration_schema
        or {"type": "object", "additionalProperties": True},
    )
