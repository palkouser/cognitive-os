"""S21D4-059: the pre-final checkpoint, and the ways a refusal record can say nothing.

A record whose whole content is "we did not do these things" is the easiest kind to write badly.
Three failure modes, and each has a test here: the not-opened map can be short by an item nobody
noticed, the stop hash can be a number that names no committed evidence, and a guard the record
claims to have exercised can have raised nothing at all.

The map is checked against the backlog's own headings rather than against a copy of the list in
this file, because a checklist compared to itself is a checklist that always passes.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

REPOSITORY = Path(__file__).resolve().parents[3]
SPRINT = REPOSITORY / "docs/sprints/sprint-21"
BACKLOG = SPRINT / "sprint-21d4-technical-backlog.md"
EVIDENCE = SPRINT / "evidence"
CHECKPOINT = EVIDENCE / "sprint-21d4-pre-final-checkpoint.json"
SELECTION = EVIDENCE / "sprint-21d4-learner-selection.json"
PRE_REGISTRATION = EVIDENCE / "sprint-21d4-pre-registration.json"

#: Every conditional task downstream of the candidate selection. S21D4-059 is absent because it
#: is the record itself; S21D4-075 is absent because the backlog declares it unconditional.
EXPECTED_NOT_OPENED = {
    *(f"S21D4-0{number}" for number in range(50, 59)),
    *(f"S21D4-0{number}" for number in range(60, 70)),
    *(f"S21D4-0{number}" for number in (70, 71, 72, 73, 74, 76, 77)),
}


def _load() -> dict[str, Any]:
    return json.loads(CHECKPOINT.read_text(encoding="utf-8"))


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def test_the_record_reproduces_its_own_seal_and_the_bytes_it_cites() -> None:
    document = _load()
    body = {key: value for key, value in document.items() if key != "integrity_content_hash"}
    canonical = json.dumps(body, indent=1, sort_keys=True, ensure_ascii=False).encode("utf-8")

    assert _sha256(canonical) == document["integrity_content_hash"]
    assert document["pre_registration_sha256"] == _sha256(PRE_REGISTRATION.read_bytes())
    for precondition in document["preconditions"]:
        cited = EVIDENCE / precondition["evidence"]
        assert precondition["evidence_sha256"] == _sha256(cited.read_bytes())


def test_the_stop_hash_is_the_seal_of_a_committed_record() -> None:
    """A stop hash nothing can be resolved to is a citation of nothing."""
    document = _load()
    stop = document["decision"]["stop_hash"]

    assert stop == json.loads(SELECTION.read_text(encoding="utf-8"))["integrity_content_hash"]
    assert document["decision"]["stop_source"] == "S21D4-039 candidate selection"
    assert {row["stop_hash"] for row in document["not_opened"]} == {stop}


def test_the_first_failure_is_the_first_precondition_the_backlog_declares() -> None:
    document = _load()
    preconditions = document["preconditions"]
    failed = [item["name"] for item in preconditions if not item["passed"]]

    assert preconditions[0]["name"] == "S21D4-039 selected one candidate"
    assert document["decision"]["first_failed_precondition"] == failed[0]
    assert document["decision"]["authorised"] is False
    assert document["decision"]["capability_granted"] is None
    assert preconditions[1]["passed"] is True, "the continuation did permit correction work"


def test_every_dependent_task_carries_a_typed_record_and_none_is_missing() -> None:
    records = _load()["not_opened"]

    assert {row["item"] for row in records} == EXPECTED_NOT_OPENED
    assert {row["status"] for row in records} == {"not_opened"}
    assert all(row["would_have"] for row in records)


def test_every_named_item_is_a_heading_in_the_backlog() -> None:
    """A map naming an item nobody planned would be a map of this script's imagination."""
    backlog = BACKLOG.read_text(encoding="utf-8")

    for item in sorted(EXPECTED_NOT_OPENED):
        assert f"### {item} " in backlog


def test_no_planned_conditional_item_was_left_out_of_the_map() -> None:
    """The other direction: read the backlog and check the map covers what it declares.

    `EXPECTED_NOT_OPENED` above is a second copy of the same list, so comparing the record to it
    only proves the two copies agree. This derives the population from the document that
    declares it, and names the three exemptions instead of the twenty-six inclusions.
    """
    headings = set(re.findall(r"^### (S21D4-0\d\d) ", BACKLOG.read_text(encoding="utf-8"), re.M))
    conditional = {name for name in headings if "050" <= name[-3:] <= "077"}
    exempt = {
        "S21D4-059",  # the checkpoint itself
        "S21D4-075",  # declared unconditional by the backlog
    }

    assert conditional - exempt == {row["item"] for row in _load()["not_opened"]}


def test_the_unconditional_substrate_gate_is_not_in_the_map() -> None:
    document = _load()

    assert "S21D4-075" not in {row["item"] for row in document["not_opened"]}
    assert [row["item"] for row in document["unconditional"]] == ["S21D4-075"]


def test_nothing_was_opened_sealed_or_inspected() -> None:
    document = _load()

    assert document["final_outcomes_inspected"] is False
    assert document["final_or_canary_outcomes_inspected"] == 0
    assert document["opened_any_store"] is False
    assert document["created_any_lifecycle_state"] is False
    assert document["configurations_sealed"] == 0


class TestTheConditionTwentyContract:
    """S21D4-048's four clauses, as the record measured them."""

    def test_both_refusals_actually_raised(self) -> None:
        """`None` here would mean the guard let its own counterexample through."""
        contract = _load()["promotion_contract"]

        assert contract["a_measured_row_without_counts_is_refused"]
        assert (
            "nominal and independent decision counts"
            in (contract["a_measured_row_without_counts_is_refused"])
        )
        assert contract["an_unmeasured_row_carrying_counts_is_refused"]
        assert "counted no decisions" in contract["an_unmeasured_row_carrying_counts_is_refused"]

    def test_the_addition_moved_no_bytes_and_the_counts_are_a_new_identity(self) -> None:
        additive = _load()["promotion_contract"]["additive"]

        assert additive["a_payload_without_counts_reproduces_the_d3_bytes"] is True
        assert additive["d3_byte_sha256"] == additive["d4_byte_sha256"]
        assert additive["canonical_form_omits_the_absent_key"] is True
        assert additive["carrying_counts_is_a_different_identity"] is True
        assert additive["content_hash_with_counts"] != additive["content_hash_without_counts"]

    def test_precedence_was_executed_on_reversed_input(self) -> None:
        precedence = _load()["promotion_contract"]["precedence"]

        assert precedence["rows_supplied_in"] == "reverse gate-tuple order"
        assert precedence["first_failed_gate"] == "metamorphic_ood"
        assert precedence["unmet_gates"] == ["metamorphic_ood", "retention"]
        assert precedence["names_the_gate_the_tuple_puts_first"] is True
        assert precedence["a_failed_row_still_carries_its_denominators"] is True

    def test_the_erratum_shape_is_the_one_the_reconciliation_measured(self) -> None:
        shape = _load()["promotion_contract"]["the_errata_shape"]

        assert (shape["nominal_decisions"], shape["independent_decisions"]) == (120, 20)
        assert shape["replicated_decisions"] == 100

    def test_the_dispatch_still_reports_both_older_shapes(self) -> None:
        dispatch = _load()["promotion_contract"]["dispatch"]

        assert dispatch["schema_version"] == 2, "bumping it would make D3 payloads unreadable"
        assert dispatch["d3_bytes_report_version"] == 2
        assert dispatch["legacy_bytes_report_version"] == 1


def test_the_frozen_artifact_identity_did_not_drift_during_w2_or_w3() -> None:
    """S21D4-050's unchanged clause. The binding half is recorded as not opened, not as done."""
    artifact = _load()["artifact_contract"]

    assert artifact["feature_channels"] == 390
    assert artifact["feature_channels_unchanged"] is True
    assert artifact["feature_contract_hash"].startswith("492c90a5df420de9")
    assert artifact["feature_contract_hash_unchanged"] is True
    assert artifact["normaliser_and_grammar_unchanged"] is True
    assert artifact["selected_artifact_exists"] is False
    assert artifact["threshold_bound_into_the_artifact"] is False


def test_the_retrieval_branch_is_bound_to_its_own_stop_and_not_to_this_one() -> None:
    """A negative branch that finished is evidence; folding it into this stop would lose it."""
    branch = _load()["independent_branch"]

    assert branch["status"] == "completed"
    assert "S21D4-040" in branch["item"]
    assert "S21D4-046" not in {row["item"] for row in _load()["not_opened"]}
