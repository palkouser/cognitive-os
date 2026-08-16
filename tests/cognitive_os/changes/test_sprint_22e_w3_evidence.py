"""S22E-W3: the one approved change, and the two things the traversal found on the way.

The sealed records are read, never rebuilt: rebuilding them means a live provider call and a
286-second gate matrix, and 22C W1-F1's rule is that a validator may not re-derive a world. What
these tests hold is that each record recomputes its own seal, that the claims inside it are
consistent with each other and with the records it binds, and that the two negative controls
are really negative — a repair probe that passed on the unrepaired tree, or an approval that
named no human, would be caught here.
"""

from __future__ import annotations

import hashlib
import json
from importlib.util import find_spec
from pathlib import Path
from typing import Any

import pytest

REPO = Path(__file__).resolve().parents[3]
EVIDENCE = REPO / "docs/sprints/sprint-22/evidence"

RECORDS = {
    "change": EVIDENCE / "sprint-22e-w3-approved-change.json",
    "approval": EVIDENCE / "sprint-22e-w3-approval.json",
    "remeasurement": EVIDENCE / "sprint-22e-w3-remeasurement.json",
}

#: The repair's two files, and nothing else. The candidate that was evaluated and the commit
#: that was approved must name exactly this set — a third file appearing anywhere is either a
#: second change or a leak, and both are refusals under §2.3.
APPROVED_FILES = (
    "src/cognitive_os/proposals/service.py",
    "tests/cognitive_os/proposals/test_proposal_engine.py",
)

EXPECTED_STAGES = (
    "weakness_mined",
    "proposal_created",
    "provider_draft_merged_and_resealed",
    "proposal_approved_for_experiment",
    "baseline_negative_control_recorded",
    "experiment_requested",
    "isolation_prepared",
    "repair_applied",
    "repair_probed",
    "candidate_test_run",
    "candidate_captured_from_the_worktree",
    "candidate_scope_refused",
    "evaluation_run",
)


def _canonical(value: Any) -> bytes:
    return json.dumps(value, indent=1, sort_keys=True, ensure_ascii=False).encode("utf-8")


def _load(name: str) -> dict[str, Any]:
    return json.loads(RECORDS[name].read_text(encoding="utf-8"))


@pytest.mark.parametrize("name", sorted(RECORDS))
def test_every_w3_record_exists_and_its_seal_recomputes(name: str) -> None:
    stored = _load(name)
    body = {key: value for key, value in stored.items() if key != "integrity_content_hash"}
    assert hashlib.sha256(_canonical(body)).hexdigest() == stored["integrity_content_hash"]


# ---------------------------------------------------------------------------
# The change was the one the gate owner sealed, and it was not chosen by the driver
# ---------------------------------------------------------------------------


def test_the_change_is_the_entry_the_gate_owner_selected() -> None:
    change = _load("change")
    decisions = json.loads((EVIDENCE / "sprint-22e-decisions.json").read_text(encoding="utf-8"))
    assert change["entry_id"] == decisions["decision_two"]["selection"] == "L7"
    assert change["selection"]["selection_finding"] == "22E W1-F7"
    assert change["selection"]["decision_record_hash"] == decisions["integrity_content_hash"]


def test_the_installing_traversal_declares_its_own_exception() -> None:
    """The traversal that installs the repair ran against the unrepaired checkout.

    So the merged revision's seal really was blank during this run and the caller really did
    reseal. Both are recorded rather than smoothed over, because the alternative reading — that
    the chain was walked as written — would be false of this one traversal and true of every
    later one.
    """
    exception = _load("change")["installing_traversal_exception"]
    assert exception["merged_revision_seal_was_blank"] is True
    assert exception["caller_resealed_through_the_contract"] is True
    assert "repaired behaviour cannot be required" in exception["why"]


# ---------------------------------------------------------------------------
# The repair, and the two negative controls
# ---------------------------------------------------------------------------


def test_the_probe_holds_on_the_repair_and_fails_without_it() -> None:
    change = _load("change")
    assert change["repair_probe"]["every_probe_holds"] is True
    assert change["baseline_negative_control"]["probe_holds_without_the_repair"] is False


def test_the_probe_measures_the_success_path_and_keeps_both_refusals() -> None:
    probe = _load("change")["repair_probe"]
    assert probe["released_path_completes"] is True
    assert probe["mark_survives_to_the_returned_revision"] is True
    assert probe["merged_seal_is_the_canonical_hash"] is True
    assert probe["unsafe_draft_still_refused"] is True
    assert probe["unavailable_provider_still_falls_back"] is True


def test_the_candidate_carries_its_own_regression_test() -> None:
    change = _load("change")
    assert tuple(item["file"] for item in change["repair"]["files"]) == APPROVED_FILES
    assert change["repair"]["the_change_carries_its_own_test"] is True
    assert change["candidate_test"]["passed"] is True


def test_the_repair_was_applied_through_the_released_transformation() -> None:
    repair = _load("change")["repair"]
    assert repair["applied_by"] == "cognitive_os.changes.service.deterministic_replace"
    assert all(len(item["before_hash"]) == 64 for item in repair["files"])


# ---------------------------------------------------------------------------
# The evaluation, and the surface it did not move
# ---------------------------------------------------------------------------


def test_every_gate_that_ran_passed_and_the_matrix_was_the_full_one() -> None:
    change = _load("change")
    assert change["evaluation"]["gates"] == 15
    assert change["evaluation"]["gates_failed"] == []
    assert change["evaluation"]["gates_ran"] == change["evaluation"]["gates_passed"] == 9
    assert len(change["evaluation"]["driver_decided"]) == 6


def test_the_full_regression_and_the_type_checker_are_among_the_gates_that_ran() -> None:
    """A green matrix that skipped the expensive gates would prove much less."""
    ran = {item["gate_id"] for item in _load("change")["gates"] if item.get("ran")}
    assert {"historical_regression", "compatibility", "security", "policy"} <= ran


def test_only_the_two_approved_paths_changed_in_the_worktree() -> None:
    capture = _load("change")["worktree_capture"]
    assert tuple(sorted(capture["changed_files"])) == tuple(sorted(APPROVED_FILES))
    assert capture["only_the_declared_paths_changed"] is True


def test_the_active_surface_did_not_move_and_the_audit_trail_did() -> None:
    """A governed traversal that wrote no audit record would be a loop nobody can audit."""
    mutation = _load("change")["zero_active_state_mutation"]
    assert mutation["zero_active_state_mutation"] is True
    assert mutation["mutated_members"] == []
    assert mutation["audit_trail_moved"] is True


@pytest.mark.parametrize(
    "member", sorted(_load("change")["zero_active_state_mutation"]["per_member_unchanged"])
)
def test_each_surface_member_is_reported_unchanged_individually(member: str) -> None:
    change = _load("change")
    assert change["zero_active_state_mutation"]["per_member_unchanged"][member] is True
    assert change["surface_before"][member] == change["surface_after"][member]


# ---------------------------------------------------------------------------
# W3-F2: the released scope refusal, recorded rather than worked around
# ---------------------------------------------------------------------------


def test_the_released_scope_check_was_attempted_with_the_real_paths_and_refused() -> None:
    scope = _load("change")["released_scope_check"]
    assert scope["attempted_with_the_real_paths"] is True
    assert scope["accepted"] is False
    assert scope["refusal"] == "candidate changed a forbidden path"
    assert tuple(scope["candidate_changed_files"]) == APPROVED_FILES
    assert scope["manifest_allowed_repository_paths"] == ["proposal-scope/source_code_change.py"]


def test_the_stage_order_records_the_refusal_rather_than_omitting_the_stage() -> None:
    assert tuple(_load("change")["stages"]) == EXPECTED_STAGES


def test_no_promotion_contract_was_fabricated_around_the_refusal() -> None:
    change = _load("change")
    assert change["assessment"]["built"] is False
    assert change["promotion"]["attempted"] is False
    assert change["promotion_bundle"] is None


@pytest.mark.skipif(find_spec("cognitive_os") is None, reason="requires the package")
def test_the_placeholder_scope_is_still_what_the_released_engine_produces() -> None:
    """W3-F2 re-derived rather than quoted: the synthetic path comes from released code.

    A finding that only exists as a sentence in a record decays the moment the code moves. This
    reads the released builder and asserts the shape the refusal was about.
    """
    import inspect

    from cognitive_os.proposals import service

    source = inspect.getsource(service.build_change_specification)
    assert 'allowed_files = (f"proposal-scope/{proposal_type.value}.{suffix}",)' in source


# ---------------------------------------------------------------------------
# The named human, and the re-measurement that was not licensed
# ---------------------------------------------------------------------------


def test_the_approval_names_a_human_and_binds_the_exact_evidence() -> None:
    approval = _load("approval")
    change = _load("change")
    assert approval["approved"] is True
    assert approval["approver"].strip() != ""
    assert (
        approval["what_is_approved"]["approved_change_record_hash"]
        == (change["integrity_content_hash"])
    )
    assert approval["what_is_approved"]["diff_hash"] == change["worktree_capture"]["diff_hash"]
    assert tuple(approval["what_is_approved"]["changed_files"]) == APPROVED_FILES


def test_the_approval_permits_a_pull_request_and_nothing_further() -> None:
    approval = _load("approval")
    assert approval["what_this_approval_permits"] == [
        "a pull request against protected main carrying exactly the files named above",
    ]
    assert {"merge", "tag", "publish", "release"} <= set(approval["what_it_does_not_permit"])
    assert approval["the_merge_is_a_separate_act_by"] == "the gate owner"


def test_the_approval_says_why_it_is_not_a_promotion_review() -> None:
    why = _load("approval")["why_this_is_not_a_promotion_review"]
    assert why["finding"] == "22E W3-F2"
    assert why["released_refusal"] == "candidate changed a forbidden path"
    assert set(why["what_could_not_be_built"]) == {
        "ChangeCandidate",
        "PromotionAssessment",
        "PromotionReview",
        "PromotionBundle",
    }


def test_the_re_measurement_is_not_licensed_and_says_which_conditions_still_read_a_seal() -> None:
    resolution = _load("remeasurement")["resolution"]
    assert resolution["re_measurement_licensed"] is False
    assert resolution["instrument_re_run"] is False
    assert resolution["conditions_still_reading_a_predecessor_seal"] == [6, 7]
    assert resolution["the_sets_are_disjoint"] is True


def test_the_licence_was_resolved_from_the_ledger_rather_than_assumed() -> None:
    """L7 touching no Gate M condition is the ledger's field, not this wave's opinion."""
    remeasurement = _load("remeasurement")
    assert remeasurement["the_change_that_landed"]["touches_a_gate_m_condition"] is None
    assert remeasurement["what_this_costs_the_sprint"]["gate_m_cannot_fully_close_in_22e"] is True
    assert (
        remeasurement["what_this_costs_the_sprint"]["predicted_before_any_candidate_existed"]
        is True
    )
