"""Physical dimensionality verifier."""

from cognitive_os.domain.common import ErrorInfo
from cognitive_os.domain.enums import VerifierStatus
from cognitive_os.domain.verification import VerifierResult
from cognitive_os.domain.verifiers import VerificationRequest

from ..base import BaseVerifier
from .quantities import PhysicalQuantity, physics_descriptor, sealed_unit_registry


class DimensionVerifier(BaseVerifier):
    def __init__(self) -> None:
        super().__init__(physics_descriptor("physics.dimension"))

    async def verify(self, request: VerificationRequest) -> VerifierResult:
        try:
            actual = PhysicalQuantity.model_validate(request.subject.inline_value)
            expected = str(request.configuration["expected_unit"])
            registry = sealed_unit_registry()
            actual_dimension = registry.get_dimensionality(actual.unit)
            expected_dimension = registry.get_dimensionality(expected)
            passed = actual_dimension == expected_dimension
            return self.result(
                request,
                VerifierStatus.PASSED if passed else VerifierStatus.FAILED,
                code="physics.dimension.mismatch",
                message="physical dimensionality does not match",
                score=1 if passed else 0,
            )
        except (KeyError, TypeError, ValueError) as error:
            return self.result(
                request,
                VerifierStatus.ERROR,
                error=ErrorInfo(code="invalid_dimension", message=str(error)),
            )
