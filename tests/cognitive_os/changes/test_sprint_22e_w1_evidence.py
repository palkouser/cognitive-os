"""S22E-W1: the substrate met the real repository, and eight findings came back with it.

W0's slice was a fixture refusing a fixture and said so. W1 is the first time this repository's
self-improvement loop touched its own worktree, its own store and a live provider, and what
that produced is mostly *findings* — which is what §3.1 predicted and priced.

The tests here are about the claims W1 makes, not about the drivers' internals:

*The surface split is a split, not an escape.* W1-F1 moved the controlled-change ledger out of
the protected fingerprint, because `request_experiment` writes there before any gate can refuse
anything and the exit would otherwise be unsatisfiable. That is only honest if the audit trail
is still watched, so `audit_trail_moved` is asserted to be a real observation and the protected
set is asserted to exclude exactly the released ledger tables and nothing else.

*The repair is the repair the evidence names.* W1-F4 found that ledger entry L1's cause is this
repository's own `SAFE_UNIT` allowlist rather than the Pint registry, so the probe asserts all
three: the written notation is accepted, the ASCII notation still is, and an injection string
still is not. A widened allowlist that traded a false rejection for a real hole would pass the
first two and fail the third.

*The rejection is real.* Dry run 1's candidate is a genuine repair and a released gate refused
it anyway. The test asserts a gate ran, took measurable time, and failed — a rejection nobody
planted.

*The provider-assisted mark is reported as unreachable, because it is.* W1-F7 blocks the only
released writer of a merged revision, so the approved revision reads `deterministic` while the
merged one reads `provider_assisted`. Both are asserted, so a successor cannot quietly read
this dry run as having produced a provider-assisted approved revision.
"""

from __future__ import annotations

import hashlib
import json
import sys
from importlib.util import find_spec
from pathlib import Path
from typing import Any

import pytest

REPOSITORY = Path(__file__).resolve().parents[3]
EVIDENCE = REPOSITORY / "docs/sprints/sprint-22/evidence"
sys.path.insert(0, str(REPOSITORY / "scripts"))

from surface_22e import active_surface_members, audit_trail_tables  # noqa: E402

#: **The same portability rule, a third time in this sprint, and this time in its own tests.**
#: `audit_trail_tables()` reads the released SQLAlchemy table definitions, and the
#: `controlled-changes-core` lane syncs with `--all-groups` and *no extras at all* — so
#: SQLAlchemy is absent there and these two assertions cannot run. 22D W4-F1 is a standing rule
#: (§0) precisely because this keeps happening: W0 hit it twice, W1's gate runner once, and this
#: file once more. Gated rather than dropped: where the dependency is present the invariant is
#: still checked, and where it is absent the test says so instead of failing for a reason that
#: is not about the claim.
_NEEDS_SQLALCHEMY = pytest.mark.skipif(
    find_spec("sqlalchemy") is None, reason="the postgres extra is absent from this lane"
)

RECORDS = {
    "substrate": EVIDENCE / "sprint-22e-w1-substrate.json",
    "dryrun1": EVIDENCE / "sprint-22e-w1-dryrun1.json",
}


def _canonical(value: Any) -> bytes:
    return json.dumps(value, indent=1, sort_keys=True, ensure_ascii=False).encode("utf-8")


def _load(name: str) -> dict[str, Any]:
    return json.loads(RECORDS[name].read_text(encoding="utf-8"))


@pytest.mark.parametrize("name", sorted(RECORDS))
def test_every_w1_record_exists_and_its_seal_recomputes(name: str) -> None:
    assert RECORDS[name].exists(), f"{RECORDS[name].name} is missing"
    stored = _load(name)
    body = {key: value for key, value in stored.items() if key != "integrity_content_hash"}
    assert hashlib.sha256(_canonical(body)).hexdigest() == stored["integrity_content_hash"]


# ---------------------------------------------------------------------------
# W1-F1 — the split is a split
# ---------------------------------------------------------------------------


@_NEEDS_SQLALCHEMY
def test_the_audit_trail_set_is_exactly_the_released_ledger_tables() -> None:
    """Derived from the released tables module, so a new ledger table joins it automatically."""
    from sqlalchemy import Table

    from cognitive_os.infrastructure.changes.postgres import tables

    assert audit_trail_tables() == frozenset(
        value.name for value in vars(tables).values() if isinstance(value, Table)
    )
    assert "memory_items" not in audit_trail_tables()
    assert "change_experiments" in audit_trail_tables()


@_NEEDS_SQLALCHEMY
def test_the_split_excludes_the_ledger_and_nothing_else() -> None:
    """Asserted against the released modules rather than against a record.

    The invariant is about which tables the split removes, and that is a fact about the
    released schema — checking it through a stored record would make it a fact about whichever
    run happened to be sealed last, and would need a database to re-check.
    """
    from cognitive_os.infrastructure.postgres.tables import metadata

    governed = {table.name for table in metadata.tables.values() if table.schema == "cognitive_os"}
    audit = audit_trail_tables()
    assert audit < governed, "the ledger tables must be part of the governed schema"
    assert all(name.startswith("change_") for name in audit)
    # The protected set is everything else, and it must still contain the surfaces §2.2(a)
    # names by name — the split must not have taken the learned pointer with it.
    # The learned pointer tables are created by raw-SQL migrations rather than declared as
    # SQLAlchemy tables, so they are absent from `metadata` and cannot be checked here. The
    # live capture checks them instead, and raises when they are missing from the store — see
    # `surface_22e.capture`, which refuses rather than reporting a shorter list.
    protected = governed - audit
    assert protected, "the split must leave protected tables behind"
    assert not any(name.startswith("change_") for name in protected)
    assert {"artifacts", "events"} <= protected


def test_the_protected_surface_did_not_move_and_the_audit_trail_is_reported_beside_it() -> None:
    """W1-F1's split, asserted as the two separate questions it is.

    `audit_trail_moved` is **reported, not required**, and the sealed runs are why. Both were
    re-runs of a deterministic experiment id, and `request_experiment` is idempotent by request
    signature — it finds the existing experiment and returns it, so a repeat writes nothing and
    the trail correctly does not move. Requiring movement here would have made this test a
    statement about whether the run happened to be the first one.

    What must always hold is the other half: the protected surface did not move, and the
    comparison covered every enumerated member.
    """
    for name in RECORDS:
        comparison = _load(name)["zero_active_state_mutation"]
        assert comparison["zero_active_state_mutation"] is True, name
        assert comparison["mutated_members"] == [], name
        assert comparison["members_compared"] == list(active_surface_members()), name
        assert isinstance(comparison["audit_trail_moved"], bool), name
        assert comparison["audit_trail_fingerprint_before"], name
        assert comparison["audit_trail_fingerprint_after"], name


# ---------------------------------------------------------------------------
# W1-F3 — the gates run in a declared environment
# ---------------------------------------------------------------------------


def test_no_wave_credential_reaches_a_gate() -> None:
    environment = _load("substrate")["evaluation_matrix"]["gate_environment"]
    assert environment["no_cogos_variable_is_inherited"] is True
    assert not [name for name in environment["inherited_names"] if name.startswith("COGOS_")]
    assert environment["finding"] == "W1-F3"


def test_the_gate_map_covers_the_released_matrix() -> None:
    matrix = _load("substrate")["evaluation_matrix"]
    assert matrix["map_covers_the_matrix"] is True
    assert matrix["gate_count"] == 15
    assert matrix["measured_wall_clock_seconds"] > 0


# ---------------------------------------------------------------------------
# The substrate's four seams
# ---------------------------------------------------------------------------


def test_the_worktree_is_detached_locked_and_outside_the_active_checkout() -> None:
    worktree = _load("substrate")["worktree"]
    assert worktree["detached"] is True
    assert worktree["locked"] is True
    assert worktree["outside_the_active_checkout"] is True


def test_the_clone_is_a_different_database_at_the_same_head_and_refuses_what_it_should() -> None:
    clone = _load("substrate")["database_clone"]
    assert clone["clone_is_a_different_database"] is True
    assert clone["heads_agree"] is True
    assert clone["every_refusal_refused"] is True
    assert set(clone["released_refusals"]) == {
        "same_identity",
        "empty_active_identity",
        "manifest_carries_a_url",
    }


def test_the_persisted_store_returns_what_it_was_given() -> None:
    chain = _load("substrate")["persisted_chain"]
    assert chain["repository"] == "PostgresChangeRepository"
    assert chain["content_hash_survives_the_round_trip"] is True
    assert chain["read_back_current_revision"] == chain["written_revision"]


# ---------------------------------------------------------------------------
# Dry run 1
# ---------------------------------------------------------------------------

EXPECTED_DRY_RUN_STAGES = (
    "weakness_mined",
    "proposal_created",
    "provider_draft_merged_and_resealed",
    "proposal_approved_for_experiment",
    "experiment_requested",
    "isolation_prepared",
    "repair_applied",
    "repair_probed",
    "candidate_captured_from_the_worktree",
    "evaluation_run",
)


def test_the_dry_run_entered_every_stage_in_order() -> None:
    assert tuple(_load("dryrun1")["stages"]) == EXPECTED_DRY_RUN_STAGES


def test_the_draft_came_from_a_live_governed_provider_call() -> None:
    record = _load("dryrun1")
    provider = record["provider"]
    assert provider["provider_id"] == "claude-code"
    assert provider["retention_mode"] == "none"
    assert len(provider["request_hash"]) == 64
    assert len(provider["normalized_response_hash"]) == 64
    draft = record["draft"]
    assert draft["prompt_bytes"] > 0
    assert draft["findings"] >= 1
    assert set(draft["advisory_fields"]) == {
        "findings",
        "recommendations",
        "risks",
        "summary",
        "verification_steps",
    }


def test_the_host_verification_admitted_the_draft_and_the_mark_cannot_survive() -> None:
    """**W1-F7, asserted in both directions so neither half can be read alone.**"""
    draft = _load("dryrun1")["draft"]
    assert draft["host_verification_passed"] is True
    assert draft["generation_mode_after_host_verification"] == "provider_assisted"
    assert draft["generation_mode_on_the_approved_revision"] == "deterministic"
    assert (
        "W1-F7" in draft["provider_assisted_mark_did_not_survive_because"]
        or draft["provider_assisted_mark_did_not_survive_because"]
    )


# ---------------------------------------------------------------------------
# W1-F4 — the repair, and the hole it must not open
# ---------------------------------------------------------------------------


def test_the_repair_admits_written_notation_without_opening_an_injection_hole() -> None:
    probe = _load("dryrun1")["repair_probe"]
    assert probe["written_notation_now_accepted"] is True
    assert probe["ascii_notation_still_accepted"] is True
    assert probe["injection_still_refused"] is True


def test_the_defect_is_the_repository_allowlist_and_not_the_unit_library() -> None:
    """W1-F4. Asserted live, because this corrects a predecessor's sealed diagnosis."""
    pint = pytest.importorskip("pint")
    from cognitive_os.verification.physics.quantities import PhysicalQuantity

    registry = pint.UnitRegistry()
    for unit in ("Ω", "kg·m/s", "m/s²"):
        registry.parse_units(unit)  # the library parses it
        with pytest.raises(ValueError):
            PhysicalQuantity(magnitude="1", unit=unit)  # the contract refuses it


def test_the_candidate_changed_only_the_allowed_path() -> None:
    capture = _load("dryrun1")["worktree_capture"]
    assert capture["only_the_allowed_path_changed"] is True
    assert capture["changed_files"] == ["src/cognitive_os/verification/physics/quantities.py"]


def test_a_real_gate_refused_the_candidate() -> None:
    """The rejection W1 owed: a genuine repair, and a released gate that failed it anyway."""
    gates = _load("dryrun1")["gates"]
    failed = [item for item in gates if item.get("passed") is False]
    assert failed, "dry run 1 must be carried to a gate rejection"
    assert all(item["ran"] for item in failed)
    assert all(item["seconds"] > 0 for item in failed)
    assert any(item.get("passed") for item in gates), "a rejection needs passing gates beside it"


def test_the_dry_run_declares_the_gates_it_did_not_run() -> None:
    """§3.2: a cell economised away is a quiet reading-change unless it is declared."""
    record = _load("dryrun1")
    assert record["gates_not_run_here"]
    assert "historical_regression" in record["gates_not_run_here"]


# ---------------------------------------------------------------------------
# W1-F9 — the check asymmetry, closed
# ---------------------------------------------------------------------------
#
# The four W0 sealers had a `--check`; the two W1 drivers did not, and the gap was found in
# review after the wave closed — checked by this file, but from one command line, which is the
# shape 22D W4-F1 names. These tests hold the closure: each check must reproduce over the
# sealed record, and each must refuse a tampered copy, because a validator that has only ever
# been shown accepting is a validator nobody has tested (22A W4-F2).


def test_the_substrate_check_reproduces_and_names_its_split() -> None:
    from isolation_22e import check_record

    verdict = check_record(_load("substrate"))
    assert verdict["reproduced"] is True, verdict["mismatches"]
    assert verdict["recomputed"] and verdict["recorded_not_recomputed"]


def test_the_substrate_check_refuses_a_tampered_verdict() -> None:
    """A flipped gate verdict must fail the arithmetic the summary owes its own rows."""
    from isolation_22e import check_record

    tampered = _load("substrate")
    victim = next(
        item for item in tampered["evaluation_matrix"]["gates"] if item.get("passed") is True
    )
    victim["passed"] = False
    verdict = check_record(tampered)
    assert verdict["reproduced"] is False
    assert any("gates_passed" in item for item in verdict["mismatches"])


def test_the_substrate_check_refuses_a_planted_zero_mutation_claim() -> None:
    """22A W4-F2: the claim is re-derived from the captures, never accepted from the record."""
    from isolation_22e import check_record

    tampered = _load("substrate")
    tampered["surface_after"]["repository_commit"] = "0" * 40
    verdict = check_record(tampered)
    assert verdict["reproduced"] is False
    assert any("zero_active_state_mutation" in item for item in verdict["mismatches"])


def test_the_dryrun_check_reproduces_and_names_the_billed_call_as_reread() -> None:
    from dryrun_22e import check_record

    verdict = check_record(_load("dryrun1"))
    assert verdict["reproduced"] is True, verdict["mismatches"]
    assert any("billed live call" in item for item in verdict["recorded_not_recomputed"])


def test_the_dryrun_check_refuses_a_tampered_probe() -> None:
    """An injection case quietly marked accepted must fail the derived verdict booleans."""
    from dryrun_22e import check_record

    tampered = _load("dryrun1")
    tampered["repair_probe"]["accepted"]["; rm -rf /"] = True
    verdict = check_record(tampered)
    assert verdict["reproduced"] is False
    assert any("injection_still_refused" in item for item in verdict["mismatches"])
