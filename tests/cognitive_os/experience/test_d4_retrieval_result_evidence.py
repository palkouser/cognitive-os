"""S21D4-045 and -046: the holdout result and the decision the frozen floors produced.

A near miss is the most dangerous number in a sprint. `reciprocal_rank_fusion` clears the
recall floor and misses the MRR floor by 0.0089, which is exactly the distance at which a
fusion constant, a shortlist width or one more holdout member starts to look reasonable. So
these tests check the negative result *and* the things that make it trustworthy: that the
floors are the frozen ones, that nothing was reopened to reach them, and that the arms were
measured once against judgements written before they ran.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from cognitive_os.domain.experience_graph import GRAPH_RESOURCE_POLICY_REVISION_2_HASH
from cognitive_os.experience.graph_retrieval import GED_ITERATION_BUDGET

REPOSITORY = Path(__file__).resolve().parents[3]
EVIDENCE = REPOSITORY / "docs/sprints/sprint-21/evidence"
RESULT = EVIDENCE / "sprint-21d4-retrieval-holdout-result.json"
DECISION = EVIDENCE / "sprint-21d4-retrieval-decision.json"
QUERIES = EVIDENCE / "sprint-21d4-retrieval-queries.json"
GRAPH_ROOT = EVIDENCE / "sprint-21d4-retrieval-emg-root.json"
PROJECTION = EVIDENCE / "sprint-21d4-retrieval-emg-projection.json"
GED_DECISION = EVIDENCE / "sprint-21d4-ged-decision.json"

ARMS = (
    "no_memory",
    "exact_signature",
    "lexical",
    "minilm_vector",
    "minilm_shortlist_plus_bounded_ged",
    "reciprocal_rank_fusion",
)
RECALL_AT_5_FLOOR = 0.70
MRR_AT_10_FLOOR = 0.50


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
    assert _reproduces_its_seal(RESULT)
    assert _reproduces_its_seal(DECISION)


def test_the_result_is_bound_to_the_evidence_it_ranked() -> None:
    result = _load(RESULT)
    assert result["query_set_sha256"] == _sha256(QUERIES.read_bytes())
    assert result["graph_root_sha256"] == _sha256(GRAPH_ROOT.read_bytes())
    assert result["projection_record_sha256"] == _sha256(PROJECTION.read_bytes())
    assert result["ged_decision_sha256"] == _sha256(GED_DECISION.read_bytes())
    assert result["ged_iteration_budget"] == GED_ITERATION_BUDGET
    assert _load(DECISION)["holdout_result_sha256"] == _sha256(RESULT.read_bytes())


def test_every_arm_ran_once_and_reported_its_whole_metric_set() -> None:
    """§S21D4-045 lists them; a missing one is a metric nobody has to explain."""
    result = _load(RESULT)
    assert result["executions"] == 1
    assert result["reran_after_metrics_were_known"] is False
    assert set(result["arms"]) == set(ARMS)
    for arm in ARMS:
        row = result["arms"][arm]
        for metric in (
            "top_5_recall",
            "mrr_at_10",
            "ndcg_at_10",
            "coverage",
            "p50_latency_ms",
            "p95_latency_ms",
            "max_latency_ms",
            "timeouts",
            "budget_cutoffs",
            "mean_candidates_considered",
        ):
            assert metric in row, f"{arm} does not report {metric}"
        assert result["per_query"][arm]


def test_the_policy_model_and_reproducibility_are_all_recorded() -> None:
    benchmark = _load(RESULT)["benchmark"]
    assert benchmark["resource_policy"]["content_hash"] == GRAPH_RESOURCE_POLICY_REVISION_2_HASH
    assert benchmark["model"]["tree_digest"]
    assert benchmark["queries"] == 60
    assert benchmark["repeated_ranking_agreement"] is True
    assert all(benchmark["repeated_ranking_agreement_by_arm"][arm] for arm in ARMS)


def test_the_chance_baseline_sits_beside_the_arms() -> None:
    """Two arms score zero and one scores 0.75. Neither number means anything without this."""
    baseline = _load(RESULT)["chance_baseline"]
    assert baseline["recall_at_5"] > 0
    assert baseline["mrr_at_10"] > 0
    best = max(_load(RESULT)["arms"][arm]["top_5_recall"] for arm in ARMS)
    assert best > baseline["recall_at_5"], "no arm beat a uniformly random ranking"


def test_the_decision_is_the_frozen_rule_applied_to_the_recorded_numbers() -> None:
    decision = _load(DECISION)
    result = _load(RESULT)
    assert decision["immutable"] is True
    assert str(RECALL_AT_5_FLOOR) in decision["rule"]
    assert str(MRR_AT_10_FLOOR) in decision["rule"]
    for row in decision["trace"]:
        recorded = result["arms"][row["arm"]]
        assert row["recall_at_5"] == recorded["top_5_recall"]
        assert row["mrr_at_10"] == recorded["mrr_at_10"]
        assert row["recall_at_5_floor_met"] is (row["recall_at_5"] >= RECALL_AT_5_FLOOR)
        assert row["mrr_at_10_floor_met"] is (row["mrr_at_10"] >= MRR_AT_10_FLOOR)


def test_the_negative_result_is_recorded_with_the_floor_that_failed() -> None:
    """First-failure precedence: clearing one floor is a near miss, never a pass."""
    decision = _load(DECISION)
    assert decision["passed"] is False
    assert decision["winning_arm"] is None
    assert decision["negative_retrieval_result"] is True
    assert decision["first_failed_floor"] == "mrr_at_10"
    assert decision["stop_hash"]
    assert decision["gate_d1_condition_15"] == "remains_open"
    assert decision["gate_l2_condition_24"] == "not_met"


def test_the_arm_that_cleared_recall_is_still_not_a_pass() -> None:
    """The whole point of two floors: the best arm clears one of them."""
    trace = {row["arm"]: row for row in _load(DECISION)["trace"]}
    fusion = trace["reciprocal_rank_fusion"]
    assert fusion["recall_at_5_floor_met"] is True
    assert fusion["mrr_at_10_floor_met"] is False
    assert fusion["first_failed_floor"] == "mrr_at_10"
    assert fusion["within_budgets"] is True
    assert fusion["reproducible"] is True


def test_nothing_was_reopened_to_reach_the_floor() -> None:
    """A miss of 0.0089 is exactly where a fusion constant starts to look adjustable."""
    opened = _load(DECISION)["no_alternative_opened"]
    assert opened == {
        "fusion_variants": 0,
        "widths": 0,
        "weights": 0,
        "metrics": 0,
        "holdout_members_added": 0,
    }
    assert _load(DECISION)["minimum_queries_met"] is True


def test_the_advisory_boundary_still_has_to_be_proved() -> None:
    """A negative retrieval result is a reason to run S21D4-047, never a reason to skip it."""
    assert _load(DECISION)["s21d4_047_runs_on_every_outcome"] is True


def test_the_stop_binds_no_dependant_that_an_earlier_stop_already_bound() -> None:
    decision = _load(DECISION)
    assert decision["dependent_not_opened"] == []
    assert "S21D4-039" in decision["dependants_already_bound_to_an_earlier_stop"]
