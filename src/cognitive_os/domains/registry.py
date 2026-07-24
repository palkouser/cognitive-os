"""Problem-type registry: solvers, verifiers, skills, strategies, and budgets.

One table maps every supported task class to exactly one solver and one verifier
bundle. Resolution is deterministic and total: an unregistered problem type fails
with `UNSUPPORTED_PROBLEM_TYPE` before anything executes, so an unknown task can
never fall through to an unbounded path.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from decimal import Decimal
from fractions import Fraction
from typing import Any

from cognitive_os.domain.domains import (
    AnswerType,
    DomainKind,
    ResourceBudget,
    VerificationDisposition,
)

from . import solvers

#: A solver turns formal inputs into ordered derivation steps plus an answer.
type SolverFn = Callable[[dict[str, Any], ResourceBudget], solvers.Solution]
#: A checker independently recomputes and judges a candidate answer.
type CheckFn = Callable[[dict[str, Any], solvers.Candidate, ResourceBudget], solvers.CheckSet]


@dataclass(frozen=True, slots=True)
class ProblemTypeEntry:
    problem_type: str
    domain: DomainKind
    answer_type: AnswerType
    solver: SolverFn
    checker: CheckFn
    required_verifiers: tuple[str, ...]
    required_tools: tuple[str, ...]
    skills: tuple[str, ...]
    strategies: tuple[str, ...]
    budget: ResourceBudget


class UnsupportedProblemType(LookupError):
    """Raised when no entry resolves; never degraded into a best-effort attempt."""


_ENTRIES: dict[str, ProblemTypeEntry] = {}


def register(entry: ProblemTypeEntry) -> None:
    if entry.problem_type in _ENTRIES:
        raise ValueError(f"duplicate problem type {entry.problem_type!r}")
    _ENTRIES[entry.problem_type] = entry


def resolve(problem_type: str) -> ProblemTypeEntry:
    try:
        return _ENTRIES[problem_type]
    except KeyError as error:
        raise UnsupportedProblemType(problem_type) from error


def entries() -> tuple[ProblemTypeEntry, ...]:
    """Deterministically ordered snapshot."""
    return tuple(_ENTRIES[key] for key in sorted(_ENTRIES))


def snapshot_hash() -> str:
    from hashlib import sha256

    payload = "|".join(
        f"{item.problem_type}:{item.domain.value}:{item.answer_type.value}:"
        f"{','.join(item.required_verifiers)}:{','.join(item.skills)}:{','.join(item.strategies)}"
        for item in entries()
    )
    return sha256(payload.encode()).hexdigest()


def problem_types(domain: DomainKind) -> tuple[str, ...]:
    return tuple(item.problem_type for item in entries() if item.domain is domain)


_DEFAULT_BUDGET = ResourceBudget()

_MATH = (
    ("long-multiplication", AnswerType.EXACT, solvers.solve_long_multiplication),
    ("long-division", AnswerType.EXACT, solvers.solve_long_division),
    ("fraction-arithmetic", AnswerType.EXACT, solvers.solve_exact_expression),
    ("rational-arithmetic", AnswerType.EXACT, solvers.solve_exact_expression),
    ("algebraic-simplification", AnswerType.SYMBOLIC, solvers.solve_algebraic_simplification),
    ("linear-equation", AnswerType.EXACT, solvers.solve_linear_equation),
    ("polynomial-equation", AnswerType.STRUCTURED, solvers.solve_quadratic_equation),
    ("symbolic-equivalence", AnswerType.BOOLEAN, solvers.solve_symbolic_equivalence),
    ("exact-versus-approximate", AnswerType.APPROXIMATE, solvers.solve_approximation),
)

_PHYSICS = (
    ("unit-conversion", AnswerType.QUANTITY, solvers.solve_unit_conversion),
    ("dimensional-analysis", AnswerType.BOOLEAN, solvers.solve_dimensional_analysis),
    ("quantity-calculation", AnswerType.QUANTITY, solvers.solve_quantity_calculation),
    ("model-selection", AnswerType.STRUCTURED, solvers.solve_model_selection),
    ("conservation-check", AnswerType.BOOLEAN, solvers.solve_conservation),
    ("limiting-case", AnswerType.STRUCTURED, solvers.solve_limiting_case),
    ("order-of-magnitude", AnswerType.STRUCTURED, solvers.solve_order_of_magnitude),
    ("significant-figures", AnswerType.APPROXIMATE, solvers.solve_significant_figures),
)

_LOGIC = (
    ("truth-table", AnswerType.STRUCTURED, solvers.solve_truth_table),
    ("validity-check", AnswerType.BOOLEAN, solvers.solve_validity),
    ("satisfiability", AnswerType.SATISFIABLE, solvers.solve_satisfiability),
    ("constraint-satisfaction", AnswerType.SATISFIABLE, solvers.solve_satisfiability),
    ("consistency-check", AnswerType.BOOLEAN, solvers.solve_consistency),
    ("counterexample-search", AnswerType.COUNTEREXAMPLE, solvers.solve_counterexample),
    ("sequence-induction", AnswerType.STRUCTURED, solvers.solve_sequence_induction),
    ("competing-hypotheses", AnswerType.STRUCTURED, solvers.solve_sequence_induction),
)

_DOMAIN_METADATA: dict[DomainKind, tuple[tuple[str, ...], tuple[str, ...], tuple[str, ...]]] = {
    DomainKind.MATHEMATICS: (
        ("mathematics.exact_arithmetic", "mathematics.numeric"),
        ("exact-arithmetic-decomposition", "cross-domain-result-review"),
        ("decompose-compute-verify", "two-independent-methods"),
    ),
    DomainKind.PHYSICS: (
        ("physics.dimension", "physics.quantity"),
        ("unit-aware-physics-calculation", "dimensional-analysis-review"),
        ("units-first-physics-modelling", "assumption-mismatch-detection"),
    ),
    DomainKind.LOGIC: (
        ("logic.truth_table", "logic.counterexample"),
        ("logic-formalization", "constraint-solving"),
        ("hypothesis-constraint-solver-counterexample", "two-independent-methods"),
    ),
}


def _register_domain(
    domain: DomainKind,
    specification: tuple[tuple[str, AnswerType, SolverFn], ...],
) -> None:
    verifiers, skills, strategies = _DOMAIN_METADATA[domain]
    for problem_type, answer_type, solver in specification:
        register(
            ProblemTypeEntry(
                problem_type=problem_type,
                domain=domain,
                answer_type=answer_type,
                solver=solver,
                checker=solvers.CHECKERS[problem_type],
                required_verifiers=verifiers,
                required_tools=(f"{domain.value}.kernel",),
                skills=skills,
                strategies=strategies,
                budget=_DEFAULT_BUDGET,
            )
        )


_register_domain(DomainKind.MATHEMATICS, _MATH)
_register_domain(DomainKind.PHYSICS, _PHYSICS)
_register_domain(DomainKind.LOGIC, _LOGIC)


def exact_decimal(value: Fraction) -> Decimal:
    return Decimal(value.numerator) / Decimal(value.denominator)


__all__ = [
    "ProblemTypeEntry",
    "UnsupportedProblemType",
    "VerificationDisposition",
    "entries",
    "problem_types",
    "resolve",
    "snapshot_hash",
]
