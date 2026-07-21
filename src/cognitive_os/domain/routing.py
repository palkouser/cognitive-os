"""Immutable contracts for governed model capability evidence and routing."""

from __future__ import annotations

import math
from decimal import Decimal
from enum import StrEnum
from typing import Annotated
from uuid import UUID

from pydantic import Field, field_validator, model_validator

from .common import JsonValue, NonEmptyStr, Sha256Hex, TokenUsage, UtcDatetime
from .experience import HashedExperienceContract
from .provider import ProviderStatus


class ModelProfileStatus(StrEnum):
    DRAFT = "draft"
    REGISTERED = "registered"
    VERIFIED = "verified"
    DEPRECATED = "deprecated"
    RETRACTED = "retracted"


class CapabilityEvidenceType(StrEnum):
    PROVIDER_SELF_DESCRIPTION = "provider_self_description"
    PROVIDER_DOCUMENTATION = "provider_documentation"
    OPERATOR_DECLARATION = "operator_declaration"
    REPLAY_CONTRACT_EVIDENCE = "replay_contract_evidence"
    DETERMINISTIC_BENCHMARK = "deterministic_benchmark"
    OPT_IN_LIVE_BENCHMARK = "opt_in_live_benchmark"
    VERIFIED_TASK_OUTCOME = "verified_task_outcome"


class CapabilityDimension(StrEnum):
    ACCEPTED_TASK_RATE = "accepted_task_rate"
    VERIFIER_QUALITY = "verifier_quality"
    STRUCTURED_OUTPUT_VALIDITY = "structured_output_validity"
    TOOL_CALL_VALIDITY = "tool_call_validity"
    REPAIR_COUNT = "repair_count"
    PROVIDER_FAILURE_RATE = "provider_failure_rate"
    TIMEOUT_RATE = "timeout_rate"
    LATENCY = "latency"
    INPUT_TOKEN_USAGE = "input_token_usage"  # nosec B105
    OUTPUT_TOKEN_USAGE = "output_token_usage"  # nosec B105
    COST_UNITS = "cost_units"
    CONTEXT_FIT = "context_fit"
    POLICY_DENIAL_RATE = "policy_denial_rate"
    SAFETY_FAILURE_RATE = "safety_failure_rate"
    CODING_BENCHMARK_QUALITY = "coding_benchmark_quality"
    TASK_SIGNATURE_COVERAGE = "task_signature_coverage"


class CapabilitySupportStatus(StrEnum):
    SUPPORTED = "supported"
    UNSUPPORTED = "unsupported"
    UNKNOWN = "unknown"
    RESTRICTED = "restricted"


class TaskComplexityClass(StrEnum):
    TRIVIAL = "trivial"
    SMALL = "small"
    MEDIUM = "medium"
    LARGE = "large"
    LONG_HORIZON = "long_horizon"
    UNKNOWN = "unknown"


class ContextSizeClass(StrEnum):
    SMALL = "small"
    MEDIUM = "medium"
    LARGE = "large"
    LONG = "long"
    UNKNOWN = "unknown"


class LatencyClass(StrEnum):
    LOW = "low"
    STANDARD = "standard"
    RELAXED = "relaxed"
    UNKNOWN = "unknown"


class CostClass(StrEnum):
    LOW = "low"
    STANDARD = "standard"
    PREMIUM = "premium"
    UNKNOWN = "unknown"


class RoutingPolicyStatus(StrEnum):
    DRAFT = "draft"
    STAGED = "staged"
    SHADOW = "shadow"
    APPROVED = "approved"
    ENABLED = "enabled"
    DISABLED = "disabled"
    DEPRECATED = "deprecated"
    RETRACTED = "retracted"


class RoutingControlMode(StrEnum):
    STATIC = "static"
    SHADOW = "shadow"
    ADAPTIVE = "adaptive"
    EXPLICIT_OVERRIDE = "explicit_override"
    LEGACY_STATIC = "legacy_static"


class RoutingDecisionStatus(StrEnum):
    SELECTED = "selected"
    NO_ELIGIBLE_MODEL = "no_eligible_model"
    BLOCKED = "blocked"


class RoutingOutcomeStatus(StrEnum):
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    FAILED = "failed"
    CANCELLED = "cancelled"
    UNVERIFIABLE = "unverifiable"


class RoutingObservationStatus(StrEnum):
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    UNVERIFIABLE = "unverifiable"


class RoutingExperimentStatus(StrEnum):
    DRAFT = "draft"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class MultiModelPatternType(StrEnum):
    SINGLE_MODEL = "single_model"
    PRIMARY_WITH_FALLBACK = "primary_with_fallback"
    PLANNER_EXECUTOR = "planner_executor"
    GENERATOR_CRITIC = "generator_critic"
    MULTIPLE_PROPOSALS_WITH_VERIFIER_SELECTION = "multiple_proposals_with_verifier_selection"


class ExecutionRole(StrEnum):
    PRIMARY = "primary"
    FALLBACK = "fallback"
    PLANNER = "planner"
    EXECUTOR = "executor"
    GENERATOR = "generator"
    CRITIC = "critic"
    PROPOSER = "proposer"


class RoutingExclusionReason(StrEnum):
    PROVIDER_DISABLED = "provider_disabled"
    PROVIDER_UNHEALTHY = "provider_unhealthy"
    MODEL_NOT_CONFIGURED = "model_not_configured"
    CONTEXT_LIMIT = "context_limit"
    STRUCTURED_OUTPUT = "structured_output"
    TOOL_CALLING = "tool_calling"
    MODALITY = "modality"
    RISK = "risk"
    PROVIDER_POLICY = "provider_policy"
    EXECUTION_MODE = "execution_mode"
    SAFETY = "safety"
    COST = "cost"
    POLICY_STATUS = "policy_status"


class RoutingFallbackReason(StrEnum):
    PROVIDER_UNAVAILABLE = "provider_unavailable"
    TIMEOUT_BEFORE_SIDE_EFFECT = "timeout_before_side_effect"
    TIMEOUT_AFTER_UNCERTAIN_SIDE_EFFECT = "timeout_after_uncertain_side_effect"
    RATE_LIMITED = "rate_limited"
    INVALID_RESPONSE = "invalid_response"
    STRUCTURED_OUTPUT_FAILURE = "structured_output_failure"
    TOOL_CALL_FAILURE = "tool_call_failure"
    CONTEXT_LIMIT_FAILURE = "context_limit_failure"
    POLICY_DENIAL = "policy_denial"
    SAFETY_DENIAL = "safety_denial"
    UNKNOWN = "unknown"


class RoutingAccessType(StrEnum):
    PROFILE_LOOKUP = "profile_lookup"
    OBSERVATION_INGESTION = "observation_ingestion"
    STATISTICS_READ = "statistics_read"
    POLICY_LOOKUP = "policy_lookup"
    ROUTING_DECISION = "routing_decision"
    SHADOW_DECISION = "shadow_decision"
    EXPERIMENT_READ = "experiment_read"
    PROMOTION_ASSESSMENT = "promotion_assessment"
    OUTCOME_READ = "outcome_read"


class ModelIdentity(HashedExperienceContract):
    provider_id: NonEmptyStr
    model_id: NonEmptyStr
    model_revision: NonEmptyStr
    endpoint_profile: NonEmptyStr
    execution_mode: NonEmptyStr


class CapabilitySourceReference(HashedExperienceContract):
    evidence_type: CapabilityEvidenceType
    source_id: NonEmptyStr
    source_revision: NonEmptyStr
    source_hash: Sha256Hex
    actor_id: NonEmptyStr


class DeclaredCapability(HashedExperienceContract):
    dimension: NonEmptyStr
    support: CapabilitySupportStatus
    value: JsonValue | None = None
    source: CapabilitySourceReference


class DeclaredCapabilitySet(HashedExperienceContract):
    capabilities: tuple[DeclaredCapability, ...]

    @field_validator("capabilities")
    @classmethod
    def unique_dimensions(
        cls, value: tuple[DeclaredCapability, ...]
    ) -> tuple[DeclaredCapability, ...]:
        if len({item.dimension for item in value}) != len(value):
            raise ValueError("declared capability dimensions must be unique")
        return tuple(sorted(value, key=lambda item: item.dimension))


class CapabilityCohort(HashedExperienceContract):
    task_signature_hash: Sha256Hex
    cohort_level: NonEmptyStr
    parent_hash: Sha256Hex | None = None


class CapabilityMeasurement(HashedExperienceContract):
    measurement_id: UUID
    model_identity_hash: Sha256Hex
    cohort: CapabilityCohort
    dimension: CapabilityDimension
    value: Decimal | None
    succeeded: bool | None = None
    evidence_type: CapabilityEvidenceType
    source_refs: Annotated[tuple[Sha256Hex, ...], Field(min_length=1)]
    observed_at: UtcDatetime


class CapabilityEstimate(HashedExperienceContract):
    dimension: CapabilityDimension
    sample_count: int = Field(ge=0)
    effective_sample_count: int = Field(ge=0)
    estimate: Decimal | None = None
    lower_bound: Decimal | None = None
    upper_bound: Decimal | None = None
    uncertainty: Decimal = Field(ge=0, le=1)
    missing_count: int = Field(default=0, ge=0)
    source_class_counts: dict[CapabilityEvidenceType, int] = Field(default_factory=dict)


class CapabilityEstimateSet(HashedExperienceContract):
    cohort: CapabilityCohort
    estimates: tuple[CapabilityEstimate, ...]
    statistics_profile: NonEmptyStr
    source_observation_ids: tuple[UUID, ...]


class TaskSignature(HashedExperienceContract):
    problem_domain: NonEmptyStr
    problem_class: NonEmptyStr
    output_type: NonEmptyStr
    repository_profile: NonEmptyStr = "unknown"
    estimated_complexity: TaskComplexityClass = TaskComplexityClass.UNKNOWN
    required_tool_capabilities: tuple[NonEmptyStr, ...] = ()
    required_structured_output: bool = False
    context_size_class: ContextSizeClass = ContextSizeClass.UNKNOWN
    risk_level: NonEmptyStr = "standard"
    verifier_profile: NonEmptyStr = "default"
    latency_class: LatencyClass = LatencyClass.UNKNOWN
    cost_class: CostClass = CostClass.UNKNOWN
    strategy_revisions: tuple[NonEmptyStr, ...] = ()
    skill_revisions: tuple[NonEmptyStr, ...] = ()
    execution_role: ExecutionRole = ExecutionRole.PRIMARY
    profile_version: NonEmptyStr = "task-signature-v1"

    @field_validator("required_tool_capabilities", "strategy_revisions", "skill_revisions")
    @classmethod
    def canonical_tuple(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        return tuple(sorted(set(value)))


class ModelCapabilityProfile(HashedExperienceContract):
    model_identity: ModelIdentity
    profile_revision: int = Field(gt=0)
    previous_revision: int | None = Field(default=None, gt=0)
    status: ModelProfileStatus
    declared_capabilities: DeclaredCapabilitySet
    measured_capabilities: CapabilityEstimateSet | None = None
    supported_domains: tuple[NonEmptyStr, ...] = ()
    structured_output_support: CapabilitySupportStatus = CapabilitySupportStatus.UNKNOWN
    tool_call_support: CapabilitySupportStatus = CapabilitySupportStatus.UNKNOWN
    context_limit: int | None = Field(default=None, gt=0)
    input_modalities: tuple[NonEmptyStr, ...] = ("text",)
    output_modalities: tuple[NonEmptyStr, ...] = ("text",)
    availability_reference: Sha256Hex | None = None
    source_refs: Annotated[tuple[Sha256Hex, ...], Field(min_length=1)]
    created_at: UtcDatetime
    created_by: NonEmptyStr
    reason: NonEmptyStr

    @model_validator(mode="after")
    def validate_revision(self) -> ModelCapabilityProfile:
        if self.profile_revision == 1 and self.previous_revision is not None:
            raise ValueError("initial profile cannot have a predecessor")
        if self.profile_revision > 1 and self.previous_revision != self.profile_revision - 1:
            raise ValueError("profile revisions must be contiguous")
        return self


class ModelCapabilityRequirement(HashedExperienceContract):
    dimension: NonEmptyStr
    hard: bool = True
    minimum_value: Decimal | None = None
    required_support: CapabilitySupportStatus | None = None


class ProviderPolicyConstraint(HashedExperienceContract):
    allowed_provider_ids: tuple[NonEmptyStr, ...] = ()
    denied_provider_ids: tuple[NonEmptyStr, ...] = ()
    require_healthy: bool = True


class ContextRequirement(HashedExperienceContract):
    estimated_tokens: int = Field(ge=0)
    reserved_output_tokens: int = Field(default=0, ge=0)
    required_modalities: tuple[NonEmptyStr, ...] = ("text",)


class RoutingBudget(HashedExperienceContract):
    maximum_calls: int = Field(default=1, ge=1, le=8)
    maximum_tokens: int = Field(default=131_072, ge=1)
    maximum_tool_calls: int = Field(default=32, ge=0)
    maximum_seconds: Decimal = Field(default=Decimal("120"), gt=0)
    maximum_cost_units: Decimal | None = Field(default=None, ge=0)


class OperatorRoutingRestriction(HashedExperienceContract):
    preferred_model_hashes: tuple[Sha256Hex, ...] = ()
    allowed_model_hashes: tuple[Sha256Hex, ...] = ()
    denied_model_hashes: tuple[Sha256Hex, ...] = ()
    actor_id: NonEmptyStr
    reason: NonEmptyStr


class RoutingPolicyRevision(HashedExperienceContract):
    policy_id: NonEmptyStr
    revision: int = Field(gt=0)
    previous_revision: int | None = Field(default=None, gt=0)
    status: RoutingPolicyStatus
    control_mode: RoutingControlMode
    candidate_filters: tuple[ModelCapabilityRequirement, ...] = ()
    minimum_samples: int = Field(default=0, ge=0)
    score_weights: dict[NonEmptyStr, Decimal] = Field(default_factory=dict)
    uncertainty_penalty: Decimal = Field(default=Decimal("0.25"), ge=0)
    maximum_fallback_models: int = Field(default=8, ge=0, le=8)
    role_patterns: tuple[MultiModelPatternType, ...] = (MultiModelPatternType.SINGLE_MODEL,)
    risk_constraints: tuple[NonEmptyStr, ...] = ()
    budget_constraints: RoutingBudget = RoutingBudget()
    allowed_task_signature_hashes: tuple[Sha256Hex, ...] = ()
    operator_approval_reference: NonEmptyStr | None = None
    created_at: UtcDatetime
    created_by: NonEmptyStr
    reason: NonEmptyStr

    @field_validator("score_weights")
    @classmethod
    def finite_weights(cls, value: dict[str, Decimal]) -> dict[str, Decimal]:
        if any(not math.isfinite(float(weight)) for weight in value.values()):
            raise ValueError("routing score weights must be finite")
        return dict(sorted(value.items()))

    @model_validator(mode="after")
    def validate_policy(self) -> RoutingPolicyRevision:
        if self.revision == 1 and self.previous_revision is not None:
            raise ValueError("initial policy cannot have a predecessor")
        if self.revision > 1 and self.previous_revision != self.revision - 1:
            raise ValueError("policy revisions must be contiguous")
        if (
            self.control_mode is RoutingControlMode.ADAPTIVE
            and self.status
            in {
                RoutingPolicyStatus.APPROVED,
                RoutingPolicyStatus.ENABLED,
            }
            and not self.operator_approval_reference
        ):
            raise ValueError("adaptive approval and enablement require operator approval")
        if (
            self.status is RoutingPolicyStatus.ENABLED
            and self.control_mode is RoutingControlMode.SHADOW
        ):
            raise ValueError("shadow policies cannot execute")
        return self


class ProviderHealthSnapshot(HashedExperienceContract):
    provider_id: NonEmptyStr
    status: ProviderStatus
    checked_at: UtcDatetime


class CapabilityRegistrySnapshot(HashedExperienceContract):
    profile_hashes: Annotated[tuple[Sha256Hex, ...], Field(max_length=256)]


class ProviderRegistrySnapshot(HashedExperienceContract):
    health: Annotated[tuple[ProviderHealthSnapshot, ...], Field(max_length=256)]


class RoutingStatisticsSnapshot(HashedExperienceContract):
    statistic_hashes: tuple[Sha256Hex, ...] = ()
    profile_version: NonEmptyStr = "routing-statistics-v1"


class RoutingRequest(HashedExperienceContract):
    routing_request_id: UUID
    task_run_id: UUID
    step_id: NonEmptyStr
    task_signature: TaskSignature
    execution_role: ExecutionRole
    capability_requirements: tuple[ModelCapabilityRequirement, ...] = ()
    provider_constraints: ProviderPolicyConstraint
    context_requirement: ContextRequirement
    budget: RoutingBudget
    policy_id: NonEmptyStr
    policy_revision: int = Field(gt=0)
    provider_registry_snapshot: ProviderRegistrySnapshot
    operator_restriction: OperatorRoutingRestriction | None = None
    strategy_references: tuple[NonEmptyStr, ...] = ()
    skill_references: tuple[NonEmptyStr, ...] = ()
    requested_by: NonEmptyStr
    created_at: UtcDatetime


class RoutingExclusion(HashedExperienceContract):
    model_identity_hash: Sha256Hex
    reason: RoutingExclusionReason
    detail: NonEmptyStr


class RoutingCandidateScore(HashedExperienceContract):
    model_identity_hash: Sha256Hex
    eligible: bool
    static_priority: int = 0
    dimensions: dict[NonEmptyStr, Decimal] = Field(default_factory=dict)
    uncertainty: Decimal = Field(default=Decimal("1"), ge=0, le=1)
    total: Decimal = Decimal("0")
    source_statistics_hash: Sha256Hex | None = None
    source_cohort_level: NonEmptyStr | None = None


class RoutingCandidate(HashedExperienceContract):
    profile: ModelCapabilityProfile
    health: ProviderHealthSnapshot
    score: RoutingCandidateScore | None = None
    exclusions: tuple[RoutingExclusion, ...] = ()


class RoutingFallbackEntry(HashedExperienceContract):
    position: int = Field(gt=0)
    model_identity_hash: Sha256Hex
    reason: RoutingFallbackReason = RoutingFallbackReason.PROVIDER_UNAVAILABLE


class RoutingRoleAssignment(HashedExperienceContract):
    role: ExecutionRole
    model_identity_hash: Sha256Hex
    routing_decision_id: UUID


class RoutingDecision(HashedExperienceContract):
    decision_id: UUID
    previous_decision_id: UUID | None = None
    routing_request_id: UUID
    task_run_id: UUID
    task_signature: TaskSignature
    policy_id: NonEmptyStr
    policy_revision: int = Field(gt=0)
    control_mode: RoutingControlMode
    status: RoutingDecisionStatus
    candidate_models: tuple[Sha256Hex, ...]
    candidate_scores: tuple[RoutingCandidateScore, ...]
    exclusions: tuple[RoutingExclusion, ...]
    selected_model: ModelIdentity | None
    selected_role_pattern: MultiModelPatternType = MultiModelPatternType.SINGLE_MODEL
    role_assignments: tuple[RoutingRoleAssignment, ...] = ()
    fallback_order: tuple[RoutingFallbackEntry, ...] = ()
    static_decision_reference: UUID | None = None
    shadow_decision_reference: UUID | None = None
    reason: NonEmptyStr
    provider_registry_snapshot: ProviderRegistrySnapshot
    capability_registry_snapshot: CapabilityRegistrySnapshot
    statistics_snapshot: RoutingStatisticsSnapshot
    created_at: UtcDatetime

    @model_validator(mode="after")
    def selected_status_matches(self) -> RoutingDecision:
        if (self.status is RoutingDecisionStatus.SELECTED) != (self.selected_model is not None):
            raise ValueError("selected decisions require exactly one selected model")
        return self


class RoutingOutcome(HashedExperienceContract):
    outcome_id: UUID
    decision_id: UUID
    task_run_id: UUID
    provider_request_reference: NonEmptyStr
    provider_result_reference: NonEmptyStr | None = None
    context_bundle_reference: NonEmptyStr
    tool_result_references: tuple[NonEmptyStr, ...] = ()
    verifier_bundle_reference: NonEmptyStr | None = None
    acceptance_decision_reference: NonEmptyStr | None = None
    status: RoutingOutcomeStatus
    latency_ms: Decimal | None = Field(default=None, ge=0)
    token_usage: TokenUsage | None = None
    cost_units: Decimal | None = Field(default=None, ge=0)
    repair_count: int = Field(default=0, ge=0)
    fallback_used: bool = False
    safety_result: NonEmptyStr = "unknown"
    created_at: UtcDatetime

    @model_validator(mode="after")
    def accepted_has_evidence(self) -> RoutingOutcome:
        if self.status is RoutingOutcomeStatus.ACCEPTED and (
            not self.provider_result_reference
            or not self.verifier_bundle_reference
            or not self.acceptance_decision_reference
        ):
            raise ValueError("accepted routing outcomes require complete verified evidence")
        return self


class RoutingObservation(HashedExperienceContract):
    observation_id: UUID
    model_identity: ModelIdentity
    task_signature: TaskSignature
    routing_policy_reference: NonEmptyStr
    execution_role: ExecutionRole
    provider_call_reference: NonEmptyStr
    context_bundle_reference: NonEmptyStr
    skill_revision: NonEmptyStr | None = None
    strategy_revision: NonEmptyStr | None = None
    verifier_bundle_reference: NonEmptyStr
    acceptance_decision_reference: NonEmptyStr
    status: RoutingObservationStatus
    latency_ms: Decimal | None = Field(default=None, ge=0)
    token_usage: TokenUsage | None = None
    cost_units: Decimal | None = Field(default=None, ge=0)
    structured_output_valid: bool | None = None
    tool_calls_valid: bool | None = None
    safety_passed: bool | None = None
    source_refs: Annotated[tuple[Sha256Hex, ...], Field(min_length=1)]
    evidence_type: CapabilityEvidenceType
    created_at: UtcDatetime

    @model_validator(mode="after")
    def measured_evidence_is_authoritative(self) -> RoutingObservation:
        if (
            self.evidence_type
            in {
                CapabilityEvidenceType.PROVIDER_SELF_DESCRIPTION,
                CapabilityEvidenceType.PROVIDER_DOCUMENTATION,
            }
            and self.status is RoutingObservationStatus.ACCEPTED
        ):
            raise ValueError("provider declarations cannot create measured task success")
        return self


class RoutingStatistics(HashedExperienceContract):
    statistics_id: UUID
    model_identity_hash: Sha256Hex
    cohort: CapabilityCohort
    estimates: CapabilityEstimateSet
    source_observation_ids: tuple[UUID, ...]
    rebuilt_at: UtcDatetime


class UncertaintyAssessment(HashedExperienceContract):
    sample_count: int = Field(ge=0)
    interval_width: Decimal = Field(ge=0)
    cohort_generality: int = Field(ge=0)
    missing_dimensions: int = Field(ge=0)
    penalty: Decimal = Field(ge=0, le=1)


class ShadowRoutingResult(HashedExperienceContract):
    static_decision_id: UUID
    shadow_decision_id: UUID
    static_model_hash: Sha256Hex | None
    shadow_model_hash: Sha256Hex | None
    expected_score_delta: Decimal | None
    executed_outcome_id: UUID | None = None
    shadow_actual_outcome: None = None


class RoutingExperimentCase(HashedExperienceContract):
    case_id: NonEmptyStr
    routing_request: RoutingRequest
    expected_static_model_hash: Sha256Hex | None = None


class RoutingExperiment(HashedExperienceContract):
    experiment_id: UUID
    static_policy_reference: NonEmptyStr
    shadow_policy_reference: NonEmptyStr
    cases: Annotated[tuple[RoutingExperimentCase, ...], Field(max_length=10_000)]
    status: RoutingExperimentStatus
    created_at: UtcDatetime


class RoutingExperimentResult(HashedExperienceContract):
    experiment_id: UUID
    results: tuple[ShadowRoutingResult, ...]
    agreement_rate: Decimal = Field(ge=0, le=1)
    completed_at: UtcDatetime


class RoutingPromotionAssessment(HashedExperienceContract):
    assessment_id: UUID
    policy_id: NonEmptyStr
    policy_revision: int = Field(gt=0)
    eligible_for_approval: bool
    reasons: tuple[NonEmptyStr, ...]
    sample_count: int = Field(ge=0)
    shadow_case_count: int = Field(ge=0)
    quality_improvement: Decimal
    safety_regression: Decimal
    policy_regression: Decimal
    fallback_validated: bool
    replay_validated: bool
    operator_approval_reference: NonEmptyStr | None = None
    assessed_at: UtcDatetime


class MultiModelRole(HashedExperienceContract):
    role: ExecutionRole
    routing_request_id: UUID
    routing_decision_id: UUID
    context_bundle_reference: NonEmptyStr
    token_reservation: int = Field(ge=0)


class MultiModelPattern(HashedExperienceContract):
    pattern_type: MultiModelPatternType
    roles: Annotated[tuple[ExecutionRole, ...], Field(min_length=1, max_length=8)]


class MultiModelExecutionPlan(HashedExperienceContract):
    plan_id: UUID
    pattern: MultiModelPattern
    roles: Annotated[tuple[MultiModelRole, ...], Field(min_length=1, max_length=8)]
    effective_budget: RoutingBudget
    verifier_reference: NonEmptyStr
    controller_plan_reference: NonEmptyStr


class MultiModelRoleResult(HashedExperienceContract):
    role: ExecutionRole
    decision_id: UUID
    provider_result_reference: NonEmptyStr


class MultiModelSelectionResult(HashedExperienceContract):
    plan_id: UUID
    role_results: tuple[MultiModelRoleResult, ...]
    verifier_result_reference: NonEmptyStr
    accepted_role: ExecutionRole | None = None


class RoutingAccessRecord(HashedExperienceContract):
    access_id: UUID
    access_type: RoutingAccessType
    actor_id: NonEmptyStr
    model_identity_hash: Sha256Hex | None = None
    policy_id: NonEmptyStr | None = None
    policy_revision: int | None = Field(default=None, gt=0)
    decision_id: UUID | None = None
    accessed_at: UtcDatetime
    reason: NonEmptyStr


class RoutingReference(HashedExperienceContract):
    routing_decision_id: UUID
    routing_policy_id: NonEmptyStr
    routing_policy_revision: int = Field(gt=0)
    control_mode: RoutingControlMode
    selected_model_identity_hash: Sha256Hex
    role_assignment: ExecutionRole


class RoutingVerificationSubject(HashedExperienceContract):
    subject_type: NonEmptyStr
    subject_id: NonEmptyStr
    subject_revision: int | None = Field(default=None, gt=0)
    subject_hash: Sha256Hex
    related_hashes: tuple[Sha256Hex, ...] = ()


PUBLIC_ROUTING_CONTRACTS = (
    ModelIdentity,
    CapabilitySourceReference,
    DeclaredCapability,
    DeclaredCapabilitySet,
    CapabilityCohort,
    CapabilityMeasurement,
    CapabilityEstimate,
    CapabilityEstimateSet,
    TaskSignature,
    ModelCapabilityProfile,
    ModelCapabilityRequirement,
    ProviderPolicyConstraint,
    ContextRequirement,
    RoutingBudget,
    OperatorRoutingRestriction,
    RoutingPolicyRevision,
    ProviderHealthSnapshot,
    CapabilityRegistrySnapshot,
    ProviderRegistrySnapshot,
    RoutingStatisticsSnapshot,
    RoutingRequest,
    RoutingExclusion,
    RoutingCandidateScore,
    RoutingCandidate,
    RoutingFallbackEntry,
    RoutingRoleAssignment,
    RoutingDecision,
    RoutingOutcome,
    RoutingObservation,
    RoutingStatistics,
    UncertaintyAssessment,
    ShadowRoutingResult,
    RoutingExperimentCase,
    RoutingExperiment,
    RoutingExperimentResult,
    RoutingPromotionAssessment,
    MultiModelRole,
    MultiModelPattern,
    MultiModelExecutionPlan,
    MultiModelRoleResult,
    MultiModelSelectionResult,
    RoutingAccessRecord,
    RoutingReference,
    RoutingVerificationSubject,
)
