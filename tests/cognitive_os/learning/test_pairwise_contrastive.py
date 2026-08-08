"""The pairwise contrastive class, tested on what it refuses and what it must preserve.

Whether this class clears the Gate L2 floors is a calibration measurement on a fresh
corpus, not a unit test. What is testable now is the contract: a one-sided group cannot
contribute a contrast, mismatched encoders cannot meet in one pair set, ties fall back to
the frozen baseline rather than to a candidate ID, the margin floor abstains instead of
guessing, and the same fitting inputs produce the same sealed bytes.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from cognitive_os.learning.correction_ranking import (
    CorrectionEncodingError,
    CorrectionFeatureVector,
    Exemplar,
)
from cognitive_os.learning.pairwise_contrastive import (
    HYPOTHESIS_CLASS,
    PairwiseContrastiveModel,
    PairwiseContrastiveRanker,
    PairwiseFitError,
    fit_pairwise_direction,
)

pytest.importorskip("numpy")

FEATURES = ("signal", "noise", "constant")


def _vector(signal: float, noise: float) -> CorrectionFeatureVector:
    return CorrectionFeatureVector(
        encoder_version="correction-ranking-v1",
        values=(("signal", signal), ("noise", noise), ("constant", 1.0)),
        embedding=(0.0, 0.0),
    )


def _group(*pairs: tuple[float, bool]) -> list[Exemplar]:
    return [
        Exemplar(vector=_vector(signal, index * 0.01), accepted=accepted)
        for index, (signal, accepted) in enumerate(pairs)
    ]


def _fitting_groups() -> list[list[Exemplar]]:
    # Acceptance follows the `signal` channel; `noise` varies without carrying the label.
    return [
        _group((0.9, True), (0.8, True), (0.2, False), (0.1, False)),
        _group((0.7, True), (0.6, True), (0.3, False), (0.2, False)),
        _group((0.95, True), (0.55, True), (0.45, False), (0.05, False)),
    ]


def test_fit_learns_the_contrast_and_ranks_by_it() -> None:
    model = fit_pairwise_direction(_fitting_groups(), regularization=Decimal("1"))
    assert model.encoder_version == "correction-ranking-v1"
    assert model.feature_names == FEATURES
    assert model.fitted_group_count == 3
    assert model.fitted_pair_count == 12
    ranker = PairwiseContrastiveRanker(model)
    candidates = {
        "low": _vector(0.1, 0.5),
        "high": _vector(0.9, 0.5),
        "middle": _vector(0.5, 0.5),
    }
    ranking = ranker.rank(candidates, baseline_order=("low", "middle", "high"))
    assert not ranking.abstained
    assert ranking.ordered_candidate_ids == ("high", "middle", "low")
    assert ranking.confidence > 0


def test_the_same_inputs_produce_the_same_sealed_bytes() -> None:
    first = fit_pairwise_direction(_fitting_groups(), regularization=Decimal("1"))
    second = fit_pairwise_direction(_fitting_groups(), regularization=Decimal("1"))
    assert first.content_hash() == second.content_hash()
    assert HYPOTHESIS_CLASS.encode() in first.canonical_bytes()


def test_a_one_sided_group_is_refused() -> None:
    groups = [*_fitting_groups(), _group((0.9, True), (0.8, True))]
    with pytest.raises(PairwiseFitError, match="one-sided"):
        fit_pairwise_direction(groups, regularization=Decimal("1"))


def test_no_groups_and_a_non_positive_ridge_are_refused() -> None:
    with pytest.raises(PairwiseFitError, match="no fitting group"):
        fit_pairwise_direction([], regularization=Decimal("1"))
    with pytest.raises(PairwiseFitError, match="positive"):
        fit_pairwise_direction(_fitting_groups(), regularization=Decimal("0"))


def test_mismatched_encoders_cannot_meet_in_one_pair_set() -> None:
    other = CorrectionFeatureVector(
        encoder_version="correction-ranking-v2-not-really",
        values=(("signal", 0.5), ("noise", 0.5), ("constant", 1.0)),
        embedding=(0.0, 0.0),
    )
    groups = [
        _fitting_groups()[0],
        [Exemplar(vector=other, accepted=True), _fitting_groups()[1][2]],
    ]
    with pytest.raises(CorrectionEncodingError, match="encoded differently"):
        fit_pairwise_direction(groups, regularization=Decimal("1"))


def test_ties_keep_the_baseline_order_and_the_margin_floor_abstains() -> None:
    model = fit_pairwise_direction(_fitting_groups(), regularization=Decimal("1"))
    tied = {"first": _vector(0.5, 0.2), "second": _vector(0.5, 0.2)}
    ranking = PairwiseContrastiveRanker(model).rank(tied, baseline_order=("first", "second"))
    assert ranking.ordered_candidate_ids == ("first", "second")
    assert ranking.confidence == Decimal("0")
    assert not ranking.abstained

    floored = PairwiseContrastiveRanker(model, margin_floor=Decimal("0.000001")).rank(
        tied, baseline_order=("first", "second")
    )
    assert floored.abstained
    assert floored.reason == "below_margin_floor"
    assert floored.ordered_candidate_ids == ("first", "second")
    assert floored.confidence == Decimal("0")


def test_the_ranker_refuses_disagreeing_inputs() -> None:
    model = fit_pairwise_direction(_fitting_groups(), regularization=Decimal("1"))
    ranker = PairwiseContrastiveRanker(model)
    with pytest.raises(CorrectionEncodingError, match="disagree"):
        ranker.rank({"only": _vector(0.5, 0.5)}, baseline_order=("only", "absent"))
    with pytest.raises(CorrectionEncodingError, match="at least two"):
        ranker.rank({"only": _vector(0.5, 0.5)}, baseline_order=("only",))
    mismatched = CorrectionFeatureVector(
        encoder_version="correction-ranking-v2-not-really",
        values=(("signal", 0.5), ("noise", 0.5), ("constant", 1.0)),
        embedding=(0.0, 0.0),
    )
    with pytest.raises(CorrectionEncodingError, match="encoded differently"):
        ranker.rank(
            {"left": _vector(0.5, 0.5), "right": mismatched},
            baseline_order=("left", "right"),
        )


def test_a_model_that_cannot_have_been_fitted_is_refused() -> None:
    with pytest.raises(PairwiseFitError, match="one weight per fitted feature"):
        PairwiseContrastiveModel(
            encoder_version="correction-ranking-v1",
            feature_names=FEATURES,
            weights=(1.0,),
            regularization="1",
            fitted_group_count=1,
            fitted_pair_count=1,
        )
    with pytest.raises(PairwiseFitError, match="finite"):
        PairwiseContrastiveModel(
            encoder_version="correction-ranking-v1",
            feature_names=("signal",),
            weights=(float("nan"),),
            regularization="1",
            fitted_group_count=1,
            fitted_pair_count=1,
        )
    with pytest.raises(PairwiseFitError, match="no pairs"):
        PairwiseContrastiveModel(
            encoder_version="correction-ranking-v1",
            feature_names=("signal",),
            weights=(1.0,),
            regularization="1",
            fitted_group_count=0,
            fitted_pair_count=0,
        )
    with pytest.raises(ValueError, match="negative margin floor"):
        PairwiseContrastiveRanker(
            PairwiseContrastiveModel(
                encoder_version="correction-ranking-v1",
                feature_names=("signal",),
                weights=(1.0,),
                regularization="1",
                fitted_group_count=1,
                fitted_pair_count=1,
            ),
            margin_floor=Decimal("-0.1"),
        )


def test_settings_carry_the_sealed_identity() -> None:
    model = fit_pairwise_direction(_fitting_groups(), regularization=Decimal("1"))
    settings = PairwiseContrastiveRanker(model, margin_floor=Decimal("0.25")).settings
    assert settings["hypothesis_class"] == HYPOTHESIS_CLASS
    assert settings["model_hash"] == model.content_hash()
    assert settings["margin_floor"] == "0.25"
    assert settings["regularization"] == "1"
