"""Property-based checks for the dependency-free kernels.

Bounded, deterministic profiles: every strategy is size-limited so no generated
case can exceed the declared resource budget, and failures shrink to minimal
regression fixtures.
"""

from fractions import Fraction

import pytest
from hypothesis import HealthCheck, assume, given, settings
from hypothesis import strategies as st

from cognitive_os.domains import kernels
from cognitive_os.verification.logic.ast import LogicExpression

CI_PROFILE = settings(
    max_examples=100,
    deadline=None,
    derandomize=True,
    suppress_health_check=[HealthCheck.too_slow],
)

# Bounded so no generated case can exceed the declared ceilings.
integers = st.integers(min_value=-10_000, max_value=10_000)
nonzero = integers.filter(lambda value: value != 0)
fractions = st.builds(Fraction, integers, nonzero)
scalable_units = st.sampled_from(["m", "km", "cm", "mm", "s", "min", "h", "g", "kg"])
variables = st.sampled_from(["p", "q", "r"])


# ------------------------------------------------------------------ arithmetic


@CI_PROFILE
@given(integers, integers)
def test_long_multiplication_trace_sums_to_the_product(left: int, right: int) -> None:
    """The digit-wise route the checker uses must always agree with the product."""
    total = sum(
        abs(left) * int(digit) * 10**position
        for position, digit in enumerate(reversed(str(abs(right))))
    )
    expected = -total if (left < 0) != (right < 0) else total
    assert expected == left * right
    assert kernels.long_multiplication_trace(left, right)


@CI_PROFILE
@given(integers, nonzero)
def test_long_division_reconstructs_the_dividend(dividend: int, divisor: int) -> None:
    quotient, remainder = divmod(dividend, divisor)
    assert divisor * quotient + remainder == dividend
    assert kernels.long_division_trace(dividend, divisor)


@CI_PROFILE
@given(fractions, fractions)
def test_exact_addition_is_commutative_and_never_lossy(a: Fraction, b: Fraction) -> None:
    from cognitive_os.verification.mathematics.expression_ast import BinaryExpression, Rational

    forward = kernels.evaluate_exact(
        BinaryExpression("add", Rational(a), Rational(b)), maximum_integer_digits=4096
    )
    reverse = kernels.evaluate_exact(
        BinaryExpression("add", Rational(b), Rational(a)), maximum_integer_digits=4096
    )
    assert forward == reverse == a + b


@CI_PROFILE
@given(fractions)
def test_division_by_zero_always_raises(value: Fraction) -> None:
    from cognitive_os.verification.mathematics.expression_ast import (
        BinaryExpression,
        Integer,
        Rational,
    )

    with pytest.raises(kernels.InexactError):
        kernels.evaluate_exact(BinaryExpression("divide", Rational(value), Integer(0)))


@CI_PROFILE
@given(st.integers(min_value=0, max_value=10_000))
def test_exact_square_root_is_exact_only_for_perfect_squares(value: int) -> None:
    from math import isqrt

    from cognitive_os.verification.mathematics.expression_ast import FunctionExpression, Integer

    expression = FunctionExpression("sqrt", Integer(value))
    if isqrt(value) ** 2 == value:
        assert kernels.evaluate_exact(expression) == Fraction(isqrt(value))
    else:
        with pytest.raises(kernels.InexactError):
            kernels.evaluate_exact(expression)


# ----------------------------------------------------------------------- units


@CI_PROFILE
@given(fractions, scalable_units, scalable_units)
def test_conversion_round_trips_or_refuses(magnitude: Fraction, source: str, target: str) -> None:
    """A conversion either round-trips exactly or is refused as incompatible."""
    try:
        converted = kernels.convert(magnitude, source, target)
    except kernels.UnitError:
        assert kernels.dimension_of(source) != kernels.dimension_of(target)
        return
    assert kernels.convert(converted, target, source) == magnitude


@CI_PROFILE
@given(scalable_units, scalable_units)
def test_compatible_units_are_exactly_the_equal_dimension_pairs(source: str, target: str) -> None:
    compatible = kernels.dimension_of(source) == kernels.dimension_of(target)
    try:
        kernels.convert(Fraction(1), source, target)
    except kernels.UnitError:
        assert not compatible
    else:
        assert compatible


@CI_PROFILE
@given(fractions)
def test_offset_temperature_conversion_round_trips(magnitude: Fraction) -> None:
    for source, target in (("degC", "K"), ("degC", "degF"), ("degF", "K")):
        converted = kernels.convert(magnitude, source, target)
        assert kernels.convert(converted, target, source) == magnitude


# ----------------------------------------------------------------------- logic


def _boolean(draw: st.DrawFn, depth: int = 0) -> dict[str, object]:
    """Bounded propositional formula; depth is capped so ceilings are respected."""
    if depth >= 3 or draw(st.booleans()):
        return {"operator": "variable", "sort": "bool", "name": draw(variables)}
    operator = draw(st.sampled_from(["not", "and", "or", "xor", "implies", "equals"]))
    arity = 1 if operator == "not" else 2
    return {
        "operator": operator,
        "sort": "bool",
        "arguments": [_boolean(draw, depth + 1) for _ in range(arity)],
    }


formulas = st.composite(lambda draw: _boolean(draw))()


@CI_PROFILE
@given(formulas)
def test_classification_agrees_with_row_by_row_evaluation(payload: dict[str, object]) -> None:
    expression = LogicExpression.model_validate(payload)
    rows = kernels.truth_table(expression)
    outputs = [value for _, value in rows]
    expected = (
        "tautology" if all(outputs) else "contradiction" if not any(outputs) else "contingent"
    )
    assert kernels.classify(expression) == expected


@CI_PROFILE
@given(formulas)
def test_counterexample_and_model_are_witnesses(payload: dict[str, object]) -> None:
    expression = LogicExpression.model_validate(payload)
    witness = kernels.counterexample(expression)
    if witness is not None:
        assert kernels.evaluate_logic(expression, witness) is False
    model = kernels.satisfying_assignment(expression)
    if model is not None:
        assert kernels.evaluate_logic(expression, model) is True
    # Exactly one of the two may be absent, never both.
    assert witness is not None or model is not None


@CI_PROFILE
@given(formulas)
def test_negation_inverts_every_row(payload: dict[str, object]) -> None:
    expression = LogicExpression.model_validate(payload)
    negated = LogicExpression.model_validate(
        {"operator": "not", "sort": "bool", "arguments": [payload]}
    )
    for assignment, value in kernels.truth_table(expression):
        assert kernels.evaluate_logic(negated, assignment) is (not value)


@CI_PROFILE
@given(formulas)
def test_enumeration_stays_inside_the_row_ceiling(payload: dict[str, object]) -> None:
    expression = LogicExpression.model_validate(payload)
    variable_count = len(kernels.collect_variables(expression))
    assume(variable_count > 0)
    assert len(kernels.truth_table(expression)) == 2**variable_count
    with pytest.raises(kernels.BudgetExceededError):
        kernels.truth_table(expression, maximum_rows=2**variable_count - 1)
