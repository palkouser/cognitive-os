"""Dependency-free deterministic kernels for the mandatory CPU-only pilot path.

SymPy, Pint, and Z3 stay optional escalation tools registered in the verifier
factory. Everything the Gate K CI manifest needs is computed here from the
standard library over the Sprint 7 typed ASTs, so the core imports and the
mandatory benchmark runs with no extras, no network, and no GPU.
"""

from __future__ import annotations

from decimal import Decimal
from fractions import Fraction
from itertools import product

from cognitive_os.verification.logic.ast import LogicExpression, LogicLimits, LogicOperator
from cognitive_os.verification.mathematics.expression_ast import (
    BinaryExpression,
    Constant,
    DecimalValue,
    Expression,
    FunctionExpression,
    Integer,
    Rational,
    Symbol,
    UnaryExpression,
)


class InexactError(ValueError):
    """Raised when a value cannot be represented exactly; never silently rounded."""


class BudgetExceededError(ValueError):
    """Raised before or during execution when a declared ceiling is crossed."""


# --------------------------------------------------------------------------
# Exact arithmetic (S20-016)
# --------------------------------------------------------------------------


def evaluate_exact(
    expression: Expression,
    bindings: dict[str, Fraction] | None = None,
    *,
    maximum_integer_digits: int = 256,
) -> Fraction:
    """Evaluate the typed math AST exactly over the rationals.

    No float ever enters the path: `Decimal` literals become exact `Fraction`s
    and any operation that would leave the rationals raises `InexactError`
    rather than substituting an approximation.
    """
    values = bindings or {}

    def guard(value: Fraction) -> Fraction:
        digits = max(len(str(abs(value.numerator))), len(str(abs(value.denominator))))
        if digits > maximum_integer_digits:
            raise BudgetExceededError("exact arithmetic exceeded the integer-digit ceiling")
        return value

    def visit(node: Expression) -> Fraction:
        if isinstance(node, Integer):
            return guard(Fraction(node.value))
        if isinstance(node, Rational):
            return guard(node.value)
        if isinstance(node, DecimalValue):
            return guard(Fraction(node.value))
        if isinstance(node, Symbol):
            if node.name not in values:
                raise InexactError(f"unbound symbol {node.name!r}")
            return guard(values[node.name])
        if isinstance(node, Constant):
            raise InexactError(f"constant {node.name!r} is irrational and has no exact value")
        if isinstance(node, UnaryExpression):
            operand = visit(node.operand)
            return operand if node.operator == "positive" else -operand
        if isinstance(node, BinaryExpression):
            left, right = visit(node.left), visit(node.right)
            if node.operator == "add":
                return guard(left + right)
            if node.operator == "subtract":
                return guard(left - right)
            if node.operator == "multiply":
                return guard(left * right)
            if node.operator == "divide":
                if right == 0:
                    raise InexactError("division by zero")
                return guard(left / right)
            if node.operator == "power":
                if right.denominator != 1:
                    raise InexactError("fractional exponents are not exact")
                if right < 0 and left == 0:
                    raise InexactError("zero raised to a negative power")
                return guard(left ** int(right))
            raise InexactError(f"unsupported operator {node.operator!r}")
        if isinstance(node, FunctionExpression):
            if node.name == "abs":
                return abs(visit(node.argument))
            if node.name == "sqrt":
                return guard(_exact_sqrt(visit(node.argument)))
            raise InexactError(f"function {node.name!r} has no exact rational result")
        raise InexactError("unsupported expression node")

    return visit(expression)


def _exact_sqrt(value: Fraction) -> Fraction:
    """Exact square root, or `InexactError` when the result is irrational."""
    if value < 0:
        raise InexactError("square root of a negative number is not real")
    numerator = _exact_isqrt(value.numerator)
    denominator = _exact_isqrt(value.denominator)
    return Fraction(numerator, denominator)


def _exact_isqrt(value: int) -> int:
    from math import isqrt

    root = isqrt(value)
    if root * root != value:
        raise InexactError("square root is irrational")
    return root


def long_multiplication_trace(left: int, right: int) -> tuple[str, ...]:
    """Per-digit partial products, so a derivation can be checked step by step."""
    steps = []
    for position, digit in enumerate(reversed(str(abs(right)))):
        partial = abs(left) * int(digit) * 10**position
        steps.append(f"{abs(left)} * {digit} * 10^{position} = {partial}")
    sign = -1 if (left < 0) != (right < 0) else 1
    steps.append(f"sum * sign({sign}) = {left * right}")
    return tuple(steps)


def long_division_trace(dividend: int, divisor: int) -> tuple[str, ...]:
    """Quotient and remainder by repeated subtraction of scaled divisors."""
    if divisor == 0:
        raise InexactError("division by zero")
    quotient, remainder = divmod(abs(dividend), abs(divisor))
    steps = [
        f"{abs(dividend)} = {abs(divisor)} * {quotient} + {remainder}",
        f"quotient = {quotient}, remainder = {remainder}",
    ]
    return tuple(steps)


# --------------------------------------------------------------------------
# Project-owned unit registry and dimensional algebra (S20-024, S20-026)
# --------------------------------------------------------------------------

#: Seven SI base dimensions, in fixed order. A dimension is an exponent vector,
#: so dimensional equality is tuple equality and needs no external library.
BASE_DIMENSIONS: tuple[str, ...] = (
    "length",
    "mass",
    "time",
    "current",
    "temperature",
    "amount",
    "luminosity",
)

type Dimension = tuple[int, ...]

_DIMENSIONLESS: Dimension = (0,) * len(BASE_DIMENSIONS)


def _dim(**exponents: int) -> Dimension:
    return tuple(exponents.get(name, 0) for name in BASE_DIMENSIONS)


#: Project-owned, pinned unit definitions: unit -> (factor to SI base, dimension).
#: Values are exact `Fraction`s; nothing is fetched at runtime and no external
#: registry file is ever read, so the registry hash below is stable.
UNIT_REGISTRY: dict[str, tuple[Fraction, Dimension]] = {
    "m": (Fraction(1), _dim(length=1)),
    "km": (Fraction(1000), _dim(length=1)),
    "cm": (Fraction(1, 100), _dim(length=1)),
    "mm": (Fraction(1, 1000), _dim(length=1)),
    "kg": (Fraction(1), _dim(mass=1)),
    "g": (Fraction(1, 1000), _dim(mass=1)),
    "s": (Fraction(1), _dim(time=1)),
    "min": (Fraction(60), _dim(time=1)),
    "h": (Fraction(3600), _dim(time=1)),
    "A": (Fraction(1), _dim(current=1)),
    "K": (Fraction(1), _dim(temperature=1)),
    "mol": (Fraction(1), _dim(amount=1)),
    "cd": (Fraction(1), _dim(luminosity=1)),
    "N": (Fraction(1), _dim(mass=1, length=1, time=-2)),
    "J": (Fraction(1), _dim(mass=1, length=2, time=-2)),
    "W": (Fraction(1), _dim(mass=1, length=2, time=-3)),
    "Pa": (Fraction(1), _dim(mass=1, length=-1, time=-2)),
    "C": (Fraction(1), _dim(current=1, time=1)),
    "V": (Fraction(1), _dim(mass=1, length=2, time=-3, current=-1)),
    "Hz": (Fraction(1), _dim(time=-1)),
}

#: Offset units are handled explicitly and never auto-converted to a base unit.
OFFSET_UNITS: dict[str, tuple[Fraction, Fraction, Dimension]] = {
    "degC": (Fraction(1), Fraction(27315, 100), _dim(temperature=1)),
    "degF": (Fraction(5, 9), Fraction(45967, 180), _dim(temperature=1)),
}


class UnitError(ValueError):
    """Raised for unknown, ambiguous, or incompatible units."""


def registry_hash() -> str:
    """Stable hash over the pinned definitions, recorded with every result."""
    from hashlib import sha256

    payload = "|".join(
        f"{name}:{factor.numerator}/{factor.denominator}:{dimension}"
        for name, (factor, dimension) in sorted(UNIT_REGISTRY.items())
    )
    offsets = "|".join(
        f"{name}:{scale}:{offset}:{dimension}"
        for name, (scale, offset, dimension) in sorted(OFFSET_UNITS.items())
    )
    return sha256(f"{payload}||{offsets}".encode()).hexdigest()


def parse_unit(unit: str) -> tuple[Fraction, Dimension]:
    """Parse a bounded `a*b/c^2` unit expression into a factor and a dimension.

    Only registry symbols, `*`, `/`, and integer `^` exponents are accepted;
    there is no eval, no alias resolution, and no runtime definition injection.
    """
    text = unit.strip()
    if not text or len(text) > 128:
        raise UnitError("unit expression is empty or too long")
    if text in OFFSET_UNITS:
        raise UnitError(f"offset unit {text!r} must be converted explicitly")
    factor = Fraction(1)
    dimension = list(_DIMENSIONLESS)
    numerator, _, denominator = text.partition("/")
    if "/" in denominator:
        raise UnitError("nested division in unit expressions is not supported")
    for sign, part in ((1, numerator), (-1, denominator)):
        for token in part.split("*"):
            token = token.strip()
            if not token:
                if sign == -1 and not denominator:
                    continue
                raise UnitError(f"empty unit token in {unit!r}")
            symbol, _, exponent_text = token.partition("^")
            symbol = symbol.strip()
            try:
                exponent = int(exponent_text) if exponent_text else 1
            except ValueError as error:
                raise UnitError(f"invalid unit exponent in {token!r}") from error
            if not -12 <= exponent <= 12:
                raise UnitError("unit exponent is out of the supported range")
            if symbol not in UNIT_REGISTRY:
                raise UnitError(f"unknown unit symbol {symbol!r}")
            unit_factor, unit_dimension = UNIT_REGISTRY[symbol]
            factor *= unit_factor ** (sign * exponent)
            dimension = [
                current + sign * exponent * base
                for current, base in zip(dimension, unit_dimension, strict=True)
            ]
    return factor, tuple(dimension)


def dimension_of(unit: str) -> Dimension:
    if unit in OFFSET_UNITS:
        return OFFSET_UNITS[unit][2]
    return parse_unit(unit)[1]


def convert(magnitude: Fraction, source: str, target: str) -> Fraction:
    """Convert exactly between compatible units, offsets included."""
    if source in OFFSET_UNITS or target in OFFSET_UNITS:
        return _convert_offset(magnitude, source, target)
    source_factor, source_dimension = parse_unit(source)
    target_factor, target_dimension = parse_unit(target)
    if source_dimension != target_dimension:
        raise UnitError(f"incompatible units: {source!r} and {target!r}")
    return magnitude * source_factor / target_factor


def _convert_offset(magnitude: Fraction, source: str, target: str) -> Fraction:
    """Affine temperature conversion; scale-only conversion here is a bug, not a shortcut."""
    if dimension_of(source) != dimension_of(target):
        raise UnitError(f"incompatible units: {source!r} and {target!r}")
    if source in OFFSET_UNITS:
        scale, offset, _ = OFFSET_UNITS[source]
        kelvin = magnitude * scale + offset
    else:
        kelvin = magnitude * parse_unit(source)[0]
    if target in OFFSET_UNITS:
        scale, offset, _ = OFFSET_UNITS[target]
        return (kelvin - offset) / scale
    return kelvin / parse_unit(target)[0]


# --------------------------------------------------------------------------
# Truth tables and propositional validity (S20-033)
# --------------------------------------------------------------------------


def collect_variables(expression: LogicExpression) -> tuple[str, ...]:
    """Deterministically ordered Boolean variable names."""
    names: list[str] = []

    def visit(node: LogicExpression) -> None:
        if node.operator is LogicOperator.VARIABLE and node.name and node.name not in names:
            names.append(node.name)
        for child in node.arguments:
            visit(child)

    visit(expression)
    return tuple(sorted(names))


def evaluate_logic(expression: LogicExpression, assignment: dict[str, bool]) -> bool:
    """Evaluate a propositional expression under a total Boolean assignment."""
    operator = expression.operator
    if operator is LogicOperator.BOOLEAN:
        return bool(expression.value)
    if operator is LogicOperator.VARIABLE:
        name = expression.name or ""
        if name not in assignment:
            raise ValueError(f"unassigned variable {name!r}")
        return assignment[name]
    values = [evaluate_logic(item, assignment) for item in expression.arguments]
    if operator is LogicOperator.NOT:
        return not values[0]
    if operator is LogicOperator.AND:
        return all(values)
    if operator is LogicOperator.OR:
        return any(values)
    if operator is LogicOperator.XOR:
        return values[0] != values[1]
    if operator is LogicOperator.IMPLIES:
        return (not values[0]) or values[1]
    if operator is LogicOperator.EQUALS:
        return values[0] == values[1]
    if operator is LogicOperator.NOT_EQUALS:
        return values[0] != values[1]
    raise ValueError(f"operator {operator!r} is not propositional")


def truth_table(
    expression: LogicExpression, *, limits: LogicLimits | None = None, maximum_rows: int = 4096
) -> tuple[tuple[dict[str, bool], bool], ...]:
    """Enumerate every assignment; row ceilings fail closed before enumeration."""
    expression.enforce_limits(limits or LogicLimits())
    variables = collect_variables(expression)
    if 2 ** len(variables) > maximum_rows:
        raise BudgetExceededError("truth table exceeds the configured row ceiling")
    rows = []
    for combination in product((False, True), repeat=len(variables)):
        assignment = dict(zip(variables, combination, strict=True))
        rows.append((assignment, evaluate_logic(expression, assignment)))
    return tuple(rows)


def classify(expression: LogicExpression, **kwargs: object) -> str:
    """Return `tautology`, `contradiction`, or `contingent`."""
    results = [value for _, value in truth_table(expression, **kwargs)]  # type: ignore[arg-type]
    if all(results):
        return "tautology"
    if not any(results):
        return "contradiction"
    return "contingent"


def counterexample(expression: LogicExpression, **kwargs: object) -> dict[str, bool] | None:
    """First falsifying assignment, or `None` when the expression is valid."""
    for assignment, value in truth_table(expression, **kwargs):  # type: ignore[arg-type]
        if not value:
            return assignment
    return None


def satisfying_assignment(expression: LogicExpression, **kwargs: object) -> dict[str, bool] | None:
    for assignment, value in truth_table(expression, **kwargs):  # type: ignore[arg-type]
        if value:
            return assignment
    return None


def decimal_of(value: Fraction) -> Decimal:
    """Best-effort decimal view for reporting; exact values stay `Fraction`."""
    return Decimal(value.numerator) / Decimal(value.denominator)
