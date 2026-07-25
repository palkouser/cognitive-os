"""Sprint 21A: the forgetting gate, including the negative test that gives it force.

A gate that has never rejected anything proves nothing, so the deliberately
catastrophic case is a required test rather than an optional one.
"""

from decimal import Decimal
from uuid import uuid4

import pytest
from pydantic import ValidationError

from cognitive_os.domain.learned import (
    BaselineKind,
    BaselineLadder,
    BaselineRung,
    ForgettingVerdict,
    LearnedPromotionAssessment,
    LearnedPromotionDecision,
    MandatoryPathInvariance,
    OutOfDistributionAssessment,
)
from cognitive_os.domains.fixtures import FIXTURE_TIME, build_all_cases
from cognitive_os.infrastructure.learned.reference import AlwaysAbstainingRanker
from cognitive_os.learning.forgetting import assess_forgetting, measure_retention

CASES = build_all_cases()
SAMPLE = CASES[:6]
DIGEST = "a" * 64


def honest_ladder() -> BaselineLadder:
    """A ladder whose deterministic rung sits at the baseline the test claims."""
    return BaselineLadder(
        ladder_id=uuid4(),
        surface="skill.selection",
        split="group-aware-by-case",
        rungs=(
            BaselineRung(
                name="majority",
                kind=BaselineKind.TRIVIAL,
                score=Decimal("0.50"),
                evaluated_count=100,
                abstained=0,
                confident_errors=50,
            ),
            BaselineRung(
                name="requirements_available",
                kind=BaselineKind.DETERMINISTIC,
                score=Decimal("0.60"),
                evaluated_count=100,
                abstained=0,
                confident_errors=40,
            ),
        ),
        created_at=FIXTURE_TIME,
    )


def abstaining_out_of_distribution() -> OutOfDistributionAssessment:
    """Clean on the abstention gate, so the forgetting gate is what is under test."""
    return OutOfDistributionAssessment(
        assessment_id=uuid4(),
        component_id="reference.ranker.abstaining",
        held_out_groups=("mathematics",),
        evaluated_count=100,
        abstained=100,
        confident_errors=0,
        confidence_threshold=Decimal("0.5"),
        created_at=FIXTURE_TIME,
    )


def proven_invariance() -> MandatoryPathInvariance:
    return MandatoryPathInvariance(
        record_id=uuid4(),
        component_id="reference.ranker.abstaining",
        case_set_hash=DIGEST,
        case_count=6,
        decision_hash_absent=DIGEST,
        decision_hash_disabled=DIGEST,
        decision_hash_abstaining=DIGEST,
        created_at=FIXTURE_TIME,
    )


@pytest.mark.asyncio
async def test_retention_is_measured_per_case_across_domains() -> None:
    retention = await measure_retention(SAMPLE)
    assert len(retention) == len(SAMPLE)
    assert all(passed for _, passed in retention.values()), "the fixture baseline passes"
    assert {domain for domain, _ in retention.values()} <= {"mathematics", "physics", "logic"}


@pytest.mark.asyncio
async def test_an_unchanged_measurement_is_retained() -> None:
    before = await measure_retention(SAMPLE)
    after = await measure_retention(SAMPLE)
    assessment = assess_forgetting(before, after, session_id=uuid4())
    assert assessment.verdict is ForgettingVerdict.RETAINED
    assert assessment.regressed_cases == ()
    assert assessment.retained_case_count == len(SAMPLE)


@pytest.mark.asyncio
async def test_a_deliberately_forgetting_component_is_rejected() -> None:
    """The gate's own negative test.

    A component that learns the newest domain and loses an earlier one must be
    rejected, regardless of any improvement it claims elsewhere.
    """
    before = await measure_retention(SAMPLE)
    forgotten = next(case_id for case_id, (domain, _) in before.items() if domain == "mathematics")
    after = {
        case_id: (domain, False if case_id == forgotten else passed)
        for case_id, (domain, passed) in before.items()
    }
    assessment = assess_forgetting(before, after, session_id=uuid4())
    assert assessment.verdict is ForgettingVerdict.REGRESSED
    assert assessment.regressed_cases == (forgotten,)


@pytest.mark.asyncio
async def test_silently_dropping_a_case_counts_as_regression() -> None:
    """The easiest way to fake retention is to stop measuring the case."""
    before = await measure_retention(SAMPLE)
    dropped = sorted(before)[0]
    after = {k: v for k, v in before.items() if k != dropped}
    assessment = assess_forgetting(before, after, session_id=uuid4())
    assert assessment.verdict is ForgettingVerdict.REGRESSED
    assert dropped in assessment.regressed_cases


@pytest.mark.asyncio
async def test_regression_within_an_explicit_tolerance_is_retained() -> None:
    before = await measure_retention(SAMPLE)
    first = sorted(before)[0]
    after = {
        case_id: (domain, False if case_id == first else passed)
        for case_id, (domain, passed) in before.items()
    }
    assessment = assess_forgetting(before, after, session_id=uuid4(), tolerance=1)
    assert assessment.verdict is ForgettingVerdict.RETAINED


def test_retention_that_never_passed_is_not_established() -> None:
    before = {"case-1": ("mathematics", False)}
    assessment = assess_forgetting(before, before, session_id=uuid4())
    assert assessment.verdict is ForgettingVerdict.NOT_ESTABLISHED


def test_an_absent_baseline_is_refused() -> None:
    with pytest.raises(ValueError, match="without a baseline"):
        assess_forgetting({}, {}, session_id=uuid4())


@pytest.mark.asyncio
async def test_a_regressed_assessment_cannot_reach_an_eligible_promotion() -> None:
    """The gate is wired to the promotion decision, not merely recorded beside it."""
    before = await measure_retention(SAMPLE)
    forgotten = sorted(before)[0]
    after = {
        case_id: (domain, False if case_id == forgotten else passed)
        for case_id, (domain, passed) in before.items()
    }
    regressed = assess_forgetting(before, after, session_id=uuid4())

    with pytest.raises(ValidationError, match="forgetting regression"):
        LearnedPromotionAssessment(
            assessment_id=uuid4(),
            component_id="reference.ranker.abstaining",
            descriptor=AlwaysAbstainingRanker().descriptor,
            baseline_metric=Decimal("0.60"),
            candidate_metric=Decimal("0.90"),
            minimum_material_improvement=Decimal("0.05"),
            forgetting=regressed,
            invariance=proven_invariance(),
            baseline_ladder=honest_ladder(),
            out_of_distribution=abstaining_out_of_distribution(),
            decision=LearnedPromotionDecision.ELIGIBLE_FOR_OPERATOR_APPROVAL,
            reason="large target improvement",
            created_at=FIXTURE_TIME,
        )
