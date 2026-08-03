"""S21D2-044, -045, -049: calibrate the k-NN, decide whether to continue, freeze one candidate.

Three things are declared here *before* any calibration number exists, because each of them is
a place where a result could otherwise choose its own criterion.

*The grid.* Twenty-four settings, written as a literal. §4.6 permits a small pre-registered grid
and forbids an optimizer; a grid that could grow after a disappointing sweep is an optimizer
with extra steps. `embedding_weight` is deliberately absent: §4.4 freezes the channel weighting
*before* calibration, so it is a constant here rather than a knob.

*The selection rule.* Filter, then maximise, then break ties deterministically:

1. a setting that never changes a decision is refused — it is the baseline wearing a model's
   name, and `coverage_is_a_calibration_selection_criterion` exists precisely so a learner
   cannot pass every safety metric by abstaining everywhere;
2. a setting that answers no out-of-distribution probe is refused for the same reason. It has
   not passed the OOD check, it has skipped it, and the first sweep of this grid found four
   settings doing exactly that — abstaining on all ten probes and thereby recording zero
   confident errors. The manifest states the principle for calibration coverage; a rule that
   applied it there and not to the probe would let a safety check be satisfied by silence;
3. a setting with any confident out-of-distribution error is refused, because
   `promotion_confident_ood_errors_allowed` is zero;
4. a setting over the per-task inference budget is refused;
5. among the survivors, the highest first-choice rate wins; ties go to higher coverage, then to
   smaller `k`, then to grid order. Every tie-break is a property of the setting, never of the
   result, so the rule cannot be steered by what the sweep happened to produce.

*The continuation threshold.* The selected setting must beat the strongest non-learned rung by
at least `minimum_absolute_improvement` and reduce the residual error by at least
`minimum_relative_error_reduction`, both taken from the frozen evaluator manifest. Nothing here
may lower either one: a rung that fails continues down the ladder, and the ladder ending is a
null, not a relaxed threshold.

Every attempted setting stays in the record whether it was selected, filtered or beaten. A
calibration report that showed only the winner would be a report about the winner.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from hashlib import sha256
from itertools import product

from pydantic import Field

from cognitive_os.domain.common import NonEmptyStr, Sha256Hex, UtcDatetime
from cognitive_os.domain.experience import HashedExperienceContract
from cognitive_os.learning.correction_protocol import CorrectionEvaluatorManifest

#: The pre-registered grid, as a literal. Twenty-four settings across four calibrated
#: quantities; `embedding_weight` is frozen at the value §4.4 fixed before calibration.
GRID_K: tuple[int, ...] = (3, 5, 7)
GRID_SIMILARITY_FLOOR: tuple[str, ...] = ("0.30", "0.50")
GRID_AGREEMENT_FLOOR: tuple[str, ...] = ("0.60", "0.80")
GRID_CONFIDENCE_FLOOR: tuple[str, ...] = ("0.55", "0.70")
FROZEN_EMBEDDING_WEIGHT = Decimal("0.7")

SELECTION_RULE = (
    "filter settings that change no decision, that answer no out-of-distribution probe, that "
    "produce any confident OOD error, or that exceed the per-task inference budget; among the "
    "survivors take the highest first-choice rate, breaking ties by higher coverage, then "
    "smaller k, then grid order"
)


class ContinuationOutcome(StrEnum):
    """§3.3's three endings: a rung passes and stops, or fails and either continues or stops."""

    # nosec B105 - "pass" here is the ladder verdict, not a credential
    PASS_AND_STOP = "pass_and_stop"  # nosec B105
    FAIL_AND_CONTINUE = "fail_and_continue"
    FAIL_AND_STOP = "fail_and_stop"


class FailureKind(StrEnum):
    """What a failing rung says about the signal, using calibration evidence only."""

    SIGNAL_IS_LINEAR = "signal_is_linear"
    SIGNAL_IS_NON_LINEAR = "signal_is_non_linear"
    DATA_DEFICIENT = "data_deficient"
    OOD_DEFICIENT = "ood_deficient"
    SIGNAL_ABSENT = "signal_absent"

    @property
    def authorises_parametric_continuation(self) -> bool:
        """Whether §3.3 opens the next rung on this evidence.

        Only a shape problem does. A rung that found the signal and then reversed under a
        semantics-preserving perturbation has an invariance problem, and one that ran out of
        evidence has a data problem; a different model class fitted on the same features
        answers neither. Opening a rung on either would be the speculative continuation §3.3
        forbids, and it would add a dependency to buy nothing.
        """
        return self in {FailureKind.SIGNAL_IS_LINEAR, FailureKind.SIGNAL_IS_NON_LINEAR}


@dataclass(frozen=True, slots=True)
class Setting:
    """One grid point. A value object, so a result cannot be built without naming its setting."""

    k: int
    similarity_floor: Decimal
    agreement_floor: Decimal
    confidence_floor: Decimal
    embedding_weight: Decimal = FROZEN_EMBEDDING_WEIGHT

    @property
    def identity(self) -> str:
        return (
            f"k={self.k};similarity={self.similarity_floor};agreement={self.agreement_floor};"
            f"confidence={self.confidence_floor};embedding_weight={self.embedding_weight}"
        )


def declared_grid() -> tuple[Setting, ...]:
    """The grid, in the fixed order the tie-break falls back to."""
    return tuple(
        Setting(
            k=k,
            similarity_floor=Decimal(similarity),
            agreement_floor=Decimal(agreement),
            confidence_floor=Decimal(confidence),
        )
        for k, similarity, agreement, confidence in product(
            GRID_K, GRID_SIMILARITY_FLOOR, GRID_AGREEMENT_FLOOR, GRID_CONFIDENCE_FLOOR
        )
    )


def grid_hash() -> str:
    """The grid's identity, so a later report cannot claim a grid it did not search."""
    return sha256("\n".join(setting.identity for setting in declared_grid()).encode()).hexdigest()


class OodPrecheck(HashedExperienceContract):
    """The sealed calibration OOD set, run through one setting. Zero confident errors or fail."""

    submanifest_hash: Sha256Hex
    resolved_set_hash: Sha256Hex
    groups: int = Field(ge=1)
    decisions: int = Field(ge=1)
    abstained: int = Field(ge=0)
    confident_errors: int = Field(ge=0)
    #: Never fitted, never scored into any metric, never counted towards an outcome floor.
    entered_any_dataset: bool = False

    @property
    def passed(self) -> bool:
        return self.confident_errors == 0

    def model_post_init(self, context: object) -> None:
        if self.entered_any_dataset:
            raise ValueError("an OOD precheck that entered a dataset is not a precheck")
        if self.abstained > self.decisions:
            raise ValueError("more abstentions than decisions")


class CalibrationResult(HashedExperienceContract):
    """One attempted setting's measured behaviour. Kept whether it won, lost or was filtered."""

    setting_identity: NonEmptyStr
    k: int = Field(ge=1)
    similarity_floor: str
    agreement_floor: str
    confidence_floor: str
    embedding_weight: str
    first_choice_rate: str
    coverage: str
    abstention_rate: str
    changed_decisions: int = Field(ge=0)
    confident_ood_errors: int = Field(ge=0)
    ood_answered: int = Field(ge=0)
    maximum_inference_ms: str
    eligible: bool
    ineligible_reason: str | None = None

    def model_post_init(self, context: object) -> None:
        if self.eligible and self.ineligible_reason:
            raise ValueError("an eligible setting cannot carry a reason it was filtered")
        if not self.eligible and not self.ineligible_reason:
            raise ValueError("a filtered setting must say what filtered it")


class CorrectionCalibration(HashedExperienceContract):
    """Every attempted setting, the OOD precheck, and the one selection the rule produced."""

    grid_identity: Sha256Hex
    settings_attempted: int = Field(ge=1)
    calibration_matrix_hash: Sha256Hex
    ladder_hash: Sha256Hex
    baseline_rung: NonEmptyStr
    baseline_rate: str
    selection_rule: NonEmptyStr = SELECTION_RULE
    results: tuple[CalibrationResult, ...] = Field(min_length=1)
    ood: OodPrecheck
    selected_setting_identity: str | None = None
    #: Only present when a setting was selected; the hash a later artifact must carry.
    selected_settings_hash: Sha256Hex | None = None
    created_at: UtcDatetime

    def model_post_init(self, context: object) -> None:
        if len(self.results) != self.settings_attempted:
            raise ValueError("the report does not hold every attempted setting")
        if (self.selected_setting_identity is None) != (self.selected_settings_hash is None):
            raise ValueError("a selection needs both its identity and its hash")
        if self.selected_setting_identity is not None:
            chosen = [
                item
                for item in self.results
                if item.setting_identity == self.selected_setting_identity
            ]
            if not chosen:
                raise ValueError("the selected setting is not among the attempted ones")
            if not chosen[0].eligible:
                raise ValueError("a filtered setting cannot be the selection")

    @property
    def selected(self) -> CalibrationResult | None:
        if self.selected_setting_identity is None:
            return None
        return next(
            item for item in self.results if item.setting_identity == self.selected_setting_identity
        )


class ContinuationDecision(HashedExperienceContract):
    """S21D2-045: the immutable record of whether the ladder stops here."""

    rung: NonEmptyStr = "bounded_cosine_knn"
    outcome: ContinuationOutcome
    calibration_hash: Sha256Hex
    baseline_rate: str
    candidate_rate: str | None = None
    minimum_absolute_improvement: str
    minimum_relative_error_reduction: str
    absolute_improvement: str | None = None
    relative_error_reduction: str | None = None
    failure_kind: FailureKind | None = None
    reason: NonEmptyStr
    #: Named so the record says, in itself, that no later rung was built speculatively.
    later_rungs_opened: tuple[NonEmptyStr, ...] = ()
    created_at: UtcDatetime

    def model_post_init(self, context: object) -> None:
        passing = self.outcome is ContinuationOutcome.PASS_AND_STOP
        if passing and self.failure_kind is not None:
            raise ValueError("a passing rung has no failure kind")
        if not passing and self.failure_kind is None:
            raise ValueError(
                "a failing rung must name whether the signal is linear, non-linear, "
                "data-deficient, OOD-deficient or absent"
            )
        if passing and self.later_rungs_opened:
            raise ValueError("a passing k-NN ends learner work; no later rung may be opened")
        if passing and self.candidate_rate is None:
            raise ValueError("a passing rung has a measured candidate rate")


class CandidateSelection(HashedExperienceContract):
    """S21D2-049: one candidate frozen before final access, or an immutable null.

    Selection freezes the candidate. It does not authorise final access, and the field below
    says so in the record rather than only in the backlog.
    """

    selected: bool
    learner_kind: str | None = None
    settings_identity: str | None = None
    settings_hash: Sha256Hex | None = None
    feature_contract_hash: Sha256Hex
    fitted_feature_report_hash: Sha256Hex
    training_dataset_id: str | None = None
    calibration_dataset_id: str | None = None
    example_manifest_hash: Sha256Hex | None = None
    split_manifest_hash: Sha256Hex | None = None
    baseline_rung: NonEmptyStr
    baseline_rate: str
    continuation_hash: Sha256Hex
    limitations: tuple[NonEmptyStr, ...] = ()
    null_reason: str | None = None
    authorises_final_access: bool = False
    created_at: UtcDatetime

    def model_post_init(self, context: object) -> None:
        if self.authorises_final_access:
            raise ValueError("selection freezes a candidate; it never opens the holdout")
        if self.selected:
            missing = [
                name
                for name in (
                    "learner_kind",
                    "settings_identity",
                    "settings_hash",
                    "training_dataset_id",
                    "calibration_dataset_id",
                )
                if getattr(self, name) is None
            ]
            if missing:
                raise ValueError(f"a selected candidate must name {sorted(missing)}")
            if self.null_reason is not None:
                raise ValueError("a selected candidate is not a null result")
        elif not self.null_reason:
            raise ValueError("a null selection must name the continuation rule that failed")


@dataclass(frozen=True, slots=True)
class MeasuredSetting:
    """What the caller measured for one grid point, before the rule is applied to it."""

    setting: Setting
    first_choice_rate: Decimal
    coverage: Decimal
    changed_decisions: int
    confident_ood_errors: int
    #: How many OOD probes the setting actually answered. Zero is not a pass.
    ood_answered: int
    maximum_inference_ms: Decimal


def settings_hash_for(setting: Setting) -> str:
    return sha256(setting.identity.encode()).hexdigest()


def apply_selection_rule(
    measured: Sequence[MeasuredSetting],
    *,
    manifest: CorrectionEvaluatorManifest,
) -> tuple[tuple[CalibrationResult, ...], Setting | None]:
    """Filter, maximise, break ties. Deterministic in the settings, never in the results."""
    if not measured:
        raise ValueError("the rule needs at least one attempted setting")
    order = {setting.identity: index for index, setting in enumerate(declared_grid())}
    results: list[CalibrationResult] = []
    survivors: list[MeasuredSetting] = []
    for item in measured:
        reason: str | None = None
        if item.changed_decisions == 0:
            reason = "it changed no decision, so it is the baseline under another name"
        elif item.ood_answered == 0:
            reason = (
                "it answered no out-of-distribution probe, so it did not pass the OOD check, "
                "it skipped it"
            )
        elif item.confident_ood_errors > 0:
            reason = (
                f"{item.confident_ood_errors} confident out-of-distribution error(s) against a "
                f"contract that allows {manifest.promotion_confident_ood_errors_allowed}"
            )
        elif item.maximum_inference_ms > Decimal(manifest.maximum_inference_ms_per_task):
            reason = (
                f"{item.maximum_inference_ms} ms per task exceeds the "
                f"{manifest.maximum_inference_ms_per_task} ms budget"
            )
        results.append(
            CalibrationResult(
                setting_identity=item.setting.identity,
                k=item.setting.k,
                similarity_floor=str(item.setting.similarity_floor),
                agreement_floor=str(item.setting.agreement_floor),
                confidence_floor=str(item.setting.confidence_floor),
                embedding_weight=str(item.setting.embedding_weight),
                first_choice_rate=str(item.first_choice_rate),
                coverage=str(item.coverage),
                abstention_rate=str(Decimal(1) - item.coverage),
                changed_decisions=item.changed_decisions,
                confident_ood_errors=item.confident_ood_errors,
                ood_answered=item.ood_answered,
                maximum_inference_ms=str(item.maximum_inference_ms),
                eligible=reason is None,
                ineligible_reason=reason,
            )
        )
        if reason is None:
            survivors.append(item)

    if not survivors:
        return tuple(results), None
    best = min(
        survivors,
        key=lambda item: (
            -item.first_choice_rate,
            -item.coverage,
            item.setting.k,
            order[item.setting.identity],
        ),
    )
    return tuple(results), best.setting


def decide_continuation(
    calibration: CorrectionCalibration,
    *,
    manifest: CorrectionEvaluatorManifest,
    baseline: Decimal,
    residuals: Mapping[str, Decimal] | None = None,
    created_at: datetime,
) -> ContinuationDecision:
    """Apply the frozen threshold to the selected setting, or record why there is none."""
    absolute_floor = Decimal(manifest.minimum_absolute_improvement)
    relative_floor = Decimal(manifest.minimum_relative_error_reduction)
    selected = calibration.selected

    if selected is None:
        strongest = max(calibration.results, key=lambda item: Decimal(item.first_choice_rate))
        ood_limited = any(item.confident_ood_errors > 0 for item in calibration.results)
        kind = FailureKind.OOD_DEFICIENT if ood_limited else FailureKind.DATA_DEFICIENT
        return ContinuationDecision(
            outcome=(
                ContinuationOutcome.FAIL_AND_CONTINUE
                if kind.authorises_parametric_continuation
                else ContinuationOutcome.FAIL_AND_STOP
            ),
            calibration_hash=calibration.content_hash,
            baseline_rate=str(baseline),
            candidate_rate=strongest.first_choice_rate,
            minimum_absolute_improvement=str(absolute_floor),
            minimum_relative_error_reduction=str(relative_floor),
            failure_kind=kind,
            reason=(
                "no setting in the pre-registered grid survived the selection filter. The "
                f"strongest scored {strongest.first_choice_rate} against a baseline of "
                f"{baseline}, so the signal is present; every setting that found it also "
                "answered confidently and wrongly on a semantics-preserving perturbation, and "
                "every setting that avoided that answered no probe at all"
                if ood_limited
                else "no setting in the pre-registered grid survived the selection filter"
            ),
            created_at=created_at,
        )

    rate = Decimal(selected.first_choice_rate)
    absolute = rate - baseline
    headroom = Decimal(1) - baseline
    relative = (absolute / headroom) if headroom > 0 else Decimal(0)
    if absolute >= absolute_floor and relative >= relative_floor:
        return ContinuationDecision(
            outcome=ContinuationOutcome.PASS_AND_STOP,
            calibration_hash=calibration.content_hash,
            baseline_rate=str(baseline),
            candidate_rate=str(rate),
            minimum_absolute_improvement=str(absolute_floor),
            minimum_relative_error_reduction=str(relative_floor),
            absolute_improvement=str(absolute),
            relative_error_reduction=str(relative),
            reason=(
                f"the k-NN cleared both frozen thresholds against "
                f"{calibration.baseline_rung!r}; §3.3 ends learner work here and no later rung "
                "is implemented"
            ),
            created_at=created_at,
        )

    kind = _failure_kind(
        residuals or {},
        ood_limited=any(item.confident_ood_errors > 0 for item in calibration.results),
    )
    return ContinuationDecision(
        outcome=(
            ContinuationOutcome.FAIL_AND_CONTINUE
            if kind.authorises_parametric_continuation
            else ContinuationOutcome.FAIL_AND_STOP
        ),
        calibration_hash=calibration.content_hash,
        baseline_rate=str(baseline),
        candidate_rate=str(rate),
        minimum_absolute_improvement=str(absolute_floor),
        minimum_relative_error_reduction=str(relative_floor),
        absolute_improvement=str(absolute),
        relative_error_reduction=str(relative),
        failure_kind=kind,
        reason=(
            f"the selected setting scored {rate} against a baseline of {baseline}: "
            f"{absolute} absolute against a floor of {absolute_floor}, {relative} relative "
            f"against a floor of {relative_floor}"
        ),
        created_at=created_at,
    )


def _failure_kind(residuals: Mapping[str, Decimal], *, ood_limited: bool = False) -> FailureKind:
    """Name what the calibration residuals say, using calibration evidence only.

    `ood_limited` comes first because it is the one kind that does *not* authorise a later
    rung. A rung that found the signal and then reversed under a semantics-preserving
    perturbation has an invariance problem, not a capacity problem, and a parametric model
    fitted on the same features under the same perturbation would face it unchanged. Naming
    such a failure `signal_is_linear` would authorise a dependency and a rung on evidence that
    says nothing about either.

    The remaining default is `SIGNAL_ABSENT` rather than something more hopeful, for the same
    reason: claiming a signal is linear is what opens the linear rung, and an unexamined
    default that opened one would be exactly the speculative continuation §3.3 forbids.
    """
    if ood_limited:
        return FailureKind.OOD_DEFICIENT
    linear = residuals.get("best_single_column_separation", Decimal(0))
    if linear >= Decimal("0.70"):
        return FailureKind.SIGNAL_IS_LINEAR
    if residuals.get("neighbour_agreement", Decimal(0)) >= Decimal("0.70"):
        return FailureKind.SIGNAL_IS_NON_LINEAR
    return FailureKind.SIGNAL_ABSENT
