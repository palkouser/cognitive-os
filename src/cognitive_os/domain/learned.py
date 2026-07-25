"""Immutable contracts for the governed learning substrate and its extension seam.

A learned component is an optional, configuration-declared adapter that proposes a
decision on one surface. It never owns a decision: the deterministic path remains
the baseline and the fallback, and every component must be able to abstain.

Three invariants are enforced here rather than in review, because review does not
run in CI:

* an unexecuted counterfactual can never be recorded as an outcome
  (`LearnedShadowResult.shadow_actual_outcome` is typed `None`, copying the
  Sprint 16 routing precedent);
* a training dataset cannot contain evidence harvested from real governed runs,
  which keeps the evaluation corpus uncontaminated and therefore keeps the
  distribution measurement meaningful;
* a promotion assessment cannot become eligible while forgetting was detected or
  while mandatory-path invariance was not proven.
"""

from __future__ import annotations

from decimal import Decimal
from enum import StrEnum
from uuid import UUID

from pydantic import Field, field_validator, model_validator

from .common import ArtifactRef, JsonValue, NonEmptyStr, Sha256Hex, UtcDatetime
from .experience import HashedExperienceContract


class LearnedComponentTier(StrEnum):
    """Trial order from the Sprint 21 plan, ranked by expected success."""

    NON_PARAMETRIC = "non_parametric"
    INCREMENTAL_PARAMETRIC = "incremental_parametric"
    ADAPTER = "adapter"
    RESEARCH = "research"


class LearnedCapabilityClass(StrEnum):
    DISCRIMINATIVE = "discriminative"
    RANKING = "ranking"
    EMBEDDING = "embedding"
    ANOMALY = "anomaly"


class LearnedResourceClass(StrEnum):
    CPU = "cpu"
    CPU_PREFERRED = "cpu_preferred"


class LearnedArtifactFormat(StrEnum):
    """Loading an untrusted pickle is prohibited, so it has no enum member."""

    SAFETENSORS = "safetensors"
    JOBLIB = "joblib"
    NONE = "none"


class LearnedExplanationKind(StrEnum):
    NEIGHBOURS = "neighbours"
    FEATURE_ATTRIBUTION = "feature_attribution"
    NONE = "none"


class LearnedComponentState(StrEnum):
    REGISTERED = "registered"
    SHADOW = "shadow"
    VERIFIED = "verified"
    ACTIVE = "active"
    DISABLED = "disabled"
    RETRACTED = "retracted"


class CorpusRole(StrEnum):
    TRAINING = "training"
    EVALUATION = "evaluation"


class ProvenanceClass(StrEnum):
    """Where an observation came from, which decides what it may be used for."""

    SELF_PLAY = "self_play"
    REAL_GOVERNED_RUN = "real_governed_run"
    OPERATOR_SUPPLIED = "operator_supplied"


class CounterfactualVariation(StrEnum):
    """What was varied to obtain a label."""

    CANDIDATE_REMOVED = "candidate_removed"
    SELECTION_FORCED = "selection_forced"


class CounterfactualLabelValue(StrEnum):
    """The variation's effect relative to the baseline run."""

    USEFUL = "useful"
    NEUTRAL = "neutral"
    HARMFUL = "harmful"


class ForgettingVerdict(StrEnum):
    RETAINED = "retained"
    REGRESSED = "regressed"
    NOT_ESTABLISHED = "not_established"


class DivergenceVerdict(StrEnum):
    LOW = "low"
    HIGH = "high"
    NOT_ESTABLISHED = "not_established"


class LearnedPromotionDecision(StrEnum):
    ELIGIBLE_FOR_OPERATOR_APPROVAL = "eligible_for_operator_approval"
    INSUFFICIENT_IMPROVEMENT = "insufficient_improvement"
    FORGETTING_REGRESSION = "forgetting_regression"
    INVARIANCE_FAILURE = "invariance_failure"
    ABSTENTION_UNSUPPORTED = "abstention_unsupported"
    DISTRIBUTION_NOT_ESTABLISHED = "distribution_not_established"
    REQUIRES_MANUAL_REVIEW = "requires_manual_review"
    REJECTED = "rejected"


class NumericFeature(HashedExperienceContract):
    name: NonEmptyStr
    value: Decimal


class SituationVector(HashedExperienceContract):
    """One decision situation, encoded identically for every domain.

    Credentials, secrets, prompt bodies, and unrestricted text are prohibited as
    features; `prohibited_feature_check` records that the check ran.
    """

    encoding_version: NonEmptyStr = "situation-v1"
    surface: NonEmptyStr
    task_signature_hash: Sha256Hex
    problem_domain: NonEmptyStr
    numeric_features: tuple[NumericFeature, ...] = ()
    categorical_features: tuple[tuple[NonEmptyStr, NonEmptyStr], ...] = ()
    embedding_ref: ArtifactRef | None = None
    prohibited_feature_check: bool

    @field_validator("numeric_features")
    @classmethod
    def unique_numeric_names(cls, value: tuple[NumericFeature, ...]) -> tuple[NumericFeature, ...]:
        if len({item.name for item in value}) != len(value):
            raise ValueError("numeric feature names must be unique")
        return tuple(sorted(value, key=lambda item: item.name))

    @field_validator("categorical_features")
    @classmethod
    def unique_categorical_names(
        cls, value: tuple[tuple[str, str], ...]
    ) -> tuple[tuple[str, str], ...]:
        if len({item[0] for item in value}) != len(value):
            raise ValueError("categorical feature names must be unique")
        return tuple(sorted(value))

    @model_validator(mode="after")
    def prohibited_features_were_checked(self) -> SituationVector:
        if not self.prohibited_feature_check:
            raise ValueError("situation vector requires a completed prohibited-feature check")
        return self


class FeatureSchema(HashedExperienceContract):
    feature_schema_id: NonEmptyStr
    version: int = Field(ge=1)
    surface: NonEmptyStr
    encoding_version: NonEmptyStr
    numeric_names: tuple[NonEmptyStr, ...] = ()
    categorical_names: tuple[NonEmptyStr, ...] = ()
    prohibited_features: tuple[NonEmptyStr, ...]
    missing_value_policy: NonEmptyStr
    created_at: UtcDatetime

    @model_validator(mode="after")
    def prohibitions_are_declared(self) -> FeatureSchema:
        if not self.prohibited_features:
            raise ValueError("a feature schema must declare its prohibited features")
        overlap = (set(self.numeric_names) | set(self.categorical_names)) & set(
            self.prohibited_features
        )
        if overlap:
            raise ValueError(f"prohibited features are present in the schema: {sorted(overlap)}")
        return self


class CounterfactualLabel(HashedExperienceContract):
    """A causal label obtained by varying one decision and re-running the case.

    Two variations are supported, because the two candidate surfaces need
    different ones: removing a candidate input, and forcing a selection the
    deterministic policy would not have made. Both compare against the same
    baseline run, so the three-valued label means the same thing in both.

    Only a deterministic, provider-free run can be varied this way. A replayed run
    fails closed on the changed request (`request_fingerprint` covers the request's
    semantic content), and a live provider response differs for reasons unrelated
    to the variation. `determinism_proof` carries the digest showing the baseline
    re-ran identically before the variation was attempted.
    """

    label_id: UUID
    surface: NonEmptyStr
    case_id: NonEmptyStr
    variation_kind: CounterfactualVariation
    variation_identity: NonEmptyStr
    baseline_outcome: NonEmptyStr
    varied_outcome: NonEmptyStr
    label: CounterfactualLabelValue
    determinism_proof: Sha256Hex
    provenance_class: ProvenanceClass
    created_at: UtcDatetime

    @model_validator(mode="after")
    def only_reproducible_provenance(self) -> CounterfactualLabel:
        if self.provenance_class is ProvenanceClass.REAL_GOVERNED_RUN:
            raise ValueError(
                "a real governed run cannot be varied: the counterfactual is unobtainable"
            )
        unchanged = self.baseline_outcome == self.varied_outcome
        if self.label is CounterfactualLabelValue.NEUTRAL and not unchanged:
            raise ValueError("a neutral label requires an unchanged outcome")
        if self.label is not CounterfactualLabelValue.NEUTRAL and unchanged:
            raise ValueError("a non-neutral label requires a changed outcome")
        return self


class LabelBalance(HashedExperienceContract):
    """Class balance of a label set, so a degenerate corpus is visible up front."""

    useful: int = Field(ge=0)
    neutral: int = Field(ge=0)
    harmful: int = Field(ge=0)

    @property
    def total(self) -> int:
        return self.useful + self.neutral + self.harmful

    @property
    def degenerate(self) -> bool:
        """True when one class holds every label and there is nothing to learn."""
        counts = (self.useful, self.neutral, self.harmful)
        return self.total > 0 and max(counts) == self.total


class LearnedDatasetSnapshot(HashedExperienceContract):
    """An immutable, hash-identified training or evaluation set.

    A training snapshot may not contain real-governed-run evidence. That keeps the
    evaluation corpus uncontaminated, which is the only reason the distribution
    comparison in `DistributionComparison` means anything.
    """

    dataset_id: UUID
    revision: int = Field(ge=1)
    corpus_role: CorpusRole
    surface: NonEmptyStr
    feature_schema: FeatureSchema
    item_provenance_classes: tuple[ProvenanceClass, ...]
    observation_count: int = Field(ge=1)
    label_balance: LabelBalance | None = None
    domain_distribution: tuple[tuple[NonEmptyStr, int], ...]
    split_manifest_hash: Sha256Hex
    usage_rights_verified: bool
    distribution_limitations: tuple[NonEmptyStr, ...]
    created_at: UtcDatetime

    @field_validator("item_provenance_classes")
    @classmethod
    def canonical_provenance(
        cls, value: tuple[ProvenanceClass, ...]
    ) -> tuple[ProvenanceClass, ...]:
        if not value:
            raise ValueError("a dataset snapshot must declare its provenance classes")
        return tuple(sorted(set(value), key=lambda item: item.value))

    @model_validator(mode="after")
    def training_excludes_real_runs(self) -> LearnedDatasetSnapshot:
        if (
            self.corpus_role is CorpusRole.TRAINING
            and ProvenanceClass.REAL_GOVERNED_RUN in self.item_provenance_classes
        ):
            raise ValueError(
                "a training dataset cannot contain real-governed-run evidence: "
                "the evaluation corpus must stay uncontaminated"
            )
        if self.corpus_role is CorpusRole.TRAINING and not self.usage_rights_verified:
            raise ValueError("a training dataset requires verified usage rights")
        if not self.distribution_limitations:
            raise ValueError("a dataset snapshot must state its distribution limitations")
        return self


class LearnedComponentDescriptor(HashedExperienceContract):
    """Everything the core needs to know about a component it did not know about.

    This is what makes a new capability additive: the descriptor is declared in
    configuration, and the enums are extended by the sprint that needs a new value.
    """

    component_id: NonEmptyStr
    version: NonEmptyStr
    surface: NonEmptyStr
    tier: LearnedComponentTier
    capability_class: LearnedCapabilityClass
    resource_class: LearnedResourceClass
    required_extra: NonEmptyStr | None = None
    artifact_format: LearnedArtifactFormat
    supports_abstention: bool
    explanation_kind: LearnedExplanationKind
    deterministic_baseline: NonEmptyStr
    declared_limitations: tuple[NonEmptyStr, ...]

    @model_validator(mode="after")
    def promotable_shape(self) -> LearnedComponentDescriptor:
        if not self.declared_limitations:
            raise ValueError("a component descriptor must state its limitations")
        return self

    @property
    def promotable(self) -> bool:
        """A component that cannot abstain can never reach the active state."""
        return self.supports_abstention


class LearnedPrediction(HashedExperienceContract):
    """A proposal, never a decision. Large outputs are artifact-referenced."""

    prediction_id: UUID
    component_id: NonEmptyStr
    model_artifact_digest: Sha256Hex | None = None
    situation: SituationVector
    prediction: JsonValue | None = None
    payload_artifact: ArtifactRef | None = None
    confidence: Decimal = Field(ge=0, le=1)
    abstained: bool
    explanation: tuple[NonEmptyStr, ...] = ()
    created_at: UtcDatetime

    @model_validator(mode="after")
    def abstention_carries_no_prediction(self) -> LearnedPrediction:
        if self.abstained and (self.prediction is not None or self.payload_artifact is not None):
            raise ValueError("an abstaining prediction cannot carry a prediction payload")
        if not self.abstained and self.prediction is None and self.payload_artifact is None:
            raise ValueError("a non-abstaining prediction must carry a prediction or an artifact")
        return self


class LearnedShadowResult(HashedExperienceContract):
    """Shadow evidence that structurally cannot claim an unexecuted outcome."""

    prediction_id: UUID
    component_id: NonEmptyStr
    deterministic_baseline_decision: NonEmptyStr
    learned_shadow_decision: NonEmptyStr
    executed_decision: NonEmptyStr
    agreement: bool
    #: Typed `None`: the outcome of a decision that was never executed is not
    #: knowable, so the field cannot hold one even by mistake.
    shadow_actual_outcome: None = None
    created_at: UtcDatetime

    @model_validator(mode="after")
    def executed_decision_is_deterministic(self) -> LearnedShadowResult:
        if self.executed_decision != self.deterministic_baseline_decision:
            raise ValueError("shadow mode cannot change the executed decision")
        if self.agreement != (self.learned_shadow_decision == self.executed_decision):
            raise ValueError("recorded agreement does not match the decisions")
        return self


class MandatoryPathInvariance(HashedExperienceContract):
    """Proof that a component cannot alter the deterministic mandatory path.

    The same recorded case set is replayed with the component absent, present but
    disabled, and present but abstaining. All three decision digests must match.
    """

    record_id: UUID
    component_id: NonEmptyStr
    case_set_hash: Sha256Hex
    case_count: int = Field(ge=1)
    decision_hash_absent: Sha256Hex
    decision_hash_disabled: Sha256Hex
    decision_hash_abstaining: Sha256Hex
    created_at: UtcDatetime

    @property
    def identical(self) -> bool:
        return (
            self.decision_hash_absent
            == self.decision_hash_disabled
            == self.decision_hash_abstaining
        )


class ForgettingAssessment(HashedExperienceContract):
    """Retention across every previously passing case, in every domain."""

    assessment_id: UUID
    session_id: UUID
    baseline_manifest_hash: Sha256Hex
    per_domain_before: tuple[tuple[NonEmptyStr, int], ...]
    per_domain_after: tuple[tuple[NonEmptyStr, int], ...]
    regressed_cases: tuple[NonEmptyStr, ...]
    retained_case_count: int = Field(ge=0)
    tolerance: int = Field(ge=0)
    verdict: ForgettingVerdict
    created_at: UtcDatetime

    @model_validator(mode="after")
    def verdict_matches_evidence(self) -> ForgettingAssessment:
        if len(self.regressed_cases) > self.tolerance:
            if self.verdict is not ForgettingVerdict.REGRESSED:
                raise ValueError("regressed cases beyond tolerance require a regressed verdict")
        elif self.verdict is ForgettingVerdict.REGRESSED:
            raise ValueError("a regressed verdict requires regressed cases beyond tolerance")
        return self


class DistributionComparison(HashedExperienceContract):
    """How far the evaluation corpus sits from what a component trained on.

    Below `minimum_sample_threshold` the only permitted verdict is
    `NOT_ESTABLISHED`: an under-powered comparison must not be reportable as
    evidence of low divergence.
    """

    comparison_id: UUID
    training_dataset_id: UUID
    evaluation_dataset_id: UUID
    compared_features: tuple[NonEmptyStr, ...]
    per_feature_divergence: tuple[tuple[NonEmptyStr, Decimal], ...]
    training_sample_count: int = Field(ge=0)
    evaluation_sample_count: int = Field(ge=0)
    minimum_sample_threshold: int = Field(ge=1)
    abstention_rate_training: Decimal | None = Field(default=None, ge=0, le=1)
    abstention_rate_evaluation: Decimal | None = Field(default=None, ge=0, le=1)
    verdict: DivergenceVerdict
    limitations: tuple[NonEmptyStr, ...]
    created_at: UtcDatetime

    @property
    def conclusive(self) -> bool:
        return self.evaluation_sample_count >= self.minimum_sample_threshold

    @model_validator(mode="after")
    def underpowered_cannot_conclude(self) -> DistributionComparison:
        if not self.conclusive and self.verdict is not DivergenceVerdict.NOT_ESTABLISHED:
            raise ValueError(
                "a comparison below the minimum sample threshold can only report not_established"
            )
        if not self.limitations:
            raise ValueError("a distribution comparison must state its limitations")
        return self


class RetrievalCapacityEnvelope(HashedExperienceContract):
    """A measured retrieval capacity, at one corpus size, for one retrieval mode.

    Requirement 4 makes runtime scalability a criterion for choosing a learning
    method, which turns capacity into evidence rather than a target: a Tier A
    non-parametric method stands or falls on what retrieval can actually do at scale.

    Recall is recorded against exhaustive ground truth and is mandatory for an
    approximate measurement, because an approximate latency without its recall is the
    one number that can flatter any index. It must be absent for an exact measurement,
    where recall is 1 by construction and a stated value would imply it was measured.
    """

    envelope_id: UUID
    retrieval_mode: NonEmptyStr
    embedding_dimension: int = Field(ge=1)
    corpus_vector_count: int = Field(ge=1)
    queries_measured: int = Field(ge=1)
    result_limit: int = Field(ge=1)
    candidate_limit: int = Field(ge=1)
    latency_p50_ms: Decimal = Field(ge=0)
    latency_p95_ms: Decimal = Field(ge=0)
    recall_at_result_limit: Decimal | None = Field(default=None, ge=0, le=1)
    index_build_seconds: Decimal | None = Field(default=None, ge=0)
    index_size_bytes: int | None = Field(default=None, ge=0)
    ef_search: int | None = Field(default=None, ge=1)
    #: Whether the query plan was read back and found to contain an approximate index
    #: scan. Absent for an exact measurement, which has no index to confirm.
    index_scan_confirmed: bool | None = None
    limitations: tuple[NonEmptyStr, ...]
    created_at: UtcDatetime

    @property
    def approximate(self) -> bool:
        return self.retrieval_mode == "vector_approximate"

    @model_validator(mode="after")
    def approximation_is_reported_with_its_recall(self) -> RetrievalCapacityEnvelope:
        if self.approximate and self.recall_at_result_limit is None:
            raise ValueError("an approximate envelope must report the recall it achieved")
        if not self.approximate and self.recall_at_result_limit is not None:
            raise ValueError("an exhaustive envelope has recall 1 by construction, not by measure")
        if self.approximate and self.ef_search is None:
            raise ValueError("an approximate envelope must report the search effort it used")
        if self.latency_p95_ms < self.latency_p50_ms:
            raise ValueError("p95 latency cannot be below p50")
        if not self.limitations:
            raise ValueError("a capacity envelope must state its limitations")
        return self

    @model_validator(mode="after")
    def an_unused_index_cannot_have_lost_recall(self) -> RetrievalCapacityEnvelope:
        """The measurement's own honesty check, learned from getting it wrong.

        A cost-based planner declines an approximate index on a small corpus and runs an
        exhaustive scan instead. The recall then comes out at 1 for the least
        interesting reason imaginable, and reads as a clean result for the index. So an
        approximate envelope must say whether the plan really used the index, and if it
        did not, a recall below 1 is a contradiction: an exhaustive scan cannot miss.
        """
        if self.approximate and self.index_scan_confirmed is None:
            raise ValueError("an approximate envelope must state whether the index was used")
        if not self.approximate and self.index_scan_confirmed is not None:
            raise ValueError("an exhaustive envelope has no index scan to confirm")
        unused = self.index_scan_confirmed is False
        if unused and self.recall_at_result_limit != Decimal(1):
            raise ValueError("an exhaustive fallback cannot miss a neighbour, so recall must be 1")
        return self


class LearnedPromotionAssessment(HashedExperienceContract):
    """The gate. Improvement alone never makes a component eligible."""

    assessment_id: UUID
    component_id: NonEmptyStr
    descriptor: LearnedComponentDescriptor
    baseline_metric: Decimal
    candidate_metric: Decimal
    minimum_material_improvement: Decimal = Field(ge=0)
    forgetting: ForgettingAssessment
    invariance: MandatoryPathInvariance
    distribution: DistributionComparison | None = None
    decision: LearnedPromotionDecision
    reason: NonEmptyStr
    created_at: UtcDatetime

    @model_validator(mode="after")
    def eligibility_requires_every_gate(self) -> LearnedPromotionAssessment:
        eligible = self.decision is LearnedPromotionDecision.ELIGIBLE_FOR_OPERATOR_APPROVAL
        if not eligible:
            return self
        if self.forgetting.verdict is ForgettingVerdict.REGRESSED:
            raise ValueError("a forgetting regression cannot be eligible for approval")
        if not self.invariance.identical:
            raise ValueError("unproven mandatory-path invariance cannot be eligible for approval")
        if not self.descriptor.promotable:
            raise ValueError("a component that cannot abstain cannot be eligible for approval")
        if self.candidate_metric - self.baseline_metric < self.minimum_material_improvement:
            raise ValueError("eligibility requires a material improvement over the baseline")
        return self


PUBLIC_LEARNED_CONTRACTS: tuple[type[HashedExperienceContract], ...] = (
    NumericFeature,
    SituationVector,
    FeatureSchema,
    CounterfactualLabel,
    LabelBalance,
    LearnedDatasetSnapshot,
    LearnedComponentDescriptor,
    LearnedPrediction,
    LearnedShadowResult,
    MandatoryPathInvariance,
    ForgettingAssessment,
    DistributionComparison,
    RetrievalCapacityEnvelope,
    LearnedPromotionAssessment,
)
