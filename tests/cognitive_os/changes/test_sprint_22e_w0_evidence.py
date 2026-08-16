"""S22E-W0: the four seals reproduce, and the claims they freeze are not decorative.

Every later 22E wave is bound to these records by hash, and the sprint's first exit is a
*negative* claim — that a rejected proposal changed nothing. Negative claims are the easiest
kind to fake, so most of this file is about making them falsifiable.

*The surface can notice a change.* 22A W4-F2 is a standing rule here: a claim about what did
not change must be able to notice a change. `compare` is therefore fed a deliberately mutated
capture and required to say so, member by member. Without this test the zero-mutation exit is
a function that has only ever been shown returning `True`.

*The enumeration is an enumeration.* The active surface is derived from
`ActiveStateProtectionSnapshot`, not typed out, so if that contract grows a field this file
fails — which is the mechanism that keeps exit one honest after W0 stops looking. The sixth
member exists because the released contract cannot express the domain registry (W0-F3), and
that gap is asserted rather than narrated: if a successor widens the contract, this fails and
the extra member should go.

*The refusal refuses.* `approve_promotion` is *called* on a rejected assessment and required
to raise. A gate that has never refused anything is a gate nobody has tested.

*The gate is wired.* Every Gate M binding that reads a predecessor resolves today, and an
unresolvable path raises rather than rendering false — two of them did point at nothing when
first drafted, and W4 is the wrong wave to find that in.

*Nothing has been measured.* `measured_values: 0` in a sprint whose gate is mostly inherited.

*The ledger is priced from records that are sealed.* Every number in it is read back out of a
predecessor's record whose seal recomputes, and the one entry the plan mis-priced is marked.

`recorded_at` and the seal over it are excluded from every reproduction comparison, so no test
here fails because a clock moved (22B W2-F1/F2).
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

import pytest

REPOSITORY = Path(__file__).resolve().parents[3]
EVIDENCE = REPOSITORY / "docs/sprints/sprint-22/evidence"
sys.path.insert(0, str(REPOSITORY / "scripts"))

from pre_registration_22e import (  # noqa: E402
    EXIT_CRITERIA,
    GATE_M_CONDITIONS,
    GATE_OWNER_DECISIONS,
    UnresolvableBinding,
    resolve_binding,
    verify_bindings,
)
from surface_22e import (  # noqa: E402
    ADDITIONAL_SURFACE_MEMBERS,
    active_surface_members,
    compare,
    contract_surface_members,
)

from cognitive_os.domain.changes import ActiveStateProtectionSnapshot  # noqa: E402

RECORDS = {
    "preflight": EVIDENCE / "sprint-22e-preflight.json",
    "ledger": EVIDENCE / "sprint-22e-weakness-ledger.json",
    "contracts": EVIDENCE / "sprint-22e-contracts.json",
    "pre_registration": EVIDENCE / "sprint-22e-pre-registration.json",
    "slice": EVIDENCE / "sprint-22e-w0-slice.json",
}


def _canonical(value: Any) -> bytes:
    return json.dumps(value, indent=1, sort_keys=True, ensure_ascii=False).encode("utf-8")


def _load(name: str) -> dict[str, Any]:
    return json.loads(RECORDS[name].read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# The seals
# ---------------------------------------------------------------------------


#: `contracts` carries no seal of its own, and that is the released 22D shape rather than an
#: omission: it is a projection of the pre-registration's own readings, validated by rebuilding
#: byte-identically under `--check`. Sealing a derived document would create a second thing to
#: keep in step with the first.
UNSEALED = ("contracts",)


@pytest.mark.parametrize("name", sorted(RECORDS))
def test_every_w0_record_exists(name: str) -> None:
    assert RECORDS[name].exists(), f"{RECORDS[name].name} is missing"


@pytest.mark.parametrize("name", sorted(set(RECORDS) - set(UNSEALED)))
def test_every_sealed_w0_record_recomputes_its_own_seal(name: str) -> None:
    stored = _load(name)
    body = {key: value for key, value in stored.items() if key != "integrity_content_hash"}
    assert hashlib.sha256(_canonical(body)).hexdigest() == stored["integrity_content_hash"], (
        f"{RECORDS[name].name} does not recompute its own seal"
    )


@pytest.mark.parametrize("name", sorted(UNSEALED))
def test_the_unsealed_record_is_a_projection_of_a_sealed_one(name: str) -> None:
    """It carries no seal, so what must be true is that it rebuilds from the same sources."""
    import pre_registration_22e

    built = {"contracts": pre_registration_22e._contracts()}[name]
    assert _load(name) == built


def test_nothing_was_measured_in_w0() -> None:
    assert _load("pre_registration")["measured_values"] == 0
    assert _load("pre_registration")["amendments_made_by_22e"] == 0


# ---------------------------------------------------------------------------
# 22A W4-F2 — the claim must be able to notice a change
# ---------------------------------------------------------------------------


def _capture(**overrides: str) -> dict[str, Any]:
    values = {name: f"{name}-baseline" for name in active_surface_members()}
    values.update(overrides)
    return {"values": values, "surface_hash": hashlib.sha256(_canonical(values)).hexdigest()}


def test_the_surface_comparison_reports_no_mutation_when_nothing_moved() -> None:
    before = _capture()
    assert compare(before, _capture())["zero_active_state_mutation"] is True


@pytest.mark.parametrize("member", active_surface_members())
def test_the_surface_comparison_notices_a_change_in_every_member(member: str) -> None:
    """**The negative control.** Each member is moved on its own and must be named.

    Parametrised per member rather than moving one of them, because a comparison that only
    ever watched the first field would pass a single-member test and miss five surfaces.
    """
    result = compare(_capture(), _capture(**{member: "mutated"}))
    assert result["zero_active_state_mutation"] is False
    assert result["mutated_members"] == [member]
    assert result["per_member_unchanged"][member] is False


def test_the_comparison_is_not_reading_a_flag_supplied_by_its_input() -> None:
    """A capture that *claims* it is unchanged must not be able to say so."""
    after = _capture(repository_commit="mutated")
    after["zero_active_state_mutation"] = True  # a lie, planted where a lie would live
    assert compare(_capture(), after)["zero_active_state_mutation"] is False


# ---------------------------------------------------------------------------
# The enumeration is an enumeration (22A W4-F1)
# ---------------------------------------------------------------------------


def test_the_contract_surface_is_derived_from_the_released_contract() -> None:
    fields = set(ActiveStateProtectionSnapshot.model_fields)
    assert set(contract_surface_members()) < fields
    assert fields - set(contract_surface_members()) == {"captured_at", "content_hash"}


def test_the_additional_member_exists_only_because_the_contract_cannot_express_it() -> None:
    """W0-F3. If a successor widens the contract, this fails and the extra member goes."""
    assert ADDITIONAL_SURFACE_MEMBERS == ("domain_registry_snapshot_hash",)
    assert not set(ADDITIONAL_SURFACE_MEMBERS) & set(ActiveStateProtectionSnapshot.model_fields)


def test_the_pre_registration_publishes_the_derived_enumeration() -> None:
    published = _load("contracts")["S22E-011"]
    assert published["members"] == list(active_surface_members())
    assert published["contract_members"] == list(contract_surface_members())


# ---------------------------------------------------------------------------
# The gate is wired (§2.2d)
# ---------------------------------------------------------------------------


def test_every_predecessor_gate_m_binding_resolves_today() -> None:
    result = verify_bindings()
    assert result["predecessor_bindings_resolvable"] is True
    assert result["predecessor_values_as_expected"] is True
    assert result["this_sprint_bindings_deferred"] == 3


def test_an_unresolvable_binding_raises_rather_than_rendering_false() -> None:
    """A condition that renders false because a key was renamed is not a result."""
    with pytest.raises(UnresolvableBinding):
        resolve_binding("sprint-22d-exit-criteria.json", "criteria.no_such_key")
    with pytest.raises(UnresolvableBinding):
        resolve_binding("sprint-22d-exit-criteria.json", "criteria[99].met")
    with pytest.raises(UnresolvableBinding):
        resolve_binding("no-such-record.json", "anything")


def test_all_ten_gate_m_conditions_are_bound() -> None:
    bindings = _load("contracts")["S22E-014"]["bindings"]
    assert [item["condition"] for item in bindings] == list(range(1, 11))
    assert len(GATE_M_CONDITIONS) == 10


def test_the_two_conditions_that_fail_as_sealed_are_recorded_as_failing() -> None:
    """§1.2's honesty requirement, asserted rather than trusted to prose."""
    bindings = {item["condition"]: item for item in _load("contracts")["S22E-014"]["bindings"]}
    for condition in (6, 7):
        assert "fails as sealed" in bindings[condition]["expected_at_w0"]
        assert (
            resolve_binding(bindings[condition]["reads_record"], bindings[condition]["reads_path"])
            is False
        )
        assert "re_measurement_licensed_by" in bindings[condition]


# ---------------------------------------------------------------------------
# The gate-owner decisions (§2.1)
# ---------------------------------------------------------------------------


def test_exactly_two_gate_owner_decisions_were_taken_and_both_predate_any_candidate() -> None:
    assert sorted(GATE_OWNER_DECISIONS) == [
        "condition_5_reading",
        "zero_zero_sixteen_eligibility",
    ]
    for decision in GATE_OWNER_DECISIONS.values():
        assert decision["taken"] == "W0, before any candidate was generated"


def test_the_condition_5_decision_publishes_the_reading_it_rejected() -> None:
    """A reading that does not say what it chose against is a reading nobody can audit."""
    decision = GATE_OWNER_DECISIONS["condition_5_reading"]
    assert decision["verdict_under_this_reading"] == "holds"
    rejected = {item["reading"] for item in decision["rejected_alternatives"]}
    assert "22C's improvement arithmetic" in rejected
    assert all(item.get("verdict") == "fails" for item in decision["rejected_alternatives"])


def test_the_zero_zero_sixteen_decision_keeps_the_migration_head_at_0015() -> None:
    assert GATE_OWNER_DECISIONS["zero_zero_sixteen_eligibility"]["eligible"] is False
    assert _load("pre_registration")["migration_head"]["expected_revision"] == "0015"
    stores = _load("preflight")["stores"]
    assert stores["every_store_at_the_expected_head"] is True
    assert stores["expected_migration_head"] == "0015"


# ---------------------------------------------------------------------------
# The ledger (§1.4)
# ---------------------------------------------------------------------------


def test_the_ledger_ranks_five_entries_and_only_four_are_eligible() -> None:
    ledger = _load("ledger")
    assert [item["rank"] for item in ledger["entries"]] == [1, 2, 3, 4, 5]
    assert ledger["eligible_count"] == 4
    ineligible = [item for item in ledger["entries"] if not item["eligible"]]
    assert [item["finding"] for item in ineligible] == ["22D W2-F1"]
    assert ledger["zero_zero_sixteen_is_eligible"] is False


def test_the_two_entries_that_touch_a_gate_m_condition_rank_first() -> None:
    entries = _load("ledger")["entries"]
    assert [item["touches_a_gate_m_condition"] for item in entries[:2]] == [6, 7]


def test_the_repriced_entry_says_what_the_plan_got_wrong() -> None:
    """W0-F1. The plan calls 22B W3-F1 unrepaired; half of it shipped in 22C."""
    entry = next(item for item in _load("ledger")["entries"] if item["finding"] == "22B W3-F1")
    reproduction = entry["reproduction"]
    assert reproduction["finding"] == "W0-F1"
    assert reproduction["released_code_says"]["the_permanence_half_shipped_in_22c"] is True
    assert reproduction["released_code_says"]["items_missing_an_event_after_resume"] == 0
    assert entry["risk_class"] == "high"
    assert entry["expected_benefit"]["value_on_the_reading_the_plan_names"] == 0


def test_the_notation_ceiling_is_published_as_a_ceiling_and_not_as_a_forecast() -> None:
    entry = next(item for item in _load("ledger")["entries"] if item["finding"] == "22D W2-F2")
    benefit = entry["expected_benefit"]
    assert benefit["is_a_ceiling_not_a_forecast"] is True
    # 66 today, at most 76 if every recoverable task were notation and every one then
    # verified. The floor is 70, so condition 6 is reachable and not implied.
    assert benefit["local_model_verified_now"] == 66
    assert benefit["local_model_verified_at_the_ceiling"] == 76
    assert benefit["crosses_the_floor_at_the_ceiling"] is True


def test_the_ledger_prices_only_from_records_whose_seals_recompute() -> None:
    assert _load("ledger")["every_source_record_seal_recomputed_before_it_was_read"] is True


# ---------------------------------------------------------------------------
# The slice (§3.1)
# ---------------------------------------------------------------------------


def test_the_slice_entered_every_stage_in_order() -> None:
    rejection = _load("slice")["fixture_proposal_to_rejection"]
    assert rejection["no_stage_skipped"] is True
    assert rejection["stages_entered_in_order"] == rejection["expected_stage_order"]


def test_the_slice_rejection_arrived_through_the_released_mapping() -> None:
    """A rejection that arrived by default would prove less than one that was mapped."""
    assessment = _load("slice")["fixture_proposal_to_rejection"]["assessment"]
    assert assessment["is_a_rejection"] is True
    assert assessment["arrived_through_the_released_mapping"] is True
    assert assessment["decision"] == "security_regression"


def test_the_promotion_gate_was_called_and_raised() -> None:
    promotion = _load("slice")["fixture_proposal_to_rejection"]["promotion"]
    assert promotion["attempted"] is True
    assert promotion["refused"] is True
    assert promotion["refusal"]


def test_the_promotion_gate_raises_when_driven_live() -> None:
    """The record above is read back; this executes the refusal in-process as well.

    Two different questions — "did it refuse when the slice ran" and "does it refuse now" —
    and a record can only answer the first.
    """
    from slice_22e import _proposal_to_rejection

    result = asyncio.run(_proposal_to_rejection())
    assert result["promotion"]["refused"] is True
    assert result["no_stage_skipped"] is True


def test_the_slice_mutated_nothing_and_says_so_by_recomputation() -> None:
    comparison = _load("slice")["zero_active_state_mutation"]
    assert comparison["zero_active_state_mutation"] is True
    assert comparison["mutated_members"] == []
    assert comparison["members_compared"] == list(active_surface_members())


def test_the_slice_decides_no_exit_criterion() -> None:
    """§3.1's slice is a rehearsal. Exit one wants a real candidate refused at a real gate."""
    assert _load("slice")["reads_an_exit_criterion"] is False


# ---------------------------------------------------------------------------
# The exits, carried verbatim
# ---------------------------------------------------------------------------


def test_the_five_exit_sentences_are_carried_verbatim_and_moved_by_nobody() -> None:
    record = _load("pre_registration")
    assert record["exit_criteria"] == list(EXIT_CRITERIA)
    assert len(EXIT_CRITERIA) == 5
    assert record["amendments_made_by_22e"] == 0


def test_the_outcome_tag_is_the_programme_level_tag() -> None:
    record = _load("pre_registration")
    assert record["outcome_tag"] == "sprint-22-baseline"
    assert record["negative_outcome_tag"] == "sprint-22e-evidence-baseline"
    assert "after" in record["outcome_tag_is"]
