"""Sprint 22C W2. What cycle 1 claims, read back out of its own sealed records.

These tests need no database and no provider. They read the records the wave sealed and
assert the claims the execution log makes about them, so a later edit that improves a number
has to change a test that says what the number meant.

The wave's headline is a *negative* — one worked example in eighteen survived a governed
acquisition pipeline — and negatives are exactly the numbers that quietly improve when nobody
is pinning them.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

EVIDENCE = Path("docs/sprints/sprint-22/evidence")
CHAPTER = EVIDENCE / "sprint-22c-w2-chapter.json"
CYCLE = EVIDENCE / "sprint-22c-w2-cycle1.json"
RETAINED = EVIDENCE / "sprint-22c-w2-retained-cases.json"
PROPOSALS = EVIDENCE / "sprint-22c-w2-proposals"


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def chapter() -> dict[str, Any]:
    return _load(CHAPTER)


@pytest.fixture(scope="module")
def cycle() -> dict[str, Any]:
    return _load(CYCLE)


# --- the inventory ----------------------------------------------------------


def test_the_inventory_covers_the_three_chapters_the_rights_record_named(
    chapter,
) -> None:
    assert [item["number"] for item in chapter["chapters"]] == [2, 4, 6]
    assert [item["chosen_for"] for item in chapter["chapters"]] == [
        "mechanics.uniform-motion",
        "mechanics.statics-equilibrium",
        "mechanics.moment-balance",
    ]
    assert all(item["body_is_one_chapter"] for item in chapter["chapters"])
    assert all(item["review_declares_itself_review"] for item in chapter["chapters"])


def test_every_passage_is_located_by_the_same_rule(chapter) -> None:
    assert chapter["counts"]["worked_examples_in_the_bodies"] == 18
    assert chapter["counts"]["per_chapter"] == {"2": 9, "4": 3, "6": 6}
    assert len(chapter["passages"]) == 18
    assert len({item["passage_id"] for item in chapter["passages"]}) == 18
    # The rule is the book's own layout, and the record says so rather than carrying offsets.
    assert chapter["location_rule"]["marker"] == "WORKED EXAMPLE"
    assert "character offset" in chapter["location_rule"]["never"]


def test_the_real_source_still_interleaves_page_furniture(chapter) -> None:
    """W1's finding, at chapter scale: six of eighteen cross a page break, bytes kept."""
    assert chapter["counts"]["crossing_a_page_boundary"] == 6
    assert "cannot" in chapter["location_rule"]["bytes_are_kept"]


# --- the extraction ---------------------------------------------------------


def test_every_passage_has_a_sealed_proposal() -> None:
    identifiers = {item["passage_id"] for item in _load(CHAPTER)["passages"]}
    sealed = {path.stem for path in PROPOSALS.glob("*.json")}
    assert sealed == identifiers


def test_the_cycle_made_no_provider_call_and_every_answer_was_sealed(cycle) -> None:
    extraction = cycle["extraction"]
    assert extraction["provider_calls_this_run"] == 0
    assert extraction["every_answer_came_from_a_sealed_proposal"] is True
    assert extraction["replayed_through_the_released_provider_path"] is True
    assert extraction["origin_provider"] == ["claude-code"]
    assert len(extraction["receipts"]) == 18


def test_every_receipt_carries_the_three_hashes_replay_needs(cycle) -> None:
    for passage_id, receipt in cycle["extraction"]["receipts"].items():
        assert len(receipt["request_hash"]) == 64, passage_id
        assert len(receipt["normalized_response_hash"]) == 64, passage_id
        assert len(receipt["sealed_fixture_sha256"]) == 64, passage_id
        assert receipt["rights_decision"] == "verified", passage_id


# --- the yield, which is the wave's headline --------------------------------


def test_the_acquisition_yield_is_one_worked_example_in_eighteen(cycle) -> None:
    measured = cycle["yield"]
    assert measured["worked_examples_located"] == 18
    assert measured["formalised_by_the_provider"] == 1
    assert measured["accepted_by_the_kernel"] == 1
    assert measured["promoted"] == 1
    assert measured["quarantined"] == 17
    assert measured["acquisition_yield"] == pytest.approx(1 / 18, abs=1e-6)


def test_the_binding_constraint_is_the_domain_not_the_source(cycle) -> None:
    """Sixteen of seventeen refusals are 'no registered problem type'. W2-F1."""
    reasons = cycle["yield"]["refusal_reasons"]
    assert reasons["no_registered_problem_type"] == 16
    assert reasons["no_readable_result"] == 1
    assert sum(reasons.values()) == 17


def test_the_two_chapters_chosen_for_the_other_problem_types_yielded_nothing(
    cycle,
) -> None:
    """S22C-020 named chapters 4 and 6 for statics and moments; neither produced a case."""
    per_chapter = cycle["yield"]["per_chapter"]
    assert per_chapter["4"]["worked_examples"] == 3
    assert per_chapter["4"]["promoted"] == 0
    assert per_chapter["6"]["worked_examples"] == 6
    assert per_chapter["6"]["promoted"] == 0
    assert per_chapter["2"]["promoted"] == 1


# --- the nine stages, the replay, the citations ------------------------------


def test_the_cycle_completed_nine_stages_in_order_on_the_campaign_store(cycle) -> None:
    assert cycle["stages"]["count"] == 9
    assert cycle["stages"]["all_nine_in_order"] is True
    assert cycle["store"]["kind"] == "postgresql"
    assert cycle["store"]["database"] == "cognitive_os_s22c_campaign"


def test_the_replay_enumerates_every_domain_and_executes_the_retained_cases(
    cycle,
) -> None:
    replay = cycle["evaluate"]
    assert replay["enumeration_source"] == "registry.domain_ids()"
    assert replay["domains_enumerated"] == 6
    # W0-A1, unchanged and still true: four of six retain nothing, and the record says 0
    # rather than omitting them.
    assert replay["domains_with_retained_cases"] == 1
    assert sum(1 for item in replay["per_domain"].values() if item["cases"] == 0) == 5
    assert replay["all_retained_cases_passed"] is True


def test_the_holdout_is_the_frozen_one_and_nothing_leaked(cycle) -> None:
    assert (
        cycle["manifest"]["holdout_id"] == _load(EVIDENCE / "sprint-22c-holdout.json")["holdout_id"]
    )
    assert cycle["manifest"]["holdout_measured_values"] == 0
    leakage = cycle["evaluate"]["source_leakage"]
    assert leakage["leakage_detected"] is False
    assert leakage["curriculum_segments"] == 18
    assert leakage["holdout_store_env"] == ["COGOS_HOLDOUT_DATABASE_URL"]


def test_every_promoted_artifact_was_walked_back_to_loaded_source_bytes(cycle) -> None:
    citations = cycle["citations"]
    assert citations["promoted_artifacts"] == citations["artifacts_walked"] == 1
    assert citations["walk_covers_every_promoted_artifact"] is True
    assert citations["all_chains_resolve"] is True
    assert citations["sampled"] is False
    hops = next(iter(citations["per_artifact"].values()))["hops"]
    assert [hop["hop"] for hop in hops] == [
        "memory_provenance -> artifact_bytes",
        "artifact -> corpus_item",
        "corpus_item -> source_manifest",
        "source_manifest -> registered_source_bytes",
    ]


# --- the supersession -------------------------------------------------------


def test_the_supersession_ran_the_released_lifecycle_end_to_end(cycle) -> None:
    lifecycle = cycle["supersession"]["lifecycle"]
    assert lifecycle["candidate_to_verified_to_superseded"] == [
        "proposed",
        "supported",
        "superseded",
    ]
    assert lifecycle["predecessor_belief_status"] == "superseded"
    assert lifecycle["successor_belief_status"] == "supported"
    assert lifecycle["promotion"]["outcome"] == "supported"


def test_the_supersession_is_verified_two_ways_that_agree(cycle) -> None:
    verified = cycle["supersession"]["verified_two_ways"]
    assert verified["the_two_agree"] is True
    assert len(verified["way_one_active_view_queried"]) == 1
    assert len(verified["way_two_supersession_chain_walked"]) == 1
    edge = verified["way_two_supersession_chain_walked"][0]
    assert edge["relation"] == "supersedes"
    # The active view holds exactly what the chain says replaced the predecessor.
    assert verified["way_one_active_view_queried"] == [edge["source"]]


def test_history_survives_with_its_citations_intact(cycle) -> None:
    history = cycle["supersession"]["history_survives"]
    assert history["revision_1_loadable"] is True
    assert history["revision_2_loadable"] is True
    assert history["revision_3_loadable"] is True
    assert history["revision_2_citations_still_resolve_to_loaded_bytes"] is True
    assert history["no_row_was_deleted"] is True
    assert history["revisions_after"] == 3


def test_the_event_stream_carries_the_full_transition_sequence(cycle) -> None:
    stream = cycle["supersession"]["event_stream"]
    assert stream["full_transition_sequence_present"] is True
    assert stream["predecessor_events"] == [
        "semantic.claim_created",
        "semantic.claim_belief_changed",
        "semantic.claim_belief_changed",
    ]


def test_the_predecessor_and_successor_cite_the_same_source_bytes(cycle) -> None:
    """The source did not change; the campaign's reading of it did."""
    what = cycle["supersession"]["what_superseded_what"]
    assert what["the_source_did_not_change"] is True
    assert what["both_cite_the_same_registered_bytes"] is True
    assert what["predecessor_carried"].startswith("the statement the provider read")
    assert "kernel computed" in what["successor_carries"]


def test_the_temporal_boundary_is_recorded_as_the_mechanism(cycle) -> None:
    boundary = cycle["supersession"]["the_temporal_boundary"]
    assert boundary["predecessor_valid_to"] == boundary["successor_valid_from"]
    assert boundary["intervals_are_half_open_so_they_abut_without_overlapping"] is True
    assert "ignores belief status" in boundary["why_it_is_required"]


# --- what cycles 2 and 3 inherit --------------------------------------------


def test_the_retained_cases_are_sealed_for_the_later_cycles() -> None:
    retained = _load(RETAINED)
    assert retained["count"] == 1
    case = retained["cases"][0]
    assert case["domain_id"] == "engineering.mechanics"
    assert case["problem_type"] == "mechanics.uniform-motion"
    assert case["retained_by_cycle"] == 1
    assert len(case["source_segment_hash"]) == 64


def test_the_subject_rule_change_is_recorded_as_unexercised(cycle) -> None:
    """W2-A1. One formalised segment cannot collide, and the record refuses to claim it did."""
    rule = cycle["subject_rule"]
    assert rule["formalised_segments"] == 1
    assert rule["segments_that_would_have_collided"] == 0
    assert rule["exercised_by_this_cycle"] is False
    assert "latent here" in rule["why_the_rule_changed_anyway"]


def test_the_cycle_decides_no_exit_criterion(cycle) -> None:
    assert cycle["decides_an_exit_criterion"] is False
    assert cycle["cycle"] == 1
    assert len(cycle["limitations"]) >= 4
