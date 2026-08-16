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
import sys
from pathlib import Path
from typing import Any

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
