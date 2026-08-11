"""S22A-W2: `engineering.mechanics`, the first domain that arrived as data.

Three things are under test here and they fail for different reasons, so they are kept
apart: the kernels (arithmetic and independent judgement), the registration door (what it
admits and what it refuses), and the governed run (a task solved by the released Tool Plane
and judged by the released verifier).

**About the global registry.** `register_descriptor_domain` writes into the process-wide
problem-type table and there is no unregister — a registry that could forget a domain is a
registry that could replace one, which is the failure W1-F2 named. So this module registers
the pilot exactly once, at import, and every other module's view of the released four stays
correct because `released_snapshot_hash()` is what the compat claim binds to (S22A-030).
"""

from __future__ import annotations

from fractions import Fraction
from pathlib import Path
from typing import Any

import pytest

from cognitive_os.domain.descriptors import (
    DomainDescriptorV1,
    concept_owners,
    concept_views,
    released_domain_descriptors,
    validate_domain_package,
)
from cognitive_os.domain.domains import AnswerType, ResourceBudget, VerificationDisposition
from cognitive_os.domains import mechanics, registry
from cognitive_os.domains.descriptor_runner import run_descriptor_case
from cognitive_os.domains.solvers import Candidate, SolverError

REPOSITORY = Path(__file__).resolve().parents[3]
PACKAGE = REPOSITORY / "docs/sprints/sprint-22/packages/engineering.mechanics.v1.json"

SEALED_RELEASED_SNAPSHOT = "00187f2bc6e0015529de8388ea33a1e6287939ca4d393875400bc68320997119"

BUDGET = ResourceBudget()

PILOT: DomainDescriptorV1 = validate_domain_package(PACKAGE.read_bytes())
if (PILOT.domain_id, PILOT.revision) not in registry.registered_descriptor_domains():
    registry.register_descriptor_domain(PILOT, mechanics.MECHANICS_KERNELS)


BALANCED_JOINT: dict[str, Any] = {
    "forces": [
        {"name": "load", "fx": 0, "fy": -30},
        {"name": "cable_a", "fx": "-40", "fy": 15},
        {"name": "cable_b", "fx": 40, "fy": 15},
    ],
    "force_unit": "N",
}
CANTILEVER: dict[str, Any] = {
    "forces": [
        {"name": "load", "x": 2, "y": 0, "fx": 0, "fy": -50},
        {"name": "reaction", "x": 0, "y": 0, "fx": 0, "fy": 50},
    ],
    "pivot": {"x": 0, "y": 0},
    "force_unit": "N",
    "length_unit": "m",
    "result_unit": "N*m",
}
TROLLEY: dict[str, Any] = {
    "speed": {"magnitude": "25", "unit": "m/s"},
    "time": {"magnitude": 12, "unit": "s"},
    "result_unit": "m",
}

TASKS = {
    mechanics.STATICS_EQUILIBRIUM: BALANCED_JOINT,
    mechanics.MOMENT_BALANCE: CANTILEVER,
    mechanics.UNIFORM_MOTION: TROLLEY,
}


def _solve(problem_type: str, inputs: dict[str, Any]) -> Candidate:
    return registry.resolve(problem_type).solver(inputs, BUDGET).candidate


def _judge(problem_type: str, inputs: dict[str, Any], candidate: Candidate) -> Any:
    return registry.resolve(problem_type).checker(inputs, candidate, BUDGET)


def _passed(checks: Any) -> bool:
    return all(check.disposition is VerificationDisposition.PASS for check in checks)


# --------------------------------------------------------- the package and the door


def test_the_committed_package_is_the_one_the_pre_registration_froze() -> None:
    assert PILOT.domain_id == "engineering.mechanics"
    assert PILOT.revision == 1
    assert PILOT.lifecycle.value == "pilot"
    assert set(PILOT.problem_types) == set(mechanics.MECHANICS_KERNELS)


def test_the_pilot_declares_only_capabilities_the_released_verifier_can_judge() -> None:
    """§3.3's honesty constraint: no capability name that nothing enforces."""
    assert set(PILOT.capabilities.verifier_capabilities) == {
        mechanics.DIMENSION,
        mechanics.QUANTITY,
    }
    for problem_type, inputs in TASKS.items():
        checks = _judge(problem_type, inputs, _solve(problem_type, inputs))
        exercised = {check.capability for check in checks}
        assert exercised == set(PILOT.capabilities.verifier_capabilities), problem_type


def test_the_pilot_resolves_through_the_released_table_as_a_string_id() -> None:
    for problem_type in PILOT.problem_types:
        entry = registry.resolve(problem_type)
        assert entry.domain_id == PILOT.domain_id
        assert entry.domain is None, "a descriptor-registered domain has no enum member"
    assert set(registry.problem_types_for(PILOT.domain_id)) == set(PILOT.problem_types)
    assert PILOT.domain_id in registry.domain_ids()


def test_registering_the_pilot_leaves_the_released_snapshot_where_it_was() -> None:
    """The decision, as an assertion: one hash moves and the other cannot (S22A-030)."""
    assert registry.released_snapshot_hash() == SEALED_RELEASED_SNAPSHOT
    assert registry.snapshot_hash() != SEALED_RELEASED_SNAPSHOT
    assert len(registry.problem_types_for("physics")) == 8


def test_the_released_four_still_derive_their_sealed_descriptors() -> None:
    """Measured with the pilot registered, which is the case W1 could not test."""
    derived = {item.domain_id: item for item in released_domain_descriptors()}
    assert set(derived) == {"coding", "logic", "mathematics", "physics"}
    assert all(item.lifecycle.value == "active" for item in derived.values())


@pytest.mark.parametrize(
    ("overrides", "expected"),
    [
        ({}, "already registered"),
        (
            {
                "domain_id": "physics",
                "related_domain_ids": (),
                "concepts": (),
                "transfer_links": (),
            },
            "is a released domain",
        ),
        (
            {"domain_id": "engineering.thermofluids", "problem_types": ("mechanics.no-such-type",)},
            "no installed kernel",
        ),
        ({"domain_id": "engineering.statics"}, "already registered"),
        ({"domain_id": "engineering", "problem_types": ()}, "namespace"),
    ],
    ids=["duplicate-identity", "released-id", "missing-kernel", "type-collision", "namespace"],
)
def test_the_registration_door_refuses_and_registers_nothing_halfway(
    overrides: dict[str, Any], expected: str
) -> None:
    before = registry.entries()
    candidate = PILOT.model_copy(update={**overrides, "content_hash": ""}) if overrides else PILOT
    with pytest.raises(registry.DescriptorDomainError) as caught:
        registry.register_descriptor_domain(candidate, mechanics.MECHANICS_KERNELS)
    assert any(expected in line for line in caught.value.diagnostics), caught.value.diagnostics
    assert registry.entries() == before, "a refused registration left entries behind"


# --------------------------------------------------------------------- the kernels


def test_statics_equilibrium_agrees_with_its_independent_route() -> None:
    candidate = _solve(mechanics.STATICS_EQUILIBRIUM, BALANCED_JOINT)
    assert candidate.answer_type is AnswerType.STRUCTURED
    assert candidate.structured["equilibrium"] is True
    assert candidate.units == "N"
    assert _passed(_judge(mechanics.STATICS_EQUILIBRIUM, BALANCED_JOINT, candidate))


def test_a_dropped_force_is_caught_by_the_audit_and_not_by_the_sum() -> None:
    """The check a re-sum cannot make: the two remaining forces still sum to zero."""
    candidate = _solve(mechanics.STATICS_EQUILIBRIUM, BALANCED_JOINT)
    forged = Candidate(
        AnswerType.STRUCTURED,
        structured={
            **candidate.structured,
            "force_count": 2,
            "forces_summed": ["load", "cable_a"],
        },
        units="N",
    )
    checks = _judge(mechanics.STATICS_EQUILIBRIUM, BALANCED_JOINT, forged)
    failed = [item for item in checks if item.disposition is not VerificationDisposition.PASS]
    assert len(failed) == 1
    assert "cable_b" in failed[0].detail


def test_an_unbalanced_joint_is_reported_as_unbalanced() -> None:
    inputs = {
        "forces": [{"name": "only", "fx": 3, "fy": 4}],
        "force_unit": "N",
    }
    candidate = _solve(mechanics.STATICS_EQUILIBRIUM, inputs)
    assert candidate.structured["equilibrium"] is False
    assert candidate.structured["resultant_x"] == "3"
    assert _passed(_judge(mechanics.STATICS_EQUILIBRIUM, inputs, candidate))


def test_the_moment_checker_never_repeats_the_solver_s_sum() -> None:
    """Pivot transport: the checker reaches the same number through a different identity."""
    candidate = _solve(mechanics.MOMENT_BALANCE, CANTILEVER)
    assert candidate.exact_value == "-100"
    assert candidate.units == "N*m"
    assert _passed(_judge(mechanics.MOMENT_BALANCE, CANTILEVER, candidate))

    reversed_sign = Candidate(AnswerType.QUANTITY, exact_value="100", units="N*m")
    checks = _judge(mechanics.MOMENT_BALANCE, CANTILEVER, reversed_sign)
    assert not _passed(checks)


def test_the_moment_is_pivot_independent_when_the_forces_balance() -> None:
    """The theorem the checker relies on, asserted rather than assumed."""
    moved = {**CANTILEVER, "pivot": {"x": 5, "y": "-3"}}
    assert _solve(mechanics.MOMENT_BALANCE, moved).exact_value == "-100"


def test_uniform_motion_round_trips_through_the_released_converter() -> None:
    candidate = _solve(mechanics.UNIFORM_MOTION, TROLLEY)
    assert candidate.exact_value == "300"
    assert _passed(_judge(mechanics.UNIFORM_MOTION, TROLLEY, candidate))

    in_kilometres = {**TROLLEY, "result_unit": "km"}
    assert _solve(mechanics.UNIFORM_MOTION, in_kilometres).exact_value == "3/10"


def test_the_right_number_in_the_wrong_unit_is_refused() -> None:
    forged = Candidate(AnswerType.QUANTITY, exact_value="300", units="km")
    checks = _judge(mechanics.UNIFORM_MOTION, TROLLEY, forged)
    failed = [item for item in checks if item.disposition is not VerificationDisposition.PASS]
    assert failed and all("km" in item.detail for item in failed)


@pytest.mark.parametrize(
    ("problem_type", "inputs", "reason"),
    [
        (mechanics.STATICS_EQUILIBRIUM, {"forces": [], "force_unit": "N"}, "non-empty"),
        (
            mechanics.STATICS_EQUILIBRIUM,
            {"forces": [{"name": "a", "fx": 1.5, "fy": 0}], "force_unit": "N"},
            "float",
        ),
        (
            mechanics.STATICS_EQUILIBRIUM,
            {"forces": [{"name": "a", "fx": 1, "fy": 0}], "force_unit": "m"},
            "dimension of a force",
        ),
        (
            mechanics.STATICS_EQUILIBRIUM,
            {
                "forces": [{"name": "a", "fx": 1, "fy": 0}, {"name": "a", "fx": -1, "fy": 0}],
                "force_unit": "N",
            },
            "unique",
        ),
        (mechanics.MOMENT_BALANCE, {**CANTILEVER, "result_unit": "N"}, "not the product"),
        (mechanics.UNIFORM_MOTION, {**TROLLEY, "result_unit": "s"}, "not a length"),
        (
            mechanics.UNIFORM_MOTION,
            {**TROLLEY, "time": {"magnitude": -1, "unit": "s"}},
            "not negative",
        ),
    ],
    ids=[
        "no-forces",
        "float-input",
        "unit-is-not-a-force",
        "repeated-force-name",
        "moment-unit-mismatch",
        "displacement-unit-is-not-a-length",
        "negative-duration",
    ],
)
def test_the_solvers_refuse_rather_than_round(
    problem_type: str, inputs: dict[str, Any], reason: str
) -> None:
    with pytest.raises(SolverError) as caught:
        _solve(problem_type, inputs)
    assert reason in str(caught.value)


def test_every_kernel_is_exact_rational_arithmetic() -> None:
    """A third of a newton stays a third of a newton, all the way to the answer."""
    thirds = {
        "forces": [
            {"name": "a", "fx": "1/3", "fy": 0},
            {"name": "b", "fx": "-1/3", "fy": 0},
        ],
        "force_unit": "N",
    }
    candidate = _solve(mechanics.STATICS_EQUILIBRIUM, thirds)
    assert candidate.structured["equilibrium"] is True
    assert Fraction(candidate.structured["resultant_x"]) == 0


# ----------------------------------------------------------------- the governed run


@pytest.mark.asyncio
@pytest.mark.parametrize("problem_type", sorted(TASKS), ids=lambda name: name)
async def test_each_task_is_solved_by_the_tool_plane_and_judged_by_the_verifier(
    problem_type: str,
) -> None:
    run = await run_descriptor_case(problem_type, TASKS[problem_type])
    assert run.domain_id == "engineering.mechanics"
    assert run.tool_status == "completed"
    assert run.verifier_status == "passed"
    assert run.accepted
    # The whole authorisation trail, not just the answer: the pilot borrows the released
    # Tool Plane's policy, audit and timeout exactly as the four released domains do.
    for expected in (
        "tool_call.requested",
        "tool_call.authorized",
        "tool_call.started",
        "tool_call.completed",
        "verifier.started",
        "verifier.completed",
    ):
        assert expected in run.event_types, expected


@pytest.mark.asyncio
@pytest.mark.parametrize("problem_type", sorted(TASKS), ids=lambda name: name)
async def test_a_fabricated_answer_is_refused_on_the_same_path(problem_type: str) -> None:
    honest = await run_descriptor_case(problem_type, TASKS[problem_type])
    forged = dict(honest.candidate)
    forged["exact_value"] = "999999"
    forged["structured"] = {**forged.get("structured", {}), "equilibrium": False}
    refused = await run_descriptor_case(
        problem_type, TASKS[problem_type], candidate_override=forged
    )
    assert not refused.accepted
    assert refused.verifier_status in {"failed", "partial", "unverifiable"}


# ------------------------------------------------------------- cross-domain views


def test_a_shared_concept_is_stored_once_and_seen_from_both_domains() -> None:
    catalogue = (PILOT, *released_domain_descriptors())
    views = concept_views(catalogue)
    owners = concept_owners(catalogue)

    mine = {view.concept_id: view for view in views["engineering.mechanics"]}
    theirs = {view.concept_id: view for view in views["physics"]}
    shared = [item.concept_id for item in PILOT.concepts if item.shared_with]
    assert shared == ["mechanics.force_balance", "mechanics.moment_of_force"]

    for concept_id in shared:
        assert mine[concept_id].exposure.value == "owned"
        assert theirs[concept_id].exposure.value == "shared"
        assert owners[concept_id] == "engineering.mechanics"
        # One item, two views: the same object, so the same content hash by construction.
        assert mine[concept_id].concept is theirs[concept_id].concept


def test_a_private_concept_is_not_exposed_anywhere_else() -> None:
    views = concept_views((PILOT, *released_domain_descriptors()))
    elsewhere = [
        domain_id
        for domain_id, items in views.items()
        if domain_id != "engineering.mechanics"
        and any(view.concept_id == "mechanics.rigid_body" for view in items)
    ]
    assert elsewhere == []


def test_two_domains_may_not_both_declare_the_same_concept() -> None:
    """A concept with two owners is a concept stored twice, which is the silo itself."""
    rival = PILOT.model_copy(
        update={
            "domain_id": "engineering.statics",
            "problem_types": (),
            "content_hash": "",
        }
    )
    with pytest.raises(Exception, match="declared by both"):
        concept_owners((PILOT, rival))
