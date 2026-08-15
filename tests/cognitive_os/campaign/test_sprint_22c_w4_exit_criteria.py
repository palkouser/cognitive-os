"""Sprint 22C W4. The five exits, read once — and a negative that can still be falsified.

22B's release wave pinned its record by pushing a measured number *below* its floor in a copy
and requiring the rebuilt document to come back `typed negative`, because a release record that
can only print `pass` has verified nothing. 22C's outcome is the negative, so the test has to
run the other way: **flip the one failing verdict in a copy and require `pass`.** A record that
can only print `typed negative` has verified exactly as little.

The rest of this file asserts what the criteria record *means* — that all five criteria come
from the frozen contract verbatim, that the three cycle-wide criteria really are evaluated in
all three cycles rather than in the first one, that §5's stop clause names its three things,
and that a missing evidence field is a refusal rather than a `false` that reads like a
measurement.

`recorded_at` and the seal over it are excluded from every comparison, so no test here fails
because a clock moved (22B W2-F1/F2).
"""

from __future__ import annotations

import importlib.util
import json
import shutil
import sys
from pathlib import Path
from typing import Any

import pytest

REPOSITORY = Path(__file__).resolve().parents[3]
SCRIPTS = REPOSITORY / "scripts"
EVIDENCE = REPOSITORY / "docs/sprints/sprint-22/evidence"
RECORD = EVIDENCE / "sprint-22c-exit-criteria.json"
CONTRACTS = EVIDENCE / "sprint-22c-contracts.json"

if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))


def _module(name: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / f"{name}.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules.setdefault(name, module)
    spec.loader.exec_module(module)
    return module


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def record() -> dict[str, Any]:
    return _load(RECORD)


@pytest.fixture(scope="module")
def contracts() -> dict[str, Any]:
    return _load(CONTRACTS)


@pytest.fixture
def rebuilt(tmp_path: Path) -> Any:
    """The driver, pointed at a writable copy of the evidence tree.

    Every assertion that needs to know what the record *would* say under different evidence
    edits the copy, never the sealed originals.
    """
    copied = tmp_path / "evidence"
    shutil.copytree(EVIDENCE, copied)
    driver = _module("exit_criteria_22c")
    driver.EVIDENCE = copied
    driver.CONTRACTS = copied / "sprint-22c-contracts.json"
    driver.PRE_REGISTRATION = copied / "sprint-22c-pre-registration.json"
    driver.OUTPUT = copied / "sprint-22c-exit-criteria.json"
    return driver


def _edit(driver: Any, filename: str, path: str, value: Any) -> None:
    target = driver.EVIDENCE / filename
    body = json.loads(target.read_text(encoding="utf-8"))
    cursor = body
    parts = path.split(".")
    for part in parts[:-1]:
        cursor = cursor[part]
    cursor[parts[-1]] = value
    target.write_text(json.dumps(body, indent=1, sort_keys=True) + "\n", encoding="utf-8")


# --- what the record is ------------------------------------------------------


def test_all_five_frozen_criteria_are_read_verbatim(record, contracts) -> None:
    assert sorted(record["criteria"]) == sorted(contracts["S22C-010"]["criteria"])
    assert record["criteria_total"] == contracts["S22C-010"]["count"] == 5


def test_the_outcome_is_the_typed_negative_with_four_of_five(record) -> None:
    assert record["criteria_met"] == 4
    assert record["all_met"] is False
    assert record["outcome"] == "typed negative"


def test_exactly_one_condition_fails_in_the_whole_record(record) -> None:
    """Forty-one conditions, one of which is the sprint's result."""
    failing = [
        condition
        for criterion in record["criteria"].values()
        for condition in criterion["conditions"]
        if not condition["holds"]
    ]
    assert len(failing) == 1
    only = failing[0]
    assert only["read_from"] == (
        "sprint-22c-w3-improvement.json"
        "#comparison.at_least_one_retained_artifact_improved_a_held_out_task"
    )
    assert only["expected"] is True
    assert only["measured"] is False


def test_no_threshold_and_no_reading_moved(record) -> None:
    assert record["thresholds_moved_by_22c"] == 0
    assert record["amendments_made_by_22c"] == 0


# --- the three criteria that need every cycle --------------------------------


def test_replay_is_evaluated_in_all_three_cycles(record, contracts) -> None:
    conditions = record["criteria"]["every cycle replays all retained domains"]["conditions"]
    cycles = {name.split(":")[0] for name in (item["condition"] for item in conditions)}
    assert {"cycle 1", "cycle 2", "cycle 3"} <= cycles
    # One cycle-count condition plus six per cycle. A criterion read only in cycle 1 would
    # have passed just as happily and proved a third as much.
    assert len(conditions) == 1 + 3 * 6
    assert contracts["S22C-011"]["minimum_cycles"] == 3


def test_the_enumeration_is_the_freeze_snapshot_plus_the_two_registered_pilots(
    record, contracts
) -> None:
    """The frozen snapshot lists four; a campaign that registers two pilots enumerates six."""
    conditions = record["criteria"]["every cycle replays all retained domains"]["conditions"]
    enumeration = [item for item in conditions if "plus exactly" in item["condition"]]
    assert len(enumeration) == 3
    expected = sorted(
        [
            *contracts["S22C-011"]["domains_enumerated_at_freeze"],
            "engineering.mechanics",
            "science.chemistry",
        ]
    )
    for item in enumeration:
        assert item["measured"] == expected
        assert item["holds"] is True
    assert len(expected) == 6


def test_the_citation_walk_covers_every_promoted_artifact_in_every_cycle(record) -> None:
    conditions = record["criteria"]["source citations and hashes survive every derivative"][
        "conditions"
    ]
    assert len(conditions) == 3 * 3
    sampled = [item for item in conditions if "did not sample" in item["condition"]]
    assert len(sampled) == 3
    assert all(item["measured"] is False for item in sampled)


def test_supersession_is_verified_two_ways_and_history_is_loadable(record) -> None:
    criterion = record["criteria"][
        "a valid new revision supersedes the active view without deleting history"
    ]
    assert criterion["met"] is True
    labels = " | ".join(item["condition"] for item in criterion["conditions"])
    assert "the active view queried" in labels and "the supersession chain walked" in labels
    assert "no row was deleted" in labels
    assert "still loadable" in labels


# --- §5's stop clause --------------------------------------------------------


def test_the_stop_names_which_exit_at_which_wave_with_which_values(record) -> None:
    stop = record["the_stop"]
    assert stop["which_exit_failed"] == [
        "at least one retained artifact improves a held-out verified task"
    ]
    assert stop["at_which_wave"] == "W3"
    assert stop["after_how_many_cycles"] == 3
    assert stop["measured_values"] == {
        "cases": 4,
        "arm_a_verified_successes": 0,
        "arm_b_verified_successes": 0,
        "improved_cases": 0,
    }
    assert stop["diagnosis"] == "W3-F1"


# --- the record can say something other than what it says --------------------


def test_a_record_that_could_only_print_a_negative_would_prove_nothing(rebuilt) -> None:
    """Flip the one failing verdict in a copy: the same driver returns `pass`, 5 of 5."""
    _edit(
        rebuilt,
        "sprint-22c-w3-improvement.json",
        "comparison.at_least_one_retained_artifact_improved_a_held_out_task",
        True,
    )
    document = rebuilt.assemble()
    assert document["criteria_met"] == 5
    assert document["all_met"] is True
    assert document["outcome"] == "pass"
    assert document["the_stop"] is None


def test_a_met_criterion_can_also_fail(rebuilt) -> None:
    """The plant's verdict flipped: two exits fail, and the stop names both."""
    _edit(rebuilt, "sprint-22c-w3-plant.json", "all_four_conditions_met", False)
    document = rebuilt.assemble()
    assert document["criteria_met"] == 3
    assert document["outcome"] == "typed negative"
    assert set(document["the_stop"]["which_exit_failed"]) == {
        "a planted harmful update is quarantined",
        "at least one retained artifact improves a held-out verified task",
    }


def test_a_cycle_that_skipped_a_stage_fails_the_replay_criterion(rebuilt) -> None:
    """S22C-011: a skipped stage is not a cycle, and cycle 3 is not exempt."""
    _edit(rebuilt, "sprint-22c-w3-cycle3.json", "stages.all_nine_in_order", False)
    document = rebuilt.assemble()
    assert document["criteria"]["every cycle replays all retained domains"]["met"] is False


def test_a_walk_that_missed_a_promoted_artifact_fails_the_citation_criterion(rebuilt) -> None:
    _edit(rebuilt, "sprint-22c-w2-cycle1.json", "citations.artifacts_walked", 0)
    document = rebuilt.assemble()
    assert (
        document["criteria"]["source citations and hashes survive every derivative"]["met"] is False
    )


# --- refusals ----------------------------------------------------------------


def test_a_publication_that_no_longer_binds_its_contracts_is_refused(rebuilt) -> None:
    _edit(rebuilt, "sprint-22c-pre-registration.json", "contracts_sha256", "0" * 64)
    with pytest.raises(SystemExit, match="no longer binds"):
        rebuilt.assemble()


def test_a_missing_evidence_field_raises_rather_than_reading_as_false(rebuilt) -> None:
    """An unread criterion rendering as `false` would be one edit from a silent lie."""
    target = rebuilt.EVIDENCE / "sprint-22c-w3-plant.json"
    body = json.loads(target.read_text(encoding="utf-8"))
    del body["all_four_conditions_met"]
    target.write_text(json.dumps(body, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    with pytest.raises(SystemExit, match="does not resolve"):
        rebuilt.assemble()


def test_the_stored_record_reproduces_from_its_sealed_sources(rebuilt) -> None:
    """`--check`'s comparison, run in-process against the untouched copy."""
    stored = _load(RECORD)
    document = rebuilt.assemble()
    skip = {"recorded_at", "integrity_content_hash"}
    assert {key: value for key, value in stored.items() if key not in skip} == {
        key: value for key, value in document.items() if key not in skip
    }
