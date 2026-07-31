"""The D1 surface audit, leakage validator and triage evidence, as executable checks.

These started as `__main__` self-checks inside the modules. Bandit refuses `assert` in
`src/`, and the repository is right to: an assert compiled away under -O is not a check.
They live here instead, where they run in CI on every push.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from cognitive_os.domain.learned import SurfaceActionCostMatrix, SurfaceDisposition
from cognitive_os.learning import surfaces
from cognitive_os.learning.leakage import (
    FIELD_TIMING,
    FORBIDDEN_IN_QUERY,
    allowlisted_query_fields,
    duplicate_identities,
    validate_query_projection,
)
from cognitive_os.learning.triage_evidence import (
    correctness_vector,
    ladder,
    load_outcomes,
    oracle_free_population,
    paired_bootstrap,
    residual_headroom,
    strategy_oracle,
)


class TestSurfaceAudit:
    def test_no_c3_surface_clears_the_primary_thresholds(self) -> None:
        """The measured negative result. If this ever passes, D1's selection must be redone."""
        assert surfaces.surfaces_meeting_primary_thresholds() == ()

    def test_dispositions_match_the_measured_evidence(self) -> None:
        assert surfaces.OUTCOME_TRIAGE.disposition is SurfaceDisposition.REJECTED
        assert surfaces.STRATEGY_SELECTION.disposition is SurfaceDisposition.REJECTED
        assert surfaces.CORRECTION_CONTEXT.disposition is SurfaceDisposition.SELECTED_SECONDARY
        assert surfaces.CORRECTION_RANKING.disposition is SurfaceDisposition.DEFERRED

    def test_correction_ranking_is_the_only_balanced_candidate(self) -> None:
        assert not surfaces.CORRECTION_RANKING.degenerate
        assert surfaces.STRATEGY_SELECTION.changeable_decision_count == 0

    def test_the_selection_records_an_absent_primary_with_its_reason(self) -> None:
        decision = surfaces.selection_decision()
        assert decision.primary_surface is None
        assert decision.primary_unavailable_reason
        assert decision.secondary_surface == "experience.correction_context"

    def test_the_selection_replays_to_the_same_hash(self) -> None:
        assert (
            surfaces.selection_decision().content_hash == surfaces.selection_decision().content_hash
        )

    def test_a_cost_matrix_that_rewards_skipping_verification_is_refused(self) -> None:
        with pytest.raises(ValueError, match="cannot cost less"):
            SurfaceActionCostMatrix(
                surface="x",
                verify_now_when_accepted=Decimal("1"),
                verify_now_when_rejected=Decimal("5"),
                request_repair_when_accepted=Decimal("1"),
                request_repair_when_rejected=Decimal("5"),
                abstain_when_accepted=Decimal("0"),
                abstain_when_rejected=Decimal("0"),
            )


class TestLeakageValidator:
    def test_a_clean_pre_outcome_projection_passes(self) -> None:
        clean = {
            "task_id": "cc11c841-5a71-4cfb-97f3-db241f780836",
            "problem_domain": "logic",
            "failure_classification": "wrong_answer",
        }
        assert validate_query_projection(clean, query_group="g1", candidate_group="g2") == ()

    def test_every_refusal_has_its_own_reason_code(self) -> None:
        findings = validate_query_projection(
            {
                "task_id": "/home/palkouser/projekt/x",
                "candidate_strategy": "correct_narrow",
                "final_status": "accepted",
                "invented_field": "whatever",
                "problem_domain": "authorization: Bearer abc",
            },
            query_group="g1",
            candidate_group="g1",
            control_tokens=("deadbeef",),
        )
        assert {finding.reason for finding in findings} == {
            "host_path_present",
            "answer_revealing_field",
            "post_outcome_field",
            "unknown_field_timing",
            "credential_marker_present",
            "same_group_crossing",
        }

    def test_the_measured_oracle_is_forbidden_in_a_query(self) -> None:
        assert "candidate_strategy" in FORBIDDEN_IN_QUERY

    def test_the_allowlist_is_declared_not_defaulted(self) -> None:
        assert len(allowlisted_query_fields()) == 13
        assert len(FIELD_TIMING) == 21

    def test_duplicate_identities_are_reported(self) -> None:
        assert duplicate_identities(("a", "b", "a", "c", "b")) == ("a", "b")


class TestTriageEvidence:
    def test_the_canonical_view_is_214_unique_outcomes(self) -> None:
        outcomes = load_outcomes()
        assert len(outcomes) == 214
        assert len({item.outcome_id for item in outcomes}) == 214

    def test_the_two_populations_reconcile_to_the_released_denominator(self) -> None:
        outcomes = load_outcomes()
        coding = [o for o in outcomes if o.population == "coding"]
        benchmark = [o for o in outcomes if o.population == "benchmark"]
        assert (len(coding), len(benchmark)) == (150, 64)
        assert sum(o.accepted for o in benchmark) == 64, "the benchmark half is single class"

    def test_the_strategy_field_is_a_perfect_oracle(self) -> None:
        coding = [o for o in load_outcomes() if o.population == "coding"]
        assert strategy_oracle(coding).score == Decimal("1.0000")

    def test_no_rung_beats_a_coin_flip_once_the_oracles_are_removed(self) -> None:
        residual = residual_headroom(load_outcomes())
        assert residual["coding"]["count"] == 120
        assert residual["coding"]["accepted"] == 60
        assert residual["coding"]["strongest_score"] == "0.5000"
        assert residual["coding"]["grouped_frequency_score"] == "0.0000"
        assert residual["benchmark"]["single_class"] is True

    def test_dropping_the_baselines_leaves_only_candidate_runs(self) -> None:
        assert all(o.run_kind != "baseline" for o in oracle_free_population(load_outcomes()))

    def test_the_full_ladder_records_every_rung(self) -> None:
        rungs = ladder(load_outcomes(), split="all-214").rungs
        assert [rung.name for rung in rungs] == [
            "always_verify_now",
            "majority[accepted]",
            "visible_contract[run_kind]",
            "grouped_frequency[leave_one_out]",
        ]

    def test_the_paired_bootstrap_is_deterministic_and_ordered(self) -> None:
        outcomes = load_outcomes()
        left = correctness_vector([False] * len(outcomes), outcomes)
        right = correctness_vector([True] * len(outcomes), outcomes)
        lower, point, upper = paired_bootstrap(left, right)
        assert lower <= point <= upper
        assert paired_bootstrap(left, right) == (lower, point, upper)

    def test_a_mismatched_pair_of_score_vectors_is_refused(self) -> None:
        with pytest.raises(ValueError, match="equally sized"):
            paired_bootstrap((True, False), (True,))
