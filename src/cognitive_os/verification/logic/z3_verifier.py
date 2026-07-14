"""Bounded typed Z3 verification adapters."""

from __future__ import annotations

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
from .ast import LogicExpression, LogicLimits
from .mapping import _z3, to_z3


def _descriptor(verifier_id: str) -> VerifierDescriptor:
    return VerifierDescriptor(
        verifier_id=verifier_id,
        version="1",
        display_name=verifier_id.replace(".", " ").title(),
        description="Verify a typed bounded logic AST with Z3.",
        kind=VerifierKind.LOGIC,
        capabilities=(
            VerifierCapability(
                capability_id=f"{verifier_id}.v1",
                subject_type=VerificationSubjectType.LOGICAL_PROBLEM,
                problem_domains=(ProblemDomain.LOGIC,),
                criterion_types=(CriterionType.DOMAIN_VERIFIER,),
            ),
        ),
        determinism=VerifierDeterminism.DETERMINISTIC,
        risk_level=RiskLevel.LOW,
        default_timeout_seconds=10,
        maximum_input_bytes=262_144,
        configuration_schema={"type": "object"},
    )


def _parse(value: Any) -> LogicExpression:
    if isinstance(value, str):
        raise ValueError("raw SMT-LIB and string logic programs are forbidden")
    expression = LogicExpression.model_validate(value)
    expression.enforce_limits(LogicLimits())
    return expression


class _Z3Verifier(BaseVerifier):
    mode: str

    async def verify(self, request: VerificationRequest) -> VerifierResult:
        try:
            z3 = _z3()
            timeout_ms = int(
                cast(
                    int | str,
                    request.configuration.get("timeout_milliseconds", 10_000),
                )
            )
            if not 1 <= timeout_ms <= 60_000:
                raise ValueError("solver timeout is outside the allowed range")
            solver = z3.Solver()
            solver.set(timeout=timeout_ms)
            value = cast(Any, request.subject.inline_value)
            if self.mode in {"satisfiable", "contradiction"}:
                expressions = value if isinstance(value, list) else [value]
                if len(expressions) > 256:
                    raise ValueError("too many logic constraints")
                solver.add(*(to_z3(_parse(item)) for item in expressions))
                result = solver.check()
                expected = z3.sat if self.mode == "satisfiable" else z3.unsat
            elif self.mode == "implication":
                if not isinstance(value, dict):
                    raise ValueError("implication subject must be an object")
                premises = [_parse(item) for item in value.get("premises", [])]
                conclusion = _parse(value["conclusion"])
                solver.add(*(to_z3(item) for item in premises), z3.Not(to_z3(conclusion)))
                result, expected = solver.check(), z3.unsat
            else:
                if not isinstance(value, dict):
                    raise ValueError("equivalence subject must be an object")
                left, right = to_z3(_parse(value["left"])), to_z3(_parse(value["right"]))
                solver.add(z3.Xor(left, right))
                result, expected = solver.check(), z3.unsat
            if result == z3.unknown:
                return self.result(request, VerifierStatus.UNVERIFIABLE)
            passed = result == expected
            return self.result(
                request,
                VerifierStatus.PASSED if passed else VerifierStatus.FAILED,
                code=f"logic.{self.mode}.failed",
                message=f"logic {self.mode} expectation was not satisfied",
                score=1 if passed else 0,
            )
        except (KeyError, TypeError, ValueError) as error:
            return self.result(
                request,
                VerifierStatus.ERROR,
                error=ErrorInfo(code="invalid_logic_ast", message=str(error)),
            )


class SatisfiabilityVerifier(_Z3Verifier):
    mode = "satisfiable"

    def __init__(self) -> None:
        super().__init__(_descriptor("logic.satisfiable"))


class ContradictionVerifier(_Z3Verifier):
    mode = "contradiction"

    def __init__(self) -> None:
        super().__init__(_descriptor("logic.contradiction"))


class ImplicationVerifier(_Z3Verifier):
    mode = "implication"

    def __init__(self) -> None:
        super().__init__(_descriptor("logic.implication"))


class EquivalenceVerifier(_Z3Verifier):
    mode = "equivalence"

    def __init__(self) -> None:
        super().__init__(_descriptor("logic.equivalence"))
