"""The Sprint 21D2 pre-registration contracts for `experience.correction_ranking`.

One module, six frozen decisions, S21D2-011 through S21D2-016. They exist as contracts
rather than as prose because a pre-registration that cannot refuse anything is not a
pre-registration: the point is that fitting and evaluation code fails closed against these
objects, not that a reader is reminded what was intended.

Each contract seals its own hash. S21D2-017 names those hashes in one bundle, and every
later manifest is a hash-bound child of that bundle rather than an edit to it.

Nothing here fits, encodes or evaluates anything. The encoder (S21D2-040), the ranker
(S21D2-043) and the evaluator arrive in W2 and W6 and are checked *against* these.
"""

from __future__ import annotations

from collections.abc import Sequence
from decimal import Decimal
from enum import StrEnum

from pydantic import Field, model_validator

from cognitive_os.domain.common import NonEmptyStr
from cognitive_os.domain.experience import HashedExperienceContract


#: The five experimental partitions. They are children of the campaign protocol, not new
#: `CorpusRole` values: the durable role contract stays two-valued (S21D2-015, §4.2).
class CorrectionPartition(StrEnum):
    TRAINING = "training"
    CALIBRATION = "calibration"
    FINAL_A = "final_a"
    FINAL_B = "final_b"
    CANARY = "canary"


#: Which durable corpus role and provenance each partition is allowed to resolve to.
PARTITION_PROVENANCE: dict[CorrectionPartition, str] = {
    CorrectionPartition.TRAINING: "self_play",
    CorrectionPartition.CALIBRATION: "self_play",
    CorrectionPartition.FINAL_A: "real_governed_run",
    CorrectionPartition.FINAL_B: "real_governed_run",
    CorrectionPartition.CANARY: "real_governed_run",
}

PARTITION_CORPUS_ROLE: dict[CorrectionPartition, str] = {
    CorrectionPartition.TRAINING: "training",
    CorrectionPartition.CALIBRATION: "training",
    CorrectionPartition.FINAL_A: "evaluation",
    CorrectionPartition.FINAL_B: "evaluation",
    CorrectionPartition.CANARY: "evaluation",
}


class CorrectionCampaignMode(StrEnum):
    #: Every candidate runs, in the frozen deterministic baseline order. Used for training,
    #: calibration and both final batches, so labels stay unbiased by any ranking.
    LABEL_ALL = "label_all"
    #: Candidates run in resolved order and execution stops at the first verifier acceptance.
    #: Only reachable after activation.
    STOP_ON_FIRST_ACCEPTED = "stop_on_first_accepted"


# --------------------------------------------------------------------------- S21D2-011


class CorrectionSurfaceContract(HashedExperienceContract):
    """What a correction-ranking score is allowed to change, and what it can never touch."""

    surface: NonEmptyStr = "experience.correction_ranking"
    candidates_per_group: int = Field(default=4, ge=2, le=8)
    decision_unit: NonEmptyStr = "task_group"
    label: NonEmptyStr = "independent_hidden_verifier_accepted_or_rejected"
    prediction: NonEmptyStr = "confidence_scored_ordering_of_opaque_candidate_ids_or_abstention"

    #: The three authorities a score may not acquire. Stated as data so a test can assert on
    #: them rather than on a docstring.
    may_reorder_candidates: bool = True
    may_accept_a_correction: bool = False
    may_skip_the_sandbox: bool = False
    may_skip_the_independent_verifier: bool = False
    may_alter_unrelated_decisions: bool = False

    #: An abstention runs the deterministic ordering. It is a fallback, never a correct
    #: prediction, and it is never a changed decision.
    abstention_executes_baseline_order: bool = True
    abstention_counts_as_changed_decision: bool = False

    #: A task where the verifier accepted nothing stays in the denominator and is reported
    #: separately. Dropping it would manufacture a win out of an unsolvable task.
    task_with_no_accepted_candidate_stays_in_denominator: bool = True

    @model_validator(mode="after")
    def the_forbidden_authorities_stay_forbidden(self) -> CorrectionSurfaceContract:
        if not self.may_reorder_candidates:
            raise ValueError("a surface that cannot reorder has no action at all")
        for field in (
            "may_accept_a_correction",
            "may_skip_the_sandbox",
            "may_skip_the_independent_verifier",
            "may_alter_unrelated_decisions",
            "abstention_counts_as_changed_decision",
        ):
            if getattr(self, field):
                raise ValueError(f"{field} is permanently false for this surface")
        for field in (
            "abstention_executes_baseline_order",
            "task_with_no_accepted_candidate_stays_in_denominator",
        ):
            if not getattr(self, field):
                raise ValueError(f"{field} is permanently true for this surface")
        return self


# --------------------------------------------------------------------------- S21D2-012

#: Pre-outcome, content-derived fields the fitted matrix may contain. Anything absent here
#: is excluded by construction rather than by review.
FITTED_FEATURE_ALLOWLIST: tuple[str, ...] = (
    "problem_domain",
    "declared_problem_type",
    "task_requirement_embedding",
    "candidate_delta_embedding",
    "query_to_candidate_cosine",
    "changed_file_count",
    "hunk_count",
    "added_line_count",
    "removed_line_count",
    "ast_node_count",
    "graph_node_count",
    "graph_edge_count",
    "graph_path_length",
    "operation_kind_counts",
    "declared_verifier_capabilities",
    "missing_value_indicators",
    "encoder_version",
)

#: Every field below is either an oracle, an identity, a hidden control or post-outcome.
#: The scan in S21D2-041 reads the serialized fitted matrix, so a field that arrives under a
#: different name is caught by the allowlist rather than by this list.
FITTED_FEATURE_DENYLIST: tuple[str, ...] = (
    # construction oracles and identities
    "candidate_strategy",
    "candidate_recipe",
    "generator_role",
    "provider_id",
    "model_id",
    "candidate_id",
    "task_id",
    "group_id",
    "repository_id",
    "task_signature",
    "task_hash",
    "source_hash",
    "artifact_hash",
    "split_name",
    "partition",
    # hidden control and verifier internals
    "hidden_tests",
    "golden_solution",
    "control_patch",
    "expected_answer",
    "verifier_command",
    "verifier_output",
    "verifier_status",
    "verifier_score",
    "verifier_error",
    "timeout_result",
    "accepted_hash",
    "outcome_id",
    # post-outcome and label-derived
    "outcome_timestamp",
    "completed_at",
    "retry_count",
    "review_result",
    "promotion_state",
    "label",
    "label_accepted_by_verifier",
    # unrestricted bodies and credentials
    "prompt_body",
    "response_body",
    "credentials",
    "authorization",
    "host_path",
)


class CorrectionFeatureContract(HashedExperienceContract):
    """`correction-ranking-v1`: what may be fitted, and when it must have existed."""

    encoder_version: NonEmptyStr = "correction-ranking-v1"
    allowlist: tuple[NonEmptyStr, ...] = FITTED_FEATURE_ALLOWLIST
    denylist: tuple[NonEmptyStr, ...] = FITTED_FEATURE_DENYLIST

    #: Every allowed field must be derivable from the task and the candidate patch before the
    #: sandbox runs. That is the whole timing rule, and it is what makes the chronology proof
    #: in S21D2-041 a check rather than an assertion.
    availability: NonEmptyStr = "pre_outcome"
    feature_record_sealed_before_execution: bool = True

    #: Numeric features are clipped and scaled from training data only, with the parameters
    #: stored in the model artifact so a raw count cannot silently dominate the embedding.
    numeric_normalisation: NonEmptyStr = "clip_and_scale_from_training_only"
    normalisation_parameters_stored_in_artifact: bool = True

    @model_validator(mode="after")
    def the_two_lists_cannot_overlap(self) -> CorrectionFeatureContract:
        overlap = set(self.allowlist) & set(self.denylist)
        if overlap:
            raise ValueError(f"fields are both allowed and forbidden: {sorted(overlap)}")
        if not self.feature_record_sealed_before_execution:
            raise ValueError("a feature record written after its outcome cannot be pre-outcome")
        if not self.normalisation_parameters_stored_in_artifact:
            raise ValueError("unstored normalisation parameters make the artifact unreplayable")
        return self

    def rejects(self, field: str) -> bool:
        """A field is fitted only if the allowlist names it. Absence is refusal."""
        return field not in self.allowlist


# --------------------------------------------------------------------------- S21D2-013


class CorrectionGroupPolicy(HashedExperienceContract):
    """Group identity, so that memorising a template cannot look like generalising."""

    #: All five components are joined transitively: two tasks sharing any one of them are one
    #: group. Seed variants of a template are the same group, never new evidence.
    components: tuple[NonEmptyStr, ...] = (
        "task_identity",
        "repository_identity",
        "generator_template_lineage",
        "normalized_source_similarity_cluster",
        "source_lineage",
    )
    near_duplicate_similarity_threshold: Decimal = Decimal("0.95")
    transitive_closure: bool = True
    seed_variants_are_one_group: bool = True
    #: One group belongs to exactly one partition, permanently.
    group_belongs_to_exactly_one_partition: bool = True

    @model_validator(mode="after")
    def the_closure_and_the_partition_rule_are_not_optional(
        self,
    ) -> CorrectionGroupPolicy:
        if not self.transitive_closure:
            raise ValueError("without transitive closure a chain of near-duplicates crosses roles")
        if not self.seed_variants_are_one_group:
            raise ValueError("seed variants counted as new groups inflate the corpus")
        if not self.group_belongs_to_exactly_one_partition:
            raise ValueError("a group in two partitions is a leak, not a policy")
        if not Decimal("0") < self.near_duplicate_similarity_threshold <= Decimal("1"):
            raise ValueError("the near-duplicate threshold must be a similarity in (0, 1]")
        return self


# --------------------------------------------------------------------------- S21D2-015


class CorrectionPartitionPlan(HashedExperienceContract):
    """The minimum shape of one partition. Counts may rise before sealing, never fall."""

    partition: CorrectionPartition
    minimum_groups: int = Field(ge=1)
    candidates_per_group: int = Field(default=4, ge=2, le=8)
    minimum_outcomes: int = Field(ge=1)
    provenance: NonEmptyStr
    corpus_role: NonEmptyStr
    mode: CorrectionCampaignMode

    @model_validator(mode="after")
    def the_plan_matches_the_partition_it_names(self) -> CorrectionPartitionPlan:
        if self.provenance != PARTITION_PROVENANCE[self.partition]:
            raise ValueError(
                f"{self.partition.value} must resolve to "
                f"{PARTITION_PROVENANCE[self.partition]}, not {self.provenance}"
            )
        if self.corpus_role != PARTITION_CORPUS_ROLE[self.partition]:
            raise ValueError(
                f"{self.partition.value} must sit under corpus role "
                f"{PARTITION_CORPUS_ROLE[self.partition]}, not {self.corpus_role}"
            )
        stop_first = self.mode is CorrectionCampaignMode.STOP_ON_FIRST_ACCEPTED
        if stop_first and self.partition is not CorrectionPartition.CANARY:
            raise ValueError(
                "stop_on_first_accepted biases labels; only the canary partition may use it"
            )
        if self.partition is CorrectionPartition.CANARY and not stop_first:
            raise ValueError("the canary exists to prove stop-first runtime behaviour")
        if self.minimum_outcomes < self.minimum_groups * self.candidates_per_group:
            raise ValueError(
                "the outcome floor cannot be below groups x candidates, or it is not a floor"
            )
        return self


class CorrectionCampaignProtocol(HashedExperienceContract):
    """The executable selection rules for all five partitions, frozen before members exist.

    This freezes *rules*, not member hashes: the catalogues do not exist yet. S21D2-022 seals
    members as hash-bound children of this protocol.
    """

    partitions: tuple[CorrectionPartitionPlan, ...] = Field(min_length=5, max_length=5)
    minimum_distinct_groups: int = Field(default=115, ge=1)
    minimum_new_groups_relative_to_d1: int = Field(default=85, ge=0)

    #: A recorded failure is evidence. Only an infrastructure interruption with no terminal
    #: record may be rerun, and it is reported separately when it is.
    failed_outcomes_stay_in_the_denominator: bool = True
    retry_to_replace_a_failed_outcome: bool = False
    unrecorded_interruption_may_rerun: bool = True

    #: Fitting code has no API that returns a final or canary member, outcome or body.
    fitting_can_enumerate_final_members: bool = False

    @model_validator(mode="after")
    def every_partition_appears_exactly_once(self) -> CorrectionCampaignProtocol:
        seen = [plan.partition for plan in self.partitions]
        if len(set(seen)) != len(CorrectionPartition):
            raise ValueError("all five partitions must be planned exactly once")
        if self.retry_to_replace_a_failed_outcome:
            raise ValueError("retrying a recorded failure manufactures a label")
        if not self.failed_outcomes_stay_in_the_denominator:
            raise ValueError("a denominator that drops failures is not a denominator")
        if self.fitting_can_enumerate_final_members:
            raise ValueError("fitting that can enumerate the holdout has already opened it")
        planned = sum(plan.minimum_groups for plan in self.partitions)
        if planned < self.minimum_distinct_groups:
            raise ValueError(
                f"the five partitions plan {planned} groups, below the declared "
                f"{self.minimum_distinct_groups}"
            )
        return self


class CorrectionSplitPolicy(HashedExperienceContract):
    """How the one TRAINING dataset divides, and what dataset identity must include."""

    splits: tuple[NonEmptyStr, ...] = ("fit", "calibration")
    both_splits_nonempty: bool = True
    split_union_equals_members: bool = True
    groups_never_cross_splits: bool = True
    #: The C1 builder hashed a split *policy name* alongside members, so two different
    #: assignments over the same members collided onto one dataset ID and a stale snapshot
    #: could be returned. Explicit mode binds the assignment digest itself.
    split_assignment_digest_in_dataset_identity: bool = True
    #: `maximum_page_size` is capped at 500 by configuration and cannot be raised, so explicit
    #: selection pages rather than trusting one listing.
    explicit_selection_pages_listings: bool = True

    @model_validator(mode="after")
    def the_identity_and_isolation_rules_are_not_optional(
        self,
    ) -> CorrectionSplitPolicy:
        if set(self.splits) != {"fit", "calibration"}:
            raise ValueError("the training dataset has exactly a fit and a calibration split")
        for field in (
            "both_splits_nonempty",
            "split_union_equals_members",
            "groups_never_cross_splits",
            "split_assignment_digest_in_dataset_identity",
            "explicit_selection_pages_listings",
        ):
            if not getattr(self, field):
                raise ValueError(f"{field} is required by the D2 split contract")
        return self


# --------------------------------------------------------------------------- S21D2-016


class CorrectionEvaluatorManifest(HashedExperienceContract):
    """Metrics, baseline rule, uncertainty and budgets, frozen before any final outcome."""

    primary_metric: NonEmptyStr = "task_group_first_ranked_candidate_accepted_rate"
    paired_unit: NonEmptyStr = "task_group"
    secondary_metrics: tuple[NonEmptyStr, ...] = (
        "attempts_to_first_accepted",
        "all_candidate_ranking_quality",
        "coverage",
        "abstention_rate",
        "confident_error_rate",
        "latency_ms",
        "verifier_calls",
        "provider_calls",
        "cost",
    )

    #: Derived from the ladder, never supplied by a caller, and named before final access.
    baseline_rule: NonEmptyStr = "strongest_non_learned_rung_on_the_calibration_ladder"
    baseline_ladder_rungs: tuple[NonEmptyStr, ...] = (
        "fixed_input_order",
        "deterministic_static_ordering",
        "lexical_similarity",
        "frozen_minilm_cosine",
        "width_20_bounded_graph",
    )

    minimum_changed_task_decisions: int = Field(default=20, ge=1)
    minimum_absolute_improvement: Decimal = Decimal("0.05")
    minimum_relative_error_reduction: Decimal = Decimal("0.20")
    bootstrap_seed: int = 21041
    bootstrap_resamples: int = Field(default=2000, ge=1)
    bootstrap_confidence: Decimal = Decimal("0.95")
    require_positive_direction_in_each_batch: bool = True

    #: Retention and OOD tolerances. The report threshold and the promotion contract differ on
    #: purpose: promotion is the stricter of the two and is not relaxed to match the report.
    maximum_domain_regression: Decimal = Decimal("0.02")
    maximum_aggregate_regression: Decimal = Decimal("0.01")
    maximum_reported_false_confident_rate: Decimal = Decimal("0.01")
    promotion_confident_ood_errors_allowed: int = 0
    minimum_ood_decisions: int = Field(default=100, ge=1)
    minimum_ood_groups: int = Field(default=10, ge=1)

    #: Coverage and changed-decision rate are selection criteria at calibration, not
    #: reported-only secondaries: a learner that abstains everywhere passes every safety
    #: metric and produces zero changed decisions, which is a silent false negative.
    coverage_is_a_calibration_selection_criterion: bool = True

    #: CPU budgets. The reference path is CPU-first; an available GPU does not open a second
    #: result path.
    maximum_inference_ms_per_task: int = Field(default=250, ge=1)
    maximum_artifact_bytes: int = Field(default=64 * 1024 * 1024, ge=1)

    @model_validator(mode="after")
    def no_final_result_can_select_a_threshold(self) -> CorrectionEvaluatorManifest:
        if self.paired_unit != "task_group":
            raise ValueError(
                "four candidates of one task are correlated; resampling rows would understate "
                "the interval"
            )
        if self.promotion_confident_ood_errors_allowed != 0:
            raise ValueError("the promotion contract allows exactly zero confident OOD errors")
        if not self.require_positive_direction_in_each_batch:
            raise ValueError("an aggregate win over a non-positive batch is a batch effect")
        if not self.coverage_is_a_calibration_selection_criterion:
            raise ValueError(
                "coverage must be selected on, or abstention starves the changed-decision floor"
            )
        if self.minimum_absolute_improvement <= 0 or self.minimum_relative_error_reduction <= 0:
            raise ValueError("a non-positive benefit threshold is not a threshold")
        return self


# --------------------------------------------------------------------------- S21D2-014


class CorrectionPowerAnalysis(HashedExperienceContract):
    """Pre-fit sizing. It may raise a minimum before sealing and may never lower one."""

    #: Task-level first-choice success of any label-blind ordering, measured on D1: every task
    #: has exactly two accepted candidates of four.
    assumed_baseline_first_choice_rate: Decimal = Decimal("0.50")
    target_absolute_improvement: Decimal = Decimal("0.05")
    assumed_disagreement_rate: Decimal
    required_changed_decisions: int = Field(default=20, ge=1)
    planned_final_groups: int = Field(ge=1)
    bootstrap_resamples: int = Field(default=2000, ge=1)
    bootstrap_seed: int = 21041

    #: Condition 15 needs at least 50 qualifying failed-state queries out of the final groups,
    #: and a group only qualifies if its execution actually produced a usable failed/successful
    #: pair. Fifty final groups therefore do not guarantee fifty queries.
    required_retrieval_queries: int = Field(default=50, ge=1)
    assumed_retrieval_yield_per_group: Decimal

    @model_validator(mode="after")
    def the_plan_must_clear_both_floors(self) -> CorrectionPowerAnalysis:
        if not Decimal("0") < self.assumed_disagreement_rate <= Decimal("1"):
            raise ValueError("the disagreement rate must be a proportion in (0, 1]")
        if not Decimal("0") < self.assumed_retrieval_yield_per_group <= Decimal("1"):
            raise ValueError("the retrieval yield must be a proportion in (0, 1]")
        expected_changes = int(self.planned_final_groups * self.assumed_disagreement_rate)
        if expected_changes < self.required_changed_decisions:
            raise ValueError(
                f"{self.planned_final_groups} final groups at a "
                f"{self.assumed_disagreement_rate} disagreement rate yield {expected_changes} "
                f"changed decisions, below the fixed floor of {self.required_changed_decisions}"
            )
        expected_queries = int(self.planned_final_groups * self.assumed_retrieval_yield_per_group)
        if expected_queries < self.required_retrieval_queries:
            raise ValueError(
                f"{self.planned_final_groups} final groups at a "
                f"{self.assumed_retrieval_yield_per_group} yield produce {expected_queries} "
                f"qualifying queries, below the {self.required_retrieval_queries} condition 15 "
                f"needs"
            )
        return self

    @property
    def final_groups_per_batch(self) -> int:
        """Two independent batches, so the plan is split evenly and rounded up."""
        return -(-self.planned_final_groups // 2)


# --------------------------------------------------------------------------- S21D3-010..017

# Revision 3 is additive. The released D2 classes above must keep their byte-for-byte
# serialisation and hashes because D3 diagnoses D2 through those exact contracts.


class CorrectionRankingUnitContractV3(HashedExperienceContract):
    """The units that D2 conflated, frozen before another OOD score exists."""

    revision: int = 3
    group_ranking: NonEmptyStr = "one_order_or_abstention_for_one_four_candidate_task_group"
    candidate_outcome: NonEmptyStr = "one_independently_verified_label_for_one_candidate"
    metamorphic_case: NonEmptyStr = "one_transformation_of_one_group_and_one_ranking_decision"
    coverage: NonEmptyStr = "answered_ranking_decisions_divided_by_all_ranking_decisions"
    abstention: NonEmptyStr = "one_group_decision_that_executes_the_deterministic_order"
    changed_action: NonEmptyStr = "covered_first_action_differs_from_deterministic_baseline"
    confident_error: NonEmptyStr = "covered_first_action_is_wrong_at_or_above_confidence_floor"
    candidates_per_decision: int = Field(default=4, ge=4, le=4)
    decisions_equal_answered_plus_abstained: bool = True
    candidate_outcomes_equal_decisions_times_candidates: bool = True
    rates_name_numerator_and_denominator_units: bool = True

    @model_validator(mode="after")
    def the_units_cannot_be_relabelled(self) -> CorrectionRankingUnitContractV3:
        if self.candidates_per_decision != 4:
            raise ValueError("correction ranking has exactly four candidates per decision")
        for field in (
            "decisions_equal_answered_plus_abstained",
            "candidate_outcomes_equal_decisions_times_candidates",
            "rates_name_numerator_and_denominator_units",
        ):
            if not getattr(self, field):
                raise ValueError(f"{field} is required by revision 3")
        return self


class CorrectionEvaluationCountsV3(HashedExperienceContract):
    """One unit-correct measurement; candidate slots can never pose as decisions."""

    task_groups: int = Field(ge=1)
    metamorphic_cases: int = Field(ge=0)
    ranking_decisions: int = Field(ge=1)
    candidate_outcomes: int = Field(ge=4)
    answered_decisions: int = Field(ge=0)
    abstained_decisions: int = Field(ge=0)
    changed_actions: int = Field(ge=0)
    confident_errors: int = Field(ge=0)
    candidates_per_decision: int = Field(default=4, ge=4, le=4)

    @model_validator(mode="after")
    def the_denominators_must_agree(self) -> CorrectionEvaluationCountsV3:
        if self.ranking_decisions != self.answered_decisions + self.abstained_decisions:
            raise ValueError("ranking decisions must equal answered plus abstained decisions")
        expected_outcomes = self.ranking_decisions * self.candidates_per_decision
        if self.candidate_outcomes != expected_outcomes:
            raise ValueError(
                f"candidate outcomes must equal decisions x four ({expected_outcomes})"
            )
        if self.changed_actions > self.answered_decisions:
            raise ValueError("an abstention cannot be counted as a changed action")
        if self.confident_errors > self.answered_decisions:
            raise ValueError("a confident error must be an answered decision")
        if self.metamorphic_cases and self.ranking_decisions != self.metamorphic_cases:
            raise ValueError("each metamorphic case creates exactly one ranking decision")
        return self


class CorrectionDiagnosticProtocolV3(HashedExperienceContract):
    """The spent-D2 channel diagnostic and its only permitted response."""

    revision: int = 3
    development_only: bool = True
    selection_authority: bool = False
    d2_groups: int = Field(default=10, ge=10, le=10)
    d2_candidate_outcomes: int = Field(default=40, ge=40, le=40)
    d2_ranking_decisions: int = Field(default=10, ge=10, le=10)
    d2_resolved_set_hash: NonEmptyStr = (
        "df2cb5bf817673aeb77bf6a5a46161183c5e135d8777b0bb08dad49324270ca6"
    )
    d2_submanifest_hash: NonEmptyStr = (
        "48d3b766c4dc0104dfe4653e7b808c5c1af6570d9ee9c3cfbf2b8b53082c1381"
    )
    d2_selection_hash: NonEmptyStr = (
        "274a7a932ce110d12892f3dab102f10308ad556c563483d414979cbc69950536"
    )
    d2_setting_identity: NonEmptyStr = (
        "k=3;similarity=0.30;agreement=0.60;confidence=0.55;embedding_weight=0.7"
    )
    cases: tuple[NonEmptyStr, ...] = (
        "clean",
        "identifier_rename_only",
        "issue_rewrite_only",
        "baseline_reorder_only",
        "visible_test_literal_only",
        "combined_identifier_rename_and_issue_rewrite",
    )
    record_fields: tuple[NonEmptyStr, ...] = (
        "raw_inputs",
        "encoded_scalars",
        "named_embedding_channels",
        "embedding_cosine_drift",
        "feature_hash_drift",
        "nearest_neighbours",
        "ranking",
        "confidence",
        "abstention",
        "independent_verifier_labels",
    )
    response_steps: tuple[NonEmptyStr, ...] = (
        "stop_diagnostic_not_reproducible",
        "measure_each_registered_channel_separately",
        "stop_feature_boundary_wrong_on_structural_or_test_input_drift",
        "apply_only_correction_ranking_v2_for_registered_lexical_or_diff_shape_drift",
        "stop_unregistered_feature_response_for_any_other_action_reversal",
    )
    new_d3_members_included: bool = False

    @model_validator(mode="after")
    def this_diagnostic_can_neither_select_nor_expand(
        self,
    ) -> CorrectionDiagnosticProtocolV3:
        if not self.development_only or self.selection_authority or self.new_d3_members_included:
            raise ValueError("the spent-D2 diagnostic is development-only and has no authority")
        if self.d2_candidate_outcomes != self.d2_groups * 4:
            raise ValueError("the D2 diagnostic must retain forty candidate outcomes")
        if self.d2_ranking_decisions != self.d2_groups:
            raise ValueError("the D2 diagnostic contains ten group ranking decisions, not forty")
        if len(self.cases) != 6 or len(set(self.cases)) != 6:
            raise ValueError("the six per-channel diagnostic cases are fixed")
        if len(self.response_steps) != 5:
            raise ValueError("the five-step registered response is fixed")
        return self


FITTED_FEATURE_V2_SCALARS: tuple[str, ...] = (
    "candidate_source_ast_node_count",
    "statement_graph_node_count",
    "statement_graph_edge_count",
    "statement_graph_path_count",
    "declared_verifier_capability_count",
    "missing_value_indicators",
)
FITTED_FEATURE_V2_EMBEDDING: tuple[str, ...] = tuple(
    f"canonical_candidate_source_embedding_{index:03d}" for index in range(384)
)
FITTED_FEATURE_V2_ALLOWLIST: tuple[str, ...] = (
    *FITTED_FEATURE_V2_SCALARS,
    *FITTED_FEATURE_V2_EMBEDDING,
)
FITTED_FEATURE_V2_REMOVED: tuple[str, ...] = (
    "changed_file_count",
    "hunk_count",
    "added_line_count",
    "removed_line_count",
    "task_requirement_embedding",
    "candidate_delta_embedding",
    "query_to_candidate_cosine",
)


class CorrectionFeatureContractV2(HashedExperienceContract):
    """The single D3 intervention, declared before its implementation is measured."""

    encoder_version: NonEmptyStr = "correction-ranking-v2"
    artifact_schema_identity: NonEmptyStr = "correction-ranking-artifact-v2"
    python_grammar: NonEmptyStr = "3.12"
    normalizer_version: NonEmptyStr = "cogos-python-alpha-normalizer-v2"
    # The immutable base model strips string whitespace. Hex is therefore the unambiguous
    # contract representation for a byte prefix whose final byte must be ``0a``.
    canonical_prefix_hex: NonEmptyStr = (
        "636f676f732d636f7272656374696f6e2d736f757263652d6173742d76320a"
        "707974686f6e2d6772616d6d61723d332e31320a"
    )
    canonical_payload: NonEmptyStr = (
        "ast.dump(normalized_tree,annotate_fields=True,include_attributes=False).utf8"
    )
    binding_order: NonEmptyStr = "scope_ast_preorder_then_lexical_first_binding_order"
    placeholder_grammar: NonEmptyStr = "__cogos_sNNNN_bNNNN"
    preserved_inputs: tuple[NonEmptyStr, ...] = (
        "imports_and_aliases",
        "attributes",
        "builtins",
        "magic_names",
        "string_literals",
    )
    allowlist: tuple[NonEmptyStr, ...] = FITTED_FEATURE_V2_ALLOWLIST
    removed_v1_inputs: tuple[NonEmptyStr, ...] = FITTED_FEATURE_V2_REMOVED
    denylist: tuple[NonEmptyStr, ...] = FITTED_FEATURE_DENYLIST
    embedding_channel: NonEmptyStr = "canonical_candidate_source_embedding"
    embedding_dimensions: int = Field(default=384, ge=384, le=384)
    embedding_model: NonEmptyStr = "all-MiniLM-L6-v2"
    embedding_tree_digest: NonEmptyStr = "1110a243fdf4706b3f48f1d95db1a4f5529b4d41"
    availability: NonEmptyStr = "pre_outcome"
    numeric_normalisation: NonEmptyStr = "clip_and_scale_from_training_only"
    normalisation_parameters_stored_in_artifact: bool = True
    feature_member_hashes_stored_in_artifact: bool = True
    code_revision_stored_in_artifact: bool = True
    exact_invariants: tuple[NonEmptyStr, ...] = (
        "coherent_local_identifier_rename_is_byte_vector_rank_and_confidence_identical",
        "issue_rewrite_is_feature_identical",
        "baseline_independent_statement_reorder_is_feature_identical",
        "test_only_literal_substitution_is_feature_identical",
        "seeded_semantic_mutation_changes_canonical_bytes_hash_and_vector",
        "restart_and_input_mapping_order_are_deterministic",
    )
    fail_closed_cases: tuple[NonEmptyStr, ...] = (
        "unsupported_syntax",
        "inconsistent_renaming",
        "parse_failure",
        "mapping_collision",
        "reserved_prefix_collision",
        "reflection_unsafe_binding",
        "ambiguous_binding",
    )

    @model_validator(mode="after")
    def only_the_registered_v2_representation_is_fitted(
        self,
    ) -> CorrectionFeatureContractV2:
        if self.canonical_prefix_bytes != (
            b"cogos-correction-source-ast-v2\npython-grammar=3.12\n"
        ):
            raise ValueError("the canonical byte prefix is exact")
        forbidden = set(self.allowlist) & (set(self.denylist) | set(self.removed_v1_inputs))
        if forbidden:
            raise ValueError(f"v2 fits removed or forbidden fields: {sorted(forbidden)}")
        if len(self.allowlist) != len(FITTED_FEATURE_V2_SCALARS) + self.embedding_dimensions:
            raise ValueError("every fitted embedding dimension must have a semantic name")
        if tuple(self.allowlist[-self.embedding_dimensions :]) != FITTED_FEATURE_V2_EMBEDDING:
            raise ValueError("the fitted matrix must expose all 384 embedding dimensions")
        for field in (
            "normalisation_parameters_stored_in_artifact",
            "feature_member_hashes_stored_in_artifact",
            "code_revision_stored_in_artifact",
        ):
            if not getattr(self, field):
                raise ValueError(f"{field} is required for replay")
        return self

    @property
    def canonical_prefix_bytes(self) -> bytes:
        return bytes.fromhex(self.canonical_prefix_hex)

    def rejects(self, field: str) -> bool:
        return field not in self.allowlist


class CorrectionDatasetProtocolV3(HashedExperienceContract):
    """Feature- and selection-sensitive identity without changing the durable roles."""

    revision: int = 3
    identity_formula: NonEmptyStr = (
        "uuid5(surface:corpus_role:feature_schema_hash:canonical_selection_partition_digest)"
    )
    explicit_member_fields: tuple[NonEmptyStr, ...] = (
        "campaign_identity",
        "partition",
        "observation_id",
        "group_id",
        "feature_record_hash",
        "outcome_hash",
        "member_content_hash",
    )
    grouping_components: tuple[NonEmptyStr, ...] = (
        "task_identity",
        "repository_identity",
        "generator_template_lineage",
        "normalized_source_similarity_cluster",
        "source_lineage",
    )
    transitive_grouping: bool = True
    explicit_selection_only: bool = True
    store_wide_selection_allowed: bool = False
    latest_seal_selection_allowed: bool = False
    mismatched_schema_split_role_or_surface_is_refused: bool = True
    legacy_default_identities_readable_and_unchanged: bool = True
    durable_role: NonEmptyStr = "split_manifest"
    migration_required: bool = False

    @model_validator(mode="after")
    def selection_is_an_authority_not_a_query(self) -> CorrectionDatasetProtocolV3:
        for field in (
            "transitive_grouping",
            "explicit_selection_only",
            "mismatched_schema_split_role_or_surface_is_refused",
            "legacy_default_identities_readable_and_unchanged",
        ):
            if not getattr(self, field):
                raise ValueError(f"{field} is mandatory")
        if self.store_wide_selection_allowed or self.latest_seal_selection_allowed:
            raise ValueError("store-wide and latest-seal selection are not evidence authorities")
        if self.migration_required or self.durable_role != "split_manifest":
            raise ValueError("revision 3 reuses the existing split-manifest role and migration")
        return self


class CorrectionPowerYieldAnalysisV3(HashedExperienceContract):
    """The fixed D3 sample and reserve sizes, calculated without outcome access."""

    candidates_per_group: int = Field(default=4, ge=4, le=4)
    fitting_groups: int = Field(default=50, ge=50)
    fitting_outcomes: int = Field(default=200, ge=200)
    calibration_groups: int = Field(default=20, ge=20)
    calibration_outcomes: int = Field(default=80, ge=80)
    final_groups_per_batch: int = Field(default=30, ge=30)
    final_outcomes_per_batch: int = Field(default=120, ge=120)
    canary_groups: int = Field(default=5, ge=5)
    canary_candidate_slots: int = Field(default=20, ge=20)
    transformation_cases_per_group: int = Field(default=6, ge=6, le=6)
    metamorphic_groups_per_stage: int = Field(default=20, ge=20)
    nominal_decisions_per_stage: int = Field(default=120, ge=120)
    minimum_valid_decisions_per_stage: int = Field(default=100, ge=100)
    minimum_candidate_outcomes_per_stage: int = Field(default=400, ge=400)
    retrieval_source_groups: int = Field(default=60, ge=60)
    minimum_qualifying_queries: int = Field(default=50, ge=50)
    assumed_final_changed_decision_rate: Decimal = Decimal("0.40")
    assumed_retrieval_yield: Decimal = Decimal("0.85")
    required_final_changed_decisions: int = Field(default=20, ge=20)
    target_absolute_improvement: Decimal = Decimal("0.05")
    bootstrap_seed: int = 21041
    bootstrap_resamples: int = Field(default=2000, ge=2000)

    @model_validator(mode="after")
    def every_floor_has_a_reserve_or_exact_seal(self) -> CorrectionPowerYieldAnalysisV3:
        for groups, outcomes, name in (
            (self.fitting_groups, self.fitting_outcomes, "fitting"),
            (self.calibration_groups, self.calibration_outcomes, "calibration"),
            (self.final_groups_per_batch, self.final_outcomes_per_batch, "final batch"),
            (self.canary_groups, self.canary_candidate_slots, "canary"),
        ):
            if outcomes != groups * self.candidates_per_group:
                raise ValueError(f"{name} outcomes must equal groups x four")
        if (
            self.nominal_decisions_per_stage
            != self.metamorphic_groups_per_stage * self.transformation_cases_per_group
        ):
            raise ValueError("nominal metamorphic decisions must be group-level cases")
        if self.minimum_candidate_outcomes_per_stage != self.minimum_valid_decisions_per_stage * 4:
            raise ValueError("candidate outcome floor must remain separate and fourfold")
        expected_changes = int(
            2 * self.final_groups_per_batch * self.assumed_final_changed_decision_rate
        )
        if expected_changes < self.required_final_changed_decisions:
            raise ValueError("the conservative final changed-decision yield misses the gate")
        expected_queries = int(self.retrieval_source_groups * self.assumed_retrieval_yield)
        if expected_queries < self.minimum_qualifying_queries:
            raise ValueError("retrieval overproduction does not leave fifty qualifying queries")
        return self


class CorrectionTransformationProtocolV3(HashedExperienceContract):
    """Six independently countable transformations for calibration and promotion."""

    revision: int = 3
    cases: tuple[NonEmptyStr, ...] = (
        "identifier_rename_a",
        "identifier_rename_b",
        "issue_rewrite_a",
        "issue_rewrite_b",
        "identifier_rename_a_plus_issue_rewrite_a",
        "identifier_rename_b_plus_issue_rewrite_b",
    )
    stages: tuple[NonEmptyStr, ...] = ("fresh_calibration", "promotion")
    groups_per_stage: int = Field(default=20, ge=20)
    nominal_decisions_per_stage: int = Field(default=120, ge=120)
    minimum_valid_decisions_per_stage: int = Field(default=100, ge=100)
    candidate_outcomes_per_valid_decision: int = Field(default=4, ge=4, le=4)
    case_id_formula: NonEmptyStr = "sha256(stage:source_group_id:case_name:seed)"
    manifest_order_selects_promotion_groups: bool = True
    independent_generator_and_hard_coded_oracles: bool = True
    independent_verifier_labels_every_candidate: bool = True
    d2_calibration_ood_members_reused_for_selection: bool = False
    optional_probes_excluded_from_floor: tuple[NonEmptyStr, ...] = (
        "baseline_independent_statement_reorder",
        "visible_test_equivalent_literal_substitution",
    )
    exact_not_yet_authored_members_deferred_until_s21d3_032: bool = True

    @model_validator(mode="after")
    def cases_are_decisions_not_candidate_slots(
        self,
    ) -> CorrectionTransformationProtocolV3:
        if len(self.cases) != 6 or len(set(self.cases)) != 6:
            raise ValueError("exactly six nominal transformation cases are frozen")
        if self.nominal_decisions_per_stage != self.groups_per_stage * len(self.cases):
            raise ValueError("each transformation case is one group ranking decision")
        for field in (
            "manifest_order_selects_promotion_groups",
            "independent_generator_and_hard_coded_oracles",
            "independent_verifier_labels_every_candidate",
            "exact_not_yet_authored_members_deferred_until_s21d3_032",
        ):
            if not getattr(self, field):
                raise ValueError(f"{field} is mandatory")
        if self.d2_calibration_ood_members_reused_for_selection:
            raise ValueError("spent D2 OOD members have no D3 selection authority")
        return self


class CorrectionRetrievalProtocolV3(HashedExperienceContract):
    """One fixed RRF candidate and unchanged comparators on one unseen holdout."""

    revision: int = 3
    candidate_arm: NonEmptyStr = "equal_weight_lexical_plus_minilm_reciprocal_rank_fusion"
    comparators: tuple[NonEmptyStr, ...] = (
        "no_memory",
        "exact_signature",
        "lexical",
        "minilm_vector",
        "width_20_bounded_ged",
    )
    fusion_constant: int = Field(default=60, ge=60, le=60)
    lexical_weight: Decimal = Decimal("1")
    vector_weight: Decimal = Decimal("1")
    positive_lexical_scores_only: bool = True
    minilm_ranks_complete_eligible_pool: bool = True
    lexical_ranks_complete_positive_pool: bool = True
    missing_arm_contributes_zero: bool = True
    stable_pair_id_tie_break: bool = True
    output_limit: int = Field(default=10, ge=10, le=10)
    output_truncations: int = Field(default=1, ge=1, le=1)
    bounded_ged_in_fusion: bool = False
    parameter_sweep_allowed: bool = False
    one_holdout_read: bool = True
    overproduced_source_groups: int = Field(default=60, ge=60)
    minimum_unseen_queries: int = Field(default=50, ge=50)
    resource_policy_revision: int = Field(default=2, ge=2, le=2)
    maximum_nodes: int = Field(default=64, ge=64, le=64)
    maximum_edges: int = Field(default=128, ge=128, le=128)
    maximum_path_depth: int = Field(default=32, ge=32, le=32)
    vector_shortlist: int = Field(default=20, ge=20, le=20)
    ged_comparison_ms: int = Field(default=90, ge=90, le=90)
    query_budget_ms: int = Field(default=2000, ge=2000, le=2000)
    metrics: tuple[NonEmptyStr, ...] = (
        "recall_at_5",
        "mrr_at_10",
        "ndcg_at_10",
        "p50_latency_ms",
        "p95_latency_ms",
        "maximum_latency_ms",
        "timeouts",
        "coverage",
        "candidates_considered",
        "cutoffs",
        "model_hash",
        "policy_hash",
        "query_hash",
    )

    @model_validator(mode="after")
    def the_single_retrieval_candidate_cannot_turn_into_a_sweep(
        self,
    ) -> CorrectionRetrievalProtocolV3:
        if self.lexical_weight != self.vector_weight or self.fusion_constant != 60:
            raise ValueError("revision 3 freezes equal weights and RRF constant sixty")
        for field in (
            "positive_lexical_scores_only",
            "minilm_ranks_complete_eligible_pool",
            "lexical_ranks_complete_positive_pool",
            "missing_arm_contributes_zero",
            "stable_pair_id_tie_break",
            "one_holdout_read",
        ):
            if not getattr(self, field):
                raise ValueError(f"{field} is mandatory")
        if self.bounded_ged_in_fusion or self.parameter_sweep_allowed:
            raise ValueError("GED and parameter sweeps are outside the frozen RRF arm")
        if self.output_truncations != 1:
            raise ValueError("retrieval output is truncated once, after full-pool fusion")
        return self

    def fused_score(self, lexical_rank: int | None, vector_rank: int | None) -> Decimal:
        """The frozen formula, exposed only to make exact test vectors reviewable."""
        score = Decimal("0")
        if lexical_rank is not None:
            score += self.lexical_weight / Decimal(self.fusion_constant + lexical_rank)
        if vector_rank is not None:
            score += self.vector_weight / Decimal(self.fusion_constant + vector_rank)
        return score


class D3GateBinding(HashedExperienceContract):
    """One Gate L2 condition bound to its metric, floor, evidence and stop state."""

    condition: int = Field(ge=1, le=29)
    metric_or_invariant: NonEmptyStr
    floor_or_rule: NonEmptyStr
    evidence_handle: NonEmptyStr
    predecessor_reuse: bool
    stop_status: NonEmptyStr


class D3OpenGateBinding(HashedExperienceContract):
    """One still-open Gate D1 condition and its independent D3 closure authority."""

    condition: int
    closure_rule: NonEmptyStr
    evidence_handle: NonEmptyStr
    status: NonEmptyStr = "open"


class D3GateManifest(HashedExperienceContract):
    """Every D3 gate and the typed stop chain frozen before measurement."""

    revision: int = 3
    gate_l2: tuple[D3GateBinding, ...] = Field(min_length=29, max_length=29)
    gate_d1_open: tuple[D3OpenGateBinding, ...] = Field(min_length=3, max_length=3)
    clean_coverage_floor: Decimal = Decimal("0.80")
    equivalence_coverage_floor: Decimal = Decimal("0.80")
    maximum_equivalence_coverage_loss: Decimal = Decimal("0.05")
    action_preservation_floor: Decimal = Decimal("1.00")
    calibration_confident_equivalence_errors_allowed: int = 0
    minimum_changed_clean_decisions: int = Field(default=1, ge=1)
    bootstrap_seed: int = 21041
    bootstrap_resamples: int = Field(default=2000, ge=2000)
    first_failure_precedence: bool = True
    typed_not_opened_required_fields: tuple[NonEmptyStr, ...] = (
        "status",
        "item",
        "parent_stop_hash",
        "reason",
        "recorded_at",
        "content_hash",
    )

    @model_validator(mode="after")
    def every_gate_has_exactly_one_frozen_binding(self) -> D3GateManifest:
        if {binding.condition for binding in self.gate_l2} != set(range(1, 30)):
            raise ValueError("Gate L2 conditions 1 through 29 must appear exactly once")
        if {binding.condition for binding in self.gate_d1_open} != {6, 7, 15}:
            raise ValueError("the three open Gate D1 conditions are 6, 7 and 15")
        if not self.first_failure_precedence:
            raise ValueError("dependent work must bind to the first failed decision")
        if "parent_stop_hash" not in self.typed_not_opened_required_fields:
            raise ValueError("a not-opened child without its parent stop hash is untraceable")
        return self


# Revision 4 is additive for the same reason revision 3 was: D4 reads D3's evidence through the
# revision-3 classes above, so their serialisation and hashes stay byte-identical. What follows
# is S21D4-010's counting rule, and it exists because D3 counted 120 ranking decisions that were
# 20 decisions replicated six times. Nothing above it could have refused that, because nothing
# above it asked how many of the counted decisions were distinct.


#: The one field name every revision-4 rate is divided by. It is spelled once, here, so a
#: payload cannot name a denominator it did not use.
INDEPENDENT_DENOMINATOR = "independent_decisions"

INDEPENDENCE_RULE = (
    "two counted decisions are the same decision when their fitted feature vectors are equal; "
    "independence is equality of the fitted vector, not of the task, the seed or the transform"
)


def decision_census(feature_hashes: Sequence[str]) -> tuple[int, int, int]:
    """`(nominal, independent, replicated)` for one decision set.

    The caller passes one hash of the *fitted* feature vector per counted decision, because that
    is what the rule is about. A set of six semantics-preserving transformations of one group
    encodes to one vector six times over and is therefore one decision with five replicas, which
    is exactly what S21D4-001 found in D3's grid.
    """
    nominal = len(feature_hashes)
    independent = len(set(feature_hashes))
    return nominal, independent, nominal - independent


class DecisionCensusV4(HashedExperienceContract):
    """How many decisions were counted, how many were distinct, and how many were replicas."""

    revision: int = 4
    nominal_decisions: int = Field(ge=0)
    independent_decisions: int = Field(ge=0)
    replicated_decisions: int = Field(ge=0)
    independence_rule: NonEmptyStr = INDEPENDENCE_RULE
    #: Named in the payload rather than only in the code, so a reader of the stored bytes can
    #: see which denominator produced the rates without consulting the producer.
    rate_denominator: NonEmptyStr = INDEPENDENT_DENOMINATOR

    @model_validator(mode="after")
    def the_triple_must_add_up_and_name_its_denominator(self) -> DecisionCensusV4:
        if self.nominal_decisions != self.independent_decisions + self.replicated_decisions:
            raise ValueError("nominal decisions must equal independent plus replicated decisions")
        if self.rate_denominator != INDEPENDENT_DENOMINATOR:
            raise ValueError(
                f"revision 4 rates are taken over {INDEPENDENT_DENOMINATOR}; a set reporting a "
                f"rate over {self.rate_denominator!r} is reporting a replicated denominator"
            )
        return self

    @classmethod
    def from_feature_hashes(cls, feature_hashes: Sequence[str]) -> DecisionCensusV4:
        nominal, independent, replicated = decision_census(feature_hashes)
        return cls(
            nominal_decisions=nominal,
            independent_decisions=independent,
            replicated_decisions=replicated,
        )


class CorrectionDecisionSetV4(HashedExperienceContract):
    """One measured decision set. Every rate below is over the independent denominator.

    The counts are of *independent* decisions throughout. A replica is invariance evidence — it
    says the encoder did not move when the source was renamed — and it is reported as such by the
    census, but it never enlarges a numerator or a denominator here.
    """

    revision: int = 4
    label: NonEmptyStr
    census: DecisionCensusV4
    answered_decisions: int = Field(ge=0)
    correct_decisions: int = Field(ge=0)
    confident_errors: int = Field(ge=0)
    changed_actions: int = Field(ge=0)

    @model_validator(mode="after")
    def no_count_may_exceed_the_independent_set(self) -> CorrectionDecisionSetV4:
        if self.answered_decisions > self.census.independent_decisions:
            raise ValueError("more answered decisions than independent decisions")
        for name in ("correct_decisions", "confident_errors", "changed_actions"):
            if getattr(self, name) > self.answered_decisions:
                raise ValueError(f"{name} counts an abstention as an answer")
        if self.correct_decisions + self.confident_errors > self.answered_decisions:
            raise ValueError("an answered decision is either correct or a confident error")
        return self

    def _over_independent(self, numerator: int) -> Decimal | None:
        denominator = self.census.independent_decisions
        return Decimal(numerator) / Decimal(denominator) if denominator else None

    @property
    def coverage(self) -> Decimal | None:
        """Answered independent decisions over all independent decisions."""
        return self._over_independent(self.answered_decisions)

    @property
    def accuracy(self) -> Decimal | None:
        """Correct answers over answered independent decisions."""
        answered = self.answered_decisions
        return Decimal(self.correct_decisions) / Decimal(answered) if answered else None

    @property
    def confident_error_rate(self) -> Decimal | None:
        """Confident errors over answered independent decisions."""
        answered = self.answered_decisions
        return Decimal(self.confident_errors) / Decimal(answered) if answered else None


#: Exported for schema generation. They live in `cognitive_os.learning` rather than
#: `cognitive_os.domain`, and are exported anyway, because the acceptance for S21D4-020 is that
#: the published schema refuses a decision payload that omits the triple — a refusal that only
#: exists if the triple is in the published schema.
PUBLIC_CORRECTION_COUNTING_CONTRACTS: tuple[type[HashedExperienceContract], ...] = (
    DecisionCensusV4,
    CorrectionDecisionSetV4,
)
