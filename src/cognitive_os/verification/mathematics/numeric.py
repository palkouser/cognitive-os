"""Finite numeric tolerance verifier."""

from decimal import Decimal, InvalidOperation

from cognitive_os.domain.common import ErrorInfo
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


class NumericVerifier(BaseVerifier):
    def __init__(self) -> None:
        super().__init__(
            VerifierDescriptor(
                verifier_id="mathematics.numeric",
                version="1",
                display_name="Numeric tolerance verifier",
                description=(
                    "Compare finite numbers using explicit absolute and relative tolerance."
                ),
                kind=VerifierKind.MATHEMATICS,
                capabilities=(
                    VerifierCapability(
                        capability_id="mathematics.numeric.v1",
                        subject_type=VerificationSubjectType.MATHEMATICAL_EXPRESSION,
                        problem_domains=(ProblemDomain.MATHEMATICS,),
                        criterion_types=(CriterionType.DOMAIN_VERIFIER,),
                    ),
                ),
                determinism=VerifierDeterminism.DETERMINISTIC,
                risk_level=RiskLevel.LOW,
                default_timeout_seconds=5,
                maximum_input_bytes=65_536,
                configuration_schema={"type": "object"},
            )
        )

    async def verify(self, request: VerificationRequest) -> VerifierResult:
        try:
            actual = Decimal(str(request.subject.inline_value))
            expected = Decimal(str(request.configuration["expected"]))
            absolute = Decimal(str(request.configuration.get("absolute_tolerance", "0")))
            relative = Decimal(str(request.configuration.get("relative_tolerance", "0")))
            if not all(item.is_finite() for item in (actual, expected, absolute, relative)):
                raise InvalidOperation
            passed = abs(actual - expected) <= max(absolute, relative * abs(expected))
        except (InvalidOperation, KeyError, ValueError):
            return self.result(
                request,
                VerifierStatus.ERROR,
                error=ErrorInfo(
                    code="invalid_numeric_input",
                    message="numeric input must be finite and complete",
                ),
            )
        return self.result(
            request,
            VerifierStatus.PASSED if passed else VerifierStatus.FAILED,
            code="mathematics.numeric.outside_tolerance",
            message="numeric result is outside the configured tolerance",
            score=1 if passed else 0,
        )
