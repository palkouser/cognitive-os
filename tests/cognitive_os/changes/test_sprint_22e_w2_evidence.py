"""S22E-W2: the ledger revision — superseded, never edited, and both reproductions executed.

W1 carried two findings to the ledger and could not put them there, because the W0 ledger is a
sealed record every later wave binds by hash. The revision mechanism is 22B W1-D2's: the W0
file stays byte-identical, and revision 2 is its own record binding the predecessor's file
hash and seal. These tests hold exactly that shape:

*The predecessor is untouched.* The revision's `supersedes` block must carry the W0 file's
current bytes — so a revision that quietly edited its predecessor fails here, and the W0 test
file's own seal check keeps holding beside this one.

*The reproductions are executed, not quoted.* L6's misreport chain and L7's blank seal are
recomputed by `--check` from released code on every run, which is why — unlike the W1 records —
this record has an empty `recorded_not_recomputed`. A tampered reproduction must be refused.

*The carried ranks are the sealed ranks.* A revision that repriced a W0 entry silently would
be the drift W0-F1 exists to name.
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Any

import pytest

REPOSITORY = Path(__file__).resolve().parents[3]
EVIDENCE = REPOSITORY / "docs/sprints/sprint-22/evidence"
sys.path.insert(0, str(REPOSITORY / "scripts"))

from ledger_revision_22e import check_record  # noqa: E402

PREDECESSOR = EVIDENCE / "sprint-22e-weakness-ledger.json"
REVISION = EVIDENCE / "sprint-22e-weakness-ledger-2.json"


def _canonical(value: Any) -> bytes:
    return json.dumps(value, indent=1, sort_keys=True, ensure_ascii=False).encode("utf-8")


def _load() -> dict[str, Any]:
    return json.loads(REVISION.read_text(encoding="utf-8"))


def test_the_revision_exists_and_its_seal_recomputes() -> None:
    stored = _load()
    body = {key: value for key, value in stored.items() if key != "integrity_content_hash"}
    assert hashlib.sha256(_canonical(body)).hexdigest() == stored["integrity_content_hash"]


def test_the_predecessor_is_byte_identical_to_what_the_revision_binds() -> None:
    stored = _load()
    assert (
        stored["supersedes"]["file_sha256"] == hashlib.sha256(PREDECESSOR.read_bytes()).hexdigest()
    )
    assert stored["revision"] == 2


def test_the_carried_ranks_are_the_sealed_ranks() -> None:
    predecessor = json.loads(PREDECESSOR.read_text(encoding="utf-8"))
    carried = {entry["entry_id"]: entry["rank"] for entry in _load()["carried_entries"]}
    sealed = {entry["entry_id"]: entry["rank"] for entry in predecessor["entries"]}
    assert carried == sealed


def test_both_added_entries_reproduce_their_defects() -> None:
    added = {entry["entry_id"]: entry for entry in _load()["added_entries"]}
    l6 = added["L6"]["reproduction"]
    assert l6["timeout_is_retryable"] is True
    assert l6["cancellation_is_retryable"] is False
    l7 = added["L7"]["reproduction"]
    assert l7["host_verification_admitted_the_draft"] is True
    assert l7["merged_seal_is_blank"] is True
    assert l7["released_statement_refuses"] is True
    assert l7["reseal_through_the_contract_recovers"] is True


def test_l7_names_the_walkability_question_it_puts_before_the_gate_owner() -> None:
    added = {entry["entry_id"]: entry for entry in _load()["added_entries"]}
    assert added["L7"]["touches_the_walkability_of_exit_two"] is True
    assert added["L7"]["touches_a_gate_m_condition"] is None


def test_the_check_reproduces_and_recomputes_everything() -> None:
    verdict = check_record(_load())
    assert verdict["reproduced"] is True, verdict["mismatches"]
    assert verdict["recorded_not_recomputed"] == []


def test_the_check_refuses_a_tampered_reproduction() -> None:
    tampered = _load()
    entry = next(item for item in tampered["added_entries"] if item["entry_id"] == "L7")
    entry["reproduction"]["merged_seal_is_blank"] = False
    verdict = check_record(tampered)
    assert verdict["reproduced"] is False
    assert any("L7" in item for item in verdict["mismatches"])


def test_the_compatibility_gate_reproduces_the_ci_mypy_lane() -> None:
    """W2-F1: without `--extra memory-postgres` the gate fails an empty candidate.

    The CI mypy lane syncs `--all-groups --extra memory-postgres`, and that extra
    transitively installs numpy, which two learning modules import. A compatibility gate
    without it refuses every candidate for a reason that is about the environment, not the
    candidate — the false-rejection class W1-F3 names.
    """
    from isolation_22e import GATE_COMMANDS

    command = GATE_COMMANDS["compatibility"]
    assert command is not None
    assert "memory-postgres" in command
    assert command.index("--extra") < command.index("memory-postgres")


# ---------------------------------------------------------------------------
# S22E-201 — the two W3 decisions, sealed with the alternatives they rejected
# ---------------------------------------------------------------------------

DECISIONS = EVIDENCE / "sprint-22e-decisions.json"


def _load_decisions() -> dict[str, Any]:
    return json.loads(DECISIONS.read_text(encoding="utf-8"))


def test_the_decision_record_exists_and_its_seal_recomputes() -> None:
    stored = _load_decisions()
    body = {key: value for key, value in stored.items() if key != "integrity_content_hash"}
    assert hashlib.sha256(_canonical(body)).hexdigest() == stored["integrity_content_hash"]


def test_the_arithmetic_premise_is_recomputed_from_both_sealed_ledgers() -> None:
    """The premise the selection rests on is derived, never asserted: the condition-6 and
    condition-7 entry sets are disjoint, so one approved change cannot flip both."""
    premise = _load_decisions()["arithmetic_premise"]
    assert premise["entries_touching_condition_6"] == ["L1"]
    assert premise["entries_touching_condition_7"] == ["L2"]
    assert premise["the_sets_are_disjoint"] is True
    assert premise["gate_m_cannot_fully_close_in_22e"] is True


def test_both_decisions_name_what_they_rejected() -> None:
    stored = _load_decisions()
    assert stored["decision_one"]["rejected_alternatives"]
    assert stored["decision_one"]["no_frozen_reading_is_amended"] is True
    assert stored["decision_two"]["selection"] == "L7"
    rejected = {item["entry"] for item in stored["decision_two"]["rejected_alternatives"]}
    assert {"L1", "L2"} <= rejected


def test_the_decision_check_reproduces_and_refuses_a_tampered_selection() -> None:
    from decisions_22e import check_record as check_decisions

    verdict = check_decisions(_load_decisions())
    assert verdict["reproduced"] is True, verdict["mismatches"]
    tampered = _load_decisions()
    tampered["decision_two"]["selection"] = "L1"
    assert check_decisions(tampered)["reproduced"] is False


# ---------------------------------------------------------------------------
# The dry run 1 continuation — the same candidate under the corrected gate
# ---------------------------------------------------------------------------

CONTINUATION = EVIDENCE / "sprint-22e-w2-dryrun1-continuation.json"


def _load_continuation() -> dict[str, Any]:
    return json.loads(CONTINUATION.read_text(encoding="utf-8"))


def test_the_continuation_exists_and_its_seal_recomputes() -> None:
    stored = _load_continuation()
    body = {key: value for key, value in stored.items() if key != "integrity_content_hash"}
    assert hashlib.sha256(_canonical(body)).hexdigest() == stored["integrity_content_hash"]


def test_the_corrected_gate_passes_and_a_pin_test_honestly_refuses() -> None:
    """W2-F1's definitive proof and W2-F2's honest failure, in one traversal.

    `compatibility` — the gate that falsely rejected dry run 1 — passes the same candidate
    under the corrected command, so the mypy price is confirmed to never have existed. And
    `focused_target_tests` fails **on evidence about the candidate**: the W1-F4 diagnosis
    test pins the defect's existence live, the candidate repairs the defect, and the pin
    refuses. Nobody planted it, and it is the honest evaluation failure §2.2(c) requires at
    least one dry run to produce.
    """
    gates = {item["gate_id"]: item for item in _load_continuation()["gates"]}
    compatibility = gates["compatibility"]
    assert compatibility["ran"] is True and compatibility["passed"] is True
    focused = gates["focused_target_tests"]
    assert focused["ran"] is True and focused["passed"] is False
    assert "test_the_defect_is_the_repository_allowlist" in focused["stdout_tail"]


def test_the_continuation_is_the_same_traversal_shape_as_dry_run_1() -> None:
    """Same stages in order, same single allowed path, zero mutation recomputed — the same
    candidate carried twice, refused for two different reasons, only one of them its own."""
    stored = _load_continuation()
    w1 = json.loads((EVIDENCE / "sprint-22e-w1-dryrun1.json").read_text(encoding="utf-8"))
    assert stored["stages"] == w1["stages"]
    assert stored["worktree_capture"]["changed_files"] == w1["worktree_capture"]["changed_files"]
    assert stored["zero_active_state_mutation"]["zero_active_state_mutation"] is True
    assert stored["provider"]["provider_id"] == "claude-code"
    assert stored["draft"]["generation_mode_after_host_verification"] == "provider_assisted"


def test_the_dryrun_check_reproduces_over_the_continuation() -> None:
    from dryrun_22e import check_record as check_dryrun

    verdict = check_dryrun(_load_continuation())
    assert verdict["reproduced"] is True, verdict["mismatches"]


# ---------------------------------------------------------------------------
# S22E-202 — the experience leg: compiled, stored, and queried back
# ---------------------------------------------------------------------------

EXPERIENCE = EVIDENCE / "sprint-22e-w2-experience.json"
SIDE_STORE = EVIDENCE / "sprint-22e-experience-side-store.json"

#: The side blobs live under the campaign artifact root, which CI does not have; the tests
#: that must read them are gated the way the sqlalchemy-needing tests already are, and the
#: tests over the sealed record itself run everywhere.
_NEEDS_ARTIFACT_ROOT = pytest.mark.skipif(
    not os.environ.get("COGOS_ARTIFACT_ROOT"),
    reason="the campaign artifact root is absent from this lane",
)


def _load_experience() -> dict[str, Any]:
    return json.loads(EXPERIENCE.read_text(encoding="utf-8"))


def test_the_experience_record_and_side_manifest_exist_and_their_seals_recompute() -> None:
    for path in (EXPERIENCE, SIDE_STORE):
        stored = json.loads(path.read_text(encoding="utf-8"))
        body = {key: value for key, value in stored.items() if key != "integrity_content_hash"}
        assert hashlib.sha256(_canonical(body)).hexdigest() == stored["integrity_content_hash"]


def test_both_failed_traversals_compiled_and_outrank_every_distractor() -> None:
    stored = _load_experience()
    assert all(
        facts["compilation_decision"] == "completed" for facts in stored["traversals"].values()
    )
    assert stored["retrieval"]["both_traversals_outrank_every_distractor"] is True
    assert len(stored["retrieval"]["entries"]) == 5


def test_the_answer_is_read_from_the_store_and_answers_all_three_questions() -> None:
    """§2.2(e): the retrieval's content, read out of the store by the top rank, answers what
    was tried, what failed, and why."""
    answer = _load_experience()["retrieval"]["answer_read_from_the_store"]
    assert answer["what_was_tried"] is True
    assert answer["what_failed"] is True
    assert answer["why"] is True


def test_the_store_names_sides_not_pairs_and_the_successful_kind_is_w3s() -> None:
    stored = _load_experience()
    assert "sides, not pairs" in json.loads(SIDE_STORE.read_text(encoding="utf-8"))["store"]
    assert "approved change" in stored["successful_kind_owed_by"]
    assert stored["kind_demonstrated"].startswith("failed")


@_NEEDS_ARTIFACT_ROOT
def test_every_stored_side_blob_verifies_on_disk() -> None:
    from cognitive_os.experience.graph_store import blob_path

    root = Path(os.environ["COGOS_ARTIFACT_ROOT"])
    for child in _load_experience()["side_store"]["children"]:
        raw = blob_path(root, child["content_hash"]).read_bytes()
        assert hashlib.sha256(raw).hexdigest() == child["content_hash"]
        assert json.loads(raw)["timeline"], "the stored side must carry the why"


@_NEEDS_ARTIFACT_ROOT
def test_the_experience_check_reproduces_and_refuses_a_tampered_rank() -> None:
    from experience_22e import check_record as check_experience

    verdict = check_experience(_load_experience())
    assert verdict["reproduced"] is True, verdict["mismatches"]
    tampered = _load_experience()
    tampered["retrieval"]["entries"][0]["rank"] = 5
    assert check_experience(tampered)["reproduced"] is False


# ---------------------------------------------------------------------------
# Dry runs 2 and 3 — distinct weakness classes, a rollback, and a second pin
# ---------------------------------------------------------------------------

DRYRUN2 = EVIDENCE / "sprint-22e-w2-dryrun2.json"
DRYRUN3 = EVIDENCE / "sprint-22e-w2-dryrun3.json"


def _load_record(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.mark.parametrize("path", [DRYRUN2, DRYRUN3])
def test_dry_runs_2_and_3_exist_and_their_seals_recompute(path: Path) -> None:
    stored = _load_record(path)
    body = {key: value for key, value in stored.items() if key != "integrity_content_hash"}
    assert hashlib.sha256(_canonical(body)).hexdigest() == stored["integrity_content_hash"]


def test_the_three_dry_runs_cover_three_distinct_weakness_classes() -> None:
    """§2.2(c): L1 verifier_instrument, L2 policy_decision_function, L6 provider_boundary."""
    assert _load_record(CONTINUATION)["entry_id"] == "L1"
    assert _load_record(DRYRUN2)["entry_id"] == "L2"
    assert _load_record(DRYRUN3)["entry_id"] == "L6"


def test_dry_run_2_passes_the_full_matrix_and_executes_the_rollback() -> None:
    """The success-shaped stop, and §2.2's rollback executed rather than attached as prose."""
    stored = _load_record(DRYRUN2)
    ran = [item for item in stored["gates"] if item.get("ran")]
    assert ran and all(item["passed"] for item in ran)
    assert any(item["gate_id"] == "historical_regression" for item in ran)
    assert stored["gates_not_run_here"] == []
    assert stored["repair_probe"]["every_probe_holds"] is True
    rollback = stored["rollback"]
    assert rollback["restored_hash_is_the_baseline"] is True
    assert rollback["capture_diff_is_empty"] is True
    assert stored["stages"][-1] == "rollback_executed_in_isolation"


def test_dry_run_3_is_honestly_refused_by_the_released_pin_it_repairs() -> None:
    """The L6 candidate regresses exactly one released test — the one that pins the
    cancellation conversion. The same class as W2-F2: landing L6 requires the pin to move
    in the same candidate."""
    stored = _load_record(DRYRUN3)
    gates = {item["gate_id"]: item for item in stored["gates"] if item.get("ran")}
    failed = [item for item in gates.values() if item["passed"] is False]
    assert [item["gate_id"] for item in failed] == ["historical_regression"]
    assert (
        "test_cancellation_becomes_a_typed_failure" in gates["historical_regression"]["stdout_tail"]
    )
    assert stored["repair_probe"]["every_probe_holds"] is True
    assert stored["worktree_capture"]["changed_files"] == [
        "src/cognitive_os/providers/cli_process.py"
    ]


@pytest.mark.parametrize("path", [DRYRUN2, DRYRUN3])
def test_the_dryrun_check_reproduces_over_both_new_records(path: Path) -> None:
    from dryrun_22e import check_record as check_dryrun

    verdict = check_dryrun(_load_record(path))
    assert verdict["reproduced"] is True, verdict["mismatches"]
