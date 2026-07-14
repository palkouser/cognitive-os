"""SymPy adapters constructed exclusively from the safe typed expression AST."""

from __future__ import annotations

import asyncio
import multiprocessing
from time import monotonic
from typing import Any, cast

from cognitive_os.domain.common import ErrorInfo
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
from .expression_ast import (
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
from .parsing import ExpressionLimits, UnsafeExpressionError, parse_expression


def _sympy() -> Any:
    import sympy  # type: ignore[import-untyped]

    return sympy


def to_sympy(expression: Expression) -> Any:
    sympy = _sympy()
    if isinstance(expression, Integer):
        return sympy.Integer(expression.value)
    if isinstance(expression, Rational):
        return sympy.Rational(expression.value.numerator, expression.value.denominator)
    if isinstance(expression, DecimalValue):
        return sympy.Rational(str(expression.value))
    if isinstance(expression, Symbol):
        return sympy.Symbol(expression.name)
    if isinstance(expression, Constant):
        return {"pi": sympy.pi, "e": sympy.E}[expression.name]
    if isinstance(expression, UnaryExpression):
        operand = to_sympy(expression.operand)
        return operand if expression.operator == "positive" else -operand
    if isinstance(expression, BinaryExpression):
        left, right = to_sympy(expression.left), to_sympy(expression.right)
        operations = {
            "add": lambda: left + right,
            "subtract": lambda: left - right,
            "multiply": lambda: left * right,
            "divide": lambda: left / right,
            "power": lambda: left**right,
            "equal": lambda: sympy.Eq(left, right),
        }
        return operations[expression.operator]()
    if isinstance(expression, FunctionExpression):
        functions = {
            "abs": sympy.Abs,
            "sqrt": sympy.sqrt,
            "sin": sympy.sin,
            "cos": sympy.cos,
            "tan": sympy.tan,
            "exp": sympy.exp,
            "log": sympy.log,
        }
        return functions[expression.name](to_sympy(expression.argument))
    raise TypeError("unsupported typed mathematical expression")


def _descriptor(verifier_id: str) -> VerifierDescriptor:
    return VerifierDescriptor(
        verifier_id=verifier_id,
        version="1",
        display_name=verifier_id.replace(".", " ").title(),
        description="Safely verify typed symbolic mathematical evidence.",
        kind=VerifierKind.MATHEMATICS,
        capabilities=(
            VerifierCapability(
                capability_id=f"{verifier_id}.v1",
                subject_type=VerificationSubjectType.MATHEMATICAL_EXPRESSION,
                problem_domains=(ProblemDomain.MATHEMATICS,),
                criterion_types=(CriterionType.DOMAIN_VERIFIER,),
            ),
        ),
        determinism=VerifierDeterminism.DETERMINISTIC,
        risk_level=RiskLevel.LOW,
        default_timeout_seconds=10,
        maximum_input_bytes=65_536,
        configuration_schema={"type": "object"},
    )


def _equivalence_worker(
    actual_source: str,
    expected_source: str,
    limits: ExpressionLimits,
    connection: Any,
) -> None:
    try:
        actual = to_sympy(parse_expression(actual_source, limits))
        expected = to_sympy(parse_expression(expected_source, limits))
        reduced = _sympy().simplify(actual - expected)
        equality = True if reduced == 0 else actual.equals(expected)
        connection.send(("ok", equality))
    except Exception as error:
        connection.send(("error", type(error).__name__, str(error)))
    finally:
        connection.close()


async def _bounded_equivalence(
    actual_source: str,
    expected_source: str,
    limits: ExpressionLimits,
    timeout_seconds: float,
) -> bool | None:
    context = multiprocessing.get_context("spawn")
    parent, child = context.Pipe(duplex=False)
    process = context.Process(
        target=_equivalence_worker,
        args=(actual_source, expected_source, limits, child),
        daemon=True,
    )
    process.start()
    child.close()
    deadline = monotonic() + timeout_seconds
    while process.is_alive() and monotonic() < deadline:
        await asyncio.sleep(0.01)
    if process.is_alive():
        process.terminate()
        process.join(timeout=1)
        parent.close()
        raise TimeoutError
    process.join(timeout=1)
    if not parent.poll():
        parent.close()
        raise RuntimeError("symbolic worker exited without a result")
    payload = parent.recv()
    parent.close()
    if payload[0] == "error":
        raise ValueError(f"symbolic worker rejected input: {payload[1]}")
    return cast(bool | None, payload[1])


class SymbolicEquivalenceVerifier(BaseVerifier):
    def __init__(self) -> None:
        super().__init__(_descriptor("mathematics.symbolic_equivalence"))

    async def verify(self, request: VerificationRequest) -> VerifierResult:
        try:
            actual_source = request.subject.inline_value
            expected_source = request.configuration["expected"]
            if not isinstance(actual_source, str) or not isinstance(expected_source, str):
                raise UnsafeExpressionError("symbolic inputs must be strings")
            limits = ExpressionLimits(
                maximum_nodes=int(
                    cast(int | str, request.configuration.get("maximum_expression_nodes", 512))
                ),
                maximum_symbols=int(
                    cast(int | str, request.configuration.get("maximum_symbol_count", 32))
                ),
            )
            equality = await _bounded_equivalence(
                actual_source,
                expected_source,
                limits,
                float(
                    cast(
                        int | float | str,
                        request.configuration.get("timeout_seconds", 10),
                    )
                ),
            )
            if equality is True:
                return self.result(request, VerifierStatus.PASSED, score=1)
            if equality is None:
                return self.result(request, VerifierStatus.UNVERIFIABLE)
            return self.result(
                request,
                VerifierStatus.FAILED,
                code="mathematics.not_equivalent",
                message="symbolic expressions are not equivalent",
                score=0,
            )
        except TimeoutError:
            return self.result(
                request,
                VerifierStatus.ERROR,
                error=ErrorInfo(code="symbolic_timeout", message="symbolic verification timed out"),
            )
        except (KeyError, TypeError, ValueError, UnsafeExpressionError) as error:
            return self.result(
                request,
                VerifierStatus.ERROR,
                error=ErrorInfo(code="unsafe_expression", message=str(error)),
            )


class EquationSolutionVerifier(BaseVerifier):
    def __init__(self) -> None:
        super().__init__(_descriptor("mathematics.equation_solution"))

    async def verify(self, request: VerificationRequest) -> VerifierResult:
        try:
            equation_source = request.configuration["equation"]
            variable_name = request.configuration["variable"]
            candidate_source = request.subject.inline_value
            if not all(
                isinstance(item, str) for item in (equation_source, variable_name, candidate_source)
            ):
                raise UnsafeExpressionError("equation inputs must be strings")
            equation = to_sympy(parse_expression(cast(str, equation_source)))
            candidate = to_sympy(parse_expression(cast(str, candidate_source)))
            if not getattr(equation, "is_Equality", False):
                raise UnsafeExpressionError("configured equation must use equality")
            variable = _sympy().Symbol(variable_name)
            residual = _sympy().simplify((equation.lhs - equation.rhs).subs(variable, candidate))
            passed = residual == 0
            return self.result(
                request,
                VerifierStatus.PASSED if passed else VerifierStatus.FAILED,
                code="mathematics.extraneous_solution",
                message="candidate does not satisfy the equation",
                score=1 if passed else 0,
            )
        except (KeyError, TypeError, ValueError, UnsafeExpressionError) as error:
            return self.result(
                request,
                VerifierStatus.ERROR,
                error=ErrorInfo(code="invalid_equation", message=str(error)),
            )
