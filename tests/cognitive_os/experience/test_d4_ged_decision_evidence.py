"""S21D4-041: the comparator decision, and the three measurements it is allowed to rest on.

A decision record is the easiest place to write "we chose A" and the hardest place to check
it. So the tests here refuse the conclusion unless the evidence under it holds: the clock has
to be shown deciding the score, the budget has to be shown reproducing itself, and the budget
number has to be shown following from cost rather than from taste.
"""

from __future__ import annotations

import hashlib
import json
from itertools import pairwise
from pathlib import Path
from typing import Any

from cognitive_os.domain.experience_graph import (
    GRAPH_RESOURCE_POLICY_REVISION_2,
    GRAPH_RESOURCE_POLICY_REVISION_2_HASH,
)
from cognitive_os.experience.graph_retrieval import GED_ITERATION_BUDGET

REPOSITORY = Path(__file__).resolve().parents[3]
EVIDENCE = REPOSITORY / "docs/sprints/sprint-21/evidence"
DECISION = EVIDENCE / "sprint-21d4-ged-decision.json"
PRE_REGISTRATION = EVIDENCE / "sprint-21d4-pre-registration.json"


def _load() -> dict[str, Any]:
    return json.loads(DECISION.read_text())


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def test_the_record_reproduces_its_integrity_hash() -> None:
    document = _load()
    body = {key: value for key, value in document.items() if key != "integrity_content_hash"}
    canonical = json.dumps(body, indent=1, sort_keys=True, ensure_ascii=False).encode("utf-8")
    assert _sha256(canonical) == document["integrity_content_hash"]
    assert document["pre_registration_sha256"] == _sha256(PRE_REGISTRATION.read_bytes())


def test_the_decision_is_the_one_the_code_runs() -> None:
    """A decision that names a budget the arm does not use decides nothing."""
    decision = _load()["decision"]
    assert decision["outcome"] == "deterministic_budget"
    assert decision["option"] == "a"
    assert decision["budget"] == GED_ITERATION_BUDGET == 1
    assert decision["immutable"] is True


def test_the_wall_clock_was_shown_to_decide_the_score() -> None:
    """Option B's premise, executed. Without this the choice is a preference."""
    instability = _load()["wall_clock_instability"]
    assert instability["the_clock_decides_the_score"] is True
    assert instability["pairs_whose_value_depends_on_the_clock"]
    for row in instability["per_pair"]:
        fast, slow = (str(value) for value in instability["timeouts_ms"])
        assert fast in row and slow in row


def test_the_budget_reproduced_itself_on_every_stored_pair() -> None:
    """The frozen criterion: two identical passes agree byte for byte."""
    determinism = _load()["fixed_budget_determinism"]
    assert determinism["passes"] == 2
    assert determinism["comparisons"] == 140
    assert determinism["agreement"] == 1.0
    assert determinism["pairs_that_disagreed_between_passes"] == []
    assert determinism["unscored_pairs"] == []


def test_the_budget_number_follows_from_cost_and_not_from_a_ranking() -> None:
    """Each further distance costs more than every previous one together."""
    profile = _load()["yield_cost_profile"]
    elapsed = [row["elapsed_ms"] for row in profile["profile"]]
    assert len(elapsed) >= 2
    assert all(later > earlier for earlier, later in pairwise(elapsed))
    assert profile["yields_reached"] < profile["probe_ceiling_yields"], (
        "a profile that reached its yield ceiling would not show the search failing to finish"
    )
    assert "time ceiling" in profile["stopped_by"]


def test_the_frozen_policy_was_checked_and_not_changed() -> None:
    policy = _load()["frozen_policy"]
    assert policy["policy_hash"] == GRAPH_RESOURCE_POLICY_REVISION_2_HASH
    assert policy["policy_is_frozen_and_unchanged"] is True
    assert (
        policy["per_pair_allowance_ms"] == GRAPH_RESOURCE_POLICY_REVISION_2.per_pair_ged_timeout_ms
    )
    assert policy["shortlist"] == GRAPH_RESOURCE_POLICY_REVISION_2.vector_shortlist
    assert policy["inside_the_per_pair_allowance"] is True
    assert policy["inside_the_query_budget"] is True


def test_the_one_off_warm_up_cost_is_reported_rather_than_warmed_away() -> None:
    """The steady-state figure is the honest one only if the other one is beside it."""
    policy = _load()["frozen_policy"]
    determinism = _load()["fixed_budget_determinism"]
    assert policy["first_comparison_of_the_process_ms"] > policy["worst_measured_steady_state_ms"]
    assert policy["first_comparison_exceeds_the_allowance"] is True
    assert policy["first_comparison_reading"]
    assert determinism["the_maximum_is_the_first_comparison"] is True


def test_the_predecessor_numbers_stay_irreproducible() -> None:
    """Nothing is back-filled: a deterministic comparator cannot reconstruct a clock's answer."""
    predecessors = _load()["predecessor_numbers"]
    assert predecessors["d1_d2_d3_for_this_arm"] == "irreproducible"
    assert predecessors["back_filled"] is False
    assert predecessors["recomputed"] is False


def test_the_decision_read_no_holdout_and_gates_nothing() -> None:
    document = _load()
    assert document["label"] == "development_only"
    assert document["gating"] is False
    assert document["measured_on"]["d4_retrieval_pool_read"] is False
    assert document["measured_on"]["access"] == "read_only"
    assert document["final_or_canary_outcomes_inspected"] == 0
