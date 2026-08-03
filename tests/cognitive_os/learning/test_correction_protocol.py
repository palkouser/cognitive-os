"""S21D2-011..016: the pre-registration refuses things, or it is only prose.

Every test here is a refusal. A frozen design that can be edited into agreement with an
inconvenient result has frozen nothing, so each contract is checked by trying to build the
version someone would reach for under pressure — a learner allowed to accept a correction, a
holdout fitting can enumerate, a bootstrap resampled over candidate rows, a final batch sized
below the changed-decision floor.
"""

from __future__ import annotations

from decimal import Decimal

import pytest
from pydantic import ValidationError

from cognitive_os.learning.correction_protocol import (
    FITTED_FEATURE_ALLOWLIST,
    FITTED_FEATURE_DENYLIST,
    CorrectionCampaignMode,
    CorrectionCampaignProtocol,
    CorrectionEvaluatorManifest,
    CorrectionFeatureContract,
    CorrectionGroupPolicy,
    CorrectionPartition,
    CorrectionPartitionPlan,
    CorrectionPowerAnalysis,
    CorrectionSplitPolicy,
    CorrectionSurfaceContract,
)


def five_partitions() -> tuple[CorrectionPartitionPlan, ...]:
    return (
        CorrectionPartitionPlan(
            partition=CorrectionPartition.TRAINING,
            minimum_groups=50,
            minimum_outcomes=200,
            provenance="self_play",
            corpus_role="training",
            mode=CorrectionCampaignMode.LABEL_ALL,
        ),
        CorrectionPartitionPlan(
            partition=CorrectionPartition.CALIBRATION,
            minimum_groups=10,
            minimum_outcomes=40,
            provenance="self_play",
            corpus_role="training",
            mode=CorrectionCampaignMode.LABEL_ALL,
        ),
        CorrectionPartitionPlan(
            partition=CorrectionPartition.FINAL_A,
            minimum_groups=25,
            minimum_outcomes=100,
            provenance="real_governed_run",
            corpus_role="evaluation",
            mode=CorrectionCampaignMode.LABEL_ALL,
        ),
        CorrectionPartitionPlan(
            partition=CorrectionPartition.FINAL_B,
            minimum_groups=25,
            minimum_outcomes=100,
            provenance="real_governed_run",
            corpus_role="evaluation",
            mode=CorrectionCampaignMode.LABEL_ALL,
        ),
        CorrectionPartitionPlan(
            partition=CorrectionPartition.CANARY,
            minimum_groups=5,
            minimum_outcomes=20,
            provenance="real_governed_run",
            corpus_role="evaluation",
            mode=CorrectionCampaignMode.STOP_ON_FIRST_ACCEPTED,
        ),
    )


class TestTheSurfaceCannotGrowAuthority:
    def test_the_default_contract_is_the_bounded_one(self) -> None:
        contract = CorrectionSurfaceContract()

        assert contract.may_reorder_candidates
        assert not contract.may_accept_a_correction
        assert not contract.may_skip_the_independent_verifier
        assert contract.content_hash

    @pytest.mark.parametrize(
        "field",
        [
            "may_accept_a_correction",
            "may_skip_the_sandbox",
            "may_skip_the_independent_verifier",
            "may_alter_unrelated_decisions",
            "abstention_counts_as_changed_decision",
        ],
    )
    def test_no_forbidden_authority_can_be_switched_on(self, field: str) -> None:
        with pytest.raises(ValidationError, match="permanently false"):
            CorrectionSurfaceContract(**{field: True})  # type: ignore[arg-type]

    @pytest.mark.parametrize(
        "field",
        [
            "abstention_executes_baseline_order",
            "task_with_no_accepted_candidate_stays_in_denominator",
        ],
    )
    def test_no_required_guarantee_can_be_switched_off(self, field: str) -> None:
        with pytest.raises(ValidationError, match="permanently true"):
            CorrectionSurfaceContract(**{field: False})  # type: ignore[arg-type]

    def test_a_surface_that_cannot_reorder_is_refused_rather_than_accepted_as_inert(self) -> None:
        with pytest.raises(ValidationError, match="no action at all"):
            CorrectionSurfaceContract(may_reorder_candidates=False)


class TestTheFeatureContractRefusesByAbsence:
    def test_every_denied_field_is_rejected(self) -> None:
        contract = CorrectionFeatureContract()

        assert all(contract.rejects(field) for field in FITTED_FEATURE_DENYLIST)

    def test_every_allowed_field_is_accepted(self) -> None:
        contract = CorrectionFeatureContract()

        assert not any(contract.rejects(field) for field in FITTED_FEATURE_ALLOWLIST)

    def test_an_unknown_field_is_refused_rather_than_admitted(self) -> None:
        """Absence is refusal. A new oracle does not need to be on the denylist to fail."""
        contract = CorrectionFeatureContract()

        assert contract.rejects("some_field_nobody_thought_of")

    def test_the_perfect_oracle_of_d1_is_denied_by_name_as_well(self) -> None:
        assert "candidate_strategy" in FITTED_FEATURE_DENYLIST

    def test_a_field_cannot_be_allowed_and_denied_at_once(self) -> None:
        with pytest.raises(ValidationError, match="both allowed and forbidden"):
            CorrectionFeatureContract(allowlist=("candidate_strategy",))

    def test_a_feature_record_written_after_its_outcome_is_refused(self) -> None:
        with pytest.raises(ValidationError, match="cannot be pre-outcome"):
            CorrectionFeatureContract(feature_record_sealed_before_execution=False)

    def test_unstored_normalisation_parameters_are_refused(self) -> None:
        with pytest.raises(ValidationError, match="unreplayable"):
            CorrectionFeatureContract(normalisation_parameters_stored_in_artifact=False)


class TestTheGroupPolicyKeepsTemplatesTogether:
    def test_the_default_policy_closes_transitively(self) -> None:
        policy = CorrectionGroupPolicy()

        assert policy.transitive_closure
        assert policy.seed_variants_are_one_group
        assert policy.near_duplicate_similarity_threshold == Decimal("0.95")

    @pytest.mark.parametrize(
        ("field", "message"),
        [
            ("transitive_closure", "chain of near-duplicates"),
            ("seed_variants_are_one_group", "inflate the corpus"),
            ("group_belongs_to_exactly_one_partition", "is a leak"),
        ],
    )
    def test_each_isolation_rule_is_mandatory(self, field: str, message: str) -> None:
        with pytest.raises(ValidationError, match=message):
            CorrectionGroupPolicy(**{field: False})  # type: ignore[arg-type]

    @pytest.mark.parametrize("threshold", [Decimal("0"), Decimal("-0.1"), Decimal("1.5")])
    def test_a_nonsense_similarity_threshold_is_refused(self, threshold: Decimal) -> None:
        with pytest.raises(ValidationError):
            CorrectionGroupPolicy(near_duplicate_similarity_threshold=threshold)


class TestTheCampaignProtocolBindsProvenanceToPartition:
    def test_the_planned_five_partitions_validate(self) -> None:
        protocol = CorrectionCampaignProtocol(partitions=five_partitions())

        assert protocol.minimum_distinct_groups == 115
        assert protocol.content_hash

    def test_a_final_batch_declared_self_play_is_refused(self) -> None:
        with pytest.raises(ValidationError, match="must resolve to real_governed_run"):
            CorrectionPartitionPlan(
                partition=CorrectionPartition.FINAL_A,
                minimum_groups=25,
                minimum_outcomes=100,
                provenance="self_play",
                corpus_role="evaluation",
                mode=CorrectionCampaignMode.LABEL_ALL,
            )

    def test_training_declared_real_governed_is_refused(self) -> None:
        with pytest.raises(ValidationError, match="must resolve to self_play"):
            CorrectionPartitionPlan(
                partition=CorrectionPartition.TRAINING,
                minimum_groups=50,
                minimum_outcomes=200,
                provenance="real_governed_run",
                corpus_role="training",
                mode=CorrectionCampaignMode.LABEL_ALL,
            )

    def test_a_final_batch_cannot_stop_at_the_first_acceptance(self) -> None:
        """Stop-first leaves the unattempted candidates unlabelled, which biases the batch."""
        with pytest.raises(ValidationError, match="only the canary partition"):
            CorrectionPartitionPlan(
                partition=CorrectionPartition.FINAL_A,
                minimum_groups=25,
                minimum_outcomes=100,
                provenance="real_governed_run",
                corpus_role="evaluation",
                mode=CorrectionCampaignMode.STOP_ON_FIRST_ACCEPTED,
            )

    def test_the_canary_must_actually_prove_stop_first(self) -> None:
        with pytest.raises(ValidationError, match="prove stop-first"):
            CorrectionPartitionPlan(
                partition=CorrectionPartition.CANARY,
                minimum_groups=5,
                minimum_outcomes=20,
                provenance="real_governed_run",
                corpus_role="evaluation",
                mode=CorrectionCampaignMode.LABEL_ALL,
            )

    def test_an_outcome_floor_below_groups_times_candidates_is_refused(self) -> None:
        with pytest.raises(ValidationError, match="not a floor"):
            CorrectionPartitionPlan(
                partition=CorrectionPartition.TRAINING,
                minimum_groups=50,
                minimum_outcomes=100,
                provenance="self_play",
                corpus_role="training",
                mode=CorrectionCampaignMode.LABEL_ALL,
            )

    def test_retrying_a_recorded_failure_is_refused(self) -> None:
        with pytest.raises(ValidationError, match="manufactures a label"):
            CorrectionCampaignProtocol(
                partitions=five_partitions(), retry_to_replace_a_failed_outcome=True
            )

    def test_a_denominator_that_drops_failures_is_refused(self) -> None:
        with pytest.raises(ValidationError, match="not a denominator"):
            CorrectionCampaignProtocol(
                partitions=five_partitions(), failed_outcomes_stay_in_the_denominator=False
            )

    def test_fitting_that_can_enumerate_the_holdout_is_refused(self) -> None:
        with pytest.raises(ValidationError, match="already opened it"):
            CorrectionCampaignProtocol(
                partitions=five_partitions(), fitting_can_enumerate_final_members=True
            )

    def test_a_partition_cannot_be_planned_twice_in_place_of_another(self) -> None:
        partitions = five_partitions()
        with pytest.raises(ValidationError, match="exactly once"):
            CorrectionCampaignProtocol(partitions=(*partitions[:4], partitions[0]))


class TestTheSplitPolicyBindsIdentityToAssignment:
    def test_the_default_policy_validates(self) -> None:
        policy = CorrectionSplitPolicy()

        assert set(policy.splits) == {"fit", "calibration"}
        assert policy.split_assignment_digest_in_dataset_identity

    def test_dropping_the_assignment_digest_is_refused(self) -> None:
        """Without it, two different splits over the same members share one dataset ID."""
        with pytest.raises(ValidationError, match="required by the D2 split contract"):
            CorrectionSplitPolicy(split_assignment_digest_in_dataset_identity=False)

    def test_unpaged_explicit_selection_is_refused(self) -> None:
        with pytest.raises(ValidationError, match="required by the D2 split contract"):
            CorrectionSplitPolicy(explicit_selection_pages_listings=False)

    def test_groups_crossing_splits_is_refused(self) -> None:
        with pytest.raises(ValidationError, match="required by the D2 split contract"):
            CorrectionSplitPolicy(groups_never_cross_splits=False)

    def test_the_legacy_train_holdout_naming_is_refused(self) -> None:
        with pytest.raises(ValidationError, match="fit and a calibration split"):
            CorrectionSplitPolicy(splits=("train", "holdout"))


class TestTheEvaluatorManifestCannotBeRelaxed:
    def test_the_default_manifest_carries_the_fixed_minima(self) -> None:
        manifest = CorrectionEvaluatorManifest()

        assert manifest.minimum_changed_task_decisions == 20
        assert manifest.minimum_absolute_improvement == Decimal("0.05")
        assert manifest.bootstrap_seed == 21041
        assert manifest.bootstrap_resamples == 2000
        assert manifest.promotion_confident_ood_errors_allowed == 0

    def test_resampling_candidate_rows_instead_of_task_groups_is_refused(self) -> None:
        with pytest.raises(ValidationError, match="understate"):
            CorrectionEvaluatorManifest(paired_unit="candidate_row")

    def test_allowing_a_confident_ood_error_at_promotion_is_refused(self) -> None:
        with pytest.raises(ValidationError, match="exactly zero confident OOD errors"):
            CorrectionEvaluatorManifest(promotion_confident_ood_errors_allowed=1)

    def test_dropping_the_per_batch_direction_requirement_is_refused(self) -> None:
        with pytest.raises(ValidationError, match="batch effect"):
            CorrectionEvaluatorManifest(require_positive_direction_in_each_batch=False)

    def test_demoting_coverage_to_a_reported_only_metric_is_refused(self) -> None:
        """A1/A2 from the surface audit: abstention starves the changed-decision floor."""
        with pytest.raises(ValidationError, match="starves"):
            CorrectionEvaluatorManifest(coverage_is_a_calibration_selection_criterion=False)

    @pytest.mark.parametrize("value", [Decimal("0"), Decimal("-0.05")])
    def test_a_non_positive_benefit_threshold_is_refused(self, value: Decimal) -> None:
        with pytest.raises(ValidationError, match="not a threshold"):
            CorrectionEvaluatorManifest(minimum_absolute_improvement=value)


class TestThePowerAnalysisRefusesAnUnderpoweredPlan:
    def test_a_plan_that_clears_both_floors_validates(self) -> None:
        analysis = CorrectionPowerAnalysis(
            assumed_disagreement_rate=Decimal("0.40"),
            planned_final_groups=50,
            assumed_retrieval_yield_per_group=Decimal("1.0"),
        )

        assert analysis.final_groups_per_batch == 25
        assert analysis.content_hash

    def test_too_few_groups_for_the_changed_decision_floor_is_refused(self) -> None:
        """Thirty percent disagreement over fifty groups is fifteen changes, not twenty."""
        with pytest.raises(ValidationError, match="below the fixed floor"):
            CorrectionPowerAnalysis(
                assumed_disagreement_rate=Decimal("0.30"),
                planned_final_groups=50,
                assumed_retrieval_yield_per_group=Decimal("1.0"),
            )

    def test_raising_the_group_count_repairs_the_same_disagreement_rate(self) -> None:
        analysis = CorrectionPowerAnalysis(
            assumed_disagreement_rate=Decimal("0.30"),
            planned_final_groups=68,
            assumed_retrieval_yield_per_group=Decimal("0.80"),
        )

        assert analysis.planned_final_groups == 68
        assert analysis.final_groups_per_batch == 34

    def test_too_low_a_retrieval_yield_for_condition_15_is_refused(self) -> None:
        """Fifty final groups do not guarantee fifty qualifying failed-state queries."""
        with pytest.raises(ValidationError, match="condition 15 needs"):
            CorrectionPowerAnalysis(
                assumed_disagreement_rate=Decimal("0.40"),
                planned_final_groups=50,
                assumed_retrieval_yield_per_group=Decimal("0.60"),
            )

    @pytest.mark.parametrize("rate", [Decimal("0"), Decimal("1.5")])
    def test_a_nonsense_disagreement_rate_is_refused(self, rate: Decimal) -> None:
        with pytest.raises(ValidationError):
            CorrectionPowerAnalysis(
                assumed_disagreement_rate=rate,
                planned_final_groups=50,
                assumed_retrieval_yield_per_group=Decimal("1.0"),
            )


class TestTheContractsSealTheirOwnHashes:
    def test_identical_contracts_hash_identically(self) -> None:
        assert CorrectionSurfaceContract().content_hash == CorrectionSurfaceContract().content_hash

    def test_a_changed_field_changes_the_hash(self) -> None:
        default = CorrectionEvaluatorManifest()
        stricter = CorrectionEvaluatorManifest(minimum_changed_task_decisions=25)

        assert default.content_hash != stricter.content_hash

    def test_a_declared_hash_that_does_not_match_is_refused(self) -> None:
        with pytest.raises(ValidationError, match="hash mismatch"):
            CorrectionSurfaceContract(content_hash="0" * 64)
