"""S21D2-044, -045, -049: the rule, the threshold, and the two records that cannot be softened.

The grid and the rule are declared before any number exists, so what has to be tested is that
neither can be steered afterwards: that a setting cannot pass a safety check by refusing to
answer, that the threshold cannot be cleared by a rung that never beat the baseline, and that a
failure which says nothing about model capacity does not open a rung.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest

from cognitive_os.learning.correction_protocol import CorrectionEvaluatorManifest
from cognitive_os.learning.knn_calibration import (
    FROZEN_EMBEDDING_WEIGHT,
    CandidateSelection,
    ContinuationOutcome,
    CorrectionCalibration,
    FailureKind,
    MeasuredSetting,
    OodPrecheck,
    Setting,
    apply_selection_rule,
    decide_continuation,
    declared_grid,
    grid_hash,
    settings_hash_for,
)

AT = datetime(2026, 8, 2, 13, 0, tzinfo=UTC)
MANIFEST = CorrectionEvaluatorManifest()


def _precheck(*, errors: int = 0, abstained: int = 2) -> OodPrecheck:
    return OodPrecheck(
        submanifest_hash="a" * 64,
        resolved_set_hash="b" * 64,
        groups=10,
        decisions=40,
        abstained=abstained,
        confident_errors=errors,
    )


def _measured(
    setting: Setting,
    *,
    rate: str,
    coverage: str = "0.9",
    changed: int = 5,
    errors: int = 0,
    answered: int = 8,
    milliseconds: str = "10",
) -> MeasuredSetting:
    return MeasuredSetting(
        setting=setting,
        first_choice_rate=Decimal(rate),
        coverage=Decimal(coverage),
        changed_decisions=changed,
        confident_ood_errors=errors,
        ood_answered=answered,
        maximum_inference_ms=Decimal(milliseconds),
    )


def _calibration(
    results, *, selected: Setting | None, ood: OodPrecheck | None = None
) -> CorrectionCalibration:
    return CorrectionCalibration(
        grid_identity=grid_hash(),
        settings_attempted=len(results),
        calibration_matrix_hash="c" * 64,
        ladder_hash="d" * 64,
        baseline_rung="fixed_input_order",
        baseline_rate="0.3",
        results=results,
        ood=ood or _precheck(),
        selected_setting_identity=None if selected is None else selected.identity,
        selected_settings_hash=None if selected is None else settings_hash_for(selected),
        created_at=AT,
    )


class TestTheGridIsPreRegistered:
    def test_it_is_twenty_four_settings_and_stays_that_way(self) -> None:
        assert len(declared_grid()) == 24
        assert len({setting.identity for setting in declared_grid()}) == 24

    def test_the_channel_weighting_is_a_constant_rather_than_a_knob(self) -> None:
        """§4.4 freezes it before calibration, so it is not something the sweep searches."""
        assert {setting.embedding_weight for setting in declared_grid()} == {
            FROZEN_EMBEDDING_WEIGHT
        }

    def test_the_grid_has_an_identity_a_later_report_cannot_fake(self) -> None:
        assert grid_hash() == grid_hash()
        assert len(grid_hash()) == 64


class TestTheSelectionRuleCannotBeSatisfiedBySilence:
    def test_a_setting_that_answers_no_probe_is_filtered(self) -> None:
        """W6-F1: zero confident errors out of zero answers is not a pass."""
        grid = declared_grid()
        results, selected = apply_selection_rule(
            [_measured(grid[0], rate="0.9", answered=0)], manifest=MANIFEST
        )

        assert selected is None
        assert not results[0].eligible
        assert "skipped it" in str(results[0].ineligible_reason)

    def test_a_setting_that_changes_no_decision_is_filtered(self) -> None:
        grid = declared_grid()
        results, selected = apply_selection_rule(
            [_measured(grid[0], rate="0.9", changed=0)], manifest=MANIFEST
        )

        assert selected is None
        assert "another name" in str(results[0].ineligible_reason)

    def test_any_confident_ood_error_filters_the_setting(self) -> None:
        grid = declared_grid()
        results, selected = apply_selection_rule(
            [_measured(grid[0], rate="0.9", errors=1)], manifest=MANIFEST
        )

        assert selected is None
        assert "allows 0" in str(results[0].ineligible_reason)

    def test_exceeding_the_inference_budget_filters_the_setting(self) -> None:
        grid = declared_grid()
        results, selected = apply_selection_rule(
            [_measured(grid[0], rate="0.9", milliseconds="10000")], manifest=MANIFEST
        )

        assert selected is None
        assert "budget" in str(results[0].ineligible_reason)

    def test_every_attempted_setting_stays_in_the_record(self) -> None:
        """A report that showed only the winner would be a report about the winner."""
        grid = declared_grid()
        results, _ = apply_selection_rule(
            [
                _measured(grid[0], rate="0.9", errors=1),
                _measured(grid[1], rate="0.8"),
                _measured(grid[2], rate="0.4", changed=0),
            ],
            manifest=MANIFEST,
        )

        assert len(results) == 3
        assert [item.eligible for item in results] == [False, True, False]


class TestTheTieBreakIsAPropertyOfTheSetting:
    def test_the_highest_rate_wins(self) -> None:
        grid = declared_grid()
        _, selected = apply_selection_rule(
            [_measured(grid[3], rate="0.6"), _measured(grid[1], rate="0.8")], manifest=MANIFEST
        )

        assert selected == grid[1]

    def test_a_tie_goes_to_higher_coverage_then_smaller_k(self) -> None:
        grid = declared_grid()
        seven = next(setting for setting in grid if setting.k == 7)
        three = next(setting for setting in grid if setting.k == 3)
        _, selected = apply_selection_rule(
            [
                _measured(seven, rate="0.7", coverage="0.9"),
                _measured(three, rate="0.7", coverage="0.9"),
            ],
            manifest=MANIFEST,
        )

        assert selected == three

    def test_the_rule_refuses_an_empty_sweep(self) -> None:
        with pytest.raises(ValueError, match="at least one"):
            apply_selection_rule([], manifest=MANIFEST)


class TestTheContinuationThreshold:
    def test_a_rung_that_clears_both_floors_passes_and_stops(self) -> None:
        grid = declared_grid()
        results, selected = apply_selection_rule(
            [_measured(grid[0], rate="0.9")], manifest=MANIFEST
        )
        decision = decide_continuation(
            _calibration(results, selected=selected),
            manifest=MANIFEST,
            baseline=Decimal("0.3"),
            created_at=AT,
        )

        assert decision.outcome is ContinuationOutcome.PASS_AND_STOP
        assert decision.failure_kind is None
        assert decision.later_rungs_opened == ()

    def test_a_rung_that_matches_the_baseline_does_not_clear_it(self) -> None:
        grid = declared_grid()
        results, selected = apply_selection_rule(
            [_measured(grid[0], rate="0.3")], manifest=MANIFEST
        )
        decision = decide_continuation(
            _calibration(results, selected=selected),
            manifest=MANIFEST,
            baseline=Decimal("0.3"),
            created_at=AT,
        )

        assert decision.outcome is not ContinuationOutcome.PASS_AND_STOP
        assert decision.absolute_improvement == "0.0"

    def test_a_passing_rung_cannot_record_a_later_rung(self) -> None:
        with pytest.raises(ValueError, match="ends learner work"):
            _passing_decision(later_rungs_opened=("logistic",))

    def test_a_failing_rung_must_name_its_kind(self) -> None:
        with pytest.raises(ValueError, match="must name whether"):
            _passing_decision(outcome=ContinuationOutcome.FAIL_AND_STOP, failure_kind=None)


class TestWhichFailuresOpenALaterRung:
    def test_a_shape_problem_authorises_continuation(self) -> None:
        assert FailureKind.SIGNAL_IS_LINEAR.authorises_parametric_continuation
        assert FailureKind.SIGNAL_IS_NON_LINEAR.authorises_parametric_continuation

    def test_an_invariance_or_data_problem_does_not(self) -> None:
        """A parametric model on the same features faces the same perturbation."""
        assert not FailureKind.OOD_DEFICIENT.authorises_parametric_continuation
        assert not FailureKind.DATA_DEFICIENT.authorises_parametric_continuation
        assert not FailureKind.SIGNAL_ABSENT.authorises_parametric_continuation

    def test_an_ood_limited_sweep_stops_rather_than_continues(self) -> None:
        grid = declared_grid()
        results, selected = apply_selection_rule(
            [_measured(grid[0], rate="0.9", errors=1), _measured(grid[1], rate="0.3", answered=0)],
            manifest=MANIFEST,
        )
        decision = decide_continuation(
            _calibration(results, selected=selected, ood=_precheck(errors=1)),
            manifest=MANIFEST,
            baseline=Decimal("0.3"),
            residuals={"best_single_column_separation": Decimal("0.95")},
            created_at=AT,
        )

        assert selected is None
        assert decision.failure_kind is FailureKind.OOD_DEFICIENT
        assert decision.outcome is ContinuationOutcome.FAIL_AND_STOP
        assert decision.candidate_rate == "0.9"


class TestTheSelectionRecord:
    def test_a_null_must_name_the_rule_that_failed(self) -> None:
        with pytest.raises(ValueError, match="must name the continuation rule"):
            _selection(selected=False, null_reason=None)

    def test_a_selection_must_name_its_settings_and_datasets(self) -> None:
        with pytest.raises(ValueError, match="must name"):
            _selection(selected=True)

    def test_selection_never_authorises_final_access(self) -> None:
        with pytest.raises(ValueError, match="never opens the holdout"):
            _selection(selected=False, null_reason="the rung failed", authorises_final_access=True)

    def test_a_null_record_is_hash_bound_and_complete(self) -> None:
        record = _selection(selected=False, null_reason="the rung failed OOD")

        assert record.content_hash
        assert record.authorises_final_access is False


def _passing_decision(**overrides):  # type: ignore[no-untyped-def]
    from cognitive_os.learning.knn_calibration import ContinuationDecision

    payload = {
        "outcome": ContinuationOutcome.PASS_AND_STOP,
        "calibration_hash": "e" * 64,
        "baseline_rate": "0.3",
        "candidate_rate": "0.9",
        "minimum_absolute_improvement": "0.05",
        "minimum_relative_error_reduction": "0.20",
        "reason": "cleared both floors",
        "created_at": AT,
    }
    payload.update(overrides)
    return ContinuationDecision(**payload)


def _selection(**overrides):  # type: ignore[no-untyped-def]
    payload = {
        "selected": False,
        "feature_contract_hash": "a" * 64,
        "fitted_feature_report_hash": "b" * 64,
        "baseline_rung": "fixed_input_order",
        "baseline_rate": "0.3",
        "continuation_hash": "c" * 64,
        "null_reason": "the rung failed",
        "created_at": AT,
    }
    payload.update(overrides)
    return CandidateSelection(**payload)
