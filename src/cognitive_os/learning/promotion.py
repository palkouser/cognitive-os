"""Phase 21.6/21.7: assemble the promotion verdict from measured evidence only.

Nothing here decides anything on its own. It gathers what the ladder, the forgetting
gate, the invariance gate, and the distribution comparison measured, and lets the
contract validators in `domain.learned` refuse an eligibility that the evidence does not
support. That division matters: a builder that could talk itself into eligibility would
be the single point where every other gate becomes advisory.

The expected outcome on the skill-selection surface is a **recorded no-go**, and the plan
sanctions it: "a recorded null result is a valid 21.6 outcome; the substrate's value does
not depend on it." Two independent measurements produce it — the learned component ties
the deterministic rule in distribution, and answers confidently while wrong out of it.
"""

from __future__ import annotations

from collections.abc import Sequence
from decimal import Decimal
from hashlib import sha256
from uuid import NAMESPACE_URL, uuid5

from cognitive_os.domain.learned import (
    BaselineKind,
    CorpusRole,
    CounterfactualLabel,
    DistributionComparison,
    DivergenceVerdict,
    ForgettingAssessment,
    ForgettingVerdict,
    LabelBalance,
    LearnedComponentDescriptor,
    LearnedDatasetSnapshot,
    LearnedPromotionAssessment,
    LearnedPromotionDecision,
    MandatoryPathInvariance,
    ProvenanceClass,
)
from cognitive_os.domains.fixtures import FIXTURE_TIME

from .baselines import LadderReport
from .features import feature_schema
from .selfplay import SURFACE

#: Declared before the comparison is run, so a thin sample cannot be reinterpreted as
#: adequate afterwards. Section 19 of the plan left this open for the 21.1 gate; it is
#: set here at the smallest number that could show a per-domain difference at all.
MINIMUM_COMPARISON_SAMPLE = 100


def _manifest_hash(parts: Sequence[str]) -> str:
    return sha256("|".join(sorted(parts)).encode()).hexdigest()


def training_snapshot(
    labels: Sequence[CounterfactualLabel],
    balance: LabelBalance,
    domain_distribution: Sequence[tuple[str, int]],
) -> LearnedDatasetSnapshot:
    """The self-play corpus, as an immutable training snapshot."""
    return LearnedDatasetSnapshot(
        dataset_id=uuid5(NAMESPACE_URL, f"dataset:training:{SURFACE}:{len(labels)}"),
        revision=1,
        corpus_role=CorpusRole.TRAINING,
        surface=SURFACE,
        feature_schema=feature_schema(),
        item_provenance_classes=(ProvenanceClass.SELF_PLAY,),
        observation_count=len(labels),
        label_balance=balance,
        domain_distribution=tuple(sorted(domain_distribution)),
        split_manifest_hash=_manifest_hash([item.case_id for item in labels]),
        usage_rights_verified=True,
        distribution_limitations=(
            "deterministic self-play over fixture cases only: no real governed traffic, "
            "so it cannot represent the distribution a deployment would see",
            "the 'useful' class is unreachable because every fixture baseline is accepted, "
            "making a three-valued label binary in practice",
        ),
        created_at=FIXTURE_TIME,
    )


def compare_distributions(
    training: LearnedDatasetSnapshot,
    *,
    real_run_count: int,
    real_run_domains: Sequence[tuple[str, int]] = (),
    minimum_sample: int = MINIMUM_COMPARISON_SAMPLE,
) -> DistributionComparison:
    """Gate L condition 7: measure the divergence, or say it is not established.

    Condition 7 is satisfied by measuring and disclosing, not by achieving low
    divergence. With no harvested real traffic the only permitted verdict is
    `NOT_ESTABLISHED`, and the contract enforces that rather than trusting this function
    — a caller cannot report "low divergence" off an empty evaluation set.
    """
    training_domains = dict(training.domain_distribution)
    evaluation_domains = dict(real_run_domains)
    features = tuple(sorted(set(training_domains) | set(evaluation_domains))) or ("problem_domain",)

    divergence: list[tuple[str, Decimal]] = []
    if real_run_count > 0:
        total_training = sum(training_domains.values()) or 1
        for name in features:
            training_share = Decimal(training_domains.get(name, 0)) / Decimal(total_training)
            evaluation_share = Decimal(evaluation_domains.get(name, 0)) / Decimal(real_run_count)
            divergence.append((name, abs(training_share - evaluation_share)))

    conclusive = real_run_count >= minimum_sample
    return DistributionComparison(
        comparison_id=uuid5(
            NAMESPACE_URL, f"divergence:{SURFACE}:{training.observation_count}:{real_run_count}"
        ),
        training_dataset_id=training.dataset_id,
        evaluation_dataset_id=uuid5(
            NAMESPACE_URL, f"dataset:evaluation:{SURFACE}:{real_run_count}"
        ),
        compared_features=features,
        per_feature_divergence=tuple(divergence),
        training_sample_count=training.observation_count,
        evaluation_sample_count=real_run_count,
        minimum_sample_threshold=minimum_sample,
        verdict=(
            # Only reachable with a real sample; kept explicit so the branch is visible.
            DivergenceVerdict.LOW
            if conclusive and all(value < Decimal("0.2") for _, value in divergence)
            else DivergenceVerdict.HIGH
            if conclusive
            else DivergenceVerdict.NOT_ESTABLISHED
        ),
        limitations=(
            (
                f"only {real_run_count} real governed runs are available against a declared "
                f"threshold of {minimum_sample}, so divergence is not established rather "
                "than low",
            )
            if not conclusive
            else ("measured against harvested real governed runs",)
        ),
        created_at=FIXTURE_TIME,
    )


def assess_promotion(
    descriptor: LearnedComponentDescriptor,
    report: LadderReport,
    *,
    forgetting: ForgettingAssessment,
    invariance: MandatoryPathInvariance,
    distribution: DistributionComparison | None = None,
    minimum_material_improvement: Decimal = Decimal("0.05"),
) -> LearnedPromotionAssessment:
    """Turn the ladder into a decision, refusing to round anything in the model's favour.

    `baseline_metric` is taken from the ladder rather than accepted as an argument. That
    is deliberate: it is the one number a caller could otherwise weaken to manufacture an
    apparent improvement, and on this corpus the temptation is concrete — the majority
    rung sits 43 points below the deterministic rung.
    """
    ladder = report.group_aware
    baseline = ladder.strongest_non_learned
    candidate = max(rung.score for rung in ladder.rungs if rung.kind is BaselineKind.LEARNED)
    out_of_distribution = report.out_of_distribution

    # Ordered by how fundamental the failure is, so the recorded decision names the
    # deepest problem rather than whichever check happened to run first. Invariance is
    # first because it is Gate L's defining condition.
    failures: list[tuple[LearnedPromotionDecision, str]] = []
    if not invariance.identical:
        failures.append(
            (
                LearnedPromotionDecision.INVARIANCE_FAILURE,
                "mandatory-path invariance was not proven",
            )
        )
    if forgetting.verdict is ForgettingVerdict.REGRESSED:
        failures.append(
            (
                LearnedPromotionDecision.FORGETTING_REGRESSION,
                f"retention regressed on {len(forgetting.regressed_cases)} cases",
            )
        )
    if not descriptor.promotable:
        failures.append(
            (
                LearnedPromotionDecision.ABSTENTION_UNSUPPORTED,
                "the component cannot abstain, so it cannot fall back",
            )
        )
    if not out_of_distribution.abstains_when_ignorant:
        failures.append(
            (
                LearnedPromotionDecision.ABSTENTION_UNSUPPORTED,
                f"it answered confidently and wrongly {out_of_distribution.confident_errors} "
                f"times on held-out domains while abstaining "
                f"{out_of_distribution.abstained} times",
            )
        )
    if candidate - baseline < minimum_material_improvement:
        failures.append(
            (
                LearnedPromotionDecision.INSUFFICIENT_IMPROVEMENT,
                f"it scored {candidate} against the strongest deterministic baseline "
                f"'{ladder.strongest_deterministic_name}' at {baseline}, short of the "
                f"{minimum_material_improvement} required improvement",
            )
        )

    return LearnedPromotionAssessment(
        assessment_id=uuid5(NAMESPACE_URL, f"promotion:{descriptor.component_id}:{ladder.split}"),
        component_id=descriptor.component_id,
        descriptor=descriptor,
        baseline_metric=baseline,
        candidate_metric=candidate,
        minimum_material_improvement=minimum_material_improvement,
        forgetting=forgetting,
        invariance=invariance,
        baseline_ladder=ladder,
        out_of_distribution=out_of_distribution,
        distribution=distribution,
        decision=(
            failures[0][0] if failures else LearnedPromotionDecision.ELIGIBLE_FOR_OPERATOR_APPROVAL
        ),
        reason=(
            "; ".join(reason for _, reason in failures)
            if failures
            else "every promotion gate passed"
        ),
        created_at=FIXTURE_TIME,
    )
