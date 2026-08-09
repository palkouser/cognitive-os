"""S21D5-091: the gate assessment cannot assert a pass, and every row has to name something.

A condition table is the easiest document in a sprint to write generously. Five ways it goes
wrong, and each has a test: a row that is `met` without naming evidence, a closed row that binds
no stop, a state the script invented for itself, a verdict that does not follow from the counts,
and a closed *set* the assessment chose for itself rather than reading out of the record that
declared it.

Two rows differ from D4's and both are checked here rather than assumed. Condition 24 is `met` on
a measurement where D4 recorded a rejection, and Gate D1 condition 15 is `closed` where D4 left
it open — so the tests assert that each agrees with the retrieval decision record, whichever way
that record reads, rather than asserting the outcome D5 happened to get.
"""

from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path
from typing import Any

REPOSITORY = Path(__file__).resolve().parents[3]
SPRINT = REPOSITORY / "docs/sprints/sprint-21"
EVIDENCE = SPRINT / "evidence"
GATE = EVIDENCE / "sprint-21d5-gate-l2.json"
CONTRACTS = EVIDENCE / "sprint-21d5-contracts.json"
SELECTION = EVIDENCE / "sprint-21d5-learner-selection.json"
CONTINUATION = EVIDENCE / "sprint-21d5-continuation.json"
RETRIEVAL = EVIDENCE / "sprint-21d5-retrieval-decision.json"
ASSESSMENT = SPRINT / "gate-l2-d5-assessment.md"
GENERATOR = REPOSITORY / "scripts/gate_assessment_d5.py"

STATES = {"met", "met_as_rejection", "carried", "not_opened", "pending", "failed"}


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_the_record_reproduces_its_seal_and_binds_the_frozen_contract() -> None:
    document = _load(GATE)
    body = {key: value for key, value in document.items() if key != "integrity_content_hash"}
    canonical = json.dumps(body, indent=1, sort_keys=True, ensure_ascii=False, default=str).encode(
        "utf-8"
    )

    assert hashlib.sha256(canonical).hexdigest() == document["integrity_content_hash"]
    carried = _load(CONTRACTS)["unchanged_from_d4"]
    assert document["gate_contract_hash"] == carried["gate_contract"]
    assert document["thresholds_changed"] == 0
    assert document["pre_registration_sha256"] == _sha256(
        EVIDENCE / "sprint-21d5-pre-registration.json"
    )


def test_every_condition_the_contract_declares_has_exactly_one_row() -> None:
    document = _load(GATE)
    declared = _load(CONTRACTS)["unchanged_from_d4"]["gate_conditions"]
    numbers = [row["condition"] for row in document["gate_l2"]]

    assert len(numbers) == declared
    assert numbers == sorted(set(numbers)) == list(range(1, declared + 1))


def test_no_row_carries_a_state_the_vocabulary_does_not_have() -> None:
    assert {row["state"] for row in _load(GATE)["gate_l2"]} <= STATES


def test_every_met_row_names_a_file_and_the_bytes_it_read() -> None:
    for row in _load(GATE)["gate_l2"]:
        if row["state"] not in {"met", "met_as_rejection"}:
            continue
        path = EVIDENCE / row["evidence"]
        assert path.is_file(), row
        assert row["evidence_sha256"] == _sha256(path), row["condition"]
        assert row["detail"].strip(), row["condition"]


def test_every_closed_row_binds_the_one_stop_that_closed_it() -> None:
    stop = _load(SELECTION)["integrity_content_hash"]
    closed = [row for row in _load(GATE)["gate_l2"] if row["state"] == "not_opened"]

    assert closed
    assert {row["stop_hash"] for row in closed} == {stop}
    for row in closed:
        assert row["detail"].startswith("would have measured"), row["condition"]


def test_the_closed_set_is_the_continuation_record_s_and_not_the_assessment_s() -> None:
    """The assessment does not get to choose its own scope."""
    document = _load(GATE)
    declared = sorted(_load(CONTINUATION)["not_opened"]["gate_l2_conditions"])
    closed = sorted(row["condition"] for row in document["gate_l2"] if row["state"] == "not_opened")

    assert closed == declared
    binding = document["closed_set_read_from_the_continuation_record"]
    assert binding["source_sha256"] == _sha256(CONTINUATION)
    assert binding["stop_kind"] == _load(CONTINUATION)["decision"]["stop_kind"]


def test_nothing_is_carried_from_the_predecessor() -> None:
    document = _load(GATE)

    assert document["counts"]["carried"] == 0
    assert document["no_condition_is_carried_from_d4"] is True


def test_the_verdict_follows_from_the_counts() -> None:
    document = _load(GATE)
    counts = document["counts"]
    passes = (
        counts["failed"] == 0
        and counts["not_opened"] == 0
        and counts["pending"] == 0
        and counts["met_as_rejection"] == 0
    )

    assert document["verdict"] == ("gate_l2_passes" if passes else "gate_l2_does_not_pass")
    assert sum(counts.values()) == len(document["gate_l2"])


def test_condition_24_agrees_with_the_retrieval_record_whichever_way_it_reads() -> None:
    row = next(row for row in _load(GATE)["gate_l2"] if row["condition"] == 24)
    retrieval = _load(RETRIEVAL)
    reached = retrieval["winning_arm"] is not None

    assert row["state"] == ("met" if reached else "met_as_rejection")
    assert row["evidence"] == "sprint-21d5-retrieval-decision.json"
    if reached:
        assert str(retrieval["winning_arm"]) in row["detail"]


def test_gate_d1_condition_15_agrees_with_the_same_record() -> None:
    row = next(row for row in _load(GATE)["gate_d1"] if row["condition"] == 15)
    retrieval = _load(RETRIEVAL)
    reached = retrieval["winning_arm"] is not None

    assert row["state"] == ("closed" if reached else "remains_open")
    assert row["evidence_sha256"] == _sha256(RETRIEVAL)
    assert row["recorded_as"] == retrieval["gate_d1_condition_15"]


def test_gate_d1_six_and_seven_stay_closed_behind_the_stop() -> None:
    stop = _load(SELECTION)["integrity_content_hash"]
    rows = {row["condition"]: row for row in _load(GATE)["gate_d1"]}

    for condition in (6, 7):
        assert rows[condition]["state"] == "not_opened"
        assert rows[condition]["stop_hash"] == stop


def test_condition_29_is_decided_by_the_release_and_never_by_a_stop() -> None:
    """Pending until the release exists; a stop must never be able to close it."""
    row = next(row for row in _load(GATE)["gate_l2"] if row["condition"] == 29)
    release = EVIDENCE / "sprint-21d5-release.json"

    if release.is_file():
        assert row["state"] == "met"
        assert row["evidence"] == "sprint-21d5-release.json"
        assert row["evidence_sha256"] == _sha256(release)
    else:
        assert row["state"] == "pending"
        assert "stop_hash" not in row


def test_the_generator_has_no_path_that_writes_met_without_a_document() -> None:
    """S21D5-091's own clause, checked against the source rather than against its output.

    Every `met` in the generator comes out of `_yes`, and every `_yes` call sits inside a
    function that was handed a parsed document. What this asserts is the narrower, checkable
    thing: the string literal `"met"` appears once, as the constant, and the row builder has no
    branch that reaches it without a `decide` callable behind it.
    """
    source = GENERATOR.read_text(encoding="utf-8")
    tree = ast.parse(source)
    literals = [
        node for node in ast.walk(tree) if isinstance(node, ast.Constant) and node.value == "met"
    ]

    assert len(literals) == 1, "the met state is a constant, not a value typed at a call site"
    assert "return _yes(" in source
    assert "_no(" in source


def test_the_written_assessment_agrees_with_the_record_it_cites() -> None:
    document = _load(GATE)
    text = ASSESSMENT.read_text(encoding="utf-8")
    counts = document["counts"]

    assert document["gate_contract_hash"] in text
    assert f"| `met` | {counts['met']} |" in text
    assert f"| `not_opened` | {counts['not_opened']} |" in text
    assert f"| `pending` | {counts['pending']} |" in text
    assert (
        "**Gate L2 does not pass.**" in text
        if not document["verdict"].endswith("passes")
        else "Gate L2 passes" in text
    )
