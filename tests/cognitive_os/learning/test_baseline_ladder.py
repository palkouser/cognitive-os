"""Sprint 21.6: the baseline ladder and the two traps it closes.

Both traps were live before this phase, and both were caught by measurement rather than
by review, so each has a negative test here. A gate that has never rejected anything
proves nothing.
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
from cognitive_os.infrastructure.learned.knn import ExperienceKnn, StoredExperience
from cognitive_os.learning.baselines import (
    build_examples,
    evaluate_ladder,
    group_aware_split,
    held_out_domain_split,
    score_deterministic,
    score_majority,
)
from cognitive_os.learning.features import encode, feature_schema
from cognitive_os.learning.forgetting import assess_forgetting, measure_retention
from cognitive_os.learning.promotion import assess_promotion, compare_distributions
from cognitive_os.learning.selfplay import SURFACE

DIGEST = "c" * 64


def rung(name: str, kind: BaselineKind, score: str, **overrides: object) -> BaselineRung:
    fields: dict[str, object] = {
        "name": name,
        "kind": kind,
        "score": Decimal(score),
        "evaluated_count": 300,
        "abstained": 0,
        "confident_errors": 0,
    }
    fields.update(overrides)
    return BaselineRung(**fields)  # type: ignore[arg-type]


def ladder(*rungs: BaselineRung, split: str = "group-aware-by-case") -> BaselineLadder:
    return BaselineLadder(
        ladder_id=uuid4(),
        surface=SURFACE,
        split=split,
        rungs=rungs,
        created_at=FIXTURE_TIME,
    )


def proven_invariance() -> MandatoryPathInvariance:
    return MandatoryPathInvariance(
        record_id=uuid4(),
        component_id=ExperienceKnn.component_id,
        case_set_hash=DIGEST,
        case_count=6,
        decision_hash_absent=DIGEST,
        decision_hash_disabled=DIGEST,
        decision_hash_abstaining=DIGEST,
        created_at=FIXTURE_TIME,
    )


def clean_out_of_distribution(**overrides: object) -> OutOfDistributionAssessment:
    fields: dict[str, object] = {
        "assessment_id": uuid4(),
        "component_id": ExperienceKnn.component_id,
        "held_out_groups": ("logic", "mathematics", "physics"),
        "evaluated_count": 969,
        "abstained": 969,
        "confident_errors": 0,
        "confidence_threshold": Decimal("0.5"),
        "created_at": FIXTURE_TIME,
    }
    fields.update(overrides)
    return OutOfDistributionAssessment(**fields)  # type: ignore[arg-type]


class TestLadderStructure:
    def test_a_ladder_without_a_deterministic_rung_is_refused(self) -> None:
        """The straw-man trap, closed structurally.

        Reporting only the majority class made a useless kNN look 43 points better than
        baseline. A ladder that omits the deterministic rung is that report.
        """
        with pytest.raises(ValidationError, match="straw man"):
            ladder(
                rung("majority", BaselineKind.TRIVIAL, "0.5666"),
                rung("knn", BaselineKind.LEARNED, "1.0000"),
            )

    def test_the_strongest_non_learned_rung_is_what_must_be_beaten(self) -> None:
        subject = ladder(
            rung("majority", BaselineKind.TRIVIAL, "0.5666"),
            rung("requirements_available", BaselineKind.DETERMINISTIC, "1.0000"),
            rung("knn", BaselineKind.LEARNED, "1.0000"),
        )
        assert subject.strongest_non_learned == Decimal("1.0000")
        assert subject.strongest_deterministic_name == "requirements_available"

    def test_a_learned_rung_never_raises_the_bar_it_must_clear(self) -> None:
        """A learned rung must not be able to become its own baseline."""
        subject = ladder(
            rung("majority", BaselineKind.TRIVIAL, "0.4"),
            rung("deterministic", BaselineKind.DETERMINISTIC, "0.6"),
            rung("knn", BaselineKind.LEARNED, "0.99"),
        )
        assert subject.strongest_non_learned == Decimal("0.6")

    def test_duplicate_rung_names_are_refused(self) -> None:
        with pytest.raises(ValidationError, match="unique"):
            ladder(
                rung("same", BaselineKind.DETERMINISTIC, "0.9"),
                rung("same", BaselineKind.LEARNED, "0.95"),
            )

    def test_a_rung_cannot_abstain_more_often_than_it_ran(self) -> None:
        with pytest.raises(ValidationError, match="abstain more often"):
            rung("x", BaselineKind.LEARNED, "0.5", evaluated_count=10, abstained=11)


class TestPromotionCannotBeGamed:
    def base(self, **overrides: object) -> dict[str, object]:
        subject = ladder(
            rung("majority", BaselineKind.TRIVIAL, "0.5666"),
            rung("requirements_available", BaselineKind.DETERMINISTIC, "1.0000"),
            rung("knn", BaselineKind.LEARNED, "1.0000"),
        )
        fields: dict[str, object] = {
            "assessment_id": uuid4(),
            "component_id": ExperienceKnn.component_id,
            "descriptor": ExperienceKnn().descriptor,
            "baseline_metric": subject.strongest_non_learned,
            "candidate_metric": Decimal("1.0000"),
            "minimum_material_improvement": Decimal("0.05"),
            "forgetting": self.retained(),
            "invariance": proven_invariance(),
            "baseline_ladder": subject,
            "out_of_distribution": clean_out_of_distribution(),
            "decision": LearnedPromotionDecision.REJECTED,
            "reason": "ties the deterministic baseline",
            "created_at": FIXTURE_TIME,
        }
        fields.update(overrides)
        return fields

    def retained(self):
        return assess_forgetting(
            {"case-1": ("mathematics", True)},
            {"case-1": ("mathematics", True)},
            session_id=uuid4(),
        )

    def test_a_weakened_baseline_cannot_be_substituted(self) -> None:
        """The trap, closed. Passing the majority score to manufacture a win now fails."""
        with pytest.raises(ValidationError, match="strongest non-learned rung"):
            LearnedPromotionAssessment(**self.base(baseline_metric=Decimal("0.5666")))  # type: ignore[arg-type]

    def test_the_pin_holds_even_for_a_rejection(self) -> None:
        """A recorded null result must also state the true baseline, or the record lies."""
        with pytest.raises(ValidationError, match="strongest non-learned rung"):
            LearnedPromotionAssessment(
                **self.base(
                    baseline_metric=Decimal("0.0"),
                    decision=LearnedPromotionDecision.REJECTED,
                )
            )  # type: ignore[arg-type]

    def test_a_tie_against_the_deterministic_baseline_is_recordable_as_a_no_go(self) -> None:
        assessment = LearnedPromotionAssessment(**self.base())  # type: ignore[arg-type]
        assert assessment.decision is LearnedPromotionDecision.REJECTED
        assert assessment.candidate_metric == assessment.baseline_metric

    def test_confident_answers_on_an_unseen_group_block_eligibility(self) -> None:
        """The abstention trap: measured 120 confident errors, zero abstentions."""
        with pytest.raises(ValidationError, match="confidently on an unseen group"):
            LearnedPromotionAssessment(
                **self.base(
                    candidate_metric=Decimal("1.0000"),
                    minimum_material_improvement=Decimal("0"),
                    out_of_distribution=clean_out_of_distribution(
                        abstained=0, confident_errors=120
                    ),
                    decision=LearnedPromotionDecision.ELIGIBLE_FOR_OPERATOR_APPROVAL,
                )
            )  # type: ignore[arg-type]

    def test_eligibility_is_reachable_when_every_gate_genuinely_passes(self) -> None:
        """The gate must be passable, or it proves nothing about the failures above."""
        strong = ladder(
            rung("majority", BaselineKind.TRIVIAL, "0.5"),
            rung("requirements_available", BaselineKind.DETERMINISTIC, "0.70"),
            rung("knn", BaselineKind.LEARNED, "0.90"),
        )
        assessment = LearnedPromotionAssessment(
            **self.base(
                baseline_ladder=strong,
                baseline_metric=Decimal("0.70"),
                candidate_metric=Decimal("0.90"),
                decision=LearnedPromotionDecision.ELIGIBLE_FOR_OPERATOR_APPROVAL,
                reason="materially beats the deterministic baseline and abstains when ignorant",
            )
        )  # type: ignore[arg-type]
        assert assessment.decision is LearnedPromotionDecision.ELIGIBLE_FOR_OPERATOR_APPROVAL


class TestMeasuredCorpusFindings:
    """Tests over the real corpus. These are the 21.6 result, pinned."""

    @pytest.mark.asyncio
    async def test_the_deterministic_rule_is_imperfect_on_this_corpus(self) -> None:
        """The finding that produced the null result, inverted — as a tripwire.

        Until Sprint 21C.1 this test asserted the opposite: the deterministic
        `requirements_available` rule scored a perfect 1.0000 with zero
        confident errors, which is precisely why the 21B ladder found no
        headroom and Gate L closed 8/9. Adding the coding domain — whose
        outcomes depend on whether a repair strategy actually succeeds, not on
        which capabilities were declared — broke that perfection.

        The measured numbers are pinned exactly, not bounded. They are the
        Gate L v2 condition 8b headroom evidence, and 21D.3 re-runs the ladder
        against them; a silent drift would move the baseline the learned
        components have to beat.
        """
        examples = await build_examples()
        deterministic = score_deterministic(examples)
        assert deterministic.evaluated_count == 1292
        assert deterministic.score == Decimal("0.9396"), (
            f"the deterministic rule now scores {deterministic.score}; if the corpus "
            "changed on purpose, re-run the ladder in 21D.3 and update this pin"
        )
        assert deterministic.confident_errors == 78, (
            f"confident errors moved to {deterministic.confident_errors}; the "
            "headroom the parametric tiers are measured against changed with it"
        )

    @pytest.mark.asyncio
    async def test_the_majority_baseline_is_far_below_the_deterministic_one(self) -> None:
        """Quantifies the straw man the ladder exists to prevent."""
        examples = await build_examples()
        train, test = group_aware_split(examples)
        majority = score_majority(train, test)
        deterministic = score_deterministic(test)
        assert majority.score < Decimal("0.6")
        assert deterministic.score - majority.score > Decimal("0.4")

    @pytest.mark.asyncio
    async def test_the_learned_rung_does_not_beat_the_deterministic_rung(self) -> None:
        examples = await build_examples()
        train, test = group_aware_split(examples)
        result = await evaluate_ladder(
            examples, split_name="group-aware-by-case", train=train, test=test
        )
        learned = max(item.score for item in result.rungs if item.kind is BaselineKind.LEARNED)
        assert learned <= result.strongest_non_learned

    @pytest.mark.asyncio
    async def test_a_held_out_domain_degrades_the_learned_rung_only(self) -> None:
        """The deterministic rule transfers; stored experience does not."""
        examples = await build_examples()
        train, test = held_out_domain_split(examples, "mathematics")
        result = await evaluate_ladder(
            examples, split_name="held-out-domain:mathematics", train=train, test=test
        )
        learned = next(item for item in result.rungs if item.kind is BaselineKind.LEARNED)
        deterministic = next(
            item for item in result.rungs if item.kind is BaselineKind.DETERMINISTIC
        )
        assert deterministic.score == Decimal("1.0000")
        assert learned.score < deterministic.score

    @pytest.mark.asyncio
    async def test_the_split_partitions_whole_cases(self) -> None:
        """A shared case between partitions would measure memorisation."""
        examples = await build_examples()
        train, test = group_aware_split(examples)
        assert {item.case_id for item in train}.isdisjoint({item.case_id for item in test})
        assert len(train) + len(test) == len(examples)

    @pytest.mark.asyncio
    async def test_the_recorded_verdict_is_a_no_go_for_two_independent_reasons(self) -> None:
        """Phase 21.6's actual result, produced by the real pipeline.

        The safety gates both pass here — retention retained, invariance identical — so
        the no-go is specifically about the component having no value, not about the
        substrate failing. That distinction is the whole point of recording it.
        """
        from cognitive_os.learning.baselines import run_ladder
        from cognitive_os.learning.invariance import verify_invariance
        from cognitive_os.learning.registry import LearnedComponentRegistry

        report = await run_ladder()
        sample = build_all_cases()[:4]
        retention = await measure_retention(sample)
        forgetting = assess_forgetting(retention, retention, session_id=uuid4())

        component = ExperienceKnn()
        registry = LearnedComponentRegistry()
        registry.register(component)
        invariance = await verify_invariance(component.component_id, registry, cases=sample)

        verdict = assess_promotion(
            component.descriptor,
            report,
            forgetting=forgetting,
            invariance=invariance,
        )
        assert verdict.decision is not LearnedPromotionDecision.ELIGIBLE_FOR_OPERATOR_APPROVAL
        assert verdict.forgetting.verdict is ForgettingVerdict.RETAINED
        assert verdict.invariance.identical
        assert verdict.baseline_metric == verdict.candidate_metric, "it ties, it does not lose"
        assert "short of the" in verdict.reason
        assert "confidently and wrongly" in verdict.reason


class TestDistributionComparison:
    @pytest.mark.asyncio
    async def test_no_real_traffic_yields_not_established_rather_than_low(self) -> None:
        """Gate L condition 7 forbids silently not knowing, not high divergence."""
        from cognitive_os.domain.learned import DivergenceVerdict
        from cognitive_os.learning.promotion import training_snapshot
        from cognitive_os.learning.selfplay import build_corpus

        corpus = await build_corpus(case_limit=4)
        snapshot = training_snapshot(
            corpus.labels, corpus.balance, [("mathematics", len(corpus.labels))]
        )
        comparison = compare_distributions(snapshot, real_run_count=0)
        assert comparison.verdict is DivergenceVerdict.NOT_ESTABLISHED
        assert not comparison.conclusive
        assert comparison.evaluation_sample_count == 0
        assert any("not established" in line for line in comparison.limitations)

    @pytest.mark.asyncio
    async def test_a_training_snapshot_cannot_hold_real_run_evidence(self) -> None:
        """The role separation the whole divergence measurement depends on."""
        from cognitive_os.domain.learned import CorpusRole, ProvenanceClass
        from cognitive_os.learning.promotion import training_snapshot
        from cognitive_os.learning.selfplay import build_corpus

        corpus = await build_corpus(case_limit=4)
        snapshot = training_snapshot(corpus.labels, corpus.balance, [("mathematics", 1)])
        assert snapshot.corpus_role is CorpusRole.TRAINING
        assert ProvenanceClass.REAL_GOVERNED_RUN not in snapshot.item_provenance_classes
        with pytest.raises(ValidationError, match="cannot contain real-governed-run"):
            snapshot.model_copy(
                update={"item_provenance_classes": (ProvenanceClass.REAL_GOVERNED_RUN,)}
            ).model_validate(
                snapshot.model_dump()
                | {
                    "item_provenance_classes": [ProvenanceClass.REAL_GOVERNED_RUN.value],
                    "content_hash": "",
                }
            )


class TestFeatureSchema:
    def test_prohibited_features_are_declared_and_absent(self) -> None:
        schema = feature_schema()
        assert schema.prohibited_features
        assert set(schema.categorical_names).isdisjoint(schema.prohibited_features)

    @pytest.mark.asyncio
    async def test_the_encoding_carries_only_the_declared_feature_names(self) -> None:
        """A feature vector containing the answer would "learn" by reading it."""
        from cognitive_os.learning.selfplay import skill_candidates

        case = build_all_cases()[0]
        candidate = (await skill_candidates())[0]
        vector = encode(case, candidate)
        assert {name for name, _ in vector.categorical_features} == set(
            feature_schema().categorical_names
        )
        assert vector.prohibited_feature_check
        assert vector.numeric_features == ()

    @pytest.mark.asyncio
    async def test_the_encoding_is_identical_across_every_domain(self) -> None:
        """Gate L condition 3: one encoding, not one per domain."""
        from cognitive_os.learning.selfplay import skill_candidates

        candidate = (await skill_candidates())[0]
        shapes = set()
        domains = set()
        for case in build_all_cases():
            vector = encode(case, candidate)
            shapes.add(tuple(name for name, _ in vector.categorical_features))
            domains.add(vector.problem_domain)
        assert len(shapes) == 1, f"the encoding differs by domain: {shapes}"
        # Sprint 21C.1: Gate L v2 condition 3 closes on four domains.
        assert len(domains) >= 4, f"Gate L v2 expects >= 4 domains, found {sorted(domains)}"


class TestKnnComponent:
    @pytest.mark.asyncio
    async def test_an_empty_component_abstains_and_reports_unavailable(self) -> None:
        component = ExperienceKnn()
        assert not (await component.health_check()).available
        case, candidate = build_all_cases()[0], None
        from cognitive_os.learning.selfplay import skill_candidates

        candidate = (await skill_candidates())[0]
        prediction = await component.predict(encode(case, candidate))
        assert prediction.abstained
        assert prediction.prediction is None

    @pytest.mark.asyncio
    async def test_remembering_never_mutates_stored_experience(self) -> None:
        """Tier A's forgetting defence is that learning is an append."""
        from cognitive_os.learning.selfplay import skill_candidates

        case = build_all_cases()[0]
        candidate = (await skill_candidates())[0]
        first = ExperienceKnn()
        second = first.remember(
            StoredExperience(situation=encode(case, candidate), label="harmful")
        )
        assert first.size == 0, "the original component must be untouched"
        assert second.size == 1

    @pytest.mark.asyncio
    async def test_the_explanation_is_the_neighbours(self) -> None:
        from cognitive_os.learning.selfplay import skill_candidates

        case = build_all_cases()[0]
        candidate = (await skill_candidates())[0]
        situation = encode(case, candidate)
        component = ExperienceKnn().remember(StoredExperience(situation=situation, label="harmful"))
        prediction = await component.predict(situation)
        assert not prediction.abstained
        assert prediction.prediction == "harmful"
        assert any("neighbour" in line for line in prediction.explanation)

    def test_the_descriptor_declares_its_measured_limitations(self) -> None:
        descriptor = ExperienceKnn().descriptor
        assert descriptor.supports_abstention
        assert descriptor.required_extra is None, "Tier A must need no optional extra"
        assert len(descriptor.declared_limitations) >= 2
