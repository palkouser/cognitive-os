"""Sprint 21A: the learning substrate's contracts and their structural invariants.

Every test here targets an invariant that must hold without a reviewer noticing,
because review does not run in CI.
"""

from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import pytest
from pydantic import ValidationError

from cognitive_os.domain.learned import (
    BaselineKind,
    BaselineLadder,
    BaselineRung,
    CorpusRole,
    CounterfactualLabel,
    CounterfactualLabelValue,
    CounterfactualVariation,
    DistributionComparison,
    DivergenceVerdict,
    FeatureSchema,
    ForgettingAssessment,
    ForgettingVerdict,
    LabelBalance,
    LearnedArtifactFormat,
    LearnedCapabilityClass,
    LearnedComponentDescriptor,
    LearnedComponentTier,
    LearnedDatasetSnapshot,
    LearnedExplanationKind,
    LearnedPrediction,
    LearnedPromotionAssessment,
    LearnedPromotionDecision,
    LearnedResourceClass,
    LearnedShadowResult,
    MandatoryPathInvariance,
    NumericFeature,
    OutOfDistributionAssessment,
    ProvenanceClass,
    SituationVector,
)

NOW = datetime(2026, 7, 25, tzinfo=UTC)
DIGEST = "a" * 64
OTHER_DIGEST = "b" * 64


def situation(**overrides: object) -> SituationVector:
    payload: dict[str, object] = {
        "surface": "context.reranking",
        "task_signature_hash": DIGEST,
        "problem_domain": "mathematics",
        "numeric_features": (NumericFeature(name="candidate_count", value=Decimal(4)),),
        "categorical_features": (("trust_class", "system"),),
        "prohibited_feature_check": True,
    }
    payload.update(overrides)
    return SituationVector(**payload)  # type: ignore[arg-type]


def descriptor(**overrides: object) -> LearnedComponentDescriptor:
    payload: dict[str, object] = {
        "component_id": "context.reranker.knn",
        "version": "1",
        "surface": "context.reranking",
        "tier": LearnedComponentTier.NON_PARAMETRIC,
        "capability_class": LearnedCapabilityClass.RANKING,
        "resource_class": LearnedResourceClass.CPU,
        "artifact_format": LearnedArtifactFormat.NONE,
        "supports_abstention": True,
        "explanation_kind": LearnedExplanationKind.NEIGHBOURS,
        "deterministic_baseline": "context.ranking.weighted_rrf",
        "declared_limitations": ("self-play distribution only",),
    }
    payload.update(overrides)
    return LearnedComponentDescriptor(**payload)  # type: ignore[arg-type]


def feature_schema() -> FeatureSchema:
    return FeatureSchema(
        feature_schema_id="context-reranking",
        version=1,
        surface="context.reranking",
        encoding_version="situation-v1",
        numeric_names=("candidate_count",),
        categorical_names=("trust_class",),
        prohibited_features=("prompt_body", "credential"),
        missing_value_policy="reject",
        created_at=NOW,
    )


def dataset(**overrides: object) -> LearnedDatasetSnapshot:
    payload: dict[str, object] = {
        "dataset_id": uuid4(),
        "revision": 1,
        "corpus_role": CorpusRole.TRAINING,
        "surface": "context.reranking",
        "feature_schema": feature_schema(),
        "item_provenance_classes": (ProvenanceClass.SELF_PLAY,),
        "observation_count": 10,
        "domain_distribution": (("mathematics", 10),),
        "split_manifest_hash": DIGEST,
        "usage_rights_verified": True,
        "distribution_limitations": ("self-play distribution only",),
        "created_at": NOW,
    }
    payload.update(overrides)
    return LearnedDatasetSnapshot(**payload)  # type: ignore[arg-type]


def forgetting(**overrides: object) -> ForgettingAssessment:
    payload: dict[str, object] = {
        "assessment_id": uuid4(),
        "session_id": uuid4(),
        "baseline_manifest_hash": DIGEST,
        "per_domain_before": (("mathematics", 18),),
        "per_domain_after": (("mathematics", 18),),
        "regressed_cases": (),
        "retained_case_count": 18,
        "tolerance": 0,
        "verdict": ForgettingVerdict.RETAINED,
        "created_at": NOW,
    }
    payload.update(overrides)
    return ForgettingAssessment(**payload)  # type: ignore[arg-type]


def invariance(**overrides: object) -> MandatoryPathInvariance:
    payload: dict[str, object] = {
        "record_id": uuid4(),
        "component_id": "context.reranker.knn",
        "case_set_hash": DIGEST,
        "case_count": 51,
        "decision_hash_absent": DIGEST,
        "decision_hash_disabled": DIGEST,
        "decision_hash_abstaining": DIGEST,
        "created_at": NOW,
    }
    payload.update(overrides)
    return MandatoryPathInvariance(**payload)  # type: ignore[arg-type]


class TestSituationEncoding:
    def test_prohibited_feature_check_is_mandatory(self) -> None:
        with pytest.raises(ValidationError, match="prohibited-feature check"):
            situation(prohibited_feature_check=False)

    def test_features_are_canonically_ordered_so_hashing_is_stable(self) -> None:
        first = situation(
            numeric_features=(
                NumericFeature(name="b", value=Decimal(2)),
                NumericFeature(name="a", value=Decimal(1)),
            )
        )
        second = situation(
            numeric_features=(
                NumericFeature(name="a", value=Decimal(1)),
                NumericFeature(name="b", value=Decimal(2)),
            )
        )
        assert first.content_hash == second.content_hash

    def test_duplicate_feature_names_are_rejected(self) -> None:
        with pytest.raises(ValidationError, match="unique"):
            situation(
                numeric_features=(
                    NumericFeature(name="a", value=Decimal(1)),
                    NumericFeature(name="a", value=Decimal(2)),
                )
            )

    def test_a_schema_cannot_declare_a_prohibited_feature_as_a_feature(self) -> None:
        with pytest.raises(ValidationError, match="prohibited features are present"):
            FeatureSchema(
                feature_schema_id="bad",
                version=1,
                surface="context.reranking",
                encoding_version="situation-v1",
                numeric_names=("credential",),
                prohibited_features=("credential",),
                missing_value_policy="reject",
                created_at=NOW,
            )


class TestCounterfactualLabelling:
    def test_a_real_governed_run_cannot_be_ablated(self) -> None:
        """The counterfactual is unobtainable, so the label must be impossible."""
        with pytest.raises(ValidationError, match="cannot be varied"):
            CounterfactualLabel(
                label_id=uuid4(),
                surface="context.reranking",
                case_id="case-1",
                variation_kind=CounterfactualVariation.CANDIDATE_REMOVED,
                variation_identity="assumption:0",
                baseline_outcome="accepted",
                varied_outcome="rejected",
                label=CounterfactualLabelValue.USEFUL,
                determinism_proof=DIGEST,
                provenance_class=ProvenanceClass.REAL_GOVERNED_RUN,
                created_at=NOW,
            )

    def test_a_neutral_label_requires_an_unchanged_outcome(self) -> None:
        with pytest.raises(ValidationError, match="unchanged outcome"):
            CounterfactualLabel(
                label_id=uuid4(),
                surface="context.reranking",
                case_id="case-1",
                variation_kind=CounterfactualVariation.CANDIDATE_REMOVED,
                variation_identity="assumption:0",
                baseline_outcome="accepted",
                varied_outcome="rejected",
                label=CounterfactualLabelValue.NEUTRAL,
                determinism_proof=DIGEST,
                provenance_class=ProvenanceClass.SELF_PLAY,
                created_at=NOW,
            )

    def test_a_useful_label_requires_a_changed_outcome(self) -> None:
        with pytest.raises(ValidationError, match="changed outcome"):
            CounterfactualLabel(
                label_id=uuid4(),
                surface="context.reranking",
                case_id="case-1",
                variation_kind=CounterfactualVariation.CANDIDATE_REMOVED,
                variation_identity="assumption:0",
                baseline_outcome="accepted",
                varied_outcome="accepted",
                label=CounterfactualLabelValue.USEFUL,
                determinism_proof=DIGEST,
                provenance_class=ProvenanceClass.SELF_PLAY,
                created_at=NOW,
            )

    def test_a_single_class_label_set_is_reported_as_degenerate(self) -> None:
        """A single-class label set carries no signal, whichever class it is."""
        assert LabelBalance(useful=228, neutral=0, harmful=0).degenerate is True
        assert LabelBalance(useful=200, neutral=28, harmful=0).degenerate is False
        assert LabelBalance(useful=0, neutral=0, harmful=0).degenerate is False


class TestCorpusRoleSeparation:
    def test_a_training_dataset_cannot_contain_real_run_evidence(self) -> None:
        with pytest.raises(ValidationError, match="uncontaminated"):
            dataset(
                item_provenance_classes=(
                    ProvenanceClass.SELF_PLAY,
                    ProvenanceClass.REAL_GOVERNED_RUN,
                )
            )

    def test_an_evaluation_dataset_may_contain_real_run_evidence(self) -> None:
        snapshot = dataset(
            corpus_role=CorpusRole.EVALUATION,
            item_provenance_classes=(ProvenanceClass.REAL_GOVERNED_RUN,),
            usage_rights_verified=False,
        )
        assert snapshot.corpus_role is CorpusRole.EVALUATION

    def test_a_training_dataset_requires_verified_usage_rights(self) -> None:
        with pytest.raises(ValidationError, match="usage rights"):
            dataset(usage_rights_verified=False)

    def test_a_dataset_must_state_its_distribution_limitations(self) -> None:
        with pytest.raises(ValidationError, match="distribution limitations"):
            dataset(distribution_limitations=())


class TestShadowEvidence:
    def test_shadow_mode_cannot_change_the_executed_decision(self) -> None:
        with pytest.raises(ValidationError, match="cannot change the executed decision"):
            LearnedShadowResult(
                prediction_id=uuid4(),
                component_id="context.reranker.knn",
                deterministic_baseline_decision="order-a",
                learned_shadow_decision="order-b",
                executed_decision="order-b",
                agreement=True,
                created_at=NOW,
            )

    def test_an_unexecuted_counterfactual_outcome_cannot_be_recorded(self) -> None:
        """The field is typed `None`, so even an explicit attempt fails."""
        with pytest.raises(ValidationError):
            LearnedShadowResult(
                prediction_id=uuid4(),
                component_id="context.reranker.knn",
                deterministic_baseline_decision="order-a",
                learned_shadow_decision="order-b",
                executed_decision="order-a",
                agreement=False,
                shadow_actual_outcome="it would have worked",  # type: ignore[arg-type]
                created_at=NOW,
            )

    def test_recorded_agreement_must_match_the_decisions(self) -> None:
        with pytest.raises(ValidationError, match="agreement does not match"):
            LearnedShadowResult(
                prediction_id=uuid4(),
                component_id="context.reranker.knn",
                deterministic_baseline_decision="order-a",
                learned_shadow_decision="order-b",
                executed_decision="order-a",
                agreement=True,
                created_at=NOW,
            )


class TestAbstention:
    def test_an_abstaining_prediction_carries_no_payload(self) -> None:
        with pytest.raises(ValidationError, match="cannot carry a prediction payload"):
            LearnedPrediction(
                prediction_id=uuid4(),
                component_id="context.reranker.knn",
                situation=situation(),
                prediction="order-b",
                confidence=Decimal("0.1"),
                abstained=True,
                created_at=NOW,
            )

    def test_a_non_abstaining_prediction_must_carry_something(self) -> None:
        with pytest.raises(ValidationError, match="must carry a prediction"):
            LearnedPrediction(
                prediction_id=uuid4(),
                component_id="context.reranker.knn",
                situation=situation(),
                confidence=Decimal("0.9"),
                abstained=False,
                created_at=NOW,
            )

    def test_a_component_that_cannot_abstain_is_not_promotable(self) -> None:
        assert descriptor(supports_abstention=False).promotable is False
        assert descriptor().promotable is True


class TestMandatoryPathInvariance:
    def test_identical_only_when_all_three_configurations_agree(self) -> None:
        assert invariance().identical is True
        assert invariance(decision_hash_disabled=OTHER_DIGEST).identical is False
        assert invariance(decision_hash_abstaining=OTHER_DIGEST).identical is False

    def test_a_pre_d2_record_still_loads_without_the_fourth_hash(self) -> None:
        """S21D2-057 is additive: a three-hash record is a complete proof of what it covers."""
        record = invariance()

        assert record.decision_hash_artifact_unavailable is None
        assert record.covers_artifact_unavailable is False
        assert record.identical is True

    def test_the_fourth_configuration_is_included_once_it_is_present(self) -> None:
        """The state the component did not choose: present, enabled, artifact unloadable."""
        assert invariance(decision_hash_artifact_unavailable=DIGEST).identical is True
        assert invariance(decision_hash_artifact_unavailable=OTHER_DIGEST).identical is False
        assert invariance(decision_hash_artifact_unavailable=DIGEST).covers_artifact_unavailable


class TestForgettingGate:
    def test_regressed_cases_beyond_tolerance_force_a_regressed_verdict(self) -> None:
        with pytest.raises(ValidationError, match="require a regressed verdict"):
            forgetting(regressed_cases=("domain-long-mult",), verdict=ForgettingVerdict.RETAINED)

    def test_a_regressed_verdict_requires_evidence(self) -> None:
        with pytest.raises(ValidationError, match="requires regressed cases"):
            forgetting(regressed_cases=(), verdict=ForgettingVerdict.REGRESSED)

    def test_regression_within_tolerance_may_be_retained(self) -> None:
        assert (
            forgetting(
                regressed_cases=("domain-long-mult",),
                tolerance=1,
                verdict=ForgettingVerdict.RETAINED,
            ).verdict
            is ForgettingVerdict.RETAINED
        )


class TestDistributionComparison:
    def comparison(self, **overrides: object) -> DistributionComparison:
        payload: dict[str, object] = {
            "comparison_id": uuid4(),
            "training_dataset_id": uuid4(),
            "evaluation_dataset_id": uuid4(),
            "compared_features": ("problem_domain",),
            "per_feature_divergence": (("problem_domain", Decimal("0.05")),),
            "training_sample_count": 10_000,
            "evaluation_sample_count": 13,
            "minimum_sample_threshold": 300,
            "verdict": DivergenceVerdict.NOT_ESTABLISHED,
            "limitations": ("real-run corpus is small",),
            "created_at": NOW,
        }
        payload.update(overrides)
        return DistributionComparison(**payload)  # type: ignore[arg-type]

    def test_an_underpowered_comparison_cannot_report_low_divergence(self) -> None:
        with pytest.raises(ValidationError, match="only report"):
            self.comparison(verdict=DivergenceVerdict.LOW)

    def test_conclusive_only_at_or_above_the_declared_threshold(self) -> None:
        assert self.comparison().conclusive is False
        assert self.comparison(evaluation_sample_count=300).conclusive is True

    def test_a_conclusive_comparison_may_report_a_verdict(self) -> None:
        record = self.comparison(evaluation_sample_count=500, verdict=DivergenceVerdict.LOW)
        assert record.verdict is DivergenceVerdict.LOW

    def test_limitations_are_mandatory(self) -> None:
        with pytest.raises(ValidationError, match="must state its limitations"):
            self.comparison(limitations=())


class TestPromotionGate:
    def ladder(self, deterministic: str = "0.60") -> BaselineLadder:
        """A ladder whose strongest non-learned rung is the deterministic one."""
        return BaselineLadder(
            ladder_id=uuid4(),
            surface="context.reranking",
            split="group-aware-by-case",
            rungs=(
                BaselineRung(
                    name="majority",
                    kind=BaselineKind.TRIVIAL,
                    score=Decimal("0.40"),
                    evaluated_count=200,
                    abstained=0,
                    confident_errors=120,
                ),
                BaselineRung(
                    name="weighted_rrf",
                    kind=BaselineKind.DETERMINISTIC,
                    score=Decimal(deterministic),
                    evaluated_count=200,
                    abstained=0,
                    confident_errors=80,
                ),
            ),
            created_at=NOW,
        )

    def out_of_distribution(self, **overrides: object) -> OutOfDistributionAssessment:
        payload: dict[str, object] = {
            "assessment_id": uuid4(),
            "component_id": "context.reranker.knn",
            "held_out_groups": ("mathematics",),
            "evaluated_count": 200,
            "abstained": 200,
            "confident_errors": 0,
            "confidence_threshold": Decimal("0.5"),
            "created_at": NOW,
        }
        payload.update(overrides)
        return OutOfDistributionAssessment(**payload)  # type: ignore[arg-type]

    def assessment(self, **overrides: object) -> LearnedPromotionAssessment:
        payload: dict[str, object] = {
            "assessment_id": uuid4(),
            "component_id": "context.reranker.knn",
            "descriptor": descriptor(),
            "baseline_metric": Decimal("0.60"),
            "candidate_metric": Decimal("0.70"),
            "minimum_material_improvement": Decimal("0.05"),
            "forgetting": forgetting(),
            "invariance": invariance(),
            "baseline_ladder": self.ladder(),
            "out_of_distribution": self.out_of_distribution(),
            "decision": LearnedPromotionDecision.ELIGIBLE_FOR_OPERATOR_APPROVAL,
            "reason": "materially better with retention and invariance proven",
            "created_at": NOW,
        }
        payload.update(overrides)
        return LearnedPromotionAssessment(**payload)  # type: ignore[arg-type]

    def test_a_forgetting_regression_blocks_eligibility(self) -> None:
        with pytest.raises(ValidationError, match="forgetting regression"):
            self.assessment(
                forgetting=forgetting(
                    regressed_cases=("domain-truth-table",),
                    verdict=ForgettingVerdict.REGRESSED,
                )
            )

    def test_unproven_invariance_blocks_eligibility(self) -> None:
        with pytest.raises(ValidationError, match="invariance"):
            self.assessment(invariance=invariance(decision_hash_disabled=OTHER_DIGEST))

    def test_a_component_that_cannot_abstain_blocks_eligibility(self) -> None:
        with pytest.raises(ValidationError, match="cannot abstain"):
            self.assessment(descriptor=descriptor(supports_abstention=False))

    def test_improvement_below_the_material_threshold_blocks_eligibility(self) -> None:
        with pytest.raises(ValidationError, match="material improvement"):
            self.assessment(candidate_metric=Decimal("0.61"))

    def test_a_rejected_decision_needs_no_gate_to_pass(self) -> None:
        record = self.assessment(
            decision=LearnedPromotionDecision.FORGETTING_REGRESSION,
            forgetting=forgetting(
                regressed_cases=("domain-truth-table",),
                verdict=ForgettingVerdict.REGRESSED,
            ),
        )
        assert record.decision is LearnedPromotionDecision.FORGETTING_REGRESSION

    def test_the_happy_path_is_reachable(self) -> None:
        assert self.assessment().decision is LearnedPromotionDecision.ELIGIBLE_FOR_OPERATOR_APPROVAL
