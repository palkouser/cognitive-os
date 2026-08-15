"""S22C-W1: the two inherited repairs, and the real source's first segment.

What these have to hold, beyond "the seals reproduce":

*The repairs are proven against 22B's own numbers.* A repair measured against a reproduction
chosen after the fix is a repair measured against itself. Every comparison in these records
names a value that is also in a sealed 22B record, and these tests read both.

*The crash record does not read a run that proved nothing.* The window between the record's
transaction and its event is a race, and a crash that lands outside it leaves zero orphans —
which satisfies "zero after the resume" without the repair having run. The record carries
`window_opened`, and a test that only checked the zero would pass on exactly the run that
means nothing.

*The unclosed half is stated.* The repair heals a resumed range; it does not close the
window. A record that reported only the good half would be the more dangerous artifact.

*The slice's findings are held where deleting them fails.* The real source's page furniture,
its image-only arithmetic and its two precisions are what W1 bought; they are asserted here
so a later edit cannot quietly drop them.

These read sealed records and run no database, so they hold in CI where neither the stores
nor the cleared PDF exist.
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

from campaign_22c import assertion_agrees  # noqa: E402

PLAN_R1 = EVIDENCE / "sprint-22c-repair-plan.json"
PLAN = EVIDENCE / "sprint-22c-repair-plan-r2.json"
EVENT_REPAIR = EVIDENCE / "sprint-22c-w1-event-repair.json"
CRASH = EVIDENCE / "sprint-22c-w1-crash.json"
PRECONDITION = EVIDENCE / "sprint-22c-w1-restore-precondition.json"
REINDEX = EVIDENCE / "sprint-22c-w1-restore-reindex.json"
SLICE = EVIDENCE / "sprint-22c-w1-slice.json"

W3_CRASH_22B = EVIDENCE / "sprint-22b-w3-crash.json"
W4_RECALL_22B = EVIDENCE / "sprint-22b-w4-restored-recall-clustered.json"
W2_RECALL_22B = EVIDENCE / "sprint-22b-w2-recall-clustered.json"


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _canonical(value: Any) -> bytes:
    return json.dumps(value, indent=1, sort_keys=True, ensure_ascii=False).encode("utf-8")


def _seal_reproduces(path: Path) -> bool:
    document = _load(path)
    body = {key: value for key, value in document.items() if key != "integrity_content_hash"}
    return _sha256(_canonical(body)) == document["integrity_content_hash"]


# --- the seals ---------------------------------------------------------------


def test_every_w1_record_is_sealed_over_its_own_content() -> None:
    for path in (PLAN_R1, PLAN, EVENT_REPAIR, CRASH, PRECONDITION, REINDEX, SLICE):
        assert _seal_reproduces(path), path.name


# --- W1-F4, the amendment ------------------------------------------------------


def test_revision_1_is_still_here_and_still_says_what_it_said() -> None:
    """A pre-registration that is edited after it fails is not a pre-registration."""
    revision_1 = _load(PLAN_R1)
    assert "revision" not in revision_1
    steps = {step["order"]: step["sql"] for step in revision_1["w4_f1"]["procedure"]["steps"]}
    assert steps[2] == "SET max_parallel_maintenance_workers = 4"


def test_revision_2_names_revision_1_by_hash_and_says_how_it_failed() -> None:
    plan = _load(PLAN)
    assert plan["revision"] == 2
    superseded = plan["supersedes"]
    assert superseded["revision"] == 1
    assert superseded["procedure_hash"] == _load(PLAN_R1)["w4_f1"]["procedure_hash"]
    assert superseded["sealed_in"] == "sprint-22c-repair-plan.json"
    assert "DiskFullError" in superseded["failed_with"]
    assert "/dev/shm" in superseded["why_it_failed"]
    assert "before any index was touched" in superseded["when_it_failed"]
    assert "not a pre-registration" in plan["why_a_second_revision"]


def test_the_amendment_withdrew_the_claim_that_was_too_confident() -> None:
    """Revision 1 said parallel workers were wall-clock only. That was not established."""
    steps = {step["order"]: step for step in _load(PLAN)["w4_f1"]["procedure"]["steps"]}
    assert steps[2]["sql"] == "SET max_parallel_maintenance_workers = 0"
    assert "withdrawn" in steps[2]["why"]
    assert "order-dependent" in steps[2]["why"]
    # And the lever actually under test is untouched by the amendment.
    assert steps[1]["sql"] == "SET maintenance_work_mem = '12GB'"


def test_the_precondition_is_its_own_record_because_the_rebuild_destroys_what_it_read() -> None:
    record = _load(PRECONDITION)
    assert record["held"] is True
    assert record["remeasured_restored_recall"] == _load(W4_RECALL_22B)["recall_at_k"]
    assert "W1-F4" in record["why_this_is_its_own_record"]
    assert record["recall"]["probes"] == 500


# --- S22C-030, the pre-registration ------------------------------------------


def test_the_procedure_was_frozen_before_the_first_reindex() -> None:
    plan = _load(PLAN)
    assert plan["wave"] == "W1"
    assert "the first REINDEX to touch an index" in plan["frozen_before"]
    # Revision 2 was sealed *after* the crash reproduction, which ran under revision 1. A
    # record that inherited revision 1's "frozen before both measurements" would be claiming
    # something true of the wrong revision.
    assert "the crash reproduction" in plan["frozen_after"]
    assert plan["amendments_made_by_22c"] == 0
    reindex = _load(REINDEX)
    assert reindex["procedure_hash"] == plan["w4_f1"]["procedure_hash"]
    assert reindex["procedure_was_frozen_first"] is True


def test_the_pre_registration_names_a_falsifier_and_a_fallback() -> None:
    """A hypothesis without a falsifier is a preference."""
    procedure = _load(PLAN)["w4_f1"]["procedure"]
    assert "still reads below" in procedure["falsifier"]
    assert "hnsw.ef_construction" in procedure["fallback_if_the_hypothesis_is_wrong"]["sql"]
    assert "maintenance_work_mem" in procedure["hypothesis"]
    assert "0.95" in procedure["success_reads"]


def test_the_pre_registration_binds_22bs_own_sealed_numbers() -> None:
    plan = _load(PLAN)
    assert plan["w4_f1"]["sealed_restored_recall"] == _load(W4_RECALL_22B)["recall_at_k"]
    assert plan["w4_f1"]["sealed_source_recall"] == _load(W2_RECALL_22B)["recall_at_k"]
    assert (
        plan["w3_f1"]["sealed_orphans_after_the_crash"]
        == (_load(W3_CRASH_22B)["items_missing_an_event"])
    )


# --- S22C-031, the write path ------------------------------------------------


def test_the_planted_orphan_is_repaired_by_the_resume_and_not_duplicated() -> None:
    record = _load(EVENT_REPAIR)
    assert record["creation_events_after_the_planted_crash"] == 0
    assert record["creation_events_after_the_resume"] == 1
    assert record["creation_events_after_a_second_resume"] == 1
    assert record["resume_repaired_the_orphan"] is True
    assert record["resume_is_idempotent"] is True


def test_the_crash_record_refuses_a_run_that_missed_the_window() -> None:
    """The zero only means something if there was something to close."""
    record = _load(CRASH)
    assert record["window_opened"] is True
    assert record["reading_is_refused"] is None
    assert record["items_missing_an_event_after_recovery"] > 0
    assert record["items_missing_an_event_after_resume"] == 0
    assert record["repair_closed_every_orphan"] is True
    read = next(run for run in record["runs"] if run["window_opened"])
    assert read["eventless_after_recovery"] > read["eventless_before"]
    assert read["resume_duplicated_nothing"] is True


def test_the_crash_reproduced_22bs_defect_before_repairing_it() -> None:
    record = _load(CRASH)
    assert (
        record["what_22b_measured"]["items_missing_an_event"]
        == (_load(W3_CRASH_22B)["items_missing_an_event"])
    )
    assert "after crash recovery, before the resume" in record["what_22b_measured"]["measured_when"]


def test_the_window_is_recorded_as_still_open() -> None:
    """Half a repair reported as a whole one is the failure this asserts against."""
    limitations = " ".join(_load(CRASH)["limitations"])
    assert "the window is not closed" in limitations
    assert "never re-run keeps its orphan" in limitations
    assert "stamped when the repair ran" in limitations


# --- S22C-032, the restore -----------------------------------------------------


def test_the_precondition_reproduced_22bs_sealed_number_before_anything_was_rebuilt() -> None:
    precondition = _load(REINDEX)["precondition"]
    assert precondition["held"] is True
    assert precondition["sealed_restored_recall"] == _load(W4_RECALL_22B)["recall_at_k"]
    assert precondition["remeasured_before_the_rebuild"] == precondition["sealed_restored_recall"]


def test_the_repaired_index_reads_back_over_the_floor() -> None:
    record = _load(REINDEX)
    assert record["recall"]["floor"] == 0.95
    assert record["recall"]["recall_at_k"] >= 0.95
    assert record["recall"]["meets_floor"] is True
    assert record["recall"]["probes"] == 500
    assert record["recall"]["ground_truth"] == "exact scan per probe, never sampled"
    assert record["comparison"]["recovered_by"] > 0


def test_the_reindex_record_does_not_claim_to_have_rebuilt_22bs_index() -> None:
    record = _load(REINDEX)
    assert "third graph" in record["what_this_does_not_claim"]
    assert any("one store, one dataset" in item for item in record["limitations"])


# --- S22C-033, the real source's first segment ---------------------------------


def test_the_slice_drove_all_nine_stages_in_order_over_the_cleared_source() -> None:
    record = _load(SLICE)
    assert record["stages"]["count"] == 9
    assert record["stages"]["all_nine_in_order"] is True
    assert record["source"]["verified_against_the_clearance"] is True
    assert record["source"]["license_identifier"] == "CC-BY-4.0"
    assert record["source"]["domain_id"] == "engineering.mechanics"
    assert record["manifest"]["domain_ids"] == ["engineering.mechanics"]
    assert record["manifest"]["providers"] == []


def test_the_platform_refused_the_passage_and_the_campaign_did_not_override_it() -> None:
    """W1-F5. A campaign may be stricter than the Corpus Factory, never more permissive."""
    record = _load(SLICE)
    assert record["corpus_item"]["status"] == "quarantined"
    assert record["quarantined"] == ["physics-uniform-motion-layla"]
    assert record["compiled"] == []
    assert record["promoted"] == []
    assert record["citations"]["promoted_artifacts"] == 0
    # Nothing walked is not everything walked.
    assert record["citations"]["all_chains_resolve"] is False


def test_both_verdicts_on_the_passage_are_kept_not_just_the_outcome() -> None:
    both = _load(SLICE)["the_passage_passed_on_its_merits_and_was_refused_on_its_licence"]
    assert both["cross_check_accepted"] is True
    assert both["corpus_factory_accepted"] is False
    assert both["outcome"] == "quarantined"
    assert "opposite conclusions" in both["why_both_facts_are_kept"]


def test_the_licence_block_is_surfaced_with_an_owner_and_its_awkward_consequence() -> None:
    """W1-F6, including the part that makes the obvious fix the wrong one."""
    blocked = _load(SLICE)["blocked_by"]
    assert blocked["finding"] == "W1-F6"
    assert "gate owner" in blocked["owner"]
    assert "cycle 1" in blocked["blocks"]
    resolutions = blocked["candidate_resolutions"]
    assert len(resolutions) == 2
    approve = next(item for item in resolutions if "APPROVED_LICENSES" in item["resolution"])
    assert "deny the chemistry campaign" in approve["consequence"]
    assert "surface, not to absorb" in blocked["not_taken_by_this_wave"]


def test_the_two_licences_never_meet_in_the_physics_campaign() -> None:
    record = _load(SLICE)
    assert record["manifest"]["campaign_id"] == "s22c-physics"
    assert "science.chemistry" not in record["manifest"]["domain_ids"]
    assert "CC BY-NC-SA" in record["source"]["the_other_campaign_is_not_here"]


def test_what_the_real_source_had_that_the_fixture_did_not_is_recorded() -> None:
    """The findings W1 paid a passage for, held where deleting one fails."""
    record = _load(SLICE)
    found = " ".join(record["what_the_real_source_had_that_the_fixture_did_not"])
    assert "crosses a page boundary" in found
    assert "arithmetic is an image" in found
    assert "two precisions" in found
    assert "W1-F3" in found
    assert "W1-F5" in found and "W1-F6" in found

    passage = record["passage"]
    assert passage["crosses_a_page_boundary"] is True
    assert passage["the_arithmetic_is_an_image"] is True
    assert passage["page_furniture_inside_the_passage"]
    assert passage["end"] > passage["start"]
    assert len(passage["passage_sha256"]) == 64


def test_the_cross_check_agreed_on_a_number_written_two_ways() -> None:
    cross_check = _load(SLICE)["cross_check"]
    assert cross_check["asserted"]["exact_value"] == "110.4"
    assert cross_check["kernel_exact_value"] == "552/5"
    assert cross_check["assertion_agrees_with_kernel"] is True
    assert cross_check["accepted"] is True
    assert "not a tolerance" in cross_check["the_two_are_one_number"]


# --- W1-F3, pinned in the code rather than only in the record ------------------


def test_the_assertion_comparison_reads_numbers_and_not_notations() -> None:
    agrees, _ = assertion_agrees(
        {"exact_value": "110.4", "units": "m"}, {"exact_value": "552/5", "units": "m"}
    )
    assert agrees is True


def test_it_is_exact_equality_and_not_a_significant_figures_tolerance() -> None:
    """The passage's own rounded headline must still be refused."""
    agrees, why = assertion_agrees({"exact_value": "110"}, {"exact_value": "552/5"})
    assert agrees is False
    assert "110" in why


def test_a_boolean_is_never_compared_as_a_number() -> None:
    """`Fraction(True) == Fraction(1)`, and a plant must not pass through that door."""
    agrees, _ = assertion_agrees(
        {"structured": {"balanced": True}}, {"structured": {"balanced": 1}}
    )
    assert agrees is False
    agrees, _ = assertion_agrees(
        {"structured": {"balanced": True}}, {"structured": {"balanced": False}}
    )
    assert agrees is False


def test_a_campaign_may_be_stricter_than_the_factory_and_never_more_permissive() -> None:
    """W1-F5, pinned in the code: a refused item is quarantined whatever the evidence says."""
    import asyncio

    from campaign_22c import (
        CAMPAIGN_STAGES,
        CycleRunner,
        CycleState,
        all_segments,
        fixture_manifest,
        stage_quarantine,
    )

    first = all_segments()[0]
    state = CycleState(manifest=fixture_manifest(), segments=(first,))
    state.stages_completed = [stage.value for stage in CAMPAIGN_STAGES[:4]]
    state.corpus_items[first.segment_id] = {"status": "quarantined"}
    state.cross_checks[first.segment_id] = {"accepted": True}

    asyncio.run(stage_quarantine(CycleRunner(state), None, state))
    assert state.quarantined[first.segment_id] == "unclear_license"


def test_the_released_licence_allowlist_still_has_no_open_content_licence() -> None:
    """W1-F6, pinned at its source.

    This asserts that the defect is still there, which is the right shape for a finding
    surfaced to an owner rather than absorbed: when the gate owner decides, this test fails
    and the decision has to be recorded rather than slipped in. Delete it with the decision.
    """
    from cognitive_os.corpus.factory import APPROVED_LICENSES

    assert not any(name.startswith("CC-BY") for name in APPROVED_LICENSES)
    assert frozenset({"Apache-2.0", "MIT", "BSD-3-Clause", "CC0-1.0"}) == APPROVED_LICENSES


def test_the_licence_action_configuration_is_read_by_nothing() -> None:
    """W1-F6's second half: six settings that describe behaviour nothing consults.

    `CorpusConfiguration` offers `unknown_license_action` and five siblings, and
    `CorpusFactory._route` hard-codes the same outcomes instead of reading them. Today they
    agree, so nothing is wrong and nothing is honest either: an operator who set
    `unknown_license_action = 'reject'` would get a quarantine and no warning.
    """
    import inspect

    from cognitive_os.config.corpus_config import CorpusConfiguration
    from cognitive_os.corpus import factory

    actions = [name for name in CorpusConfiguration.model_fields if name.endswith("_action")]
    assert len(actions) == 6
    source = inspect.getsource(factory)
    assert not any(name in source for name in actions)


def test_a_value_that_is_not_a_number_still_compares_exactly() -> None:
    agrees, _ = assertion_agrees({"units": "m"}, {"units": "km"})
    assert agrees is False
    agrees, _ = assertion_agrees({"units": "N*m"}, {"units": "N*m"})
    assert agrees is True
