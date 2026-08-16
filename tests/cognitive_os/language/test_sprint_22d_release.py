"""S22D-400: the five criteria read once, and what a stop is required to say.

The release record is the only place all five exits are read together, and it is not a summary
somebody wrote. What has to be true of it:

*Every verdict traces to one field of one sealed record.* A criterion is met when all of its
conditions hold, each condition names the record and the dotted path it was read from, and an
unresolvable path raises rather than rendering as `false` — which would put a met criterion one
edit away from a lie.

*The stop says what §5 requires.* Which exit failed, in which wave, with which measured values,
assembled from the conditions rather than restated beside them.

*The gates were re-read and not quoted.* §2.2(e) says a gate that cannot be re-read is red, so
each prior record's own seal is a condition of the exit that reads it.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any

import pytest

REPOSITORY = Path(__file__).resolve().parents[3]
EVIDENCE = REPOSITORY / "docs/sprints/sprint-22/evidence"
SPRINT_21 = REPOSITORY / "docs/sprints/sprint-21/evidence"
sys.path.insert(0, str(REPOSITORY / "scripts"))

from benchmark_22d import canonical  # noqa: E402
from exit_criteria_22d import _at, assemble  # noqa: E402

RELEASE = EVIDENCE / "sprint-22d-exit-criteria.json"
PRE_REGISTRATION = EVIDENCE / "sprint-22d-pre-registration.json"
W3_EXITS = EVIDENCE / "sprint-22d-w3-exits.json"

#: The five records §2.2(e) re-reads. Gate L2 and Gate D1 share one, assessed together in D7.
PRIOR = (
    SPRINT_21 / "sprint-21d7-gate-l2.json",
    EVIDENCE / "sprint-22a-exit-criteria.json",
    EVIDENCE / "sprint-22b-exit-criteria.json",
    EVIDENCE / "sprint-22c-exit-criteria.json",
)


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _sealed(path: Path) -> bool:
    stored = _load(path)
    body = {key: value for key, value in stored.items() if key != "integrity_content_hash"}
    return hashlib.sha256(canonical(body)).hexdigest() == stored["integrity_content_hash"]


def test_the_release_record_is_sealed_and_rebuilds_from_its_sources() -> None:
    """`--check`, as a test. A record that cannot be rebuilt is a record nobody can falsify."""
    assert _sealed(RELEASE)
    skip = {"recorded_at", "integrity_content_hash"}
    stored, rebuilt = _load(RELEASE), assemble()
    assert {key: value for key, value in stored.items() if key not in skip} == {
        key: value for key, value in rebuilt.items() if key not in skip
    }


def test_all_five_criteria_are_read_here_and_nowhere_else() -> None:
    stored = _load(RELEASE)
    assert [item["criterion"] for item in stored["criteria"]] == ["a", "b", "c", "d", "e"]
    assert stored["criteria_total"] == 5
    assert "read no exit as a verdict" in stored["no_wave_read_an_exit_before_this_record"]


def test_the_outcome_and_the_tag_follow_from_the_verdicts() -> None:
    """The tag is not chosen here — both names were frozen in W0 and one is selected."""
    stored = _load(RELEASE)
    pre_registration = _load(PRE_REGISTRATION)
    met = [item["criterion"] for item in stored["criteria"] if item["met"]]
    assert stored["criteria_met_ids"] == met
    assert stored["criteria_met"] == len(met)
    assert stored["all_met"] is (len(met) == 5)
    assert stored["outcome"] == ("pass" if len(met) == 5 else "typed negative")
    assert stored["outcome_tag"] == (
        pre_registration["outcome_tag"]
        if len(met) == 5
        else pre_registration["negative_outcome_tag"]
    )


def test_every_condition_names_the_record_and_field_it_was_read_from() -> None:
    for criterion in _load(RELEASE)["criteria"]:
        assert criterion["conditions"], criterion["criterion"]
        for condition in criterion["conditions"]:
            assert "#" in condition["read_from"], condition
            assert condition["holds"] is (condition["measured"] == condition["expected"])
        assert criterion["met"] is all(item["holds"] for item in criterion["conditions"])
        assert criterion["conditions_holding"] == sum(
            1 for item in criterion["conditions"] if item["holds"]
        )


def test_an_unresolvable_field_path_raises_rather_than_reading_false() -> None:
    """An unread criterion rendering as `false` is a met criterion away from a silent lie."""
    with pytest.raises(SystemExit):
        _at({"exits": {"a": {"met": True}}}, "exits.a.absent")


def test_the_stop_names_which_exit_failed_in_which_wave_with_which_values() -> None:
    """§5's requirement on a stop, asserted against the verdicts rather than against prose."""
    stored = _load(RELEASE)
    unmet = [item["criterion"] for item in stored["criteria"] if not item["met"]]
    assert [item["criterion"] for item in stored["failures"]] == unmet
    for failure in stored["failures"]:
        assert failure["wave"]
        assert failure["conditions_that_did_not_hold"]
        for condition in failure["conditions_that_did_not_hold"]:
            assert condition["measured"] != condition["expected"]
            assert condition["read_from"].startswith("sprint-22d-")


@pytest.mark.parametrize("path", PRIOR, ids=lambda item: item.name)
def test_every_prior_gate_record_still_seals(path: Path) -> None:
    """§2.2(e): a gate that cannot be re-read is red, so the seal is part of the reading."""
    assert path.exists(), f"{path.name} is absent"
    assert _sealed(path)


def test_exit_e_reads_every_prior_gate_by_name() -> None:
    exit_e = next(item for item in _load(RELEASE)["criteria"] if item["criterion"] == "e")
    read_from = {condition["read_from"].split("#")[0] for condition in exit_e["conditions"]}
    assert read_from == {path.name for path in PRIOR}
    # Gate L2's twenty-nine, Gate D1's three closed conditions, and the four sprint records.
    assert exit_e["conditions_total"] == 18
    assert exit_e["met"] is True


def test_the_measured_exits_are_traced_to_w3_and_not_restated() -> None:
    for criterion in _load(RELEASE)["criteria"]:
        if criterion["criterion"] == "e":
            continue
        assert all(
            condition["read_from"].startswith(W3_EXITS.name)
            for condition in criterion["conditions"]
        ), criterion["criterion"]


def test_the_accounting_source_is_named_because_the_finding_was_not_repaired() -> None:
    """§5 asks for 22C W2-F3 repaired *or* the accounting's source named. It names it."""
    named = _load(RELEASE)["the_accounting_source_is_named"]
    assert named["repaired"] is False
    assert "run_arm" in named["source"]
    assert "receipts digest" in named["source"]
    assert named["why_the_tool_plane_was_not_needed"]


def test_the_optional_adapter_work_was_declined_with_a_reason() -> None:
    assert "no exit needs an adapter" in _load(RELEASE)["adapter_training_not_taken"]


def test_nothing_frozen_was_amended_and_the_migration_head_did_not_move() -> None:
    stored = _load(RELEASE)
    pre_registration = _load(PRE_REGISTRATION)
    assert stored["amendments_made_by_22d"] == 0
    assert stored["readings_hash"] == pre_registration["readings_hash"]
    assert stored["pre_registration_sha256"] == pre_registration["integrity_content_hash"]
    assert stored["migration_head"]["expected_revision"] == "0015"


def test_the_w3_readings_still_rebuild_from_the_arm_records() -> None:
    assert _load(RELEASE)["w3_exits_rebuild_from_the_arm_records"] is True
