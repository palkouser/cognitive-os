"""S22A-W3: `science.chemistry`, the second domain that arrived as data.

The chemistry pilot is where §3.4's honesty constraint bites: a domain whose verifier cannot
verify is a silo wearing a lifecycle field. So the tests below spend most of their effort on
the two things that make the claim real — that every declared capability is actually
exercised, and that a wrong answer is refused for a reason a reader can check.

The pilot is registered once at import, for the reason `test_mechanics_pilot` gives: there is
no unregister, because a registry that could forget a domain could replace one (W1-F2).
"""

from __future__ import annotations

from fractions import Fraction
from pathlib import Path
from typing import Any

import pytest

from cognitive_os.domain.descriptors import (
    DomainDescriptorV1,
    DomainPackageError,
    concept_views,
    released_domain_descriptors,
    validate_domain_package,
)
from cognitive_os.domain.domains import AnswerType, ResourceBudget, VerificationDisposition
from cognitive_os.domains import chemistry, registry
from cognitive_os.domains.descriptor_runner import run_descriptor_case
from cognitive_os.domains.solvers import Candidate, SolverError

REPOSITORY = Path(__file__).resolve().parents[3]
PACKAGE = REPOSITORY / "docs/sprints/sprint-22/packages/science.chemistry.v1.json"

SEALED_RELEASED_SNAPSHOT = "00187f2bc6e0015529de8388ea33a1e6287939ca4d393875400bc68320997119"

BUDGET = ResourceBudget()

PILOT: DomainDescriptorV1 = validate_domain_package(PACKAGE.read_bytes())
if (PILOT.domain_id, PILOT.revision) not in registry.registered_descriptor_domains():
    registry.register_descriptor_domain(PILOT, chemistry.CHEMISTRY_KERNELS)

MASSES = {"C": "12", "H": "1", "O": "16"}

#: CH4 + 2 O2 -> CO2 + 2 H2O. Balanced, 80 g/mol on each side.
COMBUSTION: dict[str, Any] = {
    "reactants": [{"formula": "CH4", "coefficient": 1}, {"formula": "O2", "coefficient": 2}],
    "products": [{"formula": "CO2", "coefficient": 1}, {"formula": "H2O", "coefficient": 2}],
    "atomic_masses": MASSES,
}
#: The same equation with one water missing: hydrogen and oxygen no longer balance.
UNBALANCED: dict[str, Any] = {
    **COMBUSTION,
    "products": [{"formula": "CO2", "coefficient": 1}, {"formula": "H2O", "coefficient": 1}],
}
WATER_SAMPLE: dict[str, Any] = {
    "formula": "H2O",
    "atomic_masses": {"H": "1", "O": "16"},
    "mass": {"magnitude": "36", "unit": "g"},
    "result_unit": "mol",
}

TASKS = {
    chemistry.MASS_BALANCE: COMBUSTION,
    chemistry.MOLAR_CONVERSION: WATER_SAMPLE,
}


def _solve(problem_type: str, inputs: dict[str, Any]) -> Candidate:
    return registry.resolve(problem_type).solver(inputs, BUDGET).candidate


def _judge(problem_type: str, inputs: dict[str, Any], candidate: Candidate) -> Any:
    return registry.resolve(problem_type).checker(inputs, candidate, BUDGET)


def _passed(checks: Any) -> bool:
    return all(check.disposition is VerificationDisposition.PASS for check in checks)


def _failures(checks: Any) -> list[Any]:
    return [item for item in checks if item.disposition is not VerificationDisposition.PASS]


# ------------------------------------------------------- the package and the door


def test_the_committed_package_is_the_second_pilot_the_pre_registration_froze() -> None:
    assert PILOT.domain_id == "science.chemistry"
    assert PILOT.revision == 1
    assert PILOT.lifecycle.value == "pilot"
    assert set(PILOT.problem_types) == set(chemistry.CHEMISTRY_KERNELS)


def test_every_declared_capability_is_actually_exercised() -> None:
    """§3.4's honesty constraint, as an assertion rather than a promise.

    A capability the checker never emits would be refused at resolution by the released
    verifier (`missing_required_verifier`), so a descriptor that names one is a domain that
    can never be accepted. Checking it here means the failure is a red test, not a red run.
    """
    declared = set(PILOT.capabilities.verifier_capabilities)
    assert declared == {chemistry.DIMENSION, chemistry.QUANTITY, chemistry.STOICHIOMETRY}
    for problem_type, inputs in TASKS.items():
        exercised = {
            check.capability for check in _judge(problem_type, inputs, _solve(problem_type, inputs))
        }
        assert exercised == declared, problem_type


def test_the_new_capability_is_a_kernel_and_not_a_borrowed_name() -> None:
    """`chemistry.stoichiometry` counts atoms; the other two do what they do everywhere."""
    assert chemistry.STOICHIOMETRY == "chemistry.stoichiometry"
    assert chemistry.STOICHIOMETRY not in {
        name
        for entry in registry.entries()
        if entry.domain is not None
        for name in entry.required_verifiers
    }, "a new capability name must not silently claim a released verifier's meaning"


def test_the_excluded_candidates_are_recorded_with_reasons() -> None:
    """§3.4: a problem type that cannot be verified is out, and says why it is out."""
    assert set(chemistry.EXCLUDED_CANDIDATES) == {
        "chemistry.reaction-prediction",
        "chemistry.equilibrium-constant",
    }
    assert not set(chemistry.EXCLUDED_CANDIDATES) & set(PILOT.problem_types)
    assert all(len(reason) > 40 for reason in chemistry.EXCLUDED_CANDIDATES.values())


def test_two_pilots_resolve_side_by_side_without_moving_the_released_four() -> None:
    for problem_type in PILOT.problem_types:
        entry = registry.resolve(problem_type)
        assert entry.domain_id == PILOT.domain_id
        assert entry.domain is None
    assert registry.released_snapshot_hash() == SEALED_RELEASED_SNAPSHOT
    assert len(registry.problem_types_for("physics")) == 8


# --------------------------------------------------------------------- the kernels


def test_a_balanced_equation_is_balanced_by_both_routes() -> None:
    candidate = _solve(chemistry.MASS_BALANCE, COMBUSTION)
    assert candidate.answer_type is AnswerType.STRUCTURED
    assert candidate.structured["balanced"] is True
    assert candidate.structured["reactant_mass"] == "80"
    assert candidate.structured["product_mass"] == "80"
    assert candidate.units == "g/mol"
    assert _passed(_judge(chemistry.MASS_BALANCE, COMBUSTION, candidate))


def test_an_unbalanced_equation_is_reported_unbalanced_and_names_the_elements() -> None:
    """The failing chemistry candidate §4.2 asks for: a real reason, not only a pass."""
    candidate = _solve(chemistry.MASS_BALANCE, UNBALANCED)
    assert candidate.structured["balanced"] is False
    assert candidate.structured["unbalanced_elements"] == ["H", "O"]
    # Reporting an imbalance correctly is itself a pass: the checker agrees it is unbalanced.
    assert _passed(_judge(chemistry.MASS_BALANCE, UNBALANCED, candidate))


def test_an_unbalanced_equation_declared_balanced_is_refused() -> None:
    """The honest-looking answer: correct for a different equation, untrue for this one."""
    forged = _solve(chemistry.MASS_BALANCE, COMBUSTION)
    checks = _judge(chemistry.MASS_BALANCE, UNBALANCED, forged)
    failed = _failures(checks)
    assert failed, "a fabricated balance passed every check"
    assert any("['H', 'O']" in item.detail for item in failed)
    assert any(item.capability == chemistry.STOICHIOMETRY for item in failed)


def test_a_tally_that_disagrees_with_its_own_mass_is_caught() -> None:
    candidate = _solve(chemistry.MASS_BALANCE, COMBUSTION)
    forged = Candidate(
        AnswerType.STRUCTURED,
        structured={**candidate.structured, "reactant_mass": "81"},
        units="g/mol",
    )
    failed = _failures(_judge(chemistry.MASS_BALANCE, COMBUSTION, forged))
    assert len(failed) == 1
    assert failed[0].capability == chemistry.QUANTITY
    assert "80" in failed[0].detail


def test_molar_conversion_round_trips_through_the_molar_mass() -> None:
    candidate = _solve(chemistry.MOLAR_CONVERSION, WATER_SAMPLE)
    assert candidate.exact_value == "2"
    assert candidate.units == "mol"
    assert _passed(_judge(chemistry.MOLAR_CONVERSION, WATER_SAMPLE, candidate))


def test_a_misread_molar_mass_is_caught_by_the_inverse() -> None:
    """16 g/mol instead of 18 gives 9/4 mol; multiplying back returns 40.5 g, not 36."""
    forged = Candidate(AnswerType.QUANTITY, exact_value="9/4", units="mol")
    failed = _failures(_judge(chemistry.MOLAR_CONVERSION, WATER_SAMPLE, forged))
    assert failed
    assert any("36" in item.detail for item in failed)


def test_the_arithmetic_stays_exact() -> None:
    """A third of a gram stays a third of a gram, all the way to the answer."""
    sample = {**WATER_SAMPLE, "mass": {"magnitude": "1/3", "unit": "g"}}
    assert Fraction(_solve(chemistry.MOLAR_CONVERSION, sample).exact_value or "") == Fraction(1, 54)


@pytest.mark.parametrize(
    ("formula", "expected"),
    [("H2O", {"H": 2, "O": 1}), ("CH4", {"C": 1, "H": 4}), ("NaCl", {"Na": 1, "Cl": 1})],
)
def test_the_formula_grammar_reads_what_it_accepts(formula: str, expected: dict[str, int]) -> None:
    assert chemistry.parse_formula(formula) == expected


@pytest.mark.parametrize(
    ("problem_type", "inputs", "reason"),
    [
        (chemistry.MOLAR_CONVERSION, {**WATER_SAMPLE, "formula": "Ca(OH)2"}, "grammar"),
        (chemistry.MOLAR_CONVERSION, {**WATER_SAMPLE, "formula": "h2o"}, "grammar"),
        (
            chemistry.MOLAR_CONVERSION,
            {**WATER_SAMPLE, "atomic_masses": {"H": "1"}},
            "no declared mass for ['O']",
        ),
        (
            chemistry.MOLAR_CONVERSION,
            {**WATER_SAMPLE, "mass": {"magnitude": 36.0, "unit": "g"}},
            "float",
        ),
        (
            chemistry.MOLAR_CONVERSION,
            {**WATER_SAMPLE, "mass": {"magnitude": "36", "unit": "s"}},
            "not a mass",
        ),
        (chemistry.MOLAR_CONVERSION, {**WATER_SAMPLE, "result_unit": "g"}, "amount of substance"),
        (
            chemistry.MASS_BALANCE,
            {**COMBUSTION, "reactants": [{"formula": "CH4", "coefficient": 0}]},
            "positive whole number",
        ),
        (chemistry.MASS_BALANCE, {**COMBUSTION, "atomic_masses": {"C": "-12"}}, "positive"),
    ],
    ids=[
        "parentheses",
        "lowercase-formula",
        "undeclared-element",
        "float-mass",
        "mass-unit-is-a-time",
        "amount-unit-is-a-mass",
        "zero-coefficient",
        "negative-atomic-mass",
    ],
)
def test_the_solvers_refuse_rather_than_guess(
    problem_type: str, inputs: dict[str, Any], reason: str
) -> None:
    with pytest.raises(SolverError) as caught:
        _solve(problem_type, inputs)
    assert reason in str(caught.value)


# ----------------------------------------------------------------- the governed run


@pytest.mark.asyncio
@pytest.mark.parametrize("problem_type", sorted(TASKS), ids=lambda name: name)
async def test_each_task_is_solved_by_the_tool_plane_and_judged_by_the_verifier(
    problem_type: str,
) -> None:
    run = await run_descriptor_case(problem_type, TASKS[problem_type])
    assert run.domain_id == "science.chemistry"
    assert run.tool_status == "completed"
    assert run.verifier_status == "passed"
    assert run.accepted
    assert chemistry.STOICHIOMETRY in run.required_capabilities
    for expected in ("tool_call.authorized", "tool_call.completed", "verifier.completed"):
        assert expected in run.event_types, expected


@pytest.mark.asyncio
async def test_a_capability_that_never_runs_blocks_acceptance() -> None:
    """§3.5: a package whose capabilities name no verifier that runs is refused at resolution."""
    run = await run_descriptor_case(
        chemistry.MOLAR_CONVERSION,
        WATER_SAMPLE,
        required_capabilities=("chemistry.spectroscopy",),
    )
    assert not run.accepted
    assert run.verifier_status == "unverifiable"
    assert "chemistry.spectroscopy" in run.message


# -------------------------------------------------------------- cross-domain views


def test_both_pilots_share_into_physics_without_colliding() -> None:
    from cognitive_os.domains import mechanics

    mechanics_package = REPOSITORY / "docs/sprints/sprint-22/packages/engineering.mechanics.v1.json"
    other = validate_domain_package(mechanics_package.read_bytes())
    if (other.domain_id, other.revision) not in registry.registered_descriptor_domains():
        registry.register_descriptor_domain(other, mechanics.MECHANICS_KERNELS)

    views = concept_views((PILOT, other, *released_domain_descriptors()))
    physics = {view.concept_id: view for view in views["physics"]}
    assert {view.owner_domain_id for view in physics.values()} == {
        "science.chemistry",
        "engineering.mechanics",
    }
    assert all(view.exposure.value == "shared" for view in physics.values())


@pytest.mark.parametrize(
    ("target", "reason"),
    [
        ("science.astronomy", "no registered or released domain answers to"),
        ("science.chemistry", "does not declare"),
    ],
    ids=["target-does-not-exist", "target-never-declared-it-back"],
)
def test_a_share_the_target_never_agreed_to_is_refused(target: str, reason: str) -> None:
    """§3.5's third case, at the layer that owns it: the catalogue, not the package."""
    intruder = PILOT.model_copy(
        update={
            "domain_id": "science.materials",
            "problem_types": (),
            "related_domain_ids": (target,),
            "transfer_links": (),
            "concepts": (
                PILOT.concepts[0].model_copy(
                    update={
                        "concept_id": "materials.lattice",
                        "shared_with": (target,),
                        "content_hash": "",
                    }
                ),
            ),
            "content_hash": "",
        }
    )
    with pytest.raises(DomainPackageError, match=reason):
        concept_views((intruder, PILOT, *released_domain_descriptors()))


def test_a_share_into_a_released_domain_needs_no_reciprocity() -> None:
    """The asymmetry, asserted: the released four are derived and have nothing to declare."""
    views = concept_views((PILOT, *released_domain_descriptors()))
    assert {view.concept_id for view in views["physics"]} == {
        "chemistry.molar_mass",
        "chemistry.conservation_of_mass",
    }
