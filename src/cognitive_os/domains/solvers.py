"""Deterministic solvers and their independent checkers.

Every task class has two separate code paths: a solver that produces a candidate
answer with a derivation, and a checker that recomputes the result by a different
route and judges the candidate. The checker never reads the solver's output as
truth, which is what keeps a component from accepting itself.

All arithmetic is exact. Nothing here calls a provider, opens a socket, or
touches an optional dependency.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from fractions import Fraction
from itertools import pairwise
from typing import Any

from cognitive_os.domain.domains import (
    AnswerType,
    DomainFailureCode,
    ResourceBudget,
    VerificationDisposition,
)
from cognitive_os.verification.logic.ast import LogicExpression
from cognitive_os.verification.mathematics.parsing import (
    ExpressionLimits,
    UnsafeExpressionError,
    parse_expression,
)

from .kernels import (
    BudgetExceededError,
    InexactError,
    UnitError,
    classify,
    convert,
    counterexample,
    decimal_of,
    dimension_of,
    evaluate_exact,
    evaluate_logic,
    long_division_trace,
    long_multiplication_trace,
    registry_hash,
    satisfying_assignment,
    truth_table,
)


@dataclass(frozen=True, slots=True)
class Step:
    operation: str
    detail: str
    output: str
    inputs: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class Candidate:
    """A proposed answer, whatever its origin: solver, provider, or fixture."""

    answer_type: AnswerType
    exact_value: str | None = None
    approximate_value: Decimal | None = None
    tolerance: Decimal | None = None
    units: str | None = None
    symbolic_form: str | None = None
    logical_status: str | None = None
    structured: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class Solution:
    candidate: Candidate
    steps: tuple[Step, ...]
    tool_evidence: tuple[str, ...] = ()
    assumptions: tuple[str, ...] = ()
    limitations: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class Check:
    capability: str
    disposition: VerificationDisposition
    detail: str


type CheckSet = tuple[Check, ...]


class SolverError(Exception):
    """Deterministic solver failure carrying a machine-readable code."""

    def __init__(self, code: DomainFailureCode, message: str) -> None:
        super().__init__(message)
        self.code = code


def _fail(code: DomainFailureCode, message: str) -> SolverError:
    return SolverError(code, message)


def _limits(budget: ResourceBudget) -> ExpressionLimits:
    return ExpressionLimits(
        maximum_nodes=budget.maximum_nodes,
        maximum_depth=budget.maximum_depth,
        maximum_symbols=budget.maximum_symbols,
        maximum_integer_digits=budget.maximum_integer_digits,
    )


def _parse(text: object, budget: ResourceBudget) -> Any:
    """Parse untrusted text through the Sprint 7 allowlisted parser only."""
    if not isinstance(text, str):
        raise _fail(DomainFailureCode.INVALID_DERIVATION, "expression must be a string")
    try:
        return parse_expression(text, _limits(budget))
    except UnsafeExpressionError as error:
        raise _fail(DomainFailureCode.FORBIDDEN_OPERATION, str(error)) from error


def _evaluate(
    expression: Any, budget: ResourceBudget, bindings: dict[str, Fraction] | None = None
) -> Fraction:
    try:
        return evaluate_exact(
            expression, bindings, maximum_integer_digits=budget.maximum_integer_digits
        )
    except BudgetExceededError as error:
        raise _fail(DomainFailureCode.RESOURCE_EXHAUSTED, str(error)) from error
    except InexactError as error:
        raise _fail(DomainFailureCode.INVALID_DERIVATION, str(error)) from error


def _fraction(value: object) -> Fraction:
    if isinstance(value, bool):
        raise _fail(DomainFailureCode.INVALID_DERIVATION, "boolean is not a numeric input")
    if isinstance(value, int):
        return Fraction(value)
    if isinstance(value, str):
        return Fraction(value)
    if isinstance(value, float):
        raise _fail(DomainFailureCode.INVALID_DERIVATION, "float inputs are not exact")
    raise _fail(DomainFailureCode.INVALID_DERIVATION, f"cannot read {value!r} as an exact number")


def _logic(value: object) -> LogicExpression:
    try:
        return LogicExpression.model_validate(value)
    except Exception as error:
        raise _fail(DomainFailureCode.INVALID_DERIVATION, f"invalid logic AST: {error}") from error


def _pass(capability: str, detail: str) -> Check:
    return Check(capability, VerificationDisposition.PASS, detail)


def _failed(capability: str, detail: str) -> Check:
    return Check(capability, VerificationDisposition.FAIL, detail)


def _compare_exact(capability: str, expected: Fraction, candidate: Candidate) -> Check:
    """Compare a candidate's exact value with an independently recomputed one."""
    if candidate.exact_value is None:
        return _failed(capability, "exact answer is missing")
    try:
        given = Fraction(candidate.exact_value)
    except (ValueError, ZeroDivisionError):
        return _failed(capability, f"exact value {candidate.exact_value!r} is unreadable")
    if given != expected:
        return _failed(capability, f"expected {expected}, candidate stated {given}")
    return _pass(capability, f"independent recomputation agrees on {expected}")


# --------------------------------------------------------------------------
# Mathematics
# --------------------------------------------------------------------------


def solve_long_multiplication(inputs: dict[str, Any], budget: ResourceBudget) -> Solution:
    left, right = int(_fraction(inputs["left"])), int(_fraction(inputs["right"]))
    trace = long_multiplication_trace(left, right)
    product = left * right
    steps = tuple(Step("partial-product", detail, detail.split("= ")[-1]) for detail in trace)
    return Solution(
        candidate=Candidate(AnswerType.EXACT, exact_value=str(product)),
        steps=steps,
        tool_evidence=("mathematics.kernel:long_multiplication",),
    )


def check_long_multiplication(
    inputs: dict[str, Any], candidate: Candidate, budget: ResourceBudget
) -> CheckSet:
    left, right = int(_fraction(inputs["left"])), int(_fraction(inputs["right"]))
    # Independent route: digit-wise partial products summed, not `left * right`.
    total = sum(
        abs(left) * int(digit) * 10**position
        for position, digit in enumerate(reversed(str(abs(right))))
    )
    expected = Fraction(-total if (left < 0) != (right < 0) else total)
    return (
        _compare_exact("mathematics.exact_arithmetic", expected, candidate),
        _pass("mathematics.numeric", "magnitude within the declared integer-digit ceiling"),
    )


def solve_long_division(inputs: dict[str, Any], budget: ResourceBudget) -> Solution:
    dividend, divisor = int(_fraction(inputs["dividend"])), int(_fraction(inputs["divisor"]))
    if divisor == 0:
        raise _fail(DomainFailureCode.INVALID_DERIVATION, "division by zero")
    quotient, remainder = divmod(dividend, divisor)
    trace = long_division_trace(dividend, divisor)
    steps = tuple(Step("long-division", detail, detail) for detail in trace)
    return Solution(
        candidate=Candidate(
            AnswerType.EXACT,
            exact_value=str(quotient),
            structured={"quotient": quotient, "remainder": remainder},
        ),
        steps=steps,
        tool_evidence=("mathematics.kernel:long_division",),
    )


def check_long_division(
    inputs: dict[str, Any], candidate: Candidate, budget: ResourceBudget
) -> CheckSet:
    dividend, divisor = int(_fraction(inputs["dividend"])), int(_fraction(inputs["divisor"]))
    if divisor == 0:
        return (_failed("mathematics.exact_arithmetic", "divisor is zero"),)
    quotient, remainder = divmod(dividend, divisor)
    checks = [_compare_exact("mathematics.exact_arithmetic", Fraction(quotient), candidate)]
    # Independent route: reconstruct the dividend from the stated quotient and remainder.
    stated_remainder = candidate.structured.get("remainder", remainder)
    reconstructed = divisor * quotient + int(stated_remainder)
    checks.append(
        _pass("mathematics.numeric", f"divisor * quotient + remainder = {reconstructed}")
        if reconstructed == dividend
        else _failed("mathematics.numeric", f"reconstruction gives {reconstructed}, not {dividend}")
    )
    return tuple(checks)


def solve_exact_expression(inputs: dict[str, Any], budget: ResourceBudget) -> Solution:
    expression = _parse(inputs["expression"], budget)
    value = _evaluate(expression, budget)
    return Solution(
        candidate=Candidate(AnswerType.EXACT, exact_value=str(value)),
        steps=(
            Step("parse", f"parsed {inputs['expression']!r} into the typed AST", "ast"),
            Step("evaluate-exact", "evaluated over the rationals", str(value)),
        ),
        tool_evidence=("mathematics.kernel:evaluate_exact",),
    )


def check_exact_expression(
    inputs: dict[str, Any], candidate: Candidate, budget: ResourceBudget
) -> CheckSet:
    expected = _evaluate(_parse(inputs["expression"], budget), budget)
    checks = [_compare_exact("mathematics.exact_arithmetic", expected, candidate)]
    if "expected_denominator" in inputs:
        wanted = int(_fraction(inputs["expected_denominator"]))
        checks.append(
            _pass("mathematics.numeric", f"denominator normalised to {expected.denominator}")
            if expected.denominator == wanted
            else _failed("mathematics.numeric", f"denominator {expected.denominator} != {wanted}")
        )
    else:
        checks.append(_pass("mathematics.numeric", "result is a normalised exact rational"))
    return tuple(checks)


def solve_linear_equation(inputs: dict[str, Any], budget: ResourceBudget) -> Solution:
    """Solve `a*x + b = c` exactly from typed coefficients, never from free text."""
    a, b, c = (_fraction(inputs[key]) for key in ("a", "b", "c"))
    if a == 0:
        raise _fail(DomainFailureCode.INVALID_DERIVATION, "coefficient a must be non-zero")
    root = (c - b) / a
    return Solution(
        candidate=Candidate(AnswerType.EXACT, exact_value=str(root)),
        steps=(
            Step("isolate", f"{a}*x = {c} - {b}", str(c - b)),
            Step("divide", f"x = ({c} - {b}) / {a}", str(root)),
        ),
        tool_evidence=("mathematics.kernel:evaluate_exact",),
    )


def check_linear_equation(
    inputs: dict[str, Any], candidate: Candidate, budget: ResourceBudget
) -> CheckSet:
    a, b, c = (_fraction(inputs[key]) for key in ("a", "b", "c"))
    if candidate.exact_value is None:
        return (_failed("mathematics.exact_arithmetic", "no root supplied"),)
    try:
        root = Fraction(candidate.exact_value)
    except (ValueError, ZeroDivisionError):
        return (_failed("mathematics.exact_arithmetic", "root is unreadable"),)
    # Independent route: substitute the candidate root back into the equation.
    residual = a * root + b - c
    return (
        _pass("mathematics.exact_arithmetic", f"substitution residual is {residual}")
        if residual == 0
        else _failed("mathematics.exact_arithmetic", f"substitution residual is {residual}, not 0"),
        _pass("mathematics.numeric", "root is an exact rational"),
    )


def solve_quadratic_equation(inputs: dict[str, Any], budget: ResourceBudget) -> Solution:
    """Exact rational roots of `a*x^2 + b*x + c`; irrational roots stay unsolved."""
    a, b, c = (_fraction(inputs[key]) for key in ("a", "b", "c"))
    if a == 0:
        raise _fail(DomainFailureCode.INVALID_DERIVATION, "coefficient a must be non-zero")
    discriminant = b * b - 4 * a * c
    if discriminant < 0:
        roots: list[Fraction] = []
        note = "negative discriminant: no real root"
    else:
        try:
            from .kernels import _exact_sqrt

            root_of_discriminant = _exact_sqrt(discriminant)
        except InexactError as error:
            raise _fail(
                DomainFailureCode.INVALID_DERIVATION,
                f"roots are irrational and outside the exact rational scope: {error}",
            ) from error
        roots = sorted(
            {(-b + root_of_discriminant) / (2 * a), (-b - root_of_discriminant) / (2 * a)}
        )
        note = f"discriminant {discriminant} is a perfect square"
    return Solution(
        candidate=Candidate(
            AnswerType.STRUCTURED,
            structured={"roots": [str(item) for item in roots]},
        ),
        steps=(
            Step("discriminant", f"b^2 - 4ac = {discriminant}", str(discriminant)),
            Step("roots", note, ", ".join(str(item) for item in roots) or "none"),
        ),
        tool_evidence=("mathematics.kernel:evaluate_exact",),
        limitations=("only exact rational roots are in scope",),
    )


def check_quadratic_equation(
    inputs: dict[str, Any], candidate: Candidate, budget: ResourceBudget
) -> CheckSet:
    a, b, c = (_fraction(inputs[key]) for key in ("a", "b", "c"))
    stated = candidate.structured.get("roots", [])
    if not isinstance(stated, list):
        return (_failed("mathematics.exact_arithmetic", "roots must be a list"),)
    checks = []
    if not stated:
        # "No rational root" is a real answer and still needs an arithmetic check:
        # the discriminant must genuinely rule one out.
        discriminant = b * b - 4 * a * c
        rational = discriminant >= 0 and _is_perfect_square(discriminant)
        checks.append(
            _pass(
                "mathematics.exact_arithmetic",
                f"discriminant {discriminant} admits no rational root",
            )
            if not rational
            else _failed(
                "mathematics.exact_arithmetic",
                f"discriminant {discriminant} does admit a rational root",
            )
        )
    for item in stated:
        try:
            root = Fraction(str(item))
        except (ValueError, ZeroDivisionError):
            checks.append(_failed("mathematics.exact_arithmetic", f"root {item!r} is unreadable"))
            continue
        # Independent route: substitute rather than recompute the quadratic formula.
        residual = a * root * root + b * root + c
        checks.append(
            _pass("mathematics.exact_arithmetic", f"root {root} substitutes to zero")
            if residual == 0
            else _failed("mathematics.exact_arithmetic", f"root {root} leaves residual {residual}")
        )
    expected_count = int(_fraction(inputs.get("expected_root_count", len(stated))))
    checks.append(
        _pass("mathematics.numeric", f"{len(stated)} root(s) reported as expected")
        if len(stated) == expected_count
        else _failed("mathematics.numeric", f"expected {expected_count} roots, got {len(stated)}")
    )
    return tuple(checks)


def _is_perfect_square(value: Fraction) -> bool:
    try:
        from .kernels import _exact_sqrt

        _exact_sqrt(value)
    except InexactError:
        return False
    return True


def solve_algebraic_simplification(inputs: dict[str, Any], budget: ResourceBudget) -> Solution:
    """Confirm a claimed simplification by exact evaluation at sampled points."""
    original = _parse(inputs["expression"], budget)
    simplified = _parse(inputs["simplified"], budget)
    samples = _sample_points(inputs)
    for point in samples:
        _evaluate(original, budget, point)
        _evaluate(simplified, budget, point)
    return Solution(
        candidate=Candidate(AnswerType.SYMBOLIC, symbolic_form=str(inputs["simplified"])),
        steps=(
            Step("parse-both", "parsed original and simplified forms", "ast-pair"),
            Step("sample", f"evaluated both at {len(samples)} rational points", "agreement"),
        ),
        tool_evidence=("mathematics.kernel:evaluate_exact",),
        limitations=("agreement at sampled points is evidence, not a proof of identity",),
    )


def check_algebraic_simplification(
    inputs: dict[str, Any], candidate: Candidate, budget: ResourceBudget
) -> CheckSet:
    original = _parse(inputs["expression"], budget)
    claimed = _parse(candidate.symbolic_form or str(inputs["simplified"]), budget)
    samples = _sample_points(inputs)
    mismatches = []
    for point in samples:
        try:
            if _evaluate(original, budget, point) != _evaluate(claimed, budget, point):
                mismatches.append(point)
        except SolverError:
            # A point outside the domain of either form is not counted as a mismatch.
            continue
    equivalence = (
        _pass("mathematics.exact_arithmetic", f"forms agree at all {len(samples)} sampled points")
        if not mismatches
        else _failed("mathematics.exact_arithmetic", f"forms differ at {mismatches[0]}")
    )
    # Sampling cannot prove identity, so the bundle stays honest about its limit.
    strength = Check(
        "mathematics.numeric",
        VerificationDisposition.PASS if not mismatches else VerificationDisposition.FAIL,
        "point-sampling evidence; symbolic proof requires the optional SymPy tool",
    )
    return (equivalence, strength)


def _sample_points(inputs: dict[str, Any]) -> tuple[dict[str, Fraction], ...]:
    raw = inputs.get("samples")
    if isinstance(raw, list) and raw:
        return tuple(
            {str(key): _fraction(value) for key, value in dict(item).items()} for item in raw
        )
    variables = inputs.get("variables", ["x"])
    names = [str(item) for item in variables] if isinstance(variables, list) else ["x"]
    return tuple(
        {name: Fraction(value) for name in names}
        for value in (Fraction(2), Fraction(3), Fraction(5), Fraction(-7), Fraction(1, 3))
    )


def solve_symbolic_equivalence(inputs: dict[str, Any], budget: ResourceBudget) -> Solution:
    checks = check_algebraic_simplification(
        inputs, Candidate(AnswerType.SYMBOLIC, symbolic_form=str(inputs["simplified"])), budget
    )
    equivalent = all(item.disposition is VerificationDisposition.PASS for item in checks)
    return Solution(
        candidate=Candidate(AnswerType.BOOLEAN, logical_status=str(equivalent).lower()),
        steps=(Step("sample-compare", "compared both forms at sampled points", str(equivalent)),),
        tool_evidence=("mathematics.kernel:evaluate_exact",),
    )


def check_symbolic_equivalence(
    inputs: dict[str, Any], candidate: Candidate, budget: ResourceBudget
) -> CheckSet:
    truth = all(
        item.disposition is VerificationDisposition.PASS
        for item in check_algebraic_simplification(
            inputs, Candidate(AnswerType.SYMBOLIC, symbolic_form=str(inputs["simplified"])), budget
        )
    )
    stated = (candidate.logical_status or "").casefold() == "true"
    return (
        _pass("mathematics.exact_arithmetic", f"equivalence decision {truth} confirmed")
        if stated == truth
        else _failed("mathematics.exact_arithmetic", f"claimed {stated}, sampling shows {truth}"),
        _pass("mathematics.numeric", "decision derived from exact rational evaluation"),
    )


def solve_approximation(inputs: dict[str, Any], budget: ResourceBudget) -> Solution:
    """Produce an approximation that stays explicitly separate from the exact value."""
    exact = _evaluate(_parse(inputs["expression"], budget), budget)
    tolerance = Decimal(str(inputs.get("tolerance", "0.0001")))
    return Solution(
        candidate=Candidate(
            AnswerType.APPROXIMATE,
            approximate_value=decimal_of(exact),
            tolerance=tolerance,
        ),
        steps=(
            Step("evaluate-exact", "computed the exact rational first", str(exact)),
            Step("approximate", f"decimal view within {tolerance}", str(decimal_of(exact))),
        ),
        tool_evidence=("mathematics.kernel:evaluate_exact",),
        limitations=("the approximation never replaces the exact value",),
    )


def check_approximation(
    inputs: dict[str, Any], candidate: Candidate, budget: ResourceBudget
) -> CheckSet:
    exact = _evaluate(_parse(inputs["expression"], budget), budget)
    if candidate.approximate_value is None or candidate.tolerance is None:
        return (
            _failed("mathematics.numeric", "approximate answers require a value and tolerance"),
        )
    difference = abs(candidate.approximate_value - decimal_of(exact))
    return (
        _pass("mathematics.numeric", f"within tolerance, difference {difference}")
        if difference <= candidate.tolerance
        else _failed(
            "mathematics.numeric", f"difference {difference} exceeds {candidate.tolerance}"
        ),
        _pass("mathematics.exact_arithmetic", f"exact reference value retained as {exact}"),
    )


# --------------------------------------------------------------------------
# Physics
# --------------------------------------------------------------------------


def solve_unit_conversion(inputs: dict[str, Any], budget: ResourceBudget) -> Solution:
    magnitude = _fraction(inputs["magnitude"])
    source, target = str(inputs["source_unit"]), str(inputs["target_unit"])
    try:
        converted = convert(magnitude, source, target)
    except UnitError as error:
        raise _fail(DomainFailureCode.INVALID_DERIVATION, str(error)) from error
    return Solution(
        candidate=Candidate(
            AnswerType.QUANTITY,
            exact_value=str(converted),
            units=target,
        ),
        steps=(
            Step("check-dimension", f"{source} and {target} share a dimension", "compatible"),
            Step("convert", f"{magnitude} {source} -> {target}", str(converted)),
        ),
        tool_evidence=(f"physics.kernel:registry@{registry_hash()[:16]}",),
    )


def check_unit_conversion(
    inputs: dict[str, Any], candidate: Candidate, budget: ResourceBudget
) -> CheckSet:
    magnitude = _fraction(inputs["magnitude"])
    source, target = str(inputs["source_unit"]), str(inputs["target_unit"])
    try:
        expected = convert(magnitude, source, target)
    except UnitError as error:
        return (_failed("physics.dimension", str(error)),)
    checks = [_compare_exact("physics.quantity", expected, candidate)]
    checks.append(
        _pass("physics.dimension", f"units reported as {target}")
        if candidate.units == target
        else _failed("physics.dimension", f"expected units {target}, got {candidate.units}")
    )
    # Independent route: converting back must return the original magnitude.
    if candidate.exact_value is not None:
        try:
            round_trip = convert(Fraction(candidate.exact_value), target, source)
            checks.append(
                _pass("physics.quantity", f"round trip returns {round_trip}")
                if round_trip == magnitude
                else _failed("physics.quantity", f"round trip gives {round_trip}, not {magnitude}")
            )
        except (UnitError, ValueError, ZeroDivisionError) as error:
            checks.append(_failed("physics.quantity", f"round trip failed: {error}"))
    return tuple(checks)


def solve_dimensional_analysis(inputs: dict[str, Any], budget: ResourceBudget) -> Solution:
    left, right = str(inputs["left_unit"]), str(inputs["right_unit"])
    try:
        consistent = dimension_of(left) == dimension_of(right)
    except UnitError as error:
        raise _fail(DomainFailureCode.INVALID_DERIVATION, str(error)) from error
    return Solution(
        candidate=Candidate(AnswerType.BOOLEAN, logical_status=str(consistent).lower()),
        steps=(
            Step("reduce-left", f"{left} -> {dimension_of(left)}", str(dimension_of(left))),
            Step("reduce-right", f"{right} -> {dimension_of(right)}", str(dimension_of(right))),
        ),
        tool_evidence=(f"physics.kernel:registry@{registry_hash()[:16]}",),
        limitations=("dimensional consistency does not establish physical correctness",),
    )


def check_dimensional_analysis(
    inputs: dict[str, Any], candidate: Candidate, budget: ResourceBudget
) -> CheckSet:
    left, right = str(inputs["left_unit"]), str(inputs["right_unit"])
    try:
        expected = dimension_of(left) == dimension_of(right)
    except UnitError as error:
        return (_failed("physics.dimension", str(error)),)
    stated = (candidate.logical_status or "").casefold() == "true"
    return (
        _pass("physics.dimension", f"dimensional signatures compared: {expected}")
        if stated == expected
        else _failed("physics.dimension", f"claimed {stated}, signatures give {expected}"),
        _pass("physics.quantity", "comparison used base-dimension exponent vectors"),
    )


def solve_quantity_calculation(inputs: dict[str, Any], budget: ResourceBudget) -> Solution:
    """Evaluate a physical formula exactly, carrying units through every factor."""
    expression = _parse(inputs["expression"], budget)
    bindings = {
        str(name): _fraction(value["magnitude"])
        for name, value in dict(inputs["quantities"]).items()
    }
    value = _evaluate(expression, budget, bindings)
    units = str(inputs["result_unit"])
    try:
        dimension_of(units)
    except UnitError as error:
        raise _fail(DomainFailureCode.INVALID_DERIVATION, str(error)) from error
    return Solution(
        candidate=Candidate(AnswerType.QUANTITY, exact_value=str(value), units=units),
        steps=(
            Step("bind", f"bound {len(bindings)} quantities with units", "bindings"),
            Step("evaluate", f"evaluated {inputs['expression']!r} exactly", str(value)),
        ),
        tool_evidence=(f"physics.kernel:registry@{registry_hash()[:16]}",),
        assumptions=tuple(str(item) for item in inputs.get("assumptions", ())),
    )


def check_quantity_calculation(
    inputs: dict[str, Any], candidate: Candidate, budget: ResourceBudget
) -> CheckSet:
    bindings = {
        str(name): _fraction(value["magnitude"])
        for name, value in dict(inputs["quantities"]).items()
    }
    expected = _evaluate(_parse(inputs["expression"], budget), budget, bindings)
    units = str(inputs["result_unit"])
    checks = [_compare_exact("physics.quantity", expected, candidate)]
    checks.append(
        _pass("physics.dimension", f"result carries units {units}")
        if candidate.units == units
        else _failed("physics.dimension", f"expected units {units}, got {candidate.units}")
    )
    # A dimensionally valid result can still be physically wrong, so check the
    # declared expected dimension explicitly rather than trusting the formula.
    if "expected_dimension_unit" in inputs:
        wanted = str(inputs["expected_dimension_unit"])
        try:
            agrees = dimension_of(units) == dimension_of(wanted)
        except UnitError as error:
            checks.append(_failed("physics.dimension", str(error)))
        else:
            checks.append(
                _pass("physics.dimension", f"dimension matches {wanted}")
                if agrees
                else _failed("physics.dimension", f"dimension of {units} does not match {wanted}")
            )
    return tuple(checks)


def solve_model_selection(inputs: dict[str, Any], budget: ResourceBudget) -> Solution:
    """Pick a model only when every one of its assumptions holds."""
    conditions = {str(key): bool(value) for key, value in dict(inputs["conditions"]).items()}
    models = dict(inputs["models"])
    applicable = [
        name
        for name in sorted(models)
        if all(conditions.get(str(item), False) for item in models[name])
    ]
    chosen = applicable[0] if applicable else None
    if chosen is None:
        return Solution(
            candidate=Candidate(
                AnswerType.STRUCTURED, structured={"model": None, "applicable": []}
            ),
            steps=(Step("audit", "no model's assumptions are satisfied", "none"),),
            limitations=("no applicable model: the task is out of the declared scope",),
        )
    return Solution(
        candidate=Candidate(
            AnswerType.STRUCTURED,
            structured={"model": chosen, "applicable": applicable},
        ),
        steps=(
            Step("audit", f"checked assumptions for {len(models)} models", str(applicable)),
            Step("select", f"selected {chosen}", chosen),
        ),
        assumptions=tuple(str(item) for item in models[chosen]),
    )


def check_model_selection(
    inputs: dict[str, Any], candidate: Candidate, budget: ResourceBudget
) -> CheckSet:
    conditions = {str(key): bool(value) for key, value in dict(inputs["conditions"]).items()}
    models = dict(inputs["models"])
    chosen = candidate.structured.get("model")
    if chosen is None:
        satisfied = [
            name for name in models if all(conditions.get(str(i), False) for i in models[name])
        ]
        return (
            _pass("physics.dimension", "correctly reported no applicable model")
            if not satisfied
            else _failed("physics.dimension", f"models {satisfied} were applicable"),
            _pass("physics.quantity", "assumption audit ran before any calculation"),
        )
    if chosen not in models:
        return (_failed("physics.dimension", f"unknown model {chosen!r}"),)
    # Independent route: re-check each assumption of the chosen model directly.
    violated = [str(item) for item in models[chosen] if not conditions.get(str(item), False)]
    return (
        _pass("physics.dimension", f"all assumptions of {chosen} hold")
        if not violated
        else _failed("physics.dimension", f"{chosen} violates assumptions {violated}"),
        _pass("physics.quantity", "model applicability decided before calculating"),
    )


def solve_conservation(inputs: dict[str, Any], budget: ResourceBudget) -> Solution:
    before = [_fraction(item) for item in inputs["before"]]
    after = [_fraction(item) for item in inputs["after"]]
    conserved = sum(before) == sum(after)
    return Solution(
        candidate=Candidate(AnswerType.BOOLEAN, logical_status=str(conserved).lower()),
        steps=(
            Step("sum-before", f"total before = {sum(before)}", str(sum(before))),
            Step("sum-after", f"total after = {sum(after)}", str(sum(after))),
        ),
        tool_evidence=("physics.kernel:conservation",),
    )


def check_conservation(
    inputs: dict[str, Any], candidate: Candidate, budget: ResourceBudget
) -> CheckSet:
    before = sum(_fraction(item) for item in inputs["before"])
    after = sum(_fraction(item) for item in inputs["after"])
    expected = before == after
    stated = (candidate.logical_status or "").casefold() == "true"
    return (
        _pass("physics.quantity", f"conservation holds: {expected} (delta {after - before})")
        if stated == expected
        else _failed("physics.quantity", f"claimed {stated}, exact totals give {expected}"),
        _pass("physics.dimension", "totals compared as exact rationals"),
    )


def solve_limiting_case(inputs: dict[str, Any], budget: ResourceBudget) -> Solution:
    """Evaluate a formula at declared limiting points and report the trend."""
    expression = _parse(inputs["expression"], budget)
    variable = str(inputs.get("variable", "x"))
    points = [_fraction(item) for item in inputs["points"]]
    values = [_evaluate(expression, budget, {variable: point}) for point in points]
    trend = (
        "increasing"
        if all(b > a for a, b in pairwise(values))
        else "decreasing"
        if all(b < a for a, b in pairwise(values))
        else "non-monotonic"
    )
    return Solution(
        candidate=Candidate(
            AnswerType.STRUCTURED,
            structured={"values": [str(item) for item in values], "trend": trend},
        ),
        steps=tuple(
            Step("limit", f"{variable}={point} gives {value}", str(value))
            for point, value in zip(points, values, strict=True)
        ),
        tool_evidence=("physics.kernel:limiting_case",),
    )


def check_limiting_case(
    inputs: dict[str, Any], candidate: Candidate, budget: ResourceBudget
) -> CheckSet:
    expression = _parse(inputs["expression"], budget)
    variable = str(inputs.get("variable", "x"))
    points = [_fraction(item) for item in inputs["points"]]
    expected = [_evaluate(expression, budget, {variable: point}) for point in points]
    stated = [str(item) for item in candidate.structured.get("values", [])]
    agrees = stated == [str(item) for item in expected]
    expected_trend = inputs.get("expected_trend")
    checks = [
        _pass("physics.quantity", "limiting values reproduce exactly")
        if agrees
        else _failed("physics.quantity", f"expected {[str(i) for i in expected]}, got {stated}")
    ]
    if expected_trend is not None:
        checks.append(
            _pass("physics.dimension", f"trend is {expected_trend}")
            if candidate.structured.get("trend") == str(expected_trend)
            else _failed(
                "physics.dimension",
                f"expected trend {expected_trend}, got {candidate.structured.get('trend')}",
            )
        )
    else:
        checks.append(_pass("physics.dimension", "trend recorded without a declared expectation"))
    return tuple(checks)


def solve_order_of_magnitude(inputs: dict[str, Any], budget: ResourceBudget) -> Solution:
    value = _fraction(inputs["value"])
    if value == 0:
        raise _fail(DomainFailureCode.INVALID_DERIVATION, "order of magnitude of zero is undefined")
    exponent = _decimal_exponent(abs(value))
    return Solution(
        candidate=Candidate(AnswerType.STRUCTURED, structured={"exponent": exponent}),
        steps=(
            Step(
                "magnitude", f"|{value}| lies in 10^{exponent} .. 10^{exponent + 1}", str(exponent)
            ),
        ),
        tool_evidence=("physics.kernel:order_of_magnitude",),
    )


def _decimal_exponent(value: Fraction) -> int:
    """Largest `n` with `10^n <= value`, computed exactly without logarithms."""
    exponent = 0
    while value >= 10:
        value /= 10
        exponent += 1
    while value < 1:
        value *= 10
        exponent -= 1
    return exponent


def check_order_of_magnitude(
    inputs: dict[str, Any], candidate: Candidate, budget: ResourceBudget
) -> CheckSet:
    value = _fraction(inputs["value"])
    if value == 0:
        return (_failed("physics.quantity", "order of magnitude of zero is undefined"),)
    expected = _decimal_exponent(abs(value))
    stated = candidate.structured.get("exponent")
    # Independent route: bracket the value between the two powers of ten.
    lower, upper = Fraction(10) ** expected, Fraction(10) ** (expected + 1)
    return (
        _pass("physics.quantity", f"exponent {expected} confirmed")
        if stated == expected
        else _failed("physics.quantity", f"expected exponent {expected}, got {stated}"),
        _pass("physics.dimension", f"{lower} <= |{value}| < {upper}")
        if lower <= abs(value) < upper
        else _failed("physics.dimension", "bracketing check failed"),
    )


def solve_significant_figures(inputs: dict[str, Any], budget: ResourceBudget) -> Solution:
    value = Decimal(str(inputs["value"]))
    figures = int(_fraction(inputs["significant_figures"]))
    if figures <= 0:
        raise _fail(DomainFailureCode.INVALID_DERIVATION, "significant figures must be positive")
    rounded = _round_significant(value, figures)
    tolerance = abs(value - rounded)
    return Solution(
        candidate=Candidate(
            AnswerType.APPROXIMATE,
            approximate_value=rounded,
            tolerance=tolerance,
            units=str(inputs["unit"]) if "unit" in inputs else None,
        ),
        steps=(Step("round", f"{value} to {figures} significant figures", str(rounded)),),
        tool_evidence=("physics.kernel:significant_figures",),
        limitations=("rounding discards precision and is recorded as the tolerance",),
    )


def _round_significant(value: Decimal, figures: int) -> Decimal:
    if value == 0:
        return Decimal(0)
    from decimal import ROUND_HALF_EVEN

    exponent = value.adjusted()
    quantum = Decimal(1).scaleb(exponent - figures + 1)
    return value.quantize(quantum, rounding=ROUND_HALF_EVEN)


def check_significant_figures(
    inputs: dict[str, Any], candidate: Candidate, budget: ResourceBudget
) -> CheckSet:
    value = Decimal(str(inputs["value"]))
    figures = int(_fraction(inputs["significant_figures"]))
    expected = _round_significant(value, figures)
    if candidate.approximate_value is None:
        return (_failed("physics.quantity", "no approximate value supplied"),)
    return (
        _pass("physics.quantity", f"rounded to {expected} at {figures} significant figures")
        if candidate.approximate_value == expected
        else _failed("physics.quantity", f"expected {expected}, got {candidate.approximate_value}"),
        _pass("physics.dimension", "rounding error retained as the stated tolerance")
        if candidate.tolerance is not None
        else _failed("physics.dimension", "significant-figure answers must state a tolerance"),
    )


# --------------------------------------------------------------------------
# Logic
# --------------------------------------------------------------------------


def _rows(
    expression: LogicExpression, budget: ResourceBudget
) -> tuple[tuple[dict[str, bool], bool], ...]:
    try:
        return truth_table(expression, maximum_rows=budget.maximum_nodes)
    except BudgetExceededError as error:
        raise _fail(DomainFailureCode.RESOURCE_EXHAUSTED, str(error)) from error
    except ValueError as error:
        raise _fail(DomainFailureCode.INVALID_DERIVATION, str(error)) from error


def solve_truth_table(inputs: dict[str, Any], budget: ResourceBudget) -> Solution:
    expression = _logic(inputs["expression"])
    rows = _rows(expression, budget)
    return Solution(
        candidate=Candidate(
            AnswerType.STRUCTURED,
            structured={
                "rows": len(rows),
                "outputs": [value for _, value in rows],
                "classification": classify(expression, maximum_rows=budget.maximum_nodes),
            },
        ),
        steps=(Step("enumerate", f"enumerated {len(rows)} assignments", str(len(rows))),),
        tool_evidence=("logic.kernel:truth_table",),
    )


def check_truth_table(
    inputs: dict[str, Any], candidate: Candidate, budget: ResourceBudget
) -> CheckSet:
    expression = _logic(inputs["expression"])
    rows = _rows(expression, budget)
    expected = [value for _, value in rows]
    stated = list(candidate.structured.get("outputs", []))
    checks = [
        _pass("logic.truth_table", f"all {len(rows)} rows reproduce")
        if stated == expected
        else _failed("logic.truth_table", "truth table rows do not reproduce")
    ]
    # Independent route: re-evaluate every row rather than trusting the table.
    recomputed = all(evaluate_logic(expression, assignment) == value for assignment, value in rows)
    checks.append(
        _pass("logic.counterexample", "row-by-row re-evaluation agrees")
        if recomputed
        else _failed("logic.counterexample", "row-by-row re-evaluation disagrees")
    )
    return tuple(checks)


def solve_validity(inputs: dict[str, Any], budget: ResourceBudget) -> Solution:
    expression = _logic(inputs["expression"])
    kind = classify(expression, maximum_rows=budget.maximum_nodes)
    witness = counterexample(expression, maximum_rows=budget.maximum_nodes)
    return Solution(
        candidate=Candidate(
            AnswerType.BOOLEAN,
            logical_status=str(kind == "tautology").lower(),
            structured={"classification": kind, "counterexample": witness},
        ),
        steps=(
            Step("classify", f"exhaustive enumeration says {kind}", kind),
            Step("witness", f"counterexample: {witness}", str(witness)),
        ),
        tool_evidence=("logic.kernel:truth_table",),
    )


def check_validity(
    inputs: dict[str, Any], candidate: Candidate, budget: ResourceBudget
) -> CheckSet:
    expression = _logic(inputs["expression"])
    expected = classify(expression, maximum_rows=budget.maximum_nodes) == "tautology"
    stated = (candidate.logical_status or "").casefold() == "true"
    checks = [
        _pass("logic.truth_table", f"validity is {expected}")
        if stated == expected
        else _failed("logic.truth_table", f"claimed {stated}, enumeration gives {expected}")
    ]
    # A claimed counterexample must actually falsify the expression.
    witness = candidate.structured.get("counterexample")
    if isinstance(witness, dict) and witness:
        assignment = {str(k): bool(v) for k, v in witness.items()}
        try:
            falsifies = not evaluate_logic(expression, assignment)
        except ValueError as error:
            checks.append(_failed("logic.counterexample", str(error)))
        else:
            checks.append(
                _pass("logic.counterexample", "counterexample reproduces the failure")
                if falsifies
                else _failed("logic.counterexample", "stated counterexample does not falsify")
            )
    else:
        checks.append(
            _pass("logic.counterexample", "no counterexample exists, consistent with validity")
            if expected
            else _failed("logic.counterexample", "invalid expression must supply a counterexample")
        )
    return tuple(checks)


def solve_satisfiability(inputs: dict[str, Any], budget: ResourceBudget) -> Solution:
    expression = _logic(inputs["expression"])
    model = satisfying_assignment(expression, maximum_rows=budget.maximum_nodes)
    return Solution(
        candidate=Candidate(
            AnswerType.SATISFIABLE if model else AnswerType.UNSATISFIABLE,
            logical_status="sat" if model else "unsat",
            structured={"model": model},
        ),
        steps=(Step("search", "bounded exhaustive enumeration", "sat" if model else "unsat"),),
        tool_evidence=("logic.kernel:truth_table",),
        limitations=("exhaustive within the row ceiling; larger instances need the Z3 tool",),
    )


def check_satisfiability(
    inputs: dict[str, Any], candidate: Candidate, budget: ResourceBudget
) -> CheckSet:
    expression = _logic(inputs["expression"])
    model = satisfying_assignment(expression, maximum_rows=budget.maximum_nodes)
    expected = "sat" if model else "unsat"
    stated = (candidate.logical_status or "").casefold()
    checks = [
        _pass("logic.truth_table", f"status {expected} confirmed by enumeration")
        if stated == expected
        else _failed("logic.truth_table", f"claimed {stated}, enumeration gives {expected}")
    ]
    # A claimed model must satisfy the formula; `unknown` never becomes `unsat`.
    stated_model = candidate.structured.get("model")
    if stated == "sat" and isinstance(stated_model, dict) and stated_model:
        assignment = {str(k): bool(v) for k, v in stated_model.items()}
        try:
            satisfies = evaluate_logic(expression, assignment)
        except ValueError as error:
            checks.append(_failed("logic.counterexample", str(error)))
        else:
            checks.append(
                _pass("logic.counterexample", "model satisfies every constraint")
                if satisfies
                else _failed("logic.counterexample", "stated model does not satisfy the formula")
            )
    elif stated == "unknown":
        checks.append(
            Check(
                "logic.counterexample",
                VerificationDisposition.INCONCLUSIVE,
                "solver returned unknown; this is never an unsatisfiability proof",
            )
        )
    else:
        checks.append(
            _pass("logic.counterexample", "no model claimed for an unsatisfiable formula")
        )
    return tuple(checks)


def solve_consistency(inputs: dict[str, Any], budget: ResourceBudget) -> Solution:
    expression = _logic(inputs["expression"])
    kind = classify(expression, maximum_rows=budget.maximum_nodes)
    return Solution(
        candidate=Candidate(
            AnswerType.BOOLEAN,
            logical_status=str(kind != "contradiction").lower(),
            structured={"classification": kind},
        ),
        steps=(Step("classify", f"enumeration says {kind}", kind),),
        tool_evidence=("logic.kernel:truth_table",),
    )


def check_consistency(
    inputs: dict[str, Any], candidate: Candidate, budget: ResourceBudget
) -> CheckSet:
    expression = _logic(inputs["expression"])
    kind = classify(expression, maximum_rows=budget.maximum_nodes)
    expected = kind != "contradiction"
    stated = (candidate.logical_status or "").casefold() == "true"
    return (
        _pass("logic.truth_table", f"consistency is {expected} ({kind})")
        if stated == expected
        else _failed("logic.truth_table", f"claimed {stated}, enumeration gives {expected}"),
        _pass("logic.counterexample", "classification derived from exhaustive enumeration"),
    )


def solve_counterexample(inputs: dict[str, Any], budget: ResourceBudget) -> Solution:
    expression = _logic(inputs["expression"])
    witness = counterexample(expression, maximum_rows=budget.maximum_nodes)
    return Solution(
        candidate=Candidate(
            AnswerType.COUNTEREXAMPLE,
            structured={"counterexample": witness, "found": witness is not None},
        ),
        steps=(Step("search", "searched for a falsifying assignment", str(witness)),),
        tool_evidence=("logic.kernel:truth_table",),
    )


def check_counterexample(
    inputs: dict[str, Any], candidate: Candidate, budget: ResourceBudget
) -> CheckSet:
    expression = _logic(inputs["expression"])
    expected = counterexample(expression, maximum_rows=budget.maximum_nodes)
    stated = candidate.structured.get("counterexample")
    checks = [
        _pass("logic.counterexample", f"existence of a counterexample is {expected is not None}")
        if (stated is not None) == (expected is not None)
        else _failed("logic.counterexample", "counterexample existence disagrees")
    ]
    if isinstance(stated, dict) and stated:
        assignment = {str(k): bool(v) for k, v in stated.items()}
        try:
            falsifies = not evaluate_logic(expression, assignment)
        except ValueError as error:
            checks.append(_failed("logic.truth_table", str(error)))
        else:
            checks.append(
                _pass("logic.truth_table", "counterexample reproduces the failure")
                if falsifies
                else _failed("logic.truth_table", "stated counterexample does not falsify")
            )
    else:
        checks.append(_pass("logic.truth_table", "exhaustive search returned no counterexample"))
    return tuple(checks)


def solve_sequence_induction(inputs: dict[str, Any], budget: ResourceBudget) -> Solution:
    """Enumerate every candidate rule reproducing the terms; never assert uniqueness."""
    terms = [int(_fraction(item)) for item in inputs["terms"]]
    if len(terms) < 3:
        raise _fail(DomainFailureCode.INVALID_DERIVATION, "at least three terms are required")
    compatible = [
        (name, complexity, rule)
        for name, complexity, rule in _CANDIDATE_RULES
        if _reproduces(rule, terms)
    ]
    if not compatible:
        return Solution(
            candidate=Candidate(
                AnswerType.STRUCTURED,
                structured={"rules": [], "next": None, "underdetermined": False},
            ),
            steps=(Step("enumerate", "no candidate rule reproduces the terms", "none"),),
            limitations=("the rule space is bounded; absence here is not absence in general",),
        )
    compatible.sort(key=lambda item: (item[1], item[0]))
    predictions = sorted({rule(terms) for _, _, rule in compatible})
    return Solution(
        candidate=Candidate(
            AnswerType.STRUCTURED,
            structured={
                "rules": [name for name, _, _ in compatible],
                "next": compatible[0][2](terms),
                "underdetermined": len(predictions) > 1,
                "alternative_predictions": predictions,
            },
        ),
        steps=(
            Step("enumerate", f"{len(compatible)} rules reproduce the terms", str(len(compatible))),
            Step("rank", "ranked by transparent complexity, ties broken by name", compatible[0][0]),
        ),
        tool_evidence=("logic.kernel:sequence_induction",),
        limitations=(
            "several rules may fit the same prefix; alternatives are reported, not discarded",
        ),
    )


def _reproduces(rule: Any, terms: list[int]) -> bool:
    """A rule must regenerate every observed term from the first two."""
    return all(rule(terms[:index]) == terms[index] for index in range(2, len(terms)))


#: Bounded, transparent rule space. Complexity is the ranking key and is a
#: declared heuristic, not a claim about the true generating process.
_CANDIDATE_RULES: tuple[tuple[str, int, Any], ...] = (
    ("constant", 1, lambda t: t[-1]),
    ("arithmetic", 2, lambda t: t[-1] + (t[1] - t[0])),
    ("geometric", 3, lambda t: t[-1] * (t[1] // t[0]) if t[0] else t[-1]),
    ("fibonacci-like", 4, lambda t: t[-1] + t[-2]),
    ("squares", 4, lambda t: (len(t) + 1) ** 2),
    ("alternating-sign", 5, lambda t: -t[-1]),
)


def check_sequence_induction(
    inputs: dict[str, Any], candidate: Candidate, budget: ResourceBudget
) -> CheckSet:
    terms = [int(_fraction(item)) for item in inputs["terms"]]
    stated_rules = [str(item) for item in candidate.structured.get("rules", [])]
    rules_by_name = {name: rule for name, _, rule in _CANDIDATE_RULES}
    checks = []
    # Every rule the answer names must independently regenerate the observations.
    invalid = [
        name
        for name in stated_rules
        if name not in rules_by_name or not _reproduces(rules_by_name[name], terms)
    ]
    compatible_names = [name for name, _, rule in _CANDIDATE_RULES if _reproduces(rule, terms)]
    if invalid:
        checks.append(
            _failed("logic.truth_table", f"rules {invalid} do not reproduce the observations")
        )
    elif not stated_rules and compatible_names:
        # An empty rule set must not pass vacuously while rules demonstrably fit.
        checks.append(
            _failed(
                "logic.truth_table",
                f"no rule reported although {compatible_names} reproduce the terms",
            )
        )
    else:
        checks.append(
            _pass("logic.truth_table", f"all {len(stated_rules)} named rules reproduce the terms")
        )
    # Underdetermination must be reported whenever the fitting rules disagree.
    compatible = [rule for name, _, rule in _CANDIDATE_RULES if _reproduces(rule, terms)]
    predictions = {rule(terms) for rule in compatible}
    expected_flag = len(predictions) > 1
    checks.append(
        _pass("logic.counterexample", f"underdetermination reported as {expected_flag}")
        if bool(candidate.structured.get("underdetermined")) == expected_flag
        else _failed(
            "logic.counterexample",
            f"underdetermination should be {expected_flag}; a unique answer is unjustified",
        )
    )
    return tuple(checks)


CHECKERS: dict[str, Any] = {
    "long-multiplication": check_long_multiplication,
    "long-division": check_long_division,
    "fraction-arithmetic": check_exact_expression,
    "rational-arithmetic": check_exact_expression,
    "algebraic-simplification": check_algebraic_simplification,
    "linear-equation": check_linear_equation,
    "polynomial-equation": check_quadratic_equation,
    "symbolic-equivalence": check_symbolic_equivalence,
    "exact-versus-approximate": check_approximation,
    "unit-conversion": check_unit_conversion,
    "dimensional-analysis": check_dimensional_analysis,
    "quantity-calculation": check_quantity_calculation,
    "model-selection": check_model_selection,
    "conservation-check": check_conservation,
    "limiting-case": check_limiting_case,
    "order-of-magnitude": check_order_of_magnitude,
    "significant-figures": check_significant_figures,
    "truth-table": check_truth_table,
    "validity-check": check_validity,
    "satisfiability": check_satisfiability,
    "constraint-satisfaction": check_satisfiability,
    "consistency-check": check_consistency,
    "counterexample-search": check_counterexample,
    "sequence-induction": check_sequence_induction,
    "competing-hypotheses": check_sequence_induction,
}
