"""S21D4-043 and -044: the resolved holdout, read against what it claims to have executed.

A holdout record is the one place in a sprint where "declared" and "executed" are easiest to
confuse and most expensive to confuse. So these tests check the claims that separate the two:
that every baseline actually failed its hidden suite and every repair actually passed it, that
the pairs resolve out of the real store rather than out of this run's memory, and that the
integrity report refuses damage it has been handed on purpose.

The widened surface gets the same treatment. S21D4-040 could only estimate its effect
counterfactually, on a pool that predates the field; this is the pool the result is read from,
so the distinctness number here is the real one.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from cognitive_os.coding.reality_retrieval_specs_d4 import D4_RETRIEVAL_SPECS
from cognitive_os.domain.experience_graph import GRAPH_RESOURCE_POLICY_REVISION_2

REPOSITORY = Path(__file__).resolve().parents[3]
EVIDENCE = REPOSITORY / "docs/sprints/sprint-21/evidence"
PROJECTION = EVIDENCE / "sprint-21d4-retrieval-emg-projection.json"
QUERY_SET = EVIDENCE / "sprint-21d4-retrieval-query-set.json"
QUERIES = EVIDENCE / "sprint-21d4-retrieval-queries.json"
GRAPH_ROOT = EVIDENCE / "sprint-21d4-retrieval-emg-root.json"
PRE_REGISTRATION = EVIDENCE / "sprint-21d4-pre-registration.json"
SURFACE = EVIDENCE / "sprint-21d4-surface.json"

MINIMUM_QUERIES = 50


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _reproduces_its_seal(path: Path) -> bool:
    document = _load(path)
    body = {key: value for key, value in document.items() if key != "integrity_content_hash"}
    canonical = json.dumps(body, indent=1, sort_keys=True, ensure_ascii=False).encode("utf-8")
    return _sha256(canonical) == document["integrity_content_hash"]


def test_both_records_reproduce_their_integrity_hashes() -> None:
    assert _reproduces_its_seal(PROJECTION)
    assert _reproduces_its_seal(QUERY_SET)


def test_the_records_are_bound_to_the_inputs_they_rest_on() -> None:
    projection, query_set = _load(PROJECTION), _load(QUERY_SET)
    assert projection["pre_registration_sha256"] == _sha256(PRE_REGISTRATION.read_bytes())
    assert projection["surface_sha256"] == _sha256(SURFACE.read_bytes())
    assert query_set["projection_record_sha256"] == _sha256(PROJECTION.read_bytes())
    assert query_set["sha256"] == _sha256(QUERIES.read_bytes())
    assert projection["graph_set"]["root_sha256"] == _sha256(GRAPH_ROOT.read_bytes())
    for document in (projection, query_set):
        assert document["final_or_canary_outcomes_inspected"] == 0
        assert document["final_outcomes_inspected"] is False


def test_the_pool_shares_nothing_with_any_role_or_predecessor() -> None:
    """Separation runs before a single container starts, and all four lists must be empty."""
    separation = _load(PROJECTION)["separation"]
    assert separation["retrieval_groups"] == len(D4_RETRIEVAL_SPECS) == 60
    assert separation["retrieval_crossing_a_correction_role"] == []
    assert separation["task_signatures_reused_from_a_predecessor"] == []
    assert separation["query_ids_reused_from_a_predecessor"] == []
    assert separation["cross_group_near_clones"] == []
    assert separation["sealed_pool_hash"]
    assert separation["d4_seal_hash"]


def test_every_group_was_executed_rather_than_declared() -> None:
    """The claim the whole holdout rests on: a verifier refused this, then accepted that."""
    execution = _load(PROJECTION)["execution"]
    assert execution["executed_not_declared"] is True
    assert execution["groups_executed"] == execution["groups_requested"] == 60
    assert execution["baselines_that_failed_their_hidden_suite"] == 60
    assert execution["repairs_that_passed_their_hidden_suite"] == 60
    assert execution["campaign_version"] == 4
    assert execution["verifier_profile_hash"]


def test_every_pair_resolves_round_trips_and_stays_inside_its_bounds() -> None:
    projection = _load(PROJECTION)["projection"]
    assert projection["pairs"] == 60
    assert projection["source_resolution"] == 60
    assert projection["edit_path_round_trips"] == 60
    bounds = projection["bounds"]
    assert bounds["over_limit_graphs"] == 0
    assert bounds["max_nodes"] <= GRAPH_RESOURCE_POLICY_REVISION_2.nodes_per_graph
    assert bounds["declared"]["content_hash"] == GRAPH_RESOURCE_POLICY_REVISION_2.content_hash
    assert projection["creates_execution_or_correction_authority"] is False
    for row in projection["per_pair"]:
        assert row["round_trips"] is True
        assert row["source_hashes_resolved"] is True
        assert row["baseline_hidden_passed"] is False
        assert row["repair_hidden_passed"] is True
        assert row["graph_task_signature_names_the_family"] is False


def test_the_integrity_report_refuses_damage_it_was_handed() -> None:
    """An integrity report that has only ever seen intact evidence is an untested one."""
    refusals = _load(PROJECTION)["projection"]["seeded_refusals"]
    assert refusals["missing_bytes_refused"] is True
    assert refusals["broken_link_refused"] is True
    assert refusals["corrupt_bytes_refused"] is True
    assert refusals["all_three_refused"] is True


def test_the_stored_pair_set_resolves_out_of_the_real_store() -> None:
    graph_set = _load(PROJECTION)["graph_set"]
    assert graph_set["intact"] is True
    assert graph_set["resolved_pairs"] == graph_set["declared_pairs"] == 60
    assert graph_set["graph_set_id"] == "sprint-21d4-retrieval-holdout"
    assert "s21d4" in graph_set["artifact_root"]


def test_the_widened_surface_reached_this_pool_and_widened_it() -> None:
    """The number S21D4-040 could only estimate. D3 measured 1 distinct document of 60."""
    widened = _load(PROJECTION)["widened_surface"]
    assert widened["graphs"] == 120
    assert widened["terms_resolved_from_the_store"] is True
    assert widened["graphs_carrying_terms"] > 0
    discriminability = widened["discriminability"]
    assert discriminability["candidates"] == 60
    assert discriminability["d3_measured"] == 1
    # §S21D4-044 names this as its condition: greater than one, or the surface did not widen.
    assert discriminability["distinct_after_removing_domain_and_signature"] > 1


def test_the_two_sides_of_a_pair_are_two_documents() -> None:
    """A query and its answer that carry identical terms would be one document twice."""
    rows = _load(PROJECTION)["projection"]["per_pair"]
    differing = [
        row for row in rows if row["widened_surface"]["terms_differ_between_the_two_sides"]
    ]
    assert differing, "no pair's failed and repaired sides differ in their terms"
    for row in rows:
        assert row["widened_surface"]["patch_rehashed_from_the_store"] is True
        assert row["widened_surface"]["applied_to_the_executed_workspace"] is True


def test_the_queries_were_frozen_before_any_arm_existed() -> None:
    query_set = _load(QUERY_SET)
    assert query_set["frozen_before_any_arm_ran"] is True
    assert query_set["written_before_the_benchmark_subprocess_exists"] is True
    assert query_set["arms_can_read_judgements"] is False
    assert query_set["queries"] >= MINIMUM_QUERIES
    assert query_set["minimum_queries_met"] is True
    assert query_set["seen_task_queries"] == 0


def test_every_query_excludes_its_own_group() -> None:
    query_set = _load(QUERY_SET)
    assert query_set["every_query_excludes_its_own_group"] is True
    records = json.loads(QUERIES.read_text())
    assert len(records) == query_set["queries"]
    for record in records:
        own = record["query_id"].removeprefix("q:")
        assert record["excluded_groups"] == [own]
        assert own not in record["relevant_pair_ids"]
        assert record["relevant_pair_ids"]
        assert record["seen_task"] is False


def test_the_leak_guard_ran_over_the_widened_text_and_found_nothing() -> None:
    """The widened text is new surface, so the guard has more to read than it did in D3."""
    query_set = _load(QUERY_SET)
    assert query_set["leak_guard_ran_over_the_widened_text"] is True
    assert query_set["searchable_text_naming_its_own_judgement"] == []


def test_the_chance_baseline_is_recorded_beside_the_floors() -> None:
    """A floor is only a bar if the record says what nothing achieves."""
    baseline = _load(QUERY_SET)["chance_baseline"]
    assert 0 < baseline["recall_at_5"] < 1
    assert 0 < baseline["mrr_at_10"] < 1


def test_no_predecessor_store_was_written() -> None:
    stores = _load(PROJECTION)["predecessor_stores"]
    assert stores["unchanged"] is True
    assert stores["writes"] == 0
    assert set(stores["fingerprints_before"]) == {"artifacts-s21d1", "artifacts-s21d3"}
