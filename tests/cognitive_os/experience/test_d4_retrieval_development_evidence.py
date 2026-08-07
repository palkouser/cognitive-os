"""S21D4-042: the development replay, read against what it predicted before it ran.

A replay that reports "everything reproduced" is only informative if something could have
failed to. Two things could here: an unchanged arm could have moved, which would mean W3
disturbed something it never touched, and the changed arm could have stayed unstable, which
would mean the comparator decision fixed nothing. The tests check both directions.
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
DEVELOPMENT = EVIDENCE / "sprint-21d4-retrieval-development.json"
PRE_REGISTRATION = EVIDENCE / "sprint-21d4-pre-registration.json"
SURFACE = EVIDENCE / "sprint-21d4-surface.json"
GED_DECISION = EVIDENCE / "sprint-21d4-ged-decision.json"

POOLS = ("d1_eighty_query_development_set", "d3_spent_retrieval_holdout")
CHANGED_ARM = "minilm_shortlist_plus_bounded_ged"


def _load() -> dict[str, Any]:
    return json.loads(DEVELOPMENT.read_text())


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def test_the_record_reproduces_its_integrity_hash_and_its_inputs() -> None:
    document = _load()
    body = {key: value for key, value in document.items() if key != "integrity_content_hash"}
    canonical = json.dumps(body, indent=1, sort_keys=True, ensure_ascii=False).encode("utf-8")
    assert _sha256(canonical) == document["integrity_content_hash"]
    assert document["pre_registration_sha256"] == _sha256(PRE_REGISTRATION.read_bytes())
    assert document["surface_sha256"] == _sha256(SURFACE.read_bytes())
    assert document["ged_decision_sha256"] == _sha256(GED_DECISION.read_bytes())


def test_both_development_sets_were_replayed() -> None:
    pools = _load()["pools"]
    assert set(pools) == set(POOLS)
    for name in POOLS:
        pool = pools[name]
        assert pool["access"] == "read_only"
        assert pool["resource_policy"]["content_hash"] == GRAPH_RESOURCE_POLICY_REVISION_2_HASH
        assert pool["query_set"]["queries"] >= 60
        assert pool["graph_set"]["intact"] is True


def test_no_arm_that_w3_did_not_change_moved() -> None:
    """The whole point of a development replay: the blast radius is the one arm it should be."""
    document = _load()
    assert document["every_unchanged_arm_reproduced"] is True
    for name in POOLS:
        comparison = document["pools"][name]["against_the_predecessor"]
        assert comparison["unchanged_arms_that_moved"] == []
        for arm, row in comparison["per_arm"].items():
            if arm != CHANGED_ARM:
                assert row["reproduced"] is True, f"{arm} moved on {name}"


def test_the_changed_arm_now_reproduces_its_own_ranking() -> None:
    """S21D3-042 recorded it disagreeing with itself across two passes of one run."""
    document = _load()
    assert document["every_arm_reproduces_its_own_ranking"] is True
    d1 = document["pools"]["d1_eighty_query_development_set"]["repeated_ranking_agreement"]
    assert d1["the_changed_arm_did_not_before"] is True
    assert d1["the_changed_arm_now_reproduces_itself"] is True
    assert d1["arms_that_do_not_reproduce_their_own_ranking"] == []
    assert d1["recorded"][CHANGED_ARM] is False


def test_the_changed_arm_moved_only_where_the_clock_was_biting() -> None:
    """It reproduces D3's published numbers exactly and moves on D1. Both halves matter.

    The D3 graphs are five nodes, so the anytime search converged and the wall clock never
    decided anything; the D1 graphs reach thirty, so it did. An arm that had moved on both
    would have been a comparator change nobody could attribute.
    """
    pools = _load()["pools"]
    assert (
        pools["d3_spent_retrieval_holdout"]["against_the_predecessor"]["the_changed_arm_moved"]
        is False
    )
    assert (
        pools["d1_eighty_query_development_set"]["against_the_predecessor"]["the_changed_arm_moved"]
        is True
    )


def test_the_widened_surface_contributed_nothing_here_and_says_so() -> None:
    """Stored graphs predate the field. A replay claiming a widening would be claiming a lie."""
    pools = _load()["pools"]
    for name in POOLS:
        widened = pools[name]["widened_surface"]
        assert widened["graphs"] > 0
        assert widened["graphs_carrying_terms"] == 0
        assert widened["reading"]


def test_timeouts_and_budget_cutoffs_are_reported_apart() -> None:
    """§S21D4-042 requires them separate: one is a comparison, the other is a query budget."""
    pools = _load()["pools"]
    for name in POOLS:
        for arm in pools[name]["arms"].values():
            assert "timeouts" in arm and "budget_cutoffs" in arm
            assert arm["timeouts"] == 0
            assert arm["budget_cutoffs"] == 0


def test_the_replay_gates_nothing_and_wrote_nothing() -> None:
    document = _load()
    assert document["label"] == "development_only"
    assert document["gating"] is False
    assert document["d4_retrieval_pool_read"] is False
    assert document["ged_iteration_budget"] == GED_ITERATION_BUDGET
    assert document["store_writes"]["unchanged"] is True
    assert document["final_or_canary_outcomes_inspected"] == 0
