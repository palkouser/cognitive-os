"""Strict parser from a small Python expression subset into the typed math AST."""

from __future__ import annotations

import ast
from dataclasses import dataclass
from decimal import Decimal

from .expression_ast import (
    BinaryExpression,
    Constant,
    DecimalValue,
    Expression,
    FunctionExpression,
    Integer,
    Symbol,
    UnaryExpression,
)

ALLOWED_FUNCTIONS = frozenset({"abs", "sqrt", "sin", "cos", "tan", "exp", "log"})
ALLOWED_CONSTANTS = frozenset({"pi", "e"})
ALLOWED_BINARY = {
    ast.Add: "add",
    ast.Sub: "subtract",
    ast.Mult: "multiply",
    ast.Div: "divide",
    ast.Pow: "power",
}


class UnsafeExpressionError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class ExpressionLimits:
    maximum_nodes: int = 512
    maximum_depth: int = 32
    maximum_symbols: int = 32
    maximum_integer_digits: int = 256
    maximum_exponent_magnitude: int = 1000


class _Parser:
    def __init__(self, limits: ExpressionLimits) -> None:
        self.limits = limits
        self.nodes = 0
        self.symbols: set[str] = set()

    def convert(self, node: ast.AST, depth: int = 1) -> Expression:
        self.nodes += 1
        if self.nodes > self.limits.maximum_nodes or depth > self.limits.maximum_depth:
            raise UnsafeExpressionError("expression exceeds structural limits")
        if isinstance(node, ast.Constant):
            if isinstance(node.value, bool) or not isinstance(node.value, (int, float)):
                raise UnsafeExpressionError("only finite numeric literals are supported")
            if isinstance(node.value, int):
                if len(str(abs(node.value))) > self.limits.maximum_integer_digits:
                    raise UnsafeExpressionError("integer literal is too large")
                return Integer(node.value)
            value = Decimal(str(node.value))
            if not value.is_finite():
                raise UnsafeExpressionError("numeric literal must be finite")
            return DecimalValue(value)
        if isinstance(node, ast.Name):
            if node.id in ALLOWED_CONSTANTS:
                return Constant(node.id)
            if not node.id.isidentifier() or node.id.startswith("_"):
                raise UnsafeExpressionError("invalid symbol name")
            self.symbols.add(node.id)
            if len(self.symbols) > self.limits.maximum_symbols:
                raise UnsafeExpressionError("expression contains too many symbols")
            return Symbol(node.id)
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
            return UnaryExpression(
                "positive" if isinstance(node.op, ast.UAdd) else "negative",
                self.convert(node.operand, depth + 1),
            )
        if isinstance(node, ast.BinOp) and type(node.op) in ALLOWED_BINARY:
            if isinstance(node.op, ast.Pow) and isinstance(node.right, ast.Constant):
                exponent = node.right.value
                if (
                    not isinstance(exponent, (int, float))
                    or abs(exponent) > self.limits.maximum_exponent_magnitude
                ):
                    raise UnsafeExpressionError("exponent exceeds configured limit")
            return BinaryExpression(
                ALLOWED_BINARY[type(node.op)],
                self.convert(node.left, depth + 1),
                self.convert(node.right, depth + 1),
            )
        if isinstance(node, ast.Call):
            if not isinstance(node.func, ast.Name) or node.func.id not in ALLOWED_FUNCTIONS:
                raise UnsafeExpressionError("function is not allowlisted")
            if len(node.args) != 1 or node.keywords:
                raise UnsafeExpressionError("functions require exactly one positional argument")
            return FunctionExpression(node.func.id, self.convert(node.args[0], depth + 1))
        if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], ast.Eq):
            return BinaryExpression(
                "equal",
                self.convert(node.left, depth + 1),
                self.convert(node.comparators[0], depth + 1),
            )
        raise UnsafeExpressionError(f"unsupported expression syntax: {type(node).__name__}")


def parse_expression(source: str, limits: ExpressionLimits | None = None) -> Expression:
    if len(source.encode()) > 65_536:
        raise UnsafeExpressionError("expression source is too large")
    try:
        parsed = ast.parse(source, mode="eval")
    except SyntaxError as error:
        raise UnsafeExpressionError("expression syntax is invalid") from error
    return _Parser(limits or ExpressionLimits()).convert(parsed.body)
