"""The containment contrastive class, tested on its seams rather than on its rates.

Whether this class clears the amended §2.3 is W2's measurement on a corpus that does not exist
yet. What W0 can test is the four seams a wave would otherwise discover late:

*The assembly refuses drifted scalar names.* `relational_numbers` takes the six scalars out of
sealed v2 records by name, and §5.1 sends the vertical slice at exactly this seam: a reordered
or renamed sealed record must fail loudly rather than feed the direction numbers under the
wrong names.

*The same inputs seal the same bytes.* W2 fits once and reproduces the fit across a process
restart against the groundwork's sealed model hash; §5.2 calls a fit that does not reproduce a
stop-worthy defect. The determinism this test proves is the in-process half — the sealed-hash
half is `test_d7_w0_evidence.py`, which rebuilds the groundwork's model from its record.

*The embedding is gone.* The class is defined over seven channels, and a vector carrying the
390 the released class fitted is not a wide version of this class, it is a different one.

*Ties and abstention behave like the released ranker's.* The margin floor decides whether the
ranker answers, never whether a decision is admitted; admission is the conformal bar's job.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from cognitive_os.learning.containment_contrastive import (
    FIT_RULE,
    FITTED_RELATIONAL_CHANNELS,
    HYPOTHESIS_CLASS,
    ContainmentContrastiveModel,
    ContainmentContrastiveRanker,
    ContainmentFitError,
    RelationalGroup,
    fit_containment_direction,
    relational_numbers,
)
from cognitive_os.learning.correction_protocol import FITTED_FEATURE_V2_SCALARS
from cognitive_os.learning.correction_ranking import CorrectionEncodingError
from cognitive_os.learning.repair_containment import REPAIR_CONTAINMENT_CHANNEL

pytest.importorskip("numpy")

BASELINE = "def f(values):\n    return values\n"
SOURCES = {
    "complete": "def f(values):\n    if values is None:\n        return []\n"
    "    if not values:\n        return []\n    return values\n",
    "partial": "def f(values):\n    if values is None:\n        return []\n    return values\n",
}


def _sealed(scale: float) -> tuple[tuple[str, float], ...]:
    return tuple((name, scale + index) for index, name in enumerate(FITTED_FEATURE_V2_SCALARS))


def _numbers(containment: float, signal: float) -> tuple[float, ...]:
    """Six scalars where only the first carries the label, plus the containment share."""
    return (signal, 0.1, 0.2, 0.3, 0.4, 0.5, containment)


def _group(name: str, *rows: tuple[float, float, bool]) -> RelationalGroup:
    order = tuple(f"{name}-{index}" for index in range(len(rows)))
    return RelationalGroup(
        group=name,
        order=order,
        numbers={
            candidate: _numbers(containment, signal)
            for candidate, (containment, signal, _) in zip(order, rows, strict=True)
        },
        accepted={
            candidate: accepted for candidate, (_, _, accepted) in zip(order, rows, strict=True)
        },
    )


def _fitting_groups() -> list[RelationalGroup]:
    # Acceptance follows containment; the scalar channel varies without carrying the label.
    return [
        _group("a", (0.9, 0.4, True), (0.8, 0.9, True), (0.2, 0.1, False), (0.1, 0.6, False)),
        _group("b", (0.7, 0.2, True), (0.6, 0.8, True), (0.3, 0.5, False), (0.2, 0.3, False)),
        _group("c", (0.95, 0.7, True), (0.55, 0.1, True), (0.45, 0.9, False), (0.05, 0.2, False)),
    ]


class TestTheRelationalAssembly:
    def test_seven_channels_are_six_sealed_scalars_and_one_derived_share(self) -> None:
        expected = (*FITTED_FEATURE_V2_SCALARS, REPAIR_CONTAINMENT_CHANNEL)
        assert expected == FITTED_RELATIONAL_CHANNELS
        assert len(FITTED_RELATIONAL_CHANNELS) == 7
        assert not any("embedding" in name for name in FITTED_RELATIONAL_CHANNELS)

        numbers = relational_numbers(
            {"complete": _sealed(1.0), "partial": _sealed(2.0)},
            baseline_source=BASELINE,
            sources_by_candidate=SOURCES,
        )
        assert numbers["complete"][:6] == tuple(value for _, value in _sealed(1.0))
        # The complete repair contains the partial one entirely; the partial one does not.
        assert numbers["complete"][6] == pytest.approx(1.0)
        assert numbers["partial"][6] == pytest.approx(2 / 3)

    def test_a_drifted_sealed_record_fails_here_rather_than_in_the_direction(self) -> None:
        """§5.1's named seam: wrong names, or the right names in the wrong order."""
        renamed = (("drifted_name", 1.0), *_sealed(1.0)[1:])
        with pytest.raises(CorrectionEncodingError, match="exact six sealed v2 scalars"):
            relational_numbers(
                {"complete": renamed, "partial": _sealed(2.0)},
                baseline_source=BASELINE,
                sources_by_candidate=SOURCES,
            )
        reordered = tuple(reversed(_sealed(1.0)))
        with pytest.raises(CorrectionEncodingError, match="exact six sealed v2 scalars"):
            relational_numbers(
                {"complete": reordered, "partial": _sealed(2.0)},
                baseline_source=BASELINE,
                sources_by_candidate=SOURCES,
            )

    def test_sealed_records_and_group_sources_must_name_the_same_candidates(self) -> None:
        with pytest.raises(CorrectionEncodingError, match="disagree"):
            relational_numbers(
                {"complete": _sealed(1.0)},
                baseline_source=BASELINE,
                sources_by_candidate=SOURCES,
            )


class TestTheFit:
    def test_it_learns_the_contrast_and_the_same_inputs_seal_the_same_bytes(self) -> None:
        first = fit_containment_direction(_fitting_groups(), regularization=Decimal("1"))
        second = fit_containment_direction(
            list(reversed(_fitting_groups())), regularization=Decimal("1")
        )

        assert first.channel_names == FITTED_RELATIONAL_CHANNELS
        assert first.fitted_group_count == 3
        assert first.fitted_pair_count == 12
        # Sorted group order, so the input order of the groups cannot move the sealed bytes.
        assert first.content_hash() == second.content_hash()
        assert HYPOTHESIS_CLASS.encode() in first.canonical_bytes()
        # The containment channel is the one the labels follow, so it carries the weight.
        weights = dict(zip(first.channel_names, first.weights, strict=True))
        assert weights[REPAIR_CONTAINMENT_CHANNEL] > 0
        assert weights[REPAIR_CONTAINMENT_CHANNEL] > abs(weights[FITTED_FEATURE_V2_SCALARS[0]])

    def test_the_fit_rule_names_what_it_reads_and_what_it_does_not(self) -> None:
        assert "six sealed v2 scalars" in FIT_RULE
        assert "repair-containment share" in FIT_RULE
        assert "embedding" not in FIT_RULE

    def test_one_sided_groups_no_groups_and_a_zero_ridge_are_refused(self) -> None:
        one_sided = [*_fitting_groups(), _group("d", (0.9, 0.4, True), (0.8, 0.2, True))]
        with pytest.raises(ContainmentFitError, match="one-sided"):
            fit_containment_direction(one_sided, regularization=Decimal("1"))
        with pytest.raises(ContainmentFitError, match="no fitting group"):
            fit_containment_direction([], regularization=Decimal("1"))
        with pytest.raises(ContainmentFitError, match="positive"):
            fit_containment_direction(_fitting_groups(), regularization=Decimal("0"))

    def test_a_group_off_the_channel_set_cannot_be_assembled(self) -> None:
        with pytest.raises(ContainmentFitError, match="off the relational channel set"):
            RelationalGroup(
                group="wide",
                order=("left", "right"),
                numbers={"left": (0.0,) * 390, "right": (0.0,) * 390},
                accepted={"left": True, "right": False},
            )
        with pytest.raises(ContainmentFitError, match="names disagree"):
            RelationalGroup(
                group="mismatched",
                order=("left", "right"),
                numbers={"left": _numbers(0.5, 0.5), "right": _numbers(0.4, 0.4)},
                accepted={"left": True},
            )

    def test_a_model_that_cannot_have_been_fitted_is_refused(self) -> None:
        for weights, message in (
            ((1.0,), "one weight per fitted channel"),
            ((float("nan"),) * 7, "must be finite"),
        ):
            with pytest.raises(ContainmentFitError, match=message):
                ContainmentContrastiveModel(
                    channel_names=FITTED_RELATIONAL_CHANNELS,
                    weights=weights,
                    regularization="1",
                    fitted_group_count=1,
                    fitted_pair_count=1,
                )
        with pytest.raises(ContainmentFitError, match="names the seven channels"):
            ContainmentContrastiveModel(
                channel_names=FITTED_FEATURE_V2_SCALARS,
                weights=(1.0,) * 6,
                regularization="1",
                fitted_group_count=1,
                fitted_pair_count=1,
            )
        with pytest.raises(ContainmentFitError, match="no pairs"):
            ContainmentContrastiveModel(
                channel_names=FITTED_RELATIONAL_CHANNELS,
                weights=(1.0,) * 7,
                regularization="1",
                fitted_group_count=0,
                fitted_pair_count=0,
            )


class TestTheRanker:
    def test_it_ranks_by_projection_and_carries_the_sealed_identity(self) -> None:
        model = fit_containment_direction(_fitting_groups(), regularization=Decimal("1"))
        ranker = ContainmentContrastiveRanker(model, margin_floor=Decimal("0.25"))
        ranking = ranker.rank(
            {
                "low": _numbers(0.1, 0.9),
                "high": _numbers(0.9, 0.1),
                "middle": _numbers(0.5, 0.5),
            },
            baseline_order=("low", "middle", "high"),
        )

        assert not ranking.abstained
        assert ranking.ordered_candidate_ids == ("high", "middle", "low")
        assert ranking.confidence > 0
        assert ranker.settings == {
            "hypothesis_class": HYPOTHESIS_CLASS,
            "model_hash": model.content_hash(),
            "regularization": "1",
            "margin_floor": "0.25",
        }

    def test_ties_keep_the_baseline_order_and_the_floor_abstains(self) -> None:
        model = fit_containment_direction(_fitting_groups(), regularization=Decimal("1"))
        tied = {"first": _numbers(0.5, 0.5), "second": _numbers(0.5, 0.5)}

        ranking = ContainmentContrastiveRanker(model).rank(tied, baseline_order=("first", "second"))
        assert ranking.ordered_candidate_ids == ("first", "second")
        assert ranking.confidence == Decimal("0")
        assert not ranking.abstained

        floored = ContainmentContrastiveRanker(model, margin_floor=Decimal("0.000001")).rank(
            tied, baseline_order=("first", "second")
        )
        assert floored.abstained
        assert floored.reason == "below_margin_floor"
        assert floored.ordered_candidate_ids == ("first", "second")

    def test_it_refuses_disagreeing_inputs_and_a_negative_floor(self) -> None:
        model = fit_containment_direction(_fitting_groups(), regularization=Decimal("1"))
        ranker = ContainmentContrastiveRanker(model)
        with pytest.raises(CorrectionEncodingError, match="disagree"):
            ranker.rank({"only": _numbers(0.5, 0.5)}, baseline_order=("only", "absent"))
        with pytest.raises(CorrectionEncodingError, match="at least two"):
            ranker.rank({"only": _numbers(0.5, 0.5)}, baseline_order=("only",))
        with pytest.raises(CorrectionEncodingError, match="dimensions disagree"):
            ranker.rank(
                {"left": _numbers(0.5, 0.5), "right": (0.1, 0.2)},
                baseline_order=("left", "right"),
            )
        with pytest.raises(ValueError, match="negative margin floor"):
            ContainmentContrastiveRanker(model, margin_floor=Decimal("-0.1"))
