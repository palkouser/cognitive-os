"""Explicit unit-conversion verifier."""

from decimal import Decimal

from cognitive_os.domain.common import ErrorInfo
from cognitive_os.domain.enums import VerifierStatus
from cognitive_os.domain.verification import VerifierResult
from cognitive_os.domain.verifiers import VerificationRequest

from ..base import BaseVerifier
from .quantities import PhysicalQuantity, physics_descriptor, sealed_unit_registry


class UnitConversionVerifier(BaseVerifier):
    def __init__(self) -> None:
        super().__init__(physics_descriptor("physics.unit_conversion"))

    async def verify(self, request: VerificationRequest) -> VerifierResult:
        try:
            actual = PhysicalQuantity.model_validate(request.subject.inline_value)
            target_unit = str(request.configuration["target_unit"])
            expected = Decimal(str(request.configuration["expected_magnitude"]))
            tolerance = Decimal(str(request.configuration.get("absolute_tolerance", "0")))
            registry = sealed_unit_registry()
            converted = (float(actual.magnitude) * registry.parse_units(actual.unit)).to(
                target_unit
            )
            passed = abs(Decimal(str(converted.magnitude)) - expected) <= tolerance
            return self.result(
                request,
                VerifierStatus.PASSED if passed else VerifierStatus.FAILED,
                code="physics.unit_conversion.mismatch",
                message="unit conversion result does not match",
                score=1 if passed else 0,
            )
        except (KeyError, TypeError, ValueError) as error:
            return self.result(
                request,
                VerifierStatus.ERROR,
                error=ErrorInfo(code="invalid_unit_conversion", message=str(error)),
            )
