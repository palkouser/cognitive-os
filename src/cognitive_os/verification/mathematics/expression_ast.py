"""Closed typed AST for safe symbolic mathematics."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from fractions import Fraction


@dataclass(frozen=True, slots=True)
class Integer:
    value: int


@dataclass(frozen=True, slots=True)
class Rational:
    value: Fraction


@dataclass(frozen=True, slots=True)
class DecimalValue:
    value: Decimal


@dataclass(frozen=True, slots=True)
class Symbol:
    name: str


@dataclass(frozen=True, slots=True)
class Constant:
    name: str


@dataclass(frozen=True, slots=True)
class UnaryExpression:
    operator: str
    operand: Expression


@dataclass(frozen=True, slots=True)
class BinaryExpression:
    operator: str
    left: Expression
    right: Expression


@dataclass(frozen=True, slots=True)
class FunctionExpression:
    name: str
    argument: Expression


type Expression = (
    Integer
    | Rational
    | DecimalValue
    | Symbol
    | Constant
    | UnaryExpression
    | BinaryExpression
    | FunctionExpression
)
