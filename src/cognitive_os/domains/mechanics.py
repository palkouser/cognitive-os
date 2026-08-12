"""The `engineering.mechanics` pilot's deterministic kernels (Sprint 22A W2, §3.3).

Three problem types, each an exact rational computation over the released unit registry,
each judged by a checker that reaches the same number by a different road. Nothing here is
new physics and nothing here is a model: the point of the pilot is that a domain the
platform never heard of before can arrive as data and still be held to the released
standard of evidence.

**Why these three.** §3.3 bounds the pilot to what the released `physics.dimension` and
`physics.quantity` capabilities can actually judge, and each kernel earns those two names
honestly:

- `mechanics.statics-equilibrium` decides whether a set of coplanar forces balances. The
  checker recomputes the resultant by a different accumulation *and* audits the force list
  for a dropped or duplicated member, which re-summing in another order would never catch.
- `mechanics.moment-balance` computes the resultant moment about a stated pivot. The
  checker never repeats that sum: it computes the moment about the origin and transports it
  to the pivot through the shift identity, so a sign error in the solver's lever arms
  survives only if the same error is made twice in two different formulae.
- `mechanics.uniform-motion` computes a displacement from a speed and a duration through
  the released converter. The checker inverts it — displacement and duration back to a
  speed — so the conversion is exercised in both directions.

**On the problem-type names.** The released four own bare ids (`unit-conversion`,
`truth-table`) because they were registered before there was anywhere else for a name to
live; those are released facts and cannot move. A domain arriving as data namespaces its
own, which is what keeps a registry that any package can extend from becoming a race for
short names.
"""

from __future__ import annotations

from fractions import Fraction
from typing import Any

from cognitive_os.domain.domains import (
    AnswerType,
    DomainFailureCode,
    ResourceBudget,
    VerificationDisposition,
)

from .kernels import UnitError, dimension_of, parse_unit, registry_hash
from .registry import DomainKernel
from .solvers import Candidate, Check, CheckSet, Solution, SolverError, Step

#: The two released capabilities every check below reports under. They are not borrowed
#: names: `physics.dimension` checks are dimensional comparisons through the released unit
#: registry, and `physics.quantity` checks are exact recomputations of a magnitude.
DIMENSION = "physics.dimension"
QUANTITY = "physics.quantity"

STATICS_EQUILIBRIUM = "mechanics.statics-equilibrium"
MOMENT_BALANCE = "mechanics.moment-balance"
UNIFORM_MOTION = "mechanics.uniform-motion"


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


def _forces(inputs: dict[str, Any]) -> tuple[tuple[str, Fraction, Fraction], ...]:
    """`(name, fx, fy)` for each declared force, with names required and unique.

    Names are mandatory because the equilibrium checker's independent contribution is an
    audit of *which* forces were summed, and an anonymous list cannot be audited.
    """
    raw = inputs.get("forces")
    if not isinstance(raw, list | tuple) or not raw:
        raise _fail("forces: expected a non-empty list of forces")
    read: list[tuple[str, Fraction, Fraction]] = []
    for index, item in enumerate(raw):
        if not isinstance(item, dict):
            raise _fail(f"forces[{index}]: each force is an object with name, fx and fy")
        name = item.get("name")
        if not isinstance(name, str) or not name:
            raise _fail(f"forces[{index}]: every force needs a non-empty name")
        read.append(
            (
                name,
                _exact(item.get("fx"), f"forces[{index}].fx"),
                _exact(item.get("fy"), f"forces[{index}].fy"),
            )
        )
    names = [item[0] for item in read]
    if len(set(names)) != len(names):
        raise _fail("forces: force names must be unique; a repeated name cannot be audited")
    return tuple(read)


def _force_unit(inputs: dict[str, Any]) -> str:
    unit = inputs.get("force_unit", "N")
    if not isinstance(unit, str):
        raise _fail("force_unit: expected a unit symbol")
    try:
        parse_unit(unit)
    except UnitError as error:
        raise _fail(f"force_unit: {error}") from error
    return unit


def _check(capability: str, passed: bool, detail: str) -> Check:
    """One check, with a detail that reads correctly whether it passed or failed (W2-F2)."""
    return Check(
        capability,
        VerificationDisposition.PASS if passed else VerificationDisposition.FAIL,
        detail,
    )


def _same_dimension(left: str, right: str) -> bool:
    return dimension_of(left) == dimension_of(right)


# --------------------------------------------------------------------------
# Statics equilibrium
# --------------------------------------------------------------------------


def solve_statics_equilibrium(inputs: dict[str, Any], budget: ResourceBudget) -> Solution:
    forces = _forces(inputs)
    unit = _force_unit(inputs)
    if not _same_dimension(unit, "N"):
        raise _fail(f"force_unit: {unit!r} does not have the dimension of a force")
    resultant_x = Fraction(0)
    resultant_y = Fraction(0)
    steps = []
    for name, fx, fy in forces:
        resultant_x += fx
        resultant_y += fy
        steps.append(
            Step(
                "accumulate",
                f"added {name} = ({fx}, {fy}) {unit}",
                f"({resultant_x}, {resultant_y})",
            )
        )
    equilibrium = resultant_x == 0 and resultant_y == 0
    steps.append(
        Step(
            "decide",
            f"resultant ({resultant_x}, {resultant_y}) {unit}",
            "equilibrium" if equilibrium else "not in equilibrium",
        )
    )
    return Solution(
        candidate=Candidate(
            AnswerType.STRUCTURED,
            structured={
                "equilibrium": equilibrium,
                "resultant_x": str(resultant_x),
                "resultant_y": str(resultant_y),
                "force_count": len(forces),
                "forces_summed": [name for name, _, _ in forces],
            },
            units=unit,
        ),
        steps=tuple(steps),
        tool_evidence=(f"physics.kernel:registry@{registry_hash()[:16]}",),
        assumptions=(
            "the forces are coplanar and act on one rigid body",
            "the body is in static equilibrium if and only if the resultant force vanishes",
        ),
        limitations=(
            "force balance alone does not establish equilibrium of a body free to rotate; "
            "the moment balance is the separate problem type",
        ),
    )


def check_statics_equilibrium(
    inputs: dict[str, Any], candidate: Candidate, budget: ResourceBudget
) -> CheckSet:
    forces = _forces(inputs)
    unit = _force_unit(inputs)
    stated = dict(candidate.structured)
    checks: list[Check] = []

    # Independent route: split by sign and combine, rather than accumulating in input
    # order, so a sign handled wrongly in one pass does not reproduce itself in the other.
    expected_x = sum((fx for _, fx, _ in forces if fx > 0), Fraction(0)) + sum(
        (fx for _, fx, _ in forces if fx < 0), Fraction(0)
    )
    expected_y = sum((fy for _, _, fy in forces if fy > 0), Fraction(0)) + sum(
        (fy for _, _, fy in forces if fy < 0), Fraction(0)
    )
    expected_equilibrium = expected_x == 0 and expected_y == 0

    try:
        claimed_x = Fraction(str(stated.get("resultant_x")))
        claimed_y = Fraction(str(stated.get("resultant_y")))
    except (ValueError, ZeroDivisionError):
        checks.append(_check(QUANTITY, False, "the claimed resultant is not an exact rational"))
        claimed_x = claimed_y = None  # type: ignore[assignment]
    else:
        checks.append(
            _check(
                QUANTITY,
                claimed_x == expected_x and claimed_y == expected_y,
                f"independent recomputation gives ({expected_x}, {expected_y}) {unit}, "
                f"candidate stated ({claimed_x}, {claimed_y})",
            )
        )

    checks.append(
        _check(
            QUANTITY,
            bool(stated.get("equilibrium")) is expected_equilibrium,
            f"equilibrium on the recomputed resultant is {expected_equilibrium}; candidate "
            f"claimed {stated.get('equilibrium')!r}",
        )
    )

    # The audit a re-sum cannot do: every declared force was summed exactly once.
    summed = stated.get("forces_summed")
    declared = [name for name, _, _ in forces]
    checks.append(
        _check(
            QUANTITY,
            isinstance(summed, list | tuple) and list(summed) == declared,
            f"the declared forces are {declared}; the derivation accounts for {summed!r}",
        )
    )

    checks.append(
        _check(
            DIMENSION,
            candidate.units == unit and _same_dimension(unit, "N"),
            f"the resultant must carry the force unit {unit!r}; candidate reported "
            f"{candidate.units!r}",
        )
    )
    return tuple(checks)


# --------------------------------------------------------------------------
# Moment balance
# --------------------------------------------------------------------------


def _placed_forces(
    inputs: dict[str, Any],
) -> tuple[tuple[str, Fraction, Fraction, Fraction, Fraction], ...]:
    raw = inputs.get("forces")
    if not isinstance(raw, list | tuple) or not raw:
        raise _fail("forces: expected a non-empty list of placed forces")
    read = []
    for index, item in enumerate(raw):
        if not isinstance(item, dict):
            raise _fail(f"forces[{index}]: each placed force is an object with name, x, y, fx, fy")
        name = item.get("name")
        if not isinstance(name, str) or not name:
            raise _fail(f"forces[{index}]: every placed force needs a non-empty name")
        read.append(
            (
                name,
                _exact(item.get("x"), f"forces[{index}].x"),
                _exact(item.get("y"), f"forces[{index}].y"),
                _exact(item.get("fx"), f"forces[{index}].fx"),
                _exact(item.get("fy"), f"forces[{index}].fy"),
            )
        )
    return tuple(read)


def _pivot(inputs: dict[str, Any]) -> tuple[Fraction, Fraction]:
    raw = inputs.get("pivot")
    if not isinstance(raw, dict):
        raise _fail("pivot: expected an object with x and y")
    return _exact(raw.get("x"), "pivot.x"), _exact(raw.get("y"), "pivot.y")


def _moment_units(inputs: dict[str, Any]) -> tuple[str, str, str]:
    force_unit = _force_unit(inputs)
    length_unit = inputs.get("length_unit", "m")
    result_unit = inputs.get("result_unit", "N*m")
    for name, unit in (("length_unit", length_unit), ("result_unit", result_unit)):
        if not isinstance(unit, str):
            raise _fail(f"{name}: expected a unit symbol")
        try:
            parse_unit(unit)
        except UnitError as error:
            raise _fail(f"{name}: {error}") from error
    return force_unit, str(length_unit), str(result_unit)


def solve_moment_balance(inputs: dict[str, Any], budget: ResourceBudget) -> Solution:
    forces = _placed_forces(inputs)
    pivot_x, pivot_y = _pivot(inputs)
    force_unit, length_unit, result_unit = _moment_units(inputs)
    if not _same_dimension(result_unit, f"{force_unit}*{length_unit}"):
        raise _fail(
            f"result_unit: {result_unit!r} is not the product of {force_unit!r} and {length_unit!r}"
        )
    total = Fraction(0)
    steps = []
    for name, x, y, fx, fy in forces:
        contribution = (x - pivot_x) * fy - (y - pivot_y) * fx
        total += contribution
        steps.append(
            Step(
                "moment",
                f"{name} about the pivot contributes {contribution}",
                str(total),
            )
        )
    return Solution(
        candidate=Candidate(AnswerType.QUANTITY, exact_value=str(total), units=result_unit),
        steps=tuple(steps),
        tool_evidence=(f"physics.kernel:registry@{registry_hash()[:16]}",),
        assumptions=(
            "the forces are coplanar and the moment is taken about the z axis",
            "positions and force components are exact in the declared units",
        ),
    )


def check_moment_balance(
    inputs: dict[str, Any], candidate: Candidate, budget: ResourceBudget
) -> CheckSet:
    forces = _placed_forces(inputs)
    pivot_x, pivot_y = _pivot(inputs)
    force_unit, length_unit, result_unit = _moment_units(inputs)

    # The independent route, and the reason this problem type is worth a pilot: the moment
    # about the pivot is never recomputed. It is obtained from the moment about the origin
    # by the shift identity M_p = M_0 - x_p * R_y + y_p * R_x, which is a different formula
    # over different intermediate quantities. A lever arm subtracted the wrong way round in
    # the solver would have to be made wrong identically here to survive.
    moment_about_origin = sum((x * fy - y * fx for _, x, y, fx, fy in forces), Fraction(0))
    resultant_x = sum((fx for _, _, _, fx, _ in forces), Fraction(0))
    resultant_y = sum((fy for _, _, _, _, fy in forces), Fraction(0))
    expected = moment_about_origin - pivot_x * resultant_y + pivot_y * resultant_x

    checks: list[Check] = []
    if candidate.exact_value is None:
        checks.append(_check(QUANTITY, False, "the candidate carries no exact moment"))
    else:
        try:
            stated = Fraction(candidate.exact_value)
        except (ValueError, ZeroDivisionError):
            checks.append(_check(QUANTITY, False, f"moment {candidate.exact_value!r} is not exact"))
        else:
            checks.append(
                _check(
                    QUANTITY,
                    stated == expected,
                    f"transporting the origin moment {moment_about_origin} to the pivot "
                    f"gives {expected}; candidate stated {stated}",
                )
            )
    checks.append(
        _check(
            DIMENSION,
            candidate.units == result_unit
            and _same_dimension(result_unit, f"{force_unit}*{length_unit}"),
            f"the moment must carry {result_unit!r}, the product of {force_unit!r} and "
            f"{length_unit!r}; candidate reported {candidate.units!r}",
        )
    )
    return tuple(checks)


# --------------------------------------------------------------------------
# Uniform motion
# --------------------------------------------------------------------------


def _quantity(inputs: dict[str, Any], field: str) -> tuple[Fraction, str]:
    raw = inputs.get(field)
    if not isinstance(raw, dict):
        raise _fail(f"{field}: expected an object with magnitude and unit")
    unit = raw.get("unit")
    if not isinstance(unit, str):
        raise _fail(f"{field}.unit: expected a unit symbol")
    try:
        parse_unit(unit)
    except UnitError as error:
        raise _fail(f"{field}.unit: {error}") from error
    return _exact(raw.get("magnitude"), f"{field}.magnitude"), unit


def _si(magnitude: Fraction, unit: str) -> Fraction:
    return magnitude * parse_unit(unit)[0]


def solve_uniform_motion(inputs: dict[str, Any], budget: ResourceBudget) -> Solution:
    speed, speed_unit = _quantity(inputs, "speed")
    duration, time_unit = _quantity(inputs, "time")
    result_unit = inputs.get("result_unit", "m")
    if not isinstance(result_unit, str):
        raise _fail("result_unit: expected a unit symbol")
    try:
        parse_unit(result_unit)
    except UnitError as error:
        raise _fail(f"result_unit: {error}") from error
    if not _same_dimension(speed_unit, "m/s"):
        raise _fail(f"speed.unit: {speed_unit!r} is not a speed")
    if not _same_dimension(time_unit, "s"):
        raise _fail(f"time.unit: {time_unit!r} is not a duration")
    if not _same_dimension(result_unit, "m"):
        raise _fail(f"result_unit: {result_unit!r} is not a length")
    if duration < 0:
        raise _fail("time.magnitude: a duration is not negative")

    displacement_si = _si(speed, speed_unit) * _si(duration, time_unit)
    displacement = displacement_si / parse_unit(result_unit)[0]
    return Solution(
        candidate=Candidate(AnswerType.QUANTITY, exact_value=str(displacement), units=result_unit),
        steps=(
            Step(
                "to-si",
                f"{speed} {speed_unit} and {duration} {time_unit} in SI base units",
                f"{_si(speed, speed_unit)} m/s, {_si(duration, time_unit)} s",
            ),
            Step("multiply", "displacement = speed * time", f"{displacement_si} m"),
            Step("to-result-unit", f"expressed in {result_unit}", str(displacement)),
        ),
        tool_evidence=(f"physics.kernel:registry@{registry_hash()[:16]}",),
        assumptions=("the speed is constant over the whole duration",),
        limitations=("a constant-speed model says nothing about a body that accelerates",),
    )


def check_uniform_motion(
    inputs: dict[str, Any], candidate: Candidate, budget: ResourceBudget
) -> CheckSet:
    speed, speed_unit = _quantity(inputs, "speed")
    duration, time_unit = _quantity(inputs, "time")
    result_unit = str(inputs.get("result_unit", "m"))
    checks: list[Check] = []

    if candidate.exact_value is None:
        return (_check(QUANTITY, False, "the candidate carries no exact displacement"),)
    try:
        stated = Fraction(candidate.exact_value)
    except (ValueError, ZeroDivisionError):
        return (_check(QUANTITY, False, f"displacement {candidate.exact_value!r} is not exact"),)

    # Independent route: invert the relation. The claimed displacement and the given
    # duration must return the given speed, which exercises the released converter in the
    # opposite direction from the solver's.
    duration_si = _si(duration, time_unit)
    if duration_si == 0:
        checks.append(
            _check(
                QUANTITY,
                stated == 0,
                "a zero duration admits only a zero displacement, which cannot be inverted",
            )
        )
    else:
        recovered = _si(stated, result_unit) / duration_si
        checks.append(
            _check(
                QUANTITY,
                recovered == _si(speed, speed_unit),
                f"dividing the claimed displacement by the duration returns {recovered} m/s "
                f"against the given {_si(speed, speed_unit)} m/s",
            )
        )

    checks.append(
        _check(
            DIMENSION,
            candidate.units == result_unit and _same_dimension(result_unit, "m"),
            f"the displacement must carry the requested length unit {result_unit!r}; "
            f"candidate reported {candidate.units!r}",
        )
    )
    return tuple(checks)


#: The pilot's installed kernels, by problem type. This mapping is what a caller hands to
#: `registry.register_descriptor_domain` alongside the validated descriptor: the descriptor
#: says what the domain claims, this says what is actually implemented, and registration
#: refuses the pair when they disagree.
MECHANICS_KERNELS: dict[str, DomainKernel] = {
    STATICS_EQUILIBRIUM: DomainKernel(
        answer_type=AnswerType.STRUCTURED,
        solver=solve_statics_equilibrium,
        checker=check_statics_equilibrium,
    ),
    MOMENT_BALANCE: DomainKernel(
        answer_type=AnswerType.QUANTITY,
        solver=solve_moment_balance,
        checker=check_moment_balance,
    ),
    UNIFORM_MOTION: DomainKernel(
        answer_type=AnswerType.QUANTITY,
        solver=solve_uniform_motion,
        checker=check_uniform_motion,
    ),
}

__all__ = [
    "MECHANICS_KERNELS",
    "MOMENT_BALANCE",
    "STATICS_EQUILIBRIUM",
    "UNIFORM_MOTION",
]
