"""S21D4-091: the gate assessment cannot assert a pass, and every row has to name something.

A condition table is the easiest document in a sprint to write generously. Four ways it goes
wrong, and each has a test: a row that is `met` without naming evidence, a closed row that binds
no stop, a state the script invented for itself, and a verdict that does not follow from the
counts.

The fifth is the one this sprint keeps finding — a check with nothing to be false about — so the
row count is asserted against the frozen contract's own number rather than against the length of
this script's list.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

REPOSITORY = Path(__file__).resolve().parents[3]
SPRINT = REPOSITORY / "docs/sprints/sprint-21"
EVIDENCE = SPRINT / "evidence"
GATE = EVIDENCE / "sprint-21d4-gate-l2.json"
CONTRACTS = EVIDENCE / "sprint-21d4-contracts.json"
SELECTION = EVIDENCE / "sprint-21d4-learner-selection.json"
ASSESSMENT = SPRINT / "gate-l2-d4-assessment.md"

STATES = {"met", "met_as_rejection", "carried", "not_opened", "pending", "failed"}


def _load() -> dict[str, Any]:
    return json.loads(GATE.read_text(encoding="utf-8"))


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def test_the_record_reproduces_its_seal_and_binds_the_frozen_contract() -> None:
    document = _load()
    body = {key: value for key, value in document.items() if key != "integrity_content_hash"}
    canonical = json.dumps(body, indent=1, sort_keys=True, ensure_ascii=False, default=str).encode(
        "utf-8"
    )
    frozen = json.loads(CONTRACTS.read_text(encoding="utf-8"))["contracts"]["gates_and_stops"]

    assert _sha256(canonical) == document["integrity_content_hash"]
    assert document["gate_contract_hash"] == frozen["content_hash"]
    assert document["thresholds_changed"] == 0
    assert document["final_outcomes_inspected"] is False


def test_every_condition_the_contract_declares_has_exactly_one_row() -> None:
    """Counted against the frozen number, not against the length of the script's own list."""
    document = _load()
    declared = json.loads(CONTRACTS.read_text(encoding="utf-8"))["contracts"]["gates_and_stops"][
        "gate_l2_conditions"
    ]
    numbers = [row["condition"] for row in document["gate_l2"]]

    assert declared == 29
    assert numbers == list(range(1, declared + 1))
    assert sum(document["counts"].values()) == declared


def test_no_row_carries_a_state_the_vocabulary_does_not_have() -> None:
    assert {row["state"] for row in _load()["gate_l2"]} <= STATES


def test_every_met_row_names_a_file_and_the_bytes_it_read() -> None:
    """A `met` that names nothing is an assertion, which is what this script may not make."""
    for row in _load()["gate_l2"]:
        if row["state"] not in {"met", "met_as_rejection"}:
            continue
        cited = EVIDENCE / row["evidence"]
        assert cited.is_file(), row["condition"]
        assert row["evidence_sha256"] == _sha256(cited.read_bytes()), row["condition"]
        assert row["rule"] and row["detail"], row["condition"]


def test_every_closed_row_binds_the_one_stop_that_closed_it() -> None:
    document = _load()
    closed = [row for row in document["gate_l2"] if row["state"] == "not_opened"]
    stop = json.loads(SELECTION.read_text(encoding="utf-8"))["integrity_content_hash"]

    assert closed, "a table with nothing closed would not be this sprint's table"
    assert {row["stop_hash"] for row in closed} == {stop}
    assert {row["stop_source"] for row in closed} == {"S21D4-039 null candidate selection"}
    assert document["stops"]["selection"]["hash"] == stop


def test_nothing_is_carried_from_the_predecessor() -> None:
    """Section 2.2: D4 inherits no pass from D3, so this state must stay empty."""
    document = _load()

    assert document["counts"]["carried"] == 0
    assert document["no_condition_is_carried_from_d3"] is True


def test_the_verdict_follows_from_the_counts() -> None:
    document = _load()
    counts = document["counts"]

    assert counts["failed"] == 0
    assert counts["not_opened"] > 0
    assert counts["met_as_rejection"] == 1, "condition 24 is the measured rejection"
    assert counts["pending"] == 1, "condition 29 waits on the release"
    assert document["verdict"] == "gate_l2_does_not_pass"


def test_condition_24_is_the_measured_rejection_and_not_a_pass() -> None:
    row = next(item for item in _load()["gate_l2"] if item["condition"] == 24)
    decision = json.loads(
        (EVIDENCE / "sprint-21d4-retrieval-decision.json").read_text(encoding="utf-8")
    )

    assert row["state"] == "met_as_rejection"
    assert decision["winning_arm"] is None
    assert decision["first_failed_floor"] in row["detail"]


def test_condition_29_is_pending_rather_than_met_or_closed() -> None:
    """The release has not happened. `pending` is neither a stop nor a pass."""
    row = next(item for item in _load()["gate_l2"] if item["condition"] == 29)

    assert row["state"] == "pending"
    assert row["evidence"] is None
    assert "stop_hash" not in row


def test_gate_d1_condition_15_stays_open_on_its_own_evidence() -> None:
    """The independent branch finished, so its condition is not closed by another branch's stop."""
    rows = {row["condition"]: row for row in _load()["gate_d1_open"]}

    assert set(rows) == {6, 7, 15}
    assert rows[15]["state"] == "remains_open"
    assert rows[15]["first_failed_floor"] == "mrr_at_10"
    assert "stop_hash" not in rows[15]
    assert rows[6]["state"] == "not_opened" and rows[7]["state"] == "not_opened"


def test_the_written_assessment_agrees_with_the_record_it_cites() -> None:
    """The document is generated from the record; a hand-edited count would drift silently."""
    document = _load()
    text = ASSESSMENT.read_text(encoding="utf-8")

    assert document["gate_contract_hash"] in text
    assert "**Gate L2 does not pass.**" in text
    for state, count in document["counts"].items():
        if state in {"met", "not_opened"}:
            assert f"| `{state}` | {count} |" in text, state
