from datetime import UTC, datetime
from importlib.util import find_spec
from uuid import uuid4

import pytest

from cognitive_os.domain.enums import VerifierStatus
from cognitive_os.domain.verifiers import (
    VerificationRequest,
    VerificationSubject,
    VerificationSubjectType,
)
from cognitive_os.verification.generic import (
    ExactValueVerifier,
    JsonSchemaVerifier,
    PlanConsistencyVerifier,
)
from cognitive_os.verification.logic import (
    ContradictionVerifier,
    ImplicationVerifier,
    SatisfiabilityVerifier,
)
from cognitive_os.verification.mathematics import NumericVerifier, SymbolicEquivalenceVerifier
from cognitive_os.verification.mathematics.parsing import UnsafeExpressionError, parse_expression
from cognitive_os.verification.physics import (
    DimensionVerifier,
    QuantityVerifier,
    UnitConversionVerifier,
)


def request(
    verifier_id: str, subject_type: VerificationSubjectType, value, configuration=None
) -> VerificationRequest:
    return VerificationRequest(
        verification_id=uuid4(),
        task_run_id=uuid4(),
        criterion_id=uuid4(),
        verifier_id=verifier_id,
        verifier_version="1",
        subject=VerificationSubject(subject_type=subject_type, inline_value=value),
        configuration=configuration or {},
        requested_at=datetime.now(UTC),
        correlation_id=uuid4(),
    )


@pytest.mark.asyncio
async def test_generic_exact_schema_and_plan_verifiers() -> None:
    exact = await ExactValueVerifier().verify(
        request(
            "generic.exact",
            VerificationSubjectType.STRUCTURED_VALUE,
            " Value ",
            {"expected": "value", "strip_whitespace": True, "case_sensitive": False},
        )
    )
    schema = await JsonSchemaVerifier().verify(
        request(
            "generic.json_schema",
            VerificationSubjectType.STRUCTURED_VALUE,
            {"answer": 42},
            {"schema": {"type": "object", "required": ["answer"]}},
        )
    )
    plan = await PlanConsistencyVerifier().verify(
        request(
            "generic.plan_consistency",
            VerificationSubjectType.EXECUTION_PLAN,
            {
                "required_steps": ["a"],
                "completed_steps": ["a"],
                "failed_steps": [],
                "running_steps": [],
            },
        )
    )
    assert (exact.status, schema.status, plan.status) == (VerifierStatus.PASSED,) * 3


@pytest.mark.parametrize(
    "source", ["__import__('os')", "x.__class__", "lambda: 1", "[x for x in y]", "2 ** 1001"]
)
def test_math_parser_rejects_unsafe_expressions(source: str) -> None:
    with pytest.raises(UnsafeExpressionError):
        parse_expression(source)


@pytest.mark.skipif(find_spec("sympy") is None, reason="verification-math extra is absent")
@pytest.mark.asyncio
async def test_numeric_and_symbolic_verifiers() -> None:
    numeric = await NumericVerifier().verify(
        request(
            "mathematics.numeric",
            VerificationSubjectType.MATHEMATICAL_EXPRESSION,
            "1.001",
            {"expected": "1", "absolute_tolerance": "0.01"},
        )
    )
    symbolic = await SymbolicEquivalenceVerifier().verify(
        request(
            "mathematics.symbolic_equivalence",
            VerificationSubjectType.MATHEMATICAL_EXPRESSION,
            "(x + 1) ** 2",
            {"expected": "x ** 2 + 2*x + 1"},
        )
    )
    unsafe = await SymbolicEquivalenceVerifier().verify(
        request(
            "mathematics.symbolic_equivalence",
            VerificationSubjectType.MATHEMATICAL_EXPRESSION,
            "__import__('os')",
            {"expected": "0"},
        )
    )
    assert numeric.status is VerifierStatus.PASSED
    assert symbolic.status is VerifierStatus.PASSED
    assert unsafe.status is VerifierStatus.ERROR


def variable(name: str, sort: str = "bool") -> dict[str, object]:
    return {"operator": "variable", "sort": sort, "name": name}


@pytest.mark.skipif(find_spec("z3") is None, reason="verification-logic extra is absent")
@pytest.mark.asyncio
async def test_typed_logic_verifiers_and_raw_smt_rejection() -> None:
    satisfiable = await SatisfiabilityVerifier().verify(
        request("logic.satisfiable", VerificationSubjectType.LOGICAL_PROBLEM, variable("a"))
    )
    contradiction = await ContradictionVerifier().verify(
        request(
            "logic.contradiction",
            VerificationSubjectType.LOGICAL_PROBLEM,
            [
                {
                    "operator": "and",
                    "sort": "bool",
                    "arguments": [
                        variable("a"),
                        {"operator": "not", "sort": "bool", "arguments": [variable("a")]},
                    ],
                }
            ],
        )
    )
    implication = await ImplicationVerifier().verify(
        request(
            "logic.implication",
            VerificationSubjectType.LOGICAL_PROBLEM,
            {"premises": [variable("a")], "conclusion": variable("a")},
        )
    )
    raw = await SatisfiabilityVerifier().verify(
        request("logic.satisfiable", VerificationSubjectType.LOGICAL_PROBLEM, "(assert true)")
    )
    assert satisfiable.status is VerifierStatus.PASSED
    assert contradiction.status is VerifierStatus.PASSED
    assert implication.status is VerifierStatus.PASSED
    assert raw.status is VerifierStatus.ERROR


@pytest.mark.skipif(find_spec("pint") is None, reason="verification-physics extra is absent")
@pytest.mark.asyncio
async def test_physics_dimension_quantity_and_conversion() -> None:
    dimension = await DimensionVerifier().verify(
        request(
            "physics.dimension",
            VerificationSubjectType.PHYSICAL_QUANTITY,
            {"magnitude": "1", "unit": "newton"},
            {"expected_unit": "kilogram * meter / second ** 2"},
        )
    )
    quantity = await QuantityVerifier().verify(
        request(
            "physics.quantity",
            VerificationSubjectType.PHYSICAL_QUANTITY,
            {"magnitude": "1", "unit": "meter"},
            {"expected": {"magnitude": "100", "unit": "centimeter"}},
        )
    )
    conversion = await UnitConversionVerifier().verify(
        request(
            "physics.unit_conversion",
            VerificationSubjectType.PHYSICAL_QUANTITY,
            {"magnitude": "2", "unit": "meter"},
            {"target_unit": "centimeter", "expected_magnitude": "200"},
        )
    )
    assert (dimension.status, quantity.status, conversion.status) == (VerifierStatus.PASSED,) * 3


@pytest.mark.skipif(find_spec("pint") is None, reason="verification-physics extra is absent")
@pytest.mark.asyncio
async def test_physics_rejects_unknown_nonfinite_and_custom_units() -> None:
    unknown = await QuantityVerifier().verify(
        request(
            "physics.quantity",
            VerificationSubjectType.PHYSICAL_QUANTITY,
            {"magnitude": "1", "unit": "not_a_unit"},
            {"expected": {"magnitude": "1", "unit": "meter"}},
        )
    )
    custom = await QuantityVerifier().verify(
        request(
            "physics.quantity",
            VerificationSubjectType.PHYSICAL_QUANTITY,
            {"magnitude": "1", "unit": "meter"},
            {"expected": {"magnitude": "1", "unit": "meter"}, "definition_file": "/tmp/units"},
        )
    )
    nonfinite = await QuantityVerifier().verify(
        request(
            "physics.quantity",
            VerificationSubjectType.PHYSICAL_QUANTITY,
            {"magnitude": "NaN", "unit": "meter"},
            {"expected": {"magnitude": "1", "unit": "meter"}},
        )
    )
    assert (unknown.status, custom.status, nonfinite.status) == (VerifierStatus.ERROR,) * 3
