"""Finite physical quantity contract and comparison verifier."""

from __future__ import annotations

import re
from decimal import Decimal
from typing import Any

from pydantic import Field, field_validator

from cognitive_os.domain.base import ImmutableContractModel
from cognitive_os.domain.common import ErrorInfo, NonEmptyStr
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

SAFE_UNIT = re.compile(r"^[A-Za-z0-9_/*^ .-]{1,128}$")


class PhysicalQuantity(ImmutableContractModel):
    magnitude: Decimal
    unit: NonEmptyStr
    uncertainty: Decimal | None = Field(default=None, ge=0)

    @field_validator("magnitude")
    @classmethod
    def finite_magnitude(cls, value: Decimal) -> Decimal:
        if not value.is_finite():
            raise ValueError("physical quantity magnitude must be finite")
        return value

    @field_validator("unit")
    @classmethod
    def safe_unit(cls, value: str) -> str:
        if not SAFE_UNIT.fullmatch(value) or ".." in value or value.startswith("/"):
            raise ValueError("unit expression is not allowed")
        return value


_REGISTRY: Any | None = None


def sealed_unit_registry() -> Any:
    global _REGISTRY
    if _REGISTRY is None:
        import pint

        _REGISTRY = pint.UnitRegistry(autoconvert_offset_to_baseunit=True)
    return _REGISTRY


def physics_descriptor(verifier_id: str) -> VerifierDescriptor:
    return VerifierDescriptor(
        verifier_id=verifier_id,
        version="1",
        display_name=verifier_id.replace(".", " ").title(),
        description="Verify finite physical quantities with the sealed Pint registry.",
        kind=VerifierKind.PHYSICS,
        capabilities=(
            VerifierCapability(
                capability_id=f"{verifier_id}.v1",
                subject_type=VerificationSubjectType.PHYSICAL_QUANTITY,
                problem_domains=(ProblemDomain.PHYSICS,),
                criterion_types=(CriterionType.DOMAIN_VERIFIER,),
            ),
        ),
        determinism=VerifierDeterminism.DETERMINISTIC,
        risk_level=RiskLevel.LOW,
        default_timeout_seconds=10,
        maximum_input_bytes=65_536,
        configuration_schema={"type": "object"},
    )


class QuantityVerifier(BaseVerifier):
    def __init__(self) -> None:
        super().__init__(physics_descriptor("physics.quantity"))

    async def verify(self, request: VerificationRequest) -> VerifierResult:
        try:
            if any(
                key in request.configuration
                for key in ("definition_file", "custom_units", "unit_registry")
            ):
                raise ValueError("custom unit definitions are forbidden")
            actual = PhysicalQuantity.model_validate(request.subject.inline_value)
            expected = PhysicalQuantity.model_validate(request.configuration["expected"])
            registry = sealed_unit_registry()
            converted = (float(actual.magnitude) * registry.parse_units(actual.unit)).to(
                expected.unit
            )
            actual_value = Decimal(str(converted.magnitude))
            absolute = Decimal(str(request.configuration.get("absolute_tolerance", "0")))
            relative = Decimal(str(request.configuration.get("relative_tolerance", "0")))
            passed = abs(actual_value - expected.magnitude) <= max(
                absolute, relative * abs(expected.magnitude)
            )
            return self.result(
                request,
                VerifierStatus.PASSED if passed else VerifierStatus.FAILED,
                code="physics.quantity.mismatch",
                message="physical quantities differ outside tolerance",
                score=1 if passed else 0,
            )
        except Exception as error:
            return self.result(
                request,
                VerifierStatus.ERROR,
                error=ErrorInfo(code="invalid_physical_quantity", message=str(error)),
            )
