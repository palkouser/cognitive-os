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
    #: Formal-input keys the checker needs and the solver must never see. The
    #: coding domain carries its golden answer in the case inputs so the checker
    #: has an independent reference; handing that to the solver would make every
    #: baseline trivially perfect and the 21D headroom measurement meaningless.
    checker_only_inputs: tuple[str, ...] = ()


def solver_inputs(entry: ProblemTypeEntry, inputs: dict[str, Any]) -> dict[str, Any]:
    """The subset of formal inputs a solver is allowed to read."""
    if not entry.checker_only_inputs:
        return inputs
    withheld = set(entry.checker_only_inputs)
    return {key: value for key, value in inputs.items() if key not in withheld}


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

#: Sprint 21C.1, fourth domain. All three task classes answer with a structured
#: value (a repaired source string or a list of selected test names). The
#: solver is the registered baseline; the checker is the independent route.
_CODING = (
    ("pytest-repair", AnswerType.STRUCTURED, solvers.solve_pytest_repair),
    ("assertion-repair", AnswerType.STRUCTURED, solvers.solve_assertion_repair),
    ("test-selection", AnswerType.STRUCTURED, solvers.solve_test_selection),
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
    DomainKind.CODING: (
        # The check capabilities name what the in-process checker actually does:
        # compare the candidate against the case's golden reference, and confirm
        # that every declared edit landed. Deliberately NOT `coding.pytest` —
        # that capability means sandboxed pytest execution everywhere else in
        # the system (`verification/coding/commands.py`), and a check that never
        # ran pytest must not borrow its name. See ADR 0085.
        ("coding.golden_equality", "coding.required_checks"),
        # Two permitted skills (the python-repair and focused-tests families)
        # keep selection tight and the ADR 0084 statistic-binding story uniform.
        ("verification-driven-python-repair", "focused-test-execution"),
        # Registered strategies only — both already declare exactly these two
        # skills in `strategies/`.
        ("python-bug-fix", "verification-driven-repair"),
    ),
}


#: The tool capabilities a problem type in this domain needs in order to run.
#: Solvers cite one of these in `tool_evidence` as `<capability>:<operation>`.
#: Coding declares two: `coding.pytest` is what a real repair of these tasks
#: needs and what the permitted skills match their tool precondition against,
#: while `coding.kernel` is the deterministic in-process solve the Sprint 21C.1
#: baseline actually performs and cites.
_REQUIRED_TOOLS: dict[DomainKind, tuple[str, ...]] = {
    DomainKind.MATHEMATICS: ("mathematics.kernel",),
    DomainKind.PHYSICS: ("physics.kernel",),
    DomainKind.LOGIC: ("logic.kernel",),
    DomainKind.CODING: ("coding.pytest", "coding.kernel"),
}

#: Formal-input keys withheld from the solver, per problem type. Only the coding
#: domain needs them: its cases carry the golden answer so the checker has an
#: independent reference.
_CHECKER_ONLY_INPUTS: dict[str, tuple[str, ...]] = {
    "pytest-repair": ("golden_source",),
    "assertion-repair": ("golden_source",),
    "test-selection": ("selected_tests",),
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
                required_tools=_REQUIRED_TOOLS[domain],
                skills=skills,
                strategies=strategies,
                budget=_DEFAULT_BUDGET,
                checker_only_inputs=_CHECKER_ONLY_INPUTS.get(problem_type, ()),
            )
        )


_register_domain(DomainKind.MATHEMATICS, _MATH)
_register_domain(DomainKind.PHYSICS, _PHYSICS)
_register_domain(DomainKind.LOGIC, _LOGIC)
_register_domain(DomainKind.CODING, _CODING)


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
