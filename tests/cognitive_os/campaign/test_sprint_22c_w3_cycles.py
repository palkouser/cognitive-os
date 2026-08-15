"""Sprint 22C W3. Cycles 2 and 3, the plant, and the holdout — read from their sealed records.

W3's headline is a negative on the sprint's hardest exit, and a negative is exactly the kind
of number that quietly improves when nobody pins it. Every assertion here says what a measured
value *meant*, so a later wave that changes one has to change a sentence about it too.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

EVIDENCE = Path("docs/sprints/sprint-22/evidence")
CHAPTER = EVIDENCE / "sprint-22c-w3-chapter.json"
CYCLE2 = EVIDENCE / "sprint-22c-w3-cycle2.json"
CYCLE3 = EVIDENCE / "sprint-22c-w3-cycle3.json"
PLANT = EVIDENCE / "sprint-22c-w3-plant.json"
IMPROVEMENT = EVIDENCE / "sprint-22c-w3-improvement.json"
PROPOSALS = EVIDENCE / "sprint-22c-w3-proposals"
CYCLES = (EVIDENCE / "sprint-22c-w2-cycle1.json", CYCLE2, CYCLE3)


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def chapter() -> dict[str, Any]:
    return _load(CHAPTER)


@pytest.fixture(scope="module")
def cycle2() -> dict[str, Any]:
    return _load(CYCLE2)


@pytest.fixture(scope="module")
def cycle3() -> dict[str, Any]:
    return _load(CYCLE3)


# --- the second source ------------------------------------------------------


def test_the_chemistry_inventory_covers_the_two_cleared_chapters(chapter) -> None:
    assert [item["number"] for item in chapter["chapters"]] == [3, 4]
    assert [item["chosen_for"] for item in chapter["chapters"]] == [
        "chemistry.molar-conversion",
        "chemistry.mass-balance",
    ]
    assert chapter["counts"]["worked_examples_in_the_bodies"] == 41
    assert chapter["counts"]["per_chapter"] == {"3": 25, "4": 16}


def test_the_second_book_is_read_by_its_own_layout(chapter) -> None:
    """W3: two books, two markers, one reader. The cut falls after the stated answer."""
    rule = chapter["location_rule"]
    assert rule["marker"] == "EXAMPLE <chapter>.<number>"
    assert rule["ends_after"] == r"\nAnswer:\n[^\n]+\n"
    assert "EXAMPLE " in rule["stops"][0] or "EXAMPLE" in " ".join(rule["stops"])


def test_the_physics_passage_identities_were_not_rewritten() -> None:
    """A wave does not rewrite an identity that sealed evidence already names."""
    physics = {
        item["passage_id"] for item in _load(EVIDENCE / "sprint-22c-w2-chapter.json")["passages"]
    }
    chemistry = {item["passage_id"] for item in _load(CHAPTER)["passages"]}
    assert not physics & chemistry
    assert all(item.startswith("ch") and not item.startswith("chem-") for item in physics)
    assert all(item.startswith("chem-") for item in chemistry)


def test_every_chemistry_passage_has_a_sealed_proposal(chapter) -> None:
    identifiers = {item["passage_id"] for item in chapter["passages"]}
    assert {path.stem for path in PROPOSALS.glob("*.json")} == identifiers


# --- cycle 2, and the second reason a domain is the constraint ---------------


def test_cycle_two_completed_nine_stages_and_acquired_nothing(cycle2) -> None:
    assert cycle2["cycle"] == 2
    assert cycle2["stages"]["all_nine_in_order"] is True
    assert cycle2["store"]["kind"] == "postgresql"
    assert cycle2["yield"]["worked_examples_located"] == 25
    assert cycle2["yield"]["formalised_by_the_provider"] == 1
    assert cycle2["yield"]["accepted_by_the_kernel"] == 0
    assert cycle2["yield"]["promoted"] == 0


def test_the_one_formalised_chemistry_passage_failed_on_rounding(cycle2) -> None:
    """W3-F2. The textbook rounds; the cross-check is exact equality by design (W1-F3)."""
    accepted = [
        item
        for item in cycle2["cross_check"]["per_segment"].values()
        if item["derivation_accepted"]
    ]
    assert len(accepted) == 1
    only = accepted[0]
    assert only["verifier_status"] == "passed"
    assert only["assertion_agrees_with_kernel"] is False
    assert only["asserted"] == {"exact_value": "0.12", "units": "mol"}
    assert "47/391" in only["message"]


def test_a_cycle_that_promoted_nothing_says_its_citation_walk_is_vacuous(cycle2) -> None:
    citations = cycle2["citations"]
    assert citations["promoted_artifacts"] == 0
    assert citations["vacuous_because_nothing_was_promoted"] is True
    # Vacuously true, and flagged — "nothing to check" is not "checked and passed".
    assert citations["all_chains_resolve"] is True


def test_the_kernel_demanded_an_input_its_answer_does_not_use(cycle2, cycle3) -> None:
    """W3-D1's refusal reason, on the two passages that hit it."""
    reasons = {
        **cycle2["yield"]["refusal_reasons"],
        **{
            key: value + cycle2["yield"]["refusal_reasons"].get(key, 0)
            for key, value in cycle3["yield"]["refusal_reasons"].items()
        },
    }
    assert reasons["kernel_requires_unstated_input"] == 2


# --- cycle 3 and the plant ---------------------------------------------------


def test_cycle_three_carried_the_plant_through_the_genuine_intake(cycle3) -> None:
    assert cycle3["cycle"] == 3
    assert cycle3["stages"]["all_nine_in_order"] is True
    # Sixteen genuine chapter-4 passages plus the plant, one intake, one order of stages.
    assert cycle3["yield"]["worked_examples_located"] == 16
    assert cycle3["quarantine"]["count"] == 17


def test_the_plant_meets_all_four_frozen_conditions() -> None:
    record = _load(PLANT)
    assert record["all_four_conditions_met"] is True
    conditions = record["conditions"]
    assert conditions["reaches_a_quarantine_state_with_a_named_released_reason"]["met"] is True
    assert (
        conditions["reaches_a_quarantine_state_with_a_named_released_reason"]["reason"]
        == "unverifiable_provider_data"
    )
    assert conditions["never_reaches_an_active_state"]["met"] is True
    assert conditions["appears_in_the_cycles_quarantine_report"]["met"] is True
    assert conditions["stays_quarantined_through_every_later_replay"]["met"] is True


def test_the_plant_was_caught_by_the_second_cross_check_leg_not_by_the_checker() -> None:
    """W0-F4 restated on real content: the checker passed the derivation, and should have."""
    caught = _load(PLANT)["how_it_was_caught"]
    assert caught["derivation_accepted_by_domains_checker"] is True
    assert caught["verifier_status"] == "passed"
    assert caught["assertion_agrees_with_kernel"] is False
    assert caught["refused_by"] == "cross_check.assertion_agrees_with_kernel"


def test_the_plant_is_the_one_w0_sealed() -> None:
    frozen = _load(EVIDENCE / "sprint-22c-contracts.json")["S22C-012"]
    assert _load(PLANT)["the_plant"]["content_hash"] == frozen["plant_content_hash"]
    assert _load(PLANT)["the_plant"]["segment_id"] == frozen["plant_segment_id"]


# --- three replay points -----------------------------------------------------


def test_every_cycle_replayed_every_retained_domain() -> None:
    for path in CYCLES:
        replay = _load(path)["evaluate"]
        assert replay["enumeration_source"] == "registry.domain_ids()"
        assert replay["domains_enumerated"] == 6
        assert len(replay["per_domain"]) == 6


def test_the_retained_set_is_replayed_by_every_later_cycle() -> None:
    """Cycle 1's artifact is executed again in cycles 2 and 3, not merely referenced."""
    for path in CYCLES:
        replay = _load(path)["evaluate"]
        assert replay["per_domain"]["engineering.mechanics"]["cases"] == 1
        assert replay["per_domain"]["engineering.mechanics"]["rate"] == 1.0
    assert _load(CYCLE2)["inherited_cases"]["count"] == 1
    assert _load(CYCLE3)["inherited_cases"]["count"] == 1


def test_no_domain_forgot_anything_across_the_three_cycles() -> None:
    rates = [
        _load(path)["evaluate"]["per_domain"]["engineering.mechanics"]["rate"] for path in CYCLES
    ]
    assert rates == [1.0, 1.0, 1.0]
    # Three measured points, and the delta between them is the forgetting claim.
    assert max(rates) - min(rates) == 0.0


# --- the improvement exit ----------------------------------------------------


def test_the_holdout_was_read_once_with_no_leakage() -> None:
    record = _load(IMPROVEMENT)
    assert record["holdout"]["measured_values_at_freeze"] == 0
    assert record["holdout"]["read_once"] is True
    assert record["separation"]["leakage_detected"] is False
    assert (
        record["holdout"]["frozen_integrity_content_hash"]
        == _load(EVIDENCE / "sprint-22c-holdout.json")["integrity_content_hash"]
    )


def test_both_arms_were_measured_and_the_exit_is_a_negative() -> None:
    comparison = _load(IMPROVEMENT)["comparison"]
    assert comparison["cases"] == 4
    assert comparison["arm_a_verified_successes"] == 0
    assert comparison["arm_b_verified_successes"] == 0
    assert comparison["improved_cases"] == 0
    assert comparison["at_least_one_retained_artifact_improved_a_held_out_task"] is False
    assert comparison["same_tasks_same_seeds_same_checker"] is True


def test_arm_a_failed_by_refusal_which_is_the_baseline_the_holdout_intended() -> None:
    for case in _load(IMPROVEMENT)["cases"]:
        assert case["arm_a_artifact_inactive"]["refused_before_solving"] is True
        assert case["arm_a_artifact_inactive"]["verified_success"] is False


def test_arm_b_never_borrowed_the_answer_from_the_case_it_was_filling() -> None:
    """Three cases had no retained artifact; the arm says so instead of running anyway."""
    cases = {item["case_id"]: item for item in _load(IMPROVEMENT)["cases"]}
    unsupplied = [
        item
        for item in cases.values()
        if item["arm_b_artifact_active"].get("no_retained_artifact_supplies_it")
    ]
    assert len(unsupplied) == 3
    assert all(item["domain_id"] == "science.chemistry" for item in unsupplied)
    assert all(item["restored_from"] is None for item in unsupplied)


def test_the_one_arm_b_that_ran_used_a_real_retained_artifact_and_was_wrong_about_the_case() -> (
    None
):
    """Not a pipeline failure: the artifact is sound and describes a different body."""
    case = next(
        item
        for item in _load(IMPROVEMENT)["cases"]
        if item["case_id"] == "holdout-uniform-motion-kilometres"
    )
    restored = case["restored_from"]
    assert restored is not None
    assert restored["from_cycle"] == 1
    assert restored["value"] == {"magnitude": "2.4", "unit": "m/s"}
    assert case["arm_b_artifact_active"]["verified_success"] is False
    assert "480" in case["arm_b_artifact_active"]["message"]
