"""Manual typed LogicExpression to Z3 mapping; raw SMT-LIB is never accepted."""

from __future__ import annotations

from typing import Any

from .ast import LogicExpression, LogicOperator, LogicSort


def _z3() -> Any:
    import z3  # type: ignore[import-untyped]

    return z3


def to_z3(
    expression: LogicExpression, symbols: dict[tuple[str, LogicSort], Any] | None = None
) -> Any:
    z3 = _z3()
    symbols = symbols if symbols is not None else {}
    if expression.operator is LogicOperator.BOOLEAN:
        return z3.BoolVal(expression.value)
    if expression.operator is LogicOperator.INTEGER:
        return z3.IntVal(expression.value)
    if expression.operator is LogicOperator.RATIONAL:
        return z3.RealVal(expression.value)
    if expression.operator is LogicOperator.VARIABLE:
        key = (expression.name or "", expression.sort)
        if key not in symbols:
            factories = {
                LogicSort.BOOL: z3.Bool,
                LogicSort.INTEGER: z3.Int,
                LogicSort.REAL: z3.Real,
            }
            symbols[key] = factories[expression.sort](expression.name)
        return symbols[key]
    values = [to_z3(item, symbols) for item in expression.arguments]
    operations = {
        LogicOperator.NOT: lambda: z3.Not(values[0]),
        LogicOperator.AND: lambda: z3.And(*values),
        LogicOperator.OR: lambda: z3.Or(*values),
        LogicOperator.XOR: lambda: z3.Xor(*values),
        LogicOperator.IMPLIES: lambda: z3.Implies(*values),
        LogicOperator.EQUALS: lambda: values[0] == values[1],
        LogicOperator.NOT_EQUALS: lambda: values[0] != values[1],
        LogicOperator.LESS_THAN: lambda: values[0] < values[1],
        LogicOperator.LESS_OR_EQUAL: lambda: values[0] <= values[1],
        LogicOperator.GREATER_THAN: lambda: values[0] > values[1],
        LogicOperator.GREATER_OR_EQUAL: lambda: values[0] >= values[1],
        LogicOperator.ADD: lambda: values[0] + values[1],
        LogicOperator.SUBTRACT: lambda: values[0] - values[1],
        LogicOperator.MULTIPLY: lambda: values[0] * values[1],
        LogicOperator.DIVIDE: lambda: values[0] / values[1],
    }
    try:
        return operations[expression.operator]()
    except (KeyError, TypeError) as error:
        raise ValueError("logic expression has incompatible sorts or operator") from error
