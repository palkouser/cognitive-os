"""The split-conformal bar on hand-computed vectors.

Every vector below is small enough to check by eye, which is the point: D5's stop says the
prefix rule's coverage was hostage to the position of one error, and the replacement rule's
correctness cannot itself be a matter of trust.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest
from pydantic import ValidationError

from cognitive_os.learning.conformal_operating_point import (
    ConformalOperatingPointV5,
    ConformalPointError,
    admitted_error_upper_bound,
    conformal_rank,
    derive_conformal_point,
)
from cognitive_os.learning.selective_operating_point import (
    ScoredDecision,
    derive_zero_error_point,
    zero_error_upper_bound,
)

DERIVED_AT = datetime(2026, 8, 9, 12, tzinfo=UTC)
SOURCE = "a" * 64
PREREGISTRATION = "b" * 64


def _decisions(prefix: str, *rows: tuple[str, bool, bool]) -> tuple[ScoredDecision, ...]:
    return tuple(
        ScoredDecision(
            decision_id=f"{prefix}{index}",
            feature_hash=f"{prefix}v{index}",
            score=Decimal(score),
            answered=answered,
            correct=correct,
        )
        for index, (score, answered, correct) in enumerate(rows)
    )


def _derive(
    conformal: tuple[ScoredDecision, ...],
    certification: tuple[ScoredDecision, ...],
    **overrides: object,
) -> ConformalOperatingPointV5:
    fields: dict[str, object] = {
        "alpha": Decimal("0.25"),
        "split": "calibration",
        "calibration_source_hash": SOURCE,
        "preregistration_hash": PREREGISTRATION,
        "derived_at": DERIVED_AT,
    }
    fields.update(overrides)
    return derive_conformal_point(conformal, certification, **fields)  # type: ignore[arg-type]


def test_the_bar_is_the_quantile_of_the_wrong_margins_not_the_deepest_clean_prefix() -> None:
    """Wrong margins 0.2 0.4 0.6, alpha 0.25: rank ceil(0.75*4) = 3, so the bar is 0.6.

    The certification half admits the three decisions strictly above it — one of them wrong.
    The prefix rule would have stopped at that error; the conformal bar states it instead.
    """
    point = _derive(
        _decisions(
            "c",
            ("0.9", True, True),
            ("0.6", True, False),
            ("0.4", True, False),
            ("0.2", True, False),
        ),
        _decisions(
            "t",
            ("0.9", True, True),
            ("0.7", True, False),
            ("0.65", True, True),
            ("0.6", True, True),
            ("0.3", True, True),
        ),
    )
    assert point.quantile_exists
    assert point.wrong_decisions_in_conformal_split == 3
    assert point.quantile_rank == 3
    assert point.threshold == "0.6"
    assert point.admitted_decisions == 3
    assert point.errors_admitted == 1
    assert point.coverage == "0.6"  # three of five independent certification decisions
    assert point.observed_error_rate == str(Decimal(1) / Decimal(3))
    assert point.error_upper_bound_95 == "0.86465"


def test_a_certification_decision_tied_with_the_bar_is_not_admitted() -> None:
    """Admission is strictly above the threshold, exactly as in the rule it replaces."""
    point = _derive(
        _decisions("c", ("0.6", True, False), ("0.4", True, False), ("0.2", True, False)),
        _decisions("t", ("0.6", True, True), ("0.5", True, True)),
    )
    assert point.threshold == "0.6"
    assert point.admitted_decisions == 0
    assert point.coverage == "0"
    assert point.observed_error_rate is None
    assert point.error_upper_bound_95 is None


def test_no_wrong_decision_in_the_conformal_half_names_no_quantile() -> None:
    """An empty wrong-margin distribution has no quantile, and the record does not admit
    everything the way the zero-error rule's all-correct branch did."""
    point = _derive(
        _decisions("c", ("0.9", True, True), ("0.5", True, True)),
        _decisions("t", ("0.9", True, True), ("0.5", True, True)),
    )
    assert not point.quantile_exists
    assert point.wrong_decisions_in_conformal_split == 0
    assert point.quantile_rank == 1  # asked for the 1st of zero margins, which does not exist
    assert point.threshold is None
    assert point.admitted_decisions == 0
    assert point.coverage is None


def test_too_few_wrong_decisions_for_the_alpha_names_no_quantile_either() -> None:
    """At alpha 0.05, five wrong margins are asked for their 6th smallest."""
    point = _derive(
        _decisions(
            "c",
            ("0.5", True, False),
            ("0.4", True, False),
            ("0.3", True, False),
            ("0.2", True, False),
            ("0.1", True, False),
        ),
        _decisions("t", ("0.9", True, True)),
        alpha=Decimal("0.05"),
    )
    assert not point.quantile_exists
    assert point.wrong_decisions_in_conformal_split == 5
    assert point.quantile_rank == 6
    assert point.threshold is None


def test_abstentions_contribute_no_wrong_margin_and_are_never_admitted() -> None:
    point = _derive(
        _decisions("c", ("0.9", True, False), ("0.8", False, False)),
        _decisions("t", ("0.95", True, True), ("0.99", False, False)),
        alpha=Decimal("0.5"),
    )
    assert point.wrong_decisions_in_conformal_split == 1
    assert point.quantile_rank == 1
    assert point.threshold == "0.9"
    assert point.admitted_decisions == 1  # the answered 0.95, not the abstaining 0.99
    assert point.certification_census.independent_decisions == 2


def test_only_the_calibration_split_may_derive_a_bar() -> None:
    for split in ("final_a", "final_b", "promotion", "metamorphic", "canary"):
        with pytest.raises(ConformalPointError, match="calibration split only"):
            _derive(
                _decisions("c", ("0.9", True, False)),
                _decisions("t", ("0.9", True, True)),
                split=split,
            )


def test_alpha_lives_strictly_inside_the_unit_interval() -> None:
    for alpha in (Decimal("0"), Decimal("1"), Decimal("-0.1"), Decimal("1.5")):
        with pytest.raises(ConformalPointError, match="strictly inside"):
            _derive(
                _decisions("c", ("0.9", True, False)),
                _decisions("t", ("0.9", True, True)),
                alpha=alpha,
            )


def test_a_vector_in_both_halves_is_refused() -> None:
    conformal = _decisions("c", ("0.9", True, False), ("0.5", True, True))
    leaked = conformal[:1] + _decisions("t", ("0.7", True, True))
    with pytest.raises(ConformalPointError, match="both halves"):
        _derive(conformal, leaked)


def test_replicated_decisions_are_refused_rather_than_deduplicated() -> None:
    replicated = tuple(
        ScoredDecision(
            decision_id=f"d{index}",
            feature_hash="one-and-the-same-vector",
            score=Decimal("0.9"),
            answered=True,
            correct=False,
        )
        for index in range(6)
    )
    with pytest.raises(ConformalPointError, match="repeat another's fitted vector"):
        _derive(replicated, _decisions("t", ("0.9", True, True)))


def test_an_empty_certification_half_is_refused() -> None:
    with pytest.raises(ConformalPointError, match="certifies nothing"):
        _derive(_decisions("c", ("0.9", True, False)), ())


def test_a_second_derivation_at_a_different_alpha_is_a_search_and_is_refused() -> None:
    conformal = _decisions("c", ("0.6", True, False), ("0.4", True, False), ("0.2", True, False))
    certification = _decisions("t", ("0.9", True, True), ("0.5", True, True))
    first = _derive(conformal, certification)
    with pytest.raises(ConformalPointError, match="second, different conformal bar"):
        _derive(conformal, certification, alpha=Decimal("0.5"), previous=first)


def test_re_deriving_the_same_bar_after_a_restart_is_allowed_and_identical() -> None:
    conformal = _decisions("c", ("0.6", True, False), ("0.4", True, False), ("0.2", True, False))
    certification = _decisions("t", ("0.9", True, True), ("0.5", True, True))
    first = _derive(conformal, certification)
    again = _derive(
        conformal,
        certification,
        derived_at=datetime(2027, 1, 1, tzinfo=UTC),
        previous=first,
    )
    assert again.derivation_hash == first.derivation_hash
    assert (again.threshold, again.coverage, again.admitted_decisions) == (
        first.threshold,
        first.coverage,
        first.admitted_decisions,
    )
    assert again.derived_at != first.derived_at


def test_the_derivation_hash_moves_with_the_preregistration() -> None:
    conformal = _decisions("c", ("0.6", True, False))
    certification = _decisions("t", ("0.9", True, True))
    assert (
        _derive(conformal, certification, alpha=Decimal("0.5")).derivation_hash
        != _derive(
            conformal,
            certification,
            alpha=Decimal("0.5"),
            preregistration_hash="c" * 64,
        ).derivation_hash
    )


def test_the_bound_at_zero_errors_is_the_zero_error_rules_bound() -> None:
    """The two admission rules state their claims on one scale: k = 0 reproduces the sealed
    Clopper-Pearson values, including the 10.9% that bounds D5's 26 admitted decisions."""
    for n in (20, 26, 60, 100, 300):
        assert round(admitted_error_upper_bound(0, n), 6) == round(zero_error_upper_bound(n), 6)
    assert round(admitted_error_upper_bound(0, 26), 6) == 0.10883


def test_the_bound_grows_with_errors_and_reaches_one_when_everything_is_wrong() -> None:
    assert round(admitted_error_upper_bound(1, 20), 6) == 0.216106
    assert round(admitted_error_upper_bound(2, 20), 6) == 0.282619
    assert admitted_error_upper_bound(0, 20) < admitted_error_upper_bound(1, 20)
    # No branch handles k == n; the CDF is 1 everywhere there and the bisection lands on it.
    assert admitted_error_upper_bound(20, 20) == 1.0
    # The bar the D6 power argument is written against: one error in 58 admitted decisions.
    assert round(admitted_error_upper_bound(1, 58), 6) == 0.079198
    with pytest.raises(ValueError, match="bounds nothing"):
        admitted_error_upper_bound(0, 0)
    with pytest.raises(ValueError, match="between zero and the admitted count"):
        admitted_error_upper_bound(3, 2)


def test_alpha_bounds_the_leak_rate_which_is_the_wrong_margins_left_above_the_bar() -> None:
    """The finite-sample statement behind alpha, checked on the half that sets the bar.

    With m wrong margins and rank r, exactly m - r of them sit strictly above the threshold.
    That ratio — errors that clear their own bar — is what alpha budgets, and it is not the
    share of admitted decisions that are wrong. D5's 720-row cell has m = 12, so alpha 0.20
    leaves one wrong margin above the bar and alpha 0.10 leaves none, which is the prefix rule
    the sprint stopped on.
    """
    wrong = [Decimal(f"0.{index:02d}") for index in range(1, 13)]
    rows = tuple((str(margin), True, False) for margin in wrong)  # twelve wrong decisions
    for alpha, leaked in (
        (Decimal("0.10"), 0),
        (Decimal("0.20"), 1),
        (Decimal("0.25"), 2),
    ):
        point = _derive(
            _decisions("c", *rows),
            _decisions("t", ("0.99", True, True)),
            alpha=alpha,
        )
        assert point.quantile_exists
        above = [margin for margin in wrong if margin > Decimal(point.threshold or "0")]
        assert len(above) == leaked
        assert point.wrong_decisions_in_conformal_split - point.quantile_rank == leaked


def test_the_rank_is_the_finite_sample_quantile_not_the_plug_in_one() -> None:
    assert conformal_rank(Decimal("0.25"), 3) == 3
    assert conformal_rank(Decimal("0.5"), 3) == 2
    assert conformal_rank(Decimal("0.05"), 5) == 6  # exceeds the sample: no quantile
    assert conformal_rank(Decimal("0.1"), 99) == 90
    assert conformal_rank(Decimal("0.5"), 0) == 1


def test_a_stored_bar_cannot_be_edited_into_a_different_rank() -> None:
    point = _derive(
        _decisions("c", ("0.6", True, False), ("0.4", True, False), ("0.2", True, False)),
        _decisions("t", ("0.9", True, True)),
    )
    body = point.model_dump(mode="json", exclude={"content_hash"})
    body["quantile_rank"] = 2
    with pytest.raises(ValidationError, match="a rank that drifted is a different quantile"):
        ConformalOperatingPointV5.model_validate(body)


def test_a_stored_bar_cannot_claim_a_quantile_the_counts_do_not_support() -> None:
    point = _derive(
        _decisions("c", ("0.9", True, True)),
        _decisions("t", ("0.9", True, True)),
    )
    assert not point.quantile_exists
    body = point.model_dump(mode="json", exclude={"content_hash"})
    body["quantile_exists"] = True
    with pytest.raises(ValidationError, match="disagrees with them"):
        ConformalOperatingPointV5.model_validate(body)


def test_a_stored_bar_cannot_hide_its_error_budget() -> None:
    point = _derive(
        _decisions(
            "c",
            ("0.6", True, False),
            ("0.4", True, False),
            ("0.2", True, False),
        ),
        _decisions("t", ("0.9", True, False), ("0.8", True, True)),
    )
    assert point.errors_admitted == 1
    body = point.model_dump(mode="json", exclude={"content_hash"})
    body["observed_error_rate"] = None
    with pytest.raises(ValidationError, match="observed error rate and its upper bound"):
        ConformalOperatingPointV5.model_validate(body)


def test_stored_bytes_claiming_another_split_are_refused_too() -> None:
    point = _derive(
        _decisions("c", ("0.6", True, False)),
        _decisions("t", ("0.9", True, True)),
        alpha=Decimal("0.5"),
    )
    body = point.model_dump(mode="json", exclude={"content_hash"})
    body["split"] = "final_a"
    with pytest.raises(ValidationError, match="fitted to a holdout"):
        ConformalOperatingPointV5.model_validate(body)


def test_the_d5_stop_scenario_in_miniature_the_prefix_truncates_and_the_quantile_does_not() -> None:
    """One high-margin error truncates the prefix rule to a single admitted decision; the
    conformal bar over a disjoint half admits four and states its one-in-four budget."""
    certification = _decisions(
        "t",
        ("0.95", True, True),
        ("0.85", True, False),
        ("0.8", True, True),
        ("0.7", True, True),
        ("0.6", True, True),
        ("0.2", True, True),
    )
    prefix = derive_zero_error_point(
        certification,
        split="calibration",
        calibration_source_hash=SOURCE,
        derived_at=DERIVED_AT,
    )
    assert prefix.admitted_decisions == 1  # everything below the 0.85 error is lost

    conformal = _decisions(
        "c",
        ("0.5", True, False),
        ("0.4", True, False),
        ("0.3", True, False),
    )
    point = _derive(conformal, certification)
    assert point.threshold == "0.5"
    assert point.admitted_decisions == 5
    assert point.errors_admitted == 1
    assert Decimal(point.coverage or "0") > Decimal(prefix.coverage or "0")
