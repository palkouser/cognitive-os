"""Credential-free deterministic cross-domain benchmark cases.

Every case is built in-process from typed inputs, so the mandatory path needs no
network, no credentials, no GPU, and none of the optional domain extras.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import NAMESPACE_URL, uuid5

from cognitive_os.domain.domains import (
    AnswerType,
    DomainBenchmarkCase,
    DomainKind,
    DomainProblem,
    DomainVerificationPlan,
    ProvenanceRef,
    ResourceBudget,
    VerificationDisposition,
)

from .registry import resolve, solver_inputs
from .solvers import Candidate

FIXTURE_TIME = datetime(2026, 7, 24, tzinfo=UTC)

#: Every fixture is written for this repository, so provenance is uniform and no
#: imported third-party benchmark material is redistributed.
PROVENANCE = ProvenanceRef(
    source="cognitive-os/sprint-20-fixtures",
    revision="1",
    licence="Apache-2.0",
    redistributable=True,
    contamination_notes="Authored for Sprint 20; not derived from any public benchmark set.",
    effective_date=FIXTURE_TIME,
)

_UNKNOWNS: dict[str, tuple[str, ...]] = {
    "long-multiplication": ("product",),
    "long-division": ("quotient", "remainder"),
    "fraction-arithmetic": ("value",),
    "rational-arithmetic": ("value",),
    "algebraic-simplification": ("simplified_form",),
    "linear-equation": ("x",),
    "polynomial-equation": ("roots",),
    "symbolic-equivalence": ("equivalent",),
    "exact-versus-approximate": ("value",),
    "unit-conversion": ("converted_magnitude",),
    "dimensional-analysis": ("consistent",),
    "quantity-calculation": ("quantity",),
    "model-selection": ("model",),
    "conservation-check": ("conserved",),
    "limiting-case": ("limit_values",),
    "order-of-magnitude": ("exponent",),
    "significant-figures": ("rounded_value",),
    "truth-table": ("table",),
    "validity-check": ("valid",),
    "satisfiability": ("status",),
    "constraint-satisfaction": ("assignment",),
    "consistency-check": ("consistent",),
    "counterexample-search": ("counterexample",),
    "sequence-induction": ("next_term",),
    "competing-hypotheses": ("hypotheses",),
    # Sprint 21C.1, coding domain. The names match the structured answer keys
    # the solvers actually produce.
    "pytest-repair": ("repaired_source",),
    "assertion-repair": ("repaired_source",),
    "test-selection": ("selected_tests",),
}

_UNITS: dict[str, tuple[str, ...]] = {
    "unit-conversion": ("source_unit", "target_unit"),
    "dimensional-analysis": ("left_unit", "right_unit"),
    "quantity-calculation": ("result_unit",),
    "model-selection": ("dimensionless",),
    "conservation-check": ("J",),
    "limiting-case": ("dimensionless",),
    "order-of-magnitude": ("dimensionless",),
    "significant-figures": ("m",),
}


def build_case(
    case_id: str,
    problem_type: str,
    formal_inputs: dict[str, Any],
    *,
    statement: str,
    difficulty: str = "baseline",
    expected_disposition: VerificationDisposition = VerificationDisposition.PASS,
    assumptions: tuple[str, ...] = (),
    budget: ResourceBudget | None = None,
) -> DomainBenchmarkCase:
    """Assemble a fully typed case whose expected answer is the solver's own output.

    Ground truth comes from the solver, but acceptance is decided by the separate
    checker, so a case can only pass if two independent routes agree.
    """
    entry = resolve(problem_type)
    if entry.domain is None:
        # `DomainBenchmarkCase` and `DomainProblem` carry `DomainKind`, so this builder can
        # only speak for the four released domains. A descriptor-registered domain is not a
        # missing feature here, it is a different shape (Sprint 22A W2): refusing by name
        # beats constructing a case whose `domain` field would fail validation one frame later.
        raise ValueError(
            f"problem type {problem_type!r} belongs to descriptor-registered domain "
            f"{entry.domain_id!r}; benchmark fixtures are built for the released domains"
        )
    resource_budget = budget or entry.budget
    problem_id = uuid5(NAMESPACE_URL, f"domain-problem:{case_id}")
    # `knowns` is the human/agent-readable statement of what is given. Inputs the
    # checker alone is entitled to — the coding domain's golden answer — are not
    # given, and recording them here would hand the answer to anything that reads
    # the problem instead of solving it.
    given = solver_inputs(entry, dict(formal_inputs))
    problem = DomainProblem(
        problem_id=problem_id,
        domain=entry.domain,
        problem_type=problem_type,
        statement=statement,
        formal_inputs=formal_inputs,
        knowns={key: str(value) for key, value in given.items()},
        unknowns=_UNKNOWNS[problem_type],
        assumptions=assumptions or ("inputs are exact and bounded",),
        required_units=_UNITS.get(problem_type, ()) if entry.domain is DomainKind.PHYSICS else (),
        required_tools=entry.required_tools,
        required_verifiers=entry.required_verifiers,
        source_refs=(PROVENANCE,),
        created_at=FIXTURE_TIME,
    )
    plan = DomainVerificationPlan(
        problem_id=problem_id,
        required_capabilities=entry.required_verifiers,
        forbidden_operations=("eval", "exec", "network", "raw_smtlib"),
        resource_budget=resource_budget,
    )
    solution = entry.solver(given, resource_budget)
    expected_answer = _answer_from(problem_id, solution.candidate)
    return DomainBenchmarkCase(
        case_id=case_id,
        domain=entry.domain,
        problem_type=problem_type,
        difficulty=difficulty,
        problem=problem,
        plan=plan,
        expected_answer=expected_answer,
        expected_disposition=expected_disposition,
        required_tools=entry.required_tools,
        required_verifiers=entry.required_verifiers,
        forbidden_operations=("eval", "exec", "network", "raw_smtlib"),
        resource_budget=resource_budget,
        licence_and_source=PROVENANCE,
    )


def _answer_from(problem_id: Any, candidate: Candidate) -> Any:
    import json

    from cognitive_os.domain.domains import DomainAnswer

    return DomainAnswer(
        problem_id=problem_id,
        answer_type=candidate.answer_type,
        exact_value=candidate.exact_value,
        approximate_value=candidate.approximate_value,
        tolerance=candidate.tolerance,
        units=candidate.units,
        symbolic_form=candidate.symbolic_form,
        logical_status=candidate.logical_status,
        structured_value=json.loads(json.dumps(candidate.structured, sort_keys=True, default=str)),
        created_at=FIXTURE_TIME,
    )


def _var(name: str) -> dict[str, Any]:
    return {"operator": "variable", "sort": "bool", "name": name}


def _op(operator: str, *arguments: dict[str, Any]) -> dict[str, Any]:
    return {"operator": operator, "sort": "bool", "arguments": list(arguments)}


_P, _Q, _R = _var("p"), _var("q"), _var("r")
_MODUS_PONENS = _op("implies", _op("and", _op("implies", _P, _Q), _P), _Q)
_AFFIRMING_CONSEQUENT = _op("implies", _op("and", _op("implies", _P, _Q), _Q), _P)
_EXCLUDED_MIDDLE = _op("or", _P, _op("not", _P))
_CONTRADICTION = _op("and", _P, _op("not", _P))
_HYPOTHETICAL_SYLLOGISM = _op(
    "implies",
    _op("and", _op("implies", _P, _Q), _op("implies", _Q, _R)),
    _op("implies", _P, _R),
)
_DE_MORGAN = _op(
    "equals", _op("not", _op("and", _P, _Q)), _op("or", _op("not", _P), _op("not", _Q))
)


#: (case suffix, problem type, inputs, statement)
MATHEMATICS_CASES: tuple[tuple[str, str, dict[str, Any], str], ...] = (
    (
        "long-mult",
        "long-multiplication",
        {"left": 347, "right": 89},
        "Compute 347 * 89 by long multiplication.",
    ),
    (
        "long-mult-negative",
        "long-multiplication",
        {"left": -1234, "right": 56},
        "Compute -1234 * 56, preserving the sign.",
    ),
    (
        "long-div",
        "long-division",
        {"dividend": 1234, "divisor": 56},
        "Divide 1234 by 56, reporting quotient and remainder.",
    ),
    (
        "long-div-exact",
        "long-division",
        {"dividend": 8192, "divisor": 64},
        "Divide 8192 by 64, which leaves no remainder.",
    ),
    (
        "fractions",
        "fraction-arithmetic",
        {"expression": "3/4 + 5/6", "expected_denominator": 12},
        "Add 3/4 and 5/6 and normalise the result.",
    ),
    (
        "fractions-nested",
        "fraction-arithmetic",
        {"expression": "(2/3 - 1/6) * 4/5"},
        "Evaluate (2/3 - 1/6) * 4/5 exactly.",
    ),
    (
        "rationals",
        "rational-arithmetic",
        {"expression": "7/8 / (14/3)"},
        "Divide 7/8 by 14/3 exactly.",
    ),
    (
        "rationals-power",
        "rational-arithmetic",
        {"expression": "(3/2) ** 4"},
        "Raise 3/2 to the fourth power exactly.",
    ),
    (
        "simplify",
        "algebraic-simplification",
        {"expression": "(x + 1) * (x - 1)", "simplified": "x * x - 1", "variables": ["x"]},
        "Show that (x + 1)(x - 1) simplifies to x^2 - 1.",
    ),
    (
        "simplify-cubic",
        "algebraic-simplification",
        {"expression": "(x + 2) * (x + 2)", "simplified": "x * x + 4 * x + 4", "variables": ["x"]},
        "Expand (x + 2)^2.",
    ),
    ("linear", "linear-equation", {"a": 3, "b": -7, "c": 11}, "Solve 3x - 7 = 11 for x."),
    (
        "linear-fraction",
        "linear-equation",
        {"a": "2/5", "b": "1/3", "c": "4/3"},
        "Solve (2/5)x + 1/3 = 4/3 exactly.",
    ),
    (
        "quadratic",
        "polynomial-equation",
        {"a": 1, "b": -5, "c": 6, "expected_root_count": 2},
        "Solve x^2 - 5x + 6 = 0 over the rationals.",
    ),
    (
        "quadratic-double",
        "polynomial-equation",
        {"a": 1, "b": -4, "c": 4, "expected_root_count": 1},
        "Solve x^2 - 4x + 4 = 0, which has a repeated root.",
    ),
    (
        "quadratic-complex",
        "polynomial-equation",
        {"a": 1, "b": 0, "c": 1, "expected_root_count": 0},
        "Solve x^2 + 1 = 0, which has no real root.",
    ),
    (
        "equivalence",
        "symbolic-equivalence",
        {"expression": "x * (x + 2)", "simplified": "x * x + 2 * x", "variables": ["x"]},
        "Decide whether x(x + 2) and x^2 + 2x are equivalent.",
    ),
    (
        "equivalence-false",
        "symbolic-equivalence",
        {"expression": "x * (x + 2)", "simplified": "x * x + 2", "variables": ["x"]},
        "Decide whether x(x + 2) and x^2 + 2 are equivalent.",
    ),
    (
        "approximation",
        "exact-versus-approximate",
        {"expression": "22/7", "tolerance": "0.0001"},
        "Report 22/7 as an approximation with an explicit tolerance.",
    ),
)

PHYSICS_CASES: tuple[tuple[str, str, dict[str, Any], str], ...] = (
    (
        "speed-conversion",
        "unit-conversion",
        {"magnitude": 90, "source_unit": "km/h", "target_unit": "m/s"},
        "Convert 90 km/h into metres per second.",
    ),
    (
        "energy-conversion",
        "unit-conversion",
        {"magnitude": "5/2", "source_unit": "km", "target_unit": "m"},
        "Convert 2.5 km into metres.",
    ),
    (
        "temperature-offset",
        "unit-conversion",
        {"magnitude": 100, "source_unit": "degC", "target_unit": "degF"},
        "Convert 100 degrees Celsius into Fahrenheit, an offset-unit conversion.",
    ),
    (
        "temperature-kelvin",
        "unit-conversion",
        {"magnitude": 0, "source_unit": "degC", "target_unit": "K"},
        "Convert 0 degrees Celsius into kelvin.",
    ),
    (
        "newton-dimension",
        "dimensional-analysis",
        {"left_unit": "N", "right_unit": "kg*m/s^2"},
        "Check that the newton reduces to kg m s^-2.",
    ),
    (
        "joule-dimension",
        "dimensional-analysis",
        {"left_unit": "J", "right_unit": "N*m"},
        "Check that the joule equals a newton metre.",
    ),
    (
        "bad-dimension",
        "dimensional-analysis",
        {"left_unit": "J", "right_unit": "N"},
        "Check that energy and force do not share a dimension.",
    ),
    (
        "kinetic-energy",
        "quantity-calculation",
        {
            "expression": "m * v * v / 2",
            "quantities": {
                "m": {"magnitude": 4, "unit": "kg"},
                "v": {"magnitude": 3, "unit": "m/s"},
            },
            "result_unit": "J",
            "expected_dimension_unit": "kg*m^2/s^2",
            "assumptions": ["point mass", "non-relativistic speed"],
        },
        "Compute the kinetic energy of a 4 kg mass moving at 3 m/s.",
    ),
    (
        "ohms-law",
        "quantity-calculation",
        {
            "expression": "i * r",
            "quantities": {
                "i": {"magnitude": 2, "unit": "A"},
                "r": {"magnitude": 5, "unit": "V/A"},
            },
            "result_unit": "V",
            "assumptions": ["ohmic conductor", "steady state"],
        },
        "Compute the voltage across a 5 ohm resistor carrying 2 A.",
    ),
    (
        "model-applicable",
        "model-selection",
        {
            "conditions": {"low-speed": True, "point-mass": True, "no-friction": True},
            "models": {"newtonian": ["low-speed", "point-mass"], "relativistic": ["high-speed"]},
        },
        "Select a mechanics model for a slow-moving point mass.",
    ),
    (
        "model-inapplicable",
        "model-selection",
        {
            "conditions": {"low-speed": False, "point-mass": True},
            "models": {"newtonian": ["low-speed", "point-mass"]},
        },
        "Confirm that the Newtonian model is rejected at high speed.",
    ),
    (
        "energy-conservation",
        "conservation-check",
        {"before": [3, 4], "after": [5, 2]},
        "Check that total energy is conserved across an interaction.",
    ),
    (
        "energy-violation",
        "conservation-check",
        {"before": [3, 4], "after": [5, 5]},
        "Check an interaction that does not conserve energy.",
    ),
    (
        "limiting-case",
        "limiting-case",
        {
            "expression": "1 / x",
            "variable": "x",
            "points": [1, 2, 4, 8],
            "expected_trend": "decreasing",
        },
        "Examine 1/x as x grows.",
    ),
    (
        "magnitude",
        "order-of-magnitude",
        {"value": 6022},
        "Give the decimal order of magnitude of 6022.",
    ),
    (
        "magnitude-small",
        "order-of-magnitude",
        {"value": "1/800"},
        "Give the decimal order of magnitude of 1/800.",
    ),
    (
        "significant-figures",
        "significant-figures",
        {"value": "3.14159", "significant_figures": 3, "unit": "m"},
        "Round 3.14159 m to three significant figures.",
    ),
)

LOGIC_CASES: tuple[tuple[str, str, dict[str, Any], str], ...] = (
    (
        "modus-ponens",
        "validity-check",
        {"expression": _MODUS_PONENS},
        "Decide whether modus ponens is valid.",
    ),
    (
        "affirming-consequent",
        "validity-check",
        {"expression": _AFFIRMING_CONSEQUENT},
        "Decide whether affirming the consequent is valid.",
    ),
    (
        "hypothetical-syllogism",
        "validity-check",
        {"expression": _HYPOTHETICAL_SYLLOGISM},
        "Decide whether hypothetical syllogism is valid.",
    ),
    (
        "de-morgan",
        "validity-check",
        {"expression": _DE_MORGAN},
        "Decide whether De Morgan's law holds.",
    ),
    (
        "truth-table",
        "truth-table",
        {"expression": _MODUS_PONENS},
        "Enumerate the truth table of modus ponens.",
    ),
    (
        "truth-table-excluded-middle",
        "truth-table",
        {"expression": _EXCLUDED_MIDDLE},
        "Enumerate the truth table of the law of excluded middle.",
    ),
    (
        "sat",
        "satisfiability",
        {"expression": _op("or", _P, _Q)},
        "Decide the satisfiability of p or q.",
    ),
    (
        "unsat",
        "satisfiability",
        {"expression": _CONTRADICTION},
        "Decide the satisfiability of p and not p.",
    ),
    (
        "constraint",
        "constraint-satisfaction",
        {"expression": _op("and", _op("or", _P, _Q), _op("not", _op("and", _P, _Q)))},
        "Find an assignment satisfying exclusive disjunction.",
    ),
    (
        "consistency",
        "consistency-check",
        {"expression": _op("and", _P, _Q)},
        "Check whether p and q is a consistent constraint set.",
    ),
    (
        "inconsistency",
        "consistency-check",
        {"expression": _CONTRADICTION},
        "Check whether p and not p is consistent.",
    ),
    (
        "counterexample",
        "counterexample-search",
        {"expression": _AFFIRMING_CONSEQUENT},
        "Find a counterexample to affirming the consequent.",
    ),
    (
        "no-counterexample",
        "counterexample-search",
        {"expression": _EXCLUDED_MIDDLE},
        "Confirm that excluded middle has no counterexample.",
    ),
    (
        "sequence-arithmetic",
        "sequence-induction",
        {"terms": [2, 4, 6, 8]},
        "Continue the sequence 2, 4, 6, 8.",
    ),
    (
        "sequence-underdetermined",
        "sequence-induction",
        {"terms": [1, 2, 3]},
        "Continue 1, 2, 3, where several rules fit.",
    ),
    (
        "hypotheses",
        "competing-hypotheses",
        {"terms": [5, 5, 5]},
        "Enumerate the rules compatible with 5, 5, 5.",
    ),
)


#: Sprint 21C.1. The coding domain contributes three structured-value task
#: classes. The fixtures the registered single-edit baseline is meant to fail
#: are declared in `FALLIBLE_CODING_CASES` below, and every one of them is
#: measured against that declaration by `test_the_coding_baseline_outcome_table_is_pinned`
#: and by the `domain_kind_coding_registered` governance check — so a fixture
#: that silently stops failing is a red test, not a quiet erosion of the
#: Gate L v2 condition 8b headroom evidence.
def _patches(*pairs: tuple[str, str]) -> tuple[dict[str, str], ...]:
    return tuple({"find": find, "replace": replace} for find, replace in pairs)


CODING_CASES: tuple[tuple[str, str, dict[str, Any], str], ...] = (
    # --- pytest-repair: 7 fixtures, 2 multi-edit failures ---
    (
        "repair-single-rename",
        "pytest-repair",
        {
            "buggy_source": "def add(a, b):\n    return a - b\n",
            "golden_source": "def add(a, b):\n    return a + b\n",
            "patches": _patches(("return a - b", "return a + b")),
        },
        "Repair `add(a, b)` so it returns the sum.",
    ),
    (
        "repair-single-off-by-one",
        "pytest-repair",
        {
            "buggy_source": "def clamp(n, lo, hi):\n    return max(lo, min(hi - 1, n))\n",
            "golden_source": "def clamp(n, lo, hi):\n    return max(lo, min(hi, n))\n",
            "patches": _patches(("min(hi - 1, n)", "min(hi, n)")),
        },
        "Fix the off-by-one bug in `clamp`.",
    ),
    (
        "repair-single-negate-branch",
        "pytest-repair",
        {
            "buggy_source": "def is_positive(n):\n    return n >= 0\n",
            "golden_source": "def is_positive(n):\n    return n > 0\n",
            "patches": _patches(("return n >= 0", "return n > 0")),
        },
        "Stop treating zero as positive in `is_positive`.",
    ),
    (
        "repair-single-default-arg",
        "pytest-repair",
        {
            "buggy_source": "def shout(msg, times=2):\n    return msg * times\n",
            "golden_source": "def shout(msg, times=3):\n    return msg * times\n",
            "patches": _patches(("times=2", "times=3")),
        },
        "Default `shout` to three repetitions.",
    ),
    (
        "repair-single-import",
        "pytest-repair",
        {
            "buggy_source": "import maths\n",
            "golden_source": "import math\n",
            "patches": _patches(("import maths", "import math")),
        },
        "Repair the misspelled `maths` import.",
    ),
    # Fallible multi-edit repair tasks. Two coordinated edits are required; the
    # single-edit baseline applies the first only, the rest stay buggy, and the
    # checker rejects the disagreement with `golden_source`.
    (
        "repair-multi-rename-and-sign",
        "pytest-repair",
        {
            "buggy_source": "def sub(a, b):\n    return a + b\n",
            "golden_source": "def subtract(a, b):\n    return a - b\n",
            "patches": _patches(
                ("def sub(a, b):", "def subtract(a, b):"),
                ("return a + b", "return a - b"),
            ),
        },
        "Rename `sub` to `subtract` AND flip the operator.",
    ),
    (
        "repair-multi-branch-and-default",
        "pytest-repair",
        {
            "buggy_source": "def cap(s, n=2):\n    return s[:n+1] if len(s) >= n else s\n",
            "golden_source": "def cap(s, n=2):\n    return s[:n] if len(s) > n else s\n",
            "patches": _patches(
                (">= n else s", "> n else s"),
                ("return s[:n+1]", "return s[:n]"),
            ),
        },
        "Two coordinated fixes in `cap`: the comparison and the slice.",
    ),
    # --- test-selection: 5 fixtures, 1 fallible (indirect coverage) ---
    (
        "test-selection-direct",
        "test-selection",
        {
            "target_function": "score",
            "candidate_tests": (
                "test_score_basic",
                "test_score_negative",
                "test_other_helper",
                "test_unrelated_setup",
            ),
            "selected_tests": ("test_score_basic", "test_score_negative"),
        },
        "Select the tests that exercise `score` directly.",
    ),
    (
        "test-selection-prefix",
        "test-selection",
        {
            "target_function": "fetch",
            "candidate_tests": (
                "test_fetch_handles_empty",
                "test_fetch_retries",
                "test_format_helper",
            ),
            "selected_tests": ("test_fetch_handles_empty", "test_fetch_retries"),
        },
        "Select tests whose identifier references `fetch`.",
    ),
    (
        "test-selection-exact-match",
        "test-selection",
        {
            "target_function": "parse",
            "candidate_tests": ("test_parse", "test_parser_init", "test_utils"),
            "selected_tests": ("test_parse", "test_parser_init"),
        },
        "Select tests referencing `parse`.",
    ),
    # Fallible: `test_emergency_merge_bypass` mentions the target in its
    # identifier without exercising it, so the baseline over-selects.
    (
        "test-selection-indirect-bypass",
        "test-selection",
        {
            "target_function": "merge",
            "candidate_tests": (
                "test_merge_sorted",
                "test_merge_unsorted",
                "test_emergency_merge_bypass",
                "test_logger_setup",
            ),
            "selected_tests": ("test_merge_sorted", "test_merge_unsorted"),
        },
        "Selection must drop tests whose identifier only mentions the target indirectly.",
    ),
    # Fallible: the only test that exercises `validate` is named after the
    # helper that calls it and never mentions the target, so the baseline that
    # picks by identifier mention selects nothing at all.
    (
        "test-selection-indirect-coverage",
        "test-selection",
        {
            "target_function": "validate",
            "candidate_tests": ("test_helper_normalises_input", "test_setup"),
            "selected_tests": ("test_helper_normalises_input",),
        },
        "Select tests that exercise `validate` (only through the helper).",
    ),
    # --- assertion-repair: 5 fixtures, 2 multi-edit fallible ---
    (
        "assertion-single-message",
        "assertion-repair",
        {
            "broken_source": "assert add(2, 3) == 6, 'wrong sum'\n",
            "golden_source": "assert add(2, 3) == 5, 'wrong sum'\n",
            "patches": _patches(("== 6", "== 5")),
        },
        "Fix the expected value in the add() assertion.",
    ),
    (
        "assertion-single-operator",
        "assertion-repair",
        {
            "broken_source": "assert clamp(5, 0, 10) != 5, 'expected equal'\n",
            "golden_source": "assert clamp(5, 0, 10) == 5, 'expected equal'\n",
            "patches": _patches(("!= 5", "== 5")),
        },
        "Repair the inverted comparison in clamp().",
    ),
    (
        "assertion-single-import",
        "assertion-repair",
        {
            "broken_source": "assert maths.floor(1.5) == 1, 'floor changed'\n",
            "golden_source": "assert math.floor(1.5) == 1, 'floor changed'\n",
            "patches": _patches(("maths.floor", "math.floor")),
        },
        "Repair the misspelled module in the assertion.",
    ),
    # Fallible multi-edit: the message AND the value need fixing.
    (
        "assertion-multi-value-and-message",
        "assertion-repair",
        {
            "broken_source": "assert area(2) == 12.5, 'approx 12.5'\n",
            "golden_source": "assert area(2) == 12.57, 'approx 12.57'\n",
            "patches": _patches(
                ("== 12.5", "== 12.57"),
                ("'approx 12.5'", "'approx 12.57'"),
            ),
        },
        "Fix the value AND bring the message in line with it.",
    ),
    # Fallible multi-edit: the operator and the message must both change.
    (
        "assertion-multi-operator-and-message",
        "assertion-repair",
        {
            "broken_source": "assert order(items) != sorted(items), 'order bug'\n",
            "golden_source": "assert order(items) == sorted(items), 'order is correct'\n",
            "patches": _patches(
                ("!= sorted(items)", "== sorted(items)"),
                ("'order bug'", "'order is correct'"),
            ),
        },
        "Repair `order()` and align the message.",
    ),
)


#: Sprint 21C.1 exit evidence, in declared form: the coding cases whose
#: registered baseline is expected to be rejected. This is the per-case baseline
#: outcome table the plan asks for — a declaration that is checked against the
#: measurement, not a description of it. Six fixtures, against the four the plan
#: names as the minimum, so a single fixture drifting does not sink the gate.
FALLIBLE_CODING_CASES: frozenset[str] = frozenset(
    {
        "domain-repair-multi-rename-and-sign",
        "domain-repair-multi-branch-and-default",
        "domain-test-selection-indirect-bypass",
        "domain-test-selection-indirect-coverage",
        "domain-assertion-multi-value-and-message",
        "domain-assertion-multi-operator-and-message",
    }
)

#: The plan's floor for Gate L v2 condition 8b: at least this many coding cases
#: must have a measurably failing baseline.
MINIMUM_FALLIBLE_CODING_CASES = 4


def all_case_specifications() -> tuple[tuple[str, str, dict[str, Any], str], ...]:
    return MATHEMATICS_CASES + PHYSICS_CASES + LOGIC_CASES + CODING_CASES


def build_all_cases() -> tuple[DomainBenchmarkCase, ...]:
    """Every deterministic fixture case, in a stable order."""
    return tuple(
        build_case(
            f"domain-{suffix}",
            problem_type,
            inputs,
            statement=statement,
            expected_disposition=(
                VerificationDisposition.FAIL
                if f"domain-{suffix}" in FALLIBLE_CODING_CASES
                else VerificationDisposition.PASS
            ),
        )
        for suffix, problem_type, inputs, statement in all_case_specifications()
    )


def wrong_answer_for(case: DomainBenchmarkCase) -> Candidate:
    """A plausible but incorrect answer, used to prove rejection actually works."""
    expected = case.expected_answer
    if expected.answer_type is AnswerType.EXACT and expected.exact_value is not None:
        from fractions import Fraction

        return Candidate(AnswerType.EXACT, exact_value=str(Fraction(expected.exact_value) + 1))
    if expected.answer_type is AnswerType.QUANTITY:
        from fractions import Fraction

        return Candidate(
            AnswerType.QUANTITY,
            exact_value=str(Fraction(expected.exact_value or "0") + 1),
            units=expected.units,
        )
    if expected.answer_type is AnswerType.BOOLEAN:
        flipped = "false" if (expected.logical_status or "").casefold() == "true" else "true"
        return Candidate(AnswerType.BOOLEAN, logical_status=flipped)
    if expected.answer_type is AnswerType.APPROXIMATE:
        from decimal import Decimal

        return Candidate(
            AnswerType.APPROXIMATE,
            approximate_value=(expected.approximate_value or Decimal(0)) + Decimal(1),
            tolerance=expected.tolerance,
        )
    if expected.answer_type in (AnswerType.SATISFIABLE, AnswerType.UNSATISFIABLE):
        flipped = "unsat" if expected.logical_status == "sat" else "sat"
        return Candidate(AnswerType.SATISFIABLE, logical_status=flipped, structured={"model": {}})
    if expected.answer_type is AnswerType.SYMBOLIC:
        return Candidate(AnswerType.SYMBOLIC, symbolic_form="x * x + 12345")
    if expected.answer_type is AnswerType.COUNTEREXAMPLE:
        # Claim a counterexample where none exists, or deny the one that does.
        if expected.structured_value.get("counterexample") is None:
            return Candidate(
                AnswerType.COUNTEREXAMPLE,
                structured={"counterexample": {"p": True}, "found": True},
            )
        return Candidate(
            AnswerType.COUNTEREXAMPLE, structured={"counterexample": None, "found": False}
        )
    return Candidate(AnswerType.STRUCTURED, structured=_corrupt(expected.structured_value))


def _corrupt(structured: dict[str, Any]) -> dict[str, Any]:
    """Mutate a structured answer so it is genuinely wrong, not merely different."""
    corrupted = dict(structured)
    if "roots" in corrupted:
        # A bogus extra root fails substitution regardless of the original roots.
        corrupted["roots"] = [*[str(item) for item in corrupted["roots"]], "99991"]
    elif "model" in corrupted:
        # Name a model that is not applicable, or invent one where none applies.
        corrupted["model"] = "relativistic" if corrupted["model"] != "relativistic" else "newtonian"
    elif "rules" in corrupted:
        # Assert a single unjustified rule that does not reproduce the terms.
        corrupted["rules"] = ["alternating-sign"]
        corrupted["underdetermined"] = not bool(corrupted.get("underdetermined"))
    elif "outputs" in corrupted:
        corrupted["outputs"] = [not bool(item) for item in corrupted["outputs"]]
    elif "values" in corrupted:
        corrupted["values"] = [*corrupted["values"][:-1], "0"]
    elif "exponent" in corrupted:
        corrupted["exponent"] = int(corrupted["exponent"]) + 1
    elif "repaired_source" in corrupted:
        # A wrong repaired source: drop a character so the string disagrees with
        # the golden without needing a different replacement scheme.
        golden_text = str(corrupted["repaired_source"])
        corrupted["repaired_source"] = golden_text[:-1] if golden_text else "WRONG"
    elif "selected_tests" in corrupted:
        # Drop the first test from the selection — a wrong selection still
        # looks plausible but no longer matches the fixture's expected choice.
        selected = list(corrupted["selected_tests"])
        corrupted["selected_tests"] = selected[1:] if len(selected) > 1 else ["test_placeholder"]
    return corrupted
