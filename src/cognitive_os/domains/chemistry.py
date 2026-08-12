"""The `science.chemistry` pilot's deterministic kernels (Sprint 22A W3, §3.4).

The honesty constraint bites hardest here, and §3.4 says why: *a chemistry domain whose
verifier cannot actually verify is a silo wearing a lifecycle field.* So the pilot claims
exactly two problem types, both of which are exact arithmetic over **atomic masses declared
in the case itself** — no periodic table is shipped, fetched or assumed, because a constant
this module invented would be a fact nobody verified.

- `chemistry.mass-balance` decides whether an equation balances, and reports the molar mass
  of each side. The checker never repeats the solver's per-side comparison: it computes the
  **net** atom count per element across the whole equation, and separately re-derives both
  side masses from the formulas, so a tally that disagrees with its own mass is caught.
- `chemistry.molar-conversion` converts a mass to an amount of substance through the molar
  mass implied by a formula. The checker inverts it — amount times molar mass must return
  the given mass — which exercises the released converter in the opposite direction.

**The one new capability, and why it is not a borrowed name.** `chemistry.stoichiometry` is
a deterministic kernel: it counts atoms and compares integers. It is not a model, not a
lookup and not a heuristic, which is the whole of §3.4's requirement for a new capability
name. `physics.dimension` and `physics.quantity` do here exactly what they do everywhere
else — compare dimensions through the released unit registry, and recompute a magnitude.

**What was considered and left out**, recorded rather than quietly dropped: reaction
prediction and equilibrium constants. Both need empirical thermochemical data, so no
deterministic kernel in this repository can judge them, and a problem type whose verifier
cannot verify does not belong in a pilot.

**The formula grammar is deliberately small**: element symbols with optional counts, no
parentheses, no hydrates, no charges. A formula outside it is refused rather than guessed
at — `Ca(OH)2` is a refusal here, not a silent `Ca(OH)2 -> {Ca:1, O:1, H:2}`.
"""

from __future__ import annotations

import re
from fractions import Fraction
from typing import Any

from cognitive_os.domain.domains import (
    AnswerType,
    DomainFailureCode,
    ResourceBudget,
    VerificationDisposition,
)

from .kernels import UnitError, dimension_of, parse_unit
from .registry import DomainKernel
from .solvers import Candidate, Check, CheckSet, Solution, SolverError, Step

#: The released capabilities, doing here what they do everywhere else, plus the one new
#: name §3.4 allows: an atom count compared against an atom count.
DIMENSION = "physics.dimension"
QUANTITY = "physics.quantity"
STOICHIOMETRY = "chemistry.stoichiometry"

MASS_BALANCE = "chemistry.mass-balance"
MOLAR_CONVERSION = "chemistry.molar-conversion"

#: Element symbol followed by an optional count. Anything the scan does not consume whole is
#: a refusal, which is what keeps `Ca(OH)2` from being read as `CaOH2`.
_FORMULA_TOKEN = re.compile(r"([A-Z][a-z]?)(\d*)")
_FORMULA_MAX_LENGTH = 64

#: Problem types considered for the pilot and left out, with the reason (§3.4). Carried in
#: the module rather than only in a record, so the next person to reach for them finds out
#: here why they are absent.
EXCLUDED_CANDIDATES: dict[str, str] = {
    "chemistry.reaction-prediction": (
        "predicting the products of an arbitrary reaction needs empirical thermochemistry; "
        "no deterministic kernel here can judge an answer, so a verifier would be a name"
    ),
    "chemistry.equilibrium-constant": (
        "an equilibrium constant is measured, not derived from a formula; a kernel could "
        "only restate a number the case already carried"
    ),
}


def _fail(
    message: str, code: DomainFailureCode = DomainFailureCode.INVALID_DERIVATION
) -> SolverError:
    return SolverError(code, message)


def _exact(value: object, field: str) -> Fraction:
    """Read one exact rational input. Floats are refused rather than rounded."""
    if isinstance(value, bool):
        raise _fail(f"{field}: a boolean is not a magnitude")
    if isinstance(value, float):
        raise _fail(f"{field}: float inputs are not exact; pass an integer or a string")
    if isinstance(value, int | str):
        try:
            return Fraction(value)
        except (ValueError, ZeroDivisionError) as error:
            raise _fail(f"{field}: {value!r} is not an exact rational") from error
    raise _fail(f"{field}: cannot read {value!r} as an exact number")


def _check(capability: str, passed: bool, detail: str) -> Check:
    """One check, with a detail that states expectation and observation (W2-F2)."""
    return Check(
        capability,
        VerificationDisposition.PASS if passed else VerificationDisposition.FAIL,
        detail,
    )


def parse_formula(formula: object) -> dict[str, int]:
    """`H2O -> {'H': 2, 'O': 1}`, or a refusal naming what the grammar does not accept."""
    if not isinstance(formula, str) or not formula:
        raise _fail("formula: expected a non-empty chemical formula")
    if len(formula) > _FORMULA_MAX_LENGTH:
        raise _fail(f"formula: {formula!r} is longer than {_FORMULA_MAX_LENGTH} characters")
    counts: dict[str, int] = {}
    position = 0
    while position < len(formula):
        match = _FORMULA_TOKEN.match(formula, position)
        if match is None:
            raise _fail(
                f"formula: {formula!r} is outside the supported grammar at position "
                f"{position}; element symbols with optional counts only, no parentheses"
            )
        symbol, digits = match.group(1), match.group(2)
        counts[symbol] = counts.get(symbol, 0) + (int(digits) if digits else 1)
        position = match.end()
    return counts


def _atomic_masses(inputs: dict[str, Any]) -> dict[str, Fraction]:
    raw = inputs.get("atomic_masses")
    if not isinstance(raw, dict) or not raw:
        raise _fail("atomic_masses: the case must declare the atomic masses it relies on")
    masses = {}
    for symbol, value in raw.items():
        mass = _exact(value, f"atomic_masses.{symbol}")
        if mass <= 0:
            raise _fail(f"atomic_masses.{symbol}: an atomic mass is positive")
        masses[str(symbol)] = mass
    return masses


def _molar_mass(counts: dict[str, int], masses: dict[str, Fraction]) -> Fraction:
    missing = sorted(symbol for symbol in counts if symbol not in masses)
    if missing:
        raise _fail(f"atomic_masses: no declared mass for {missing}")
    return sum((masses[symbol] * count for symbol, count in counts.items()), Fraction(0))


def _side(inputs: dict[str, Any], field: str) -> tuple[tuple[str, int], ...]:
    raw = inputs.get(field)
    if not isinstance(raw, list | tuple) or not raw:
        raise _fail(f"{field}: expected a non-empty list of species")
    read = []
    for index, item in enumerate(raw):
        if not isinstance(item, dict):
            raise _fail(f"{field}[{index}]: each species is an object with formula and coefficient")
        coefficient = _exact(item.get("coefficient", 1), f"{field}[{index}].coefficient")
        if coefficient <= 0 or coefficient.denominator != 1:
            raise _fail(f"{field}[{index}].coefficient: expected a positive whole number")
        read.append((str(item.get("formula")), int(coefficient)))
    return tuple(read)


def _tally(side: tuple[tuple[str, int], ...]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for formula, coefficient in side:
        for symbol, count in parse_formula(formula).items():
            counts[symbol] = counts.get(symbol, 0) + count * coefficient
    return counts


def _side_mass(side: tuple[tuple[str, int], ...], masses: dict[str, Fraction]) -> Fraction:
    return sum(
        (
            _molar_mass(parse_formula(formula), masses) * coefficient
            for formula, coefficient in side
        ),
        Fraction(0),
    )


def _molar_mass_unit(inputs: dict[str, Any]) -> str:
    unit = inputs.get("molar_mass_unit", "g/mol")
    if not isinstance(unit, str):
        raise _fail("molar_mass_unit: expected a unit symbol")
    try:
        parse_unit(unit)
    except UnitError as error:
        raise _fail(f"molar_mass_unit: {error}") from error
    if dimension_of(unit) != dimension_of("g/mol"):
        raise _fail(f"molar_mass_unit: {unit!r} is not a mass per amount of substance")
    return unit


# --------------------------------------------------------------------------
# Mass balance
# --------------------------------------------------------------------------


def solve_mass_balance(inputs: dict[str, Any], budget: ResourceBudget) -> Solution:
    reactants, products = _side(inputs, "reactants"), _side(inputs, "products")
    masses = _atomic_masses(inputs)
    unit = _molar_mass_unit(inputs)

    left, right = _tally(reactants), _tally(products)
    unbalanced = sorted(
        symbol for symbol in set(left) | set(right) if left.get(symbol, 0) != right.get(symbol, 0)
    )
    reactant_mass, product_mass = _side_mass(reactants, masses), _side_mass(products, masses)
    return Solution(
        candidate=Candidate(
            AnswerType.STRUCTURED,
            structured={
                "balanced": not unbalanced,
                "unbalanced_elements": unbalanced,
                "reactant_elements": {symbol: left[symbol] for symbol in sorted(left)},
                "product_elements": {symbol: right[symbol] for symbol in sorted(right)},
                "reactant_mass": str(reactant_mass),
                "product_mass": str(product_mass),
            },
            units=unit,
        ),
        steps=(
            Step("tally-reactants", f"reactant atoms {left}", str(sorted(left.items()))),
            Step("tally-products", f"product atoms {right}", str(sorted(right.items()))),
            Step(
                "compare",
                f"molar mass {reactant_mass} {unit} against {product_mass} {unit}",
                "balanced" if not unbalanced else f"unbalanced: {unbalanced}",
            ),
        ),
        tool_evidence=("chemistry.kernel:atom_tally",),
        assumptions=(
            "the atomic masses are the ones the case declares, exactly",
            "coefficients are whole numbers and the equation is a single reaction step",
        ),
        limitations=(
            "a balanced equation is not a reaction that occurs; balance is arithmetic, not "
            "chemistry",
        ),
    )


def check_mass_balance(
    inputs: dict[str, Any], candidate: Candidate, budget: ResourceBudget
) -> CheckSet:
    reactants, products = _side(inputs, "reactants"), _side(inputs, "products")
    masses = _atomic_masses(inputs)
    unit = _molar_mass_unit(inputs)
    stated = dict(candidate.structured)

    # Independent route: the *net* count per element across the whole equation, rather than
    # two tallies compared side by side. A symbol dropped from both sides cancels in the
    # solver's comparison and shows up here as a missing key.
    net: dict[str, int] = {}
    for side, sign in ((reactants, 1), (products, -1)):
        for formula, coefficient in side:
            for symbol, count in parse_formula(formula).items():
                net[symbol] = net.get(symbol, 0) + sign * count * coefficient
    offenders = sorted(symbol for symbol, value in net.items() if value != 0)

    checks = [
        _check(
            STOICHIOMETRY,
            bool(stated.get("balanced")) is (not offenders),
            f"the net atom count leaves {offenders or 'nothing'} unbalanced; candidate "
            f"claimed balanced={stated.get('balanced')!r}",
        ),
        _check(
            STOICHIOMETRY,
            list(stated.get("unbalanced_elements") or []) == offenders,
            f"the unbalanced elements are {offenders}; candidate reported "
            f"{list(stated.get('unbalanced_elements') or [])}",
        ),
    ]

    # Masses re-derived from the formulas, not from the candidate's own tally.
    expected_left, expected_right = _side_mass(reactants, masses), _side_mass(products, masses)
    for field, expected in (("reactant_mass", expected_left), ("product_mass", expected_right)):
        try:
            claimed = Fraction(str(stated.get(field)))
        except (ValueError, ZeroDivisionError, TypeError):
            checks.append(_check(QUANTITY, False, f"{field} {stated.get(field)!r} is not exact"))
        else:
            checks.append(
                _check(
                    QUANTITY,
                    claimed == expected,
                    f"{field} recomputed from the formulas is {expected} {unit}; candidate "
                    f"stated {claimed}",
                )
            )

    # Conservation of mass is a consequence, not a restatement: a balanced equation whose
    # sides carry different molar masses means the tally and the masses disagree.
    checks.append(
        _check(
            QUANTITY,
            (expected_left == expected_right) is (not offenders),
            f"a balanced equation conserves mass; balance={not offenders} with "
            f"{expected_left} {unit} against {expected_right} {unit}",
        )
    )
    checks.append(
        _check(
            DIMENSION,
            candidate.units == unit,
            f"the molar masses must carry {unit!r}; candidate reported {candidate.units!r}",
        )
    )
    return tuple(checks)


# --------------------------------------------------------------------------
# Molar conversion
# --------------------------------------------------------------------------


def _conversion_inputs(inputs: dict[str, Any]) -> tuple[dict[str, int], Fraction, Fraction, str]:
    counts = parse_formula(inputs.get("formula"))
    masses = _atomic_masses(inputs)
    molar_mass = _molar_mass(counts, masses)
    sample = inputs.get("mass")
    if not isinstance(sample, dict):
        raise _fail("mass: expected an object with magnitude and unit")
    unit = sample.get("unit", "g")
    if not isinstance(unit, str):
        raise _fail("mass.unit: expected a unit symbol")
    try:
        if dimension_of(unit) != dimension_of("g"):
            raise _fail(f"mass.unit: {unit!r} is not a mass")
    except UnitError as error:
        raise _fail(f"mass.unit: {error}") from error
    magnitude = _exact(sample.get("magnitude"), "mass.magnitude")
    if magnitude < 0:
        raise _fail("mass.magnitude: a sample mass is not negative")
    # The declared atomic masses are per mole in grams, so the sample is taken to grams.
    in_grams = magnitude * parse_unit(unit)[0] / parse_unit("g")[0]
    return counts, molar_mass, in_grams, unit


def solve_molar_conversion(inputs: dict[str, Any], budget: ResourceBudget) -> Solution:
    counts, molar_mass, in_grams, unit = _conversion_inputs(inputs)
    result_unit = inputs.get("result_unit", "mol")
    if not isinstance(result_unit, str):
        raise _fail("result_unit: expected a unit symbol")
    try:
        if dimension_of(result_unit) != dimension_of("mol"):
            raise _fail(f"result_unit: {result_unit!r} is not an amount of substance")
    except UnitError as error:
        raise _fail(f"result_unit: {error}") from error

    amount = in_grams / molar_mass / parse_unit(result_unit)[0]
    return Solution(
        candidate=Candidate(AnswerType.QUANTITY, exact_value=str(amount), units=result_unit),
        steps=(
            Step("molar-mass", f"{inputs['formula']} = {counts}", f"{molar_mass} g/mol"),
            Step("to-grams", f"{in_grams} g from {unit}", str(in_grams)),
            Step("divide", "amount = mass / molar mass", str(amount)),
        ),
        tool_evidence=("chemistry.kernel:molar_mass",),
        assumptions=("the sample is the pure substance the formula names",),
    )


def check_molar_conversion(
    inputs: dict[str, Any], candidate: Candidate, budget: ResourceBudget
) -> CheckSet:
    counts, molar_mass, in_grams, _unit = _conversion_inputs(inputs)
    result_unit = str(inputs.get("result_unit", "mol"))
    if candidate.exact_value is None:
        return (_check(QUANTITY, False, "the candidate carries no exact amount"),)
    try:
        stated = Fraction(candidate.exact_value)
    except (ValueError, ZeroDivisionError):
        return (_check(QUANTITY, False, f"amount {candidate.exact_value!r} is not exact"),)

    # Independent route: multiply back. The claimed amount times the molar mass must return
    # the sample mass, which is the relation run the other way round.
    in_moles = stated * parse_unit(result_unit)[0]
    # The molar mass the candidate's own answer implies, re-derived from the formula and
    # compared. A formula the solver misread lands here rather than in the arithmetic.
    implied = in_grams / in_moles if in_moles != 0 else None
    return (
        _check(
            QUANTITY,
            in_moles * molar_mass == in_grams,
            f"the claimed amount times the molar mass returns {in_moles * molar_mass} g "
            f"against the given {in_grams} g",
        ),
        _check(
            STOICHIOMETRY,
            implied == molar_mass if implied is not None else in_grams == 0,
            f"{inputs.get('formula')!r} tallies to {counts}, a molar mass of {molar_mass} "
            f"g/mol; the candidate's answer implies "
            f"{implied if implied is not None else 'no molar mass at all'}",
        ),
        _check(
            DIMENSION,
            candidate.units == result_unit,
            f"the amount must carry {result_unit!r}; candidate reported {candidate.units!r}",
        ),
    )


#: The pilot's installed kernels. The descriptor says what the domain claims; this says what
#: is implemented, and registration refuses the pair when they disagree.
CHEMISTRY_KERNELS: dict[str, DomainKernel] = {
    MASS_BALANCE: DomainKernel(
        answer_type=AnswerType.STRUCTURED,
        solver=solve_mass_balance,
        checker=check_mass_balance,
    ),
    MOLAR_CONVERSION: DomainKernel(
        answer_type=AnswerType.QUANTITY,
        solver=solve_molar_conversion,
        checker=check_molar_conversion,
    ),
}

__all__ = [
    "CHEMISTRY_KERNELS",
    "EXCLUDED_CANDIDATES",
    "MASS_BALANCE",
    "MOLAR_CONVERSION",
    "parse_formula",
]
