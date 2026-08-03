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
    def the_closure_and_the_partition_rule_are_not_optional(self) -> CorrectionGroupPolicy:
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
    def the_identity_and_isolation_rules_are_not_optional(self) -> CorrectionSplitPolicy:
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
