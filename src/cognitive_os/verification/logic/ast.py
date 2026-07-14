"""Closed typed Boolean and arithmetic logic AST."""

from __future__ import annotations

from enum import StrEnum

from pydantic import Field, model_validator

from cognitive_os.domain.base import ImmutableContractModel
from cognitive_os.domain.common import JsonValue, NonEmptyStr


class LogicSort(StrEnum):
    BOOL = "bool"
    INTEGER = "integer"
    REAL = "real"


class LogicOperator(StrEnum):
    BOOLEAN = "boolean"
    INTEGER = "integer"
    RATIONAL = "rational"
    VARIABLE = "variable"
    NOT = "not"
    AND = "and"
    OR = "or"
    XOR = "xor"
    IMPLIES = "implies"
    EQUALS = "equals"
    NOT_EQUALS = "not_equals"
    LESS_THAN = "less_than"
    LESS_OR_EQUAL = "less_or_equal"
    GREATER_THAN = "greater_than"
    GREATER_OR_EQUAL = "greater_or_equal"
    ADD = "add"
    SUBTRACT = "subtract"
    MULTIPLY = "multiply"
    DIVIDE = "divide"


class LogicLimits(ImmutableContractModel):
    maximum_nodes: int = Field(default=1024, gt=0, le=8192)
    maximum_depth: int = Field(default=64, gt=0, le=256)
    maximum_variables: int = Field(default=128, gt=0, le=1024)
    maximum_constraints: int = Field(default=256, gt=0, le=4096)


class LogicExpression(ImmutableContractModel):
    operator: LogicOperator
    sort: LogicSort
    value: JsonValue = None
    name: NonEmptyStr | None = None
    arguments: tuple[LogicExpression, ...] = ()

    @model_validator(mode="after")
    def validate_shape(self) -> LogicExpression:
        literals = {LogicOperator.BOOLEAN, LogicOperator.INTEGER, LogicOperator.RATIONAL}
        unary = {LogicOperator.NOT}
        binary = {
            LogicOperator.XOR,
            LogicOperator.IMPLIES,
            LogicOperator.EQUALS,
            LogicOperator.NOT_EQUALS,
            LogicOperator.LESS_THAN,
            LogicOperator.LESS_OR_EQUAL,
            LogicOperator.GREATER_THAN,
            LogicOperator.GREATER_OR_EQUAL,
            LogicOperator.ADD,
            LogicOperator.SUBTRACT,
            LogicOperator.MULTIPLY,
            LogicOperator.DIVIDE,
        }
        if self.operator in literals and (self.value is None or self.arguments or self.name):
            raise ValueError("logic literal has invalid shape")
        if self.operator is LogicOperator.VARIABLE and (
            not self.name or self.arguments or self.value is not None
        ):
            raise ValueError("logic variable has invalid shape")
        if self.operator in unary and len(self.arguments) != 1:
            raise ValueError("unary logic operator requires one argument")
        if self.operator in binary and len(self.arguments) != 2:
            raise ValueError("binary logic operator requires two arguments")
        if self.operator in {LogicOperator.AND, LogicOperator.OR} and len(self.arguments) < 2:
            raise ValueError("Boolean aggregate requires at least two arguments")
        return self

    def enforce_limits(self, limits: LogicLimits) -> None:
        nodes = 0
        variables: set[str] = set()

        def visit(item: LogicExpression, depth: int) -> None:
            nonlocal nodes
            nodes += 1
            if nodes > limits.maximum_nodes or depth > limits.maximum_depth:
                raise ValueError("logic AST exceeds configured limits")
            if item.operator is LogicOperator.VARIABLE and item.name:
                variables.add(item.name)
            if len(variables) > limits.maximum_variables:
                raise ValueError("logic AST contains too many variables")
            for child in item.arguments:
                visit(child, depth + 1)

        visit(self, 1)
