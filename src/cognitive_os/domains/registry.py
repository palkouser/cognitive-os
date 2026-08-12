"""Problem-type registry: solvers, verifiers, skills, strategies, and budgets.

One table maps every supported task class to exactly one solver and one verifier
bundle. Resolution is deterministic and total: an unregistered problem type fails
with `UNSUPPORTED_PROBLEM_TYPE` before anything executes, so an unknown task can
never fall through to an unbounded path.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from decimal import Decimal
from fractions import Fraction
from typing import Any

from cognitive_os.domain.descriptors import (
    RELEASED_DOMAIN_CAPABILITIES,
    RELEASED_DOMAIN_IDS,
    DomainCapabilityRequirements,
    DomainDescriptorV1,
)
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
    #: The general identity, always present: a stable string domain id. For the four
    #: released domains it is the enum value verbatim, which is why moving the snapshot
    #: onto it changed no hash. For a descriptor-registered domain it is the only identity
    #: there is, and `domain` below is `None`.
    domain_id: str
    #: The released adapter's closed vocabulary (§2.3), or `None` for a domain that exists
    #: only as a descriptor. It is deliberately not widened to `DomainKind | str`: the enum
    #: means "one of the four released domains", and a nullable field says that plainly
    #: where a union would quietly invite `isinstance` branches back in.
    domain: DomainKind | None
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


def _hash_over(items: tuple[ProblemTypeEntry, ...]) -> str:
    from hashlib import sha256

    payload = "|".join(
        f"{item.problem_type}:{item.domain_id}:{item.answer_type.value}:"
        f"{','.join(item.required_verifiers)}:{','.join(item.skills)}:{','.join(item.strategies)}"
        for item in items
    )
    return sha256(payload.encode()).hexdigest()


def snapshot_hash() -> str:
    """A fingerprint of the whole resolution surface, pilots included.

    **A registry that gained a domain is allowed to say so** (Sprint 22A W2 decision
    S22A-030). A fingerprint that deliberately omitted part of the table would let two
    different resolution surfaces share one hash, which is the failure this hash exists to
    make impossible. The claim "the four released domains resolve identically" is a
    different, narrower claim, and it has its own function below.
    """
    return _hash_over(entries())


def released_snapshot_hash() -> str:
    """The four released domains' resolution surface, which no registration can move.

    This is what Sprint 22A's sealed backward-compatibility contract actually asserts, and
    it reproduces the sealed value byte-identically however many descriptor-registered
    domains a process has admitted. Registering a pilot must be unable to change it; if it
    ever does, a released domain changed, and that is the whole point of the check.
    """
    return _hash_over(tuple(item for item in entries() if item.domain is not None))


def problem_types(domain: DomainKind) -> tuple[str, ...]:
    return tuple(item.problem_type for item in entries() if item.domain is domain)


def problem_types_for(domain_id: str) -> tuple[str, ...]:
    """The same question by string id, so a caller need not know whether a domain is an
    enum member. The released four answer identically through either door."""
    return tuple(item.problem_type for item in entries() if item.domain_id == domain_id)


def domain_ids() -> tuple[str, ...]:
    """Every domain the registry currently resolves, released and descriptor-registered."""
    return tuple(sorted({item.domain_id for item in entries()}))


_DEFAULT_BUDGET = ResourceBudget()

_MATH = (
    ("long-multiplication", AnswerType.EXACT, solvers.solve_long_multiplication),
    ("long-division", AnswerType.EXACT, solvers.solve_long_division),
    ("fraction-arithmetic", AnswerType.EXACT, solvers.solve_exact_expression),
    ("rational-arithmetic", AnswerType.EXACT, solvers.solve_exact_expression),
    (
        "algebraic-simplification",
        AnswerType.SYMBOLIC,
        solvers.solve_algebraic_simplification,
    ),
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

#: **The seam** (Sprint 22A W1, §3.1). The per-domain capability tables that used to live
#: here are now descriptor data in `domain/descriptors.py`, keyed by string domain id, and the
#: registry reads them through the adapter. Two things follow, and both are the point of the
#: sprint: a domain's capabilities are data rather than a branch on an enum, and a domain that
#: is not an enum member can carry exactly the same metadata by the same route.
#:
#: The move is provably lossless rather than merely careful — `snapshot_hash()` and the four
#: derived descriptor content hashes are unchanged against the record sealed before it.


def _capabilities(domain: DomainKind) -> DomainCapabilityRequirements:
    """The released capabilities for one domain, by string id, through the adapter."""
    return RELEASED_DOMAIN_CAPABILITIES[RELEASED_DOMAIN_IDS[domain]]


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
    capabilities = _capabilities(domain)
    for problem_type, answer_type, solver in specification:
        register(
            ProblemTypeEntry(
                problem_type=problem_type,
                domain_id=RELEASED_DOMAIN_IDS[domain],
                domain=domain,
                answer_type=answer_type,
                solver=solver,
                checker=solvers.CHECKERS[problem_type],
                required_verifiers=capabilities.verifier_capabilities,
                required_tools=capabilities.tool_capabilities,
                skills=capabilities.skills,
                strategies=capabilities.strategies,
                budget=_DEFAULT_BUDGET,
                checker_only_inputs=_CHECKER_ONLY_INPUTS.get(problem_type, ()),
            )
        )


_register_domain(DomainKind.MATHEMATICS, _MATH)
_register_domain(DomainKind.PHYSICS, _PHYSICS)
_register_domain(DomainKind.LOGIC, _LOGIC)
_register_domain(DomainKind.CODING, _CODING)


# --------------------------------------------------------------------------
# Descriptor-registered domains (Sprint 22A W2, §3.1)
# --------------------------------------------------------------------------
#
# A descriptor is data and a kernel is code, and this is the one place they meet. The
# descriptor says which problem types a domain claims; the caller supplies the installed
# kernels by importing the module that defines them. Registration is therefore the join,
# and it fails closed when the two disagree: a domain that claims a problem type nobody
# implements does not half-register, it is refused with the names listed.
#
# Nothing here registers at import time. A process that never registered a descriptor
# resolves exactly the released twenty-eight entries, which is why `released_snapshot_hash`
# and `snapshot_hash` agree in a default process and are allowed to differ in one that
# admitted a pilot.


@dataclass(frozen=True, slots=True)
class DomainKernel:
    """One installed deterministic implementation pair, named by its problem type.

    Solver and checker stay two separate routes for a descriptor-registered domain exactly
    as they are for a released one: the checker recomputes rather than reading the solver's
    answer, so a pilot cannot accept itself any more than the released four can.
    """

    answer_type: AnswerType
    solver: SolverFn
    checker: CheckFn
    checker_only_inputs: tuple[str, ...] = ()


class DescriptorDomainError(ValueError):
    """A descriptor could not be admitted to the problem-type registry. `diagnostics`
    carries one finding per line, the same report shape the package boundary returns."""

    def __init__(self, diagnostics: tuple[str, ...]) -> None:
        super().__init__("; ".join(diagnostics))
        self.diagnostics = diagnostics


#: (`domain_id`, `revision`) of every descriptor admitted in this process, in order.
_DESCRIPTOR_DOMAINS: dict[tuple[str, int], tuple[str, ...]] = {}


def registered_descriptor_domains() -> tuple[tuple[str, int], ...]:
    return tuple(_DESCRIPTOR_DOMAINS)


def register_descriptor_domain(
    descriptor: DomainDescriptorV1,
    kernels: Mapping[str, DomainKernel],
) -> tuple[ProblemTypeEntry, ...]:
    """Admit one validated descriptor's problem types to the released resolution table.

    Every refusal is decided before a single entry is written. A domain that registered
    two of its three problem types and then hit a collision would leave the registry in a
    state no descriptor describes — the W1-F2 lesson in a different table — so the checks
    below run first and the writes happen only once all of them pass.
    """
    diagnostics: list[str] = []
    domain_id = descriptor.domain_id

    if domain_id in set(RELEASED_DOMAIN_IDS.values()):
        diagnostics.append(
            f"domain_id: {domain_id!r} is a released domain; a released domain is derived "
            "through the adapter and its revisions are a governance path, not a package"
        )
    if not descriptor.problem_types:
        diagnostics.append(
            "problem_types: a descriptor with no problem types is a namespace, and a "
            "namespace has nothing to register in a problem-type registry"
        )
    if (domain_id, descriptor.revision) in _DESCRIPTOR_DOMAINS:
        diagnostics.append(
            f"identity: {domain_id!r} revision {descriptor.revision} is already registered; "
            "a duplicate key is refused rather than replacing its predecessor"
        )

    missing = tuple(name for name in descriptor.problem_types if name not in kernels)
    if missing:
        diagnostics.append(
            f"kernels: no installed kernel for {sorted(missing)}; a descriptor may not "
            "claim a solver surface that no code implements"
        )
    taken = tuple(name for name in descriptor.problem_types if name in _ENTRIES)
    if taken:
        owners = ", ".join(f"{name} (owned by {_ENTRIES[name].domain_id!r})" for name in taken)
        diagnostics.append(f"problem_types: already registered: {owners}")

    if diagnostics:
        raise DescriptorDomainError(tuple(diagnostics))

    admitted = []
    for name in descriptor.problem_types:
        kernel = kernels[name]
        entry = ProblemTypeEntry(
            problem_type=name,
            domain_id=domain_id,
            domain=None,
            answer_type=kernel.answer_type,
            solver=kernel.solver,
            checker=kernel.checker,
            required_verifiers=descriptor.capabilities.verifier_capabilities,
            required_tools=descriptor.capabilities.tool_capabilities,
            skills=descriptor.capabilities.skills,
            strategies=descriptor.capabilities.strategies,
            budget=_DEFAULT_BUDGET,
            checker_only_inputs=kernel.checker_only_inputs,
        )
        register(entry)
        admitted.append(entry)
    _DESCRIPTOR_DOMAINS[(domain_id, descriptor.revision)] = descriptor.problem_types
    return tuple(admitted)


def exact_decimal(value: Fraction) -> Decimal:
    return Decimal(value.numerator) / Decimal(value.denominator)


__all__ = [
    "DescriptorDomainError",
    "DomainKernel",
    "ProblemTypeEntry",
    "UnsupportedProblemType",
    "VerificationDisposition",
    "domain_ids",
    "entries",
    "problem_types",
    "problem_types_for",
    "register_descriptor_domain",
    "registered_descriptor_domains",
    "released_snapshot_hash",
    "resolve",
    "snapshot_hash",
]
