"""S22E-W4: Gate M, the five exits, the release — and the negative's own falsifiability.

22C's release lesson is that **a negative needs the same falsifiability a pass does**. So these
tests are not lighter because the outcome is a typed negative: every condition and every
criterion names the record and path it read, the two failing conditions are pinned to the
predecessor seal they read and the licence that forbade re-reading it, and the tag that was
*not* created is asserted absent rather than merely unmentioned.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import pytest

REPO = Path(__file__).resolve().parents[3]
EVIDENCE = REPO / "docs/sprints/sprint-22/evidence"

RECORDS = {
    "gate_m": EVIDENCE / "sprint-22e-gate-m.json",
    "exits": EVIDENCE / "sprint-22e-exit-criteria.json",
    "gates": EVIDENCE / "sprint-22e-w4-gates.json",
    "release": EVIDENCE / "sprint-22e-release.json",
    "experience": EVIDENCE / "sprint-22e-w4-experience.json",
}

PROGRAMME_TAG = "sprint-22-baseline"
NEGATIVE_TAG = "sprint-22e-evidence-baseline"


def _canonical(value: Any) -> bytes:
    return json.dumps(value, indent=1, sort_keys=True, ensure_ascii=False).encode("utf-8")


def _load(name: str) -> dict[str, Any]:
    return json.loads(RECORDS[name].read_text(encoding="utf-8"))


@pytest.mark.parametrize("name", sorted(RECORDS))
def test_every_w4_record_exists_and_its_seal_recomputes(name: str) -> None:
    stored = _load(name)
    body = {key: value for key, value in stored.items() if key != "integrity_content_hash"}
    assert hashlib.sha256(_canonical(body)).hexdigest() == stored["integrity_content_hash"]


# ---------------------------------------------------------------------------
# Gate M, read once against readings frozen before any measurement existed
# ---------------------------------------------------------------------------


def test_gate_m_reads_all_ten_conditions_and_none_is_deferred() -> None:
    gate = _load("gate_m")
    assert gate["counts"]["total"] == 10
    assert [row["condition"] for row in gate["conditions"]] == list(range(1, 11))
    assert gate["read_once"] is True


def test_gate_m_is_seven_of_ten_and_names_which_failed() -> None:
    gate = _load("gate_m")
    assert gate["counts"] == {"total": 10, "met": 7, "failed": 3}
    assert gate["conditions_failed"] == [6, 7, 10]
    assert gate["all_conditions_pass"] is False


@pytest.mark.parametrize("number", [6, 7])
def test_the_inherited_failures_read_a_predecessor_seal_and_could_not_be_re_read(
    number: int,
) -> None:
    """The two conditions 22E could not move, pinned to what forbade moving them."""
    gate = _load("gate_m")
    row = next(item for item in gate["conditions"] if item["condition"] == number)
    assert row["source_kind"] == "predecessor_seal"
    assert row["reads"].startswith("sprint-22d-exit-criteria.json#")
    assert row["value"] is False
    assert row["value_is_what_w0_expected"] is True
    licence = json.loads(
        (EVIDENCE / "sprint-22e-w3-remeasurement.json").read_text(encoding="utf-8")
    )
    assert licence["resolution"]["re_measurement_licensed"] is False


def test_condition_10_fails_because_the_programme_tag_was_not_created() -> None:
    """Not because something broke: the programme tag marks a pass, and this is not one."""
    row = next(item for item in _load("gate_m")["conditions"] if item["condition"] == 10)
    assert row["value"] is None
    assert row["reads"] == "sprint-22e-release.json#tag.peels_to"
    release = _load("release")
    assert release["tag"]["name"] == PROGRAMME_TAG
    assert release["tag"]["created"] is False
    assert release["tag"]["why_not_created"]


@pytest.mark.parametrize("number", [1, 2, 3, 4, 5, 8, 9])
def test_each_met_condition_names_the_record_it_read(number: int) -> None:
    row = next(item for item in _load("gate_m")["conditions"] if item["condition"] == number)
    assert row["met"] is True
    assert "#" in row["reads"]
    assert row["sentence"]


# ---------------------------------------------------------------------------
# The release head's gates: two independent verdicts
# ---------------------------------------------------------------------------


def test_the_lanes_were_read_at_the_release_head_and_all_passed() -> None:
    gates = _load("gates")
    release = _load("release")
    assert gates["release_head"] == release["release"]["merge_commit"]
    assert gates["lanes_not_successful"] == []
    assert gates["lane_count"] == 30


def test_every_family_condition_9_names_has_a_passing_lane() -> None:
    """ "the gates pass" as an enumeration a test can check, not as a word."""
    gates = _load("gates")
    assert set(gates["condition_9_families"]) == {
        "security",
        "provider",
        "migration",
        "distribution",
        "repository_language",
    }
    for family in gates["condition_9_families"].values():
        assert family["conclusion"] == "success", family
    assert gates["every_named_family_has_a_passing_lane"] is True


def test_the_local_matrix_is_a_second_independent_verdict() -> None:
    matrix = _load("gates")["local_matrix"]
    assert matrix["gates"] == 15
    assert matrix["failed"] == []
    assert matrix["ran"] == matrix["passed"] == 9
    assert {"historical_regression", "compatibility", "security"} <= set(matrix["gate_ids_passed"])


# ---------------------------------------------------------------------------
# The release, and the tag discipline
# ---------------------------------------------------------------------------


def test_the_negative_tag_is_annotated_and_peels_to_the_merge_commit() -> None:
    release = _load("release")
    negative = release["negative_tag"]
    assert negative["name"] == NEGATIVE_TAG
    assert negative["created"] is True
    assert negative["annotated"] is True
    assert negative["peels_to"] == release["release"]["merge_commit"]
    assert negative["peels_to_the_merge_commit"] is True


def test_the_tag_was_placed_after_the_squash_merge() -> None:
    """22C's release lesson: a squash merge leaves the wave branch a non-ancestor."""
    release = _load("release")
    assert release["release"]["merge_method"] == "squash"
    assert release["negative_tag"]["placed_after_the_squash_merge"] is True
    assert "non-ancestor" in release["negative_tag"]["why_that_order"]


def test_the_release_head_ci_was_green_at_the_exact_commit() -> None:
    release = _load("release")
    ci = release["release"]["post_merge_ci"]
    assert ci["head_sha"] == release["release"]["merge_commit"]
    assert ci["conclusion"] == "success"
    assert set(ci["job_counts"]) == {"success"}


# ---------------------------------------------------------------------------
# The five exits
# ---------------------------------------------------------------------------


def test_the_exit_sentences_are_the_pre_registered_ones_unmoved() -> None:
    exits = _load("exits")
    registration = json.loads(
        (EVIDENCE / "sprint-22e-pre-registration.json").read_text(encoding="utf-8")
    )
    assert [item["criterion"] for item in exits["criteria"]] == registration["exit_criteria"]
    assert registration["amendments_made_by_22e"] == 0


def test_three_of_five_exits_are_met_and_the_outcome_is_a_typed_negative() -> None:
    exits = _load("exits")
    assert exits["counts"] == {"total": 5, "met": 3, "unmet": 2}
    assert exits["outcome"] == "typed_negative"
    assert exits["all_met"] is False
    assert [item["index"] for item in exits["criteria"] if not item["met"]] == [3, 4]


def test_the_zero_mutation_exit_counted_every_traversal_the_sprint_ran() -> None:
    criterion = _load("exits")["criteria"][0]
    assert criterion["met"] is True
    assert criterion["traversals_measured"] == 7
    assert all(row["mutated_members"] == [] for row in criterion["records"])
    assert criterion["at_least_one_rejection_was_real"]["refusing_gate"]


def test_the_approved_change_exit_rests_on_the_landed_bytes_not_on_a_green_tick() -> None:
    criterion = _load("exits")["criteria"][1]
    assert criterion["met"] is True
    assert criterion["landed_bytes_are_the_evaluated_bytes"] is True
    assert criterion["post_merge_ci"] == "success"
    assert criterion["one_change_only"] == 2


def test_the_experience_exit_is_judged_on_its_own_words() -> None:
    """The stricter distinguishability probe is reported beside the verdict, never inside it."""
    criterion = _load("exits")["criteria"][2]
    assert criterion["met"] is True
    assert criterion["failed_kind"]["outranked_every_distractor"] is True
    assert criterion["successful_kind"]["read_back_validates_as_the_contract"] is True
    assert "stricter_probe_not_required_by_the_sentence" in criterion


@pytest.mark.parametrize("index", [3, 4])
def test_each_unmet_exit_names_the_measured_value_that_failed_it(index: int) -> None:
    """A negative needs the same falsifiability a pass does (22C's release lesson)."""
    criterion = _load("exits")["criteria"][index]
    assert criterion["met"] is False
    assert criterion["reads"]
    if index == 3:
        assert criterion["conditions_failed"] == [6, 7, 10]
        assert all(item["measured_value"] is not True for item in criterion["each_failure"])
    else:
        assert criterion["programme_tag_created"] is False
        assert criterion["why_not"]
        assert criterion["negative_tag"]["created"] is True
