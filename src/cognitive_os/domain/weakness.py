"""Immutable contracts for governed, diagnostic-only weakness mining."""

from __future__ import annotations

import math
import re
from decimal import Decimal
from enum import StrEnum
from pathlib import PurePosixPath, PureWindowsPath
from typing import Annotated
from uuid import UUID

from pydantic import Field, field_validator, model_validator

from .common import JsonValue, NonEmptyStr, Sha256Hex, UtcDatetime
from .experience import HashedExperienceContract
from .memory import MemorySensitivity
from .routing import TaskSignature


class WeaknessType(StrEnum):
    MODEL_ROUTING_FAILURE = "model_routing_failure"
    TOOL_ROUTING_FAILURE = "tool_routing_failure"
    PROVIDER_STRUCTURED_OUTPUT_FAILURE = "provider_structured_output_failure"
    PROVIDER_AVAILABILITY_FAILURE = "provider_availability_failure"
    CONTEXT_REQUIRED_ITEM_MISSING = "context_required_item_missing"
    CONTEXT_IRRELEVANT_CONTENT = "context_irrelevant_content"
    CONTEXT_BUDGET_FAILURE = "context_budget_failure"
    RETRIEVAL_RECALL_FAILURE = "retrieval_recall_failure"
    RETRIEVAL_SCOPE_OR_SENSITIVITY_DENIAL = "retrieval_scope_or_sensitivity_denial"
    MISSING_SKILL = "missing_skill"
    SKILL_PRECONDITION_FAILURE = "skill_precondition_failure"
    SKILL_EXECUTION_FAILURE = "skill_execution_failure"
    STRATEGY_MISMATCH = "strategy_mismatch"
    STRATEGY_FALLBACK_OVERUSE = "strategy_fallback_overuse"
    VERIFIER_GAP = "verifier_gap"
    VERIFIER_INSTABILITY = "verifier_instability"
    MEMORY_RETRIEVAL_FAILURE = "memory_retrieval_failure"
    SEMANTIC_CONTRADICTION_BLOCK = "semantic_contradiction_block"
    CORPUS_COVERAGE_GAP = "corpus_coverage_gap"
    EXCESSIVE_REPAIR = "excessive_repair"
    EXCESSIVE_ITERATION = "excessive_iteration"
    UNNECESSARY_PROVIDER_CALL = "unnecessary_provider_call"
    UNNECESSARY_TOOL_CALL = "unnecessary_tool_call"
    COST_REGRESSION = "cost_regression"
    LATENCY_REGRESSION = "latency_regression"
    POLICY_DENIAL_PATTERN = "policy_denial_pattern"
    SANDBOX_FAILURE = "sandbox_failure"
    USER_CORRECTION_PATTERN = "user_correction_pattern"
    UNKNOWN = "unknown"


class WeaknessSignalStatus(StrEnum):
    OBSERVED = "observed"
    CONFLICTED = "conflicted"
    INVALID = "invalid"


class WeaknessStatus(StrEnum):
    CANDIDATE = "candidate"
    CONFIRMED = "confirmed"
    MONITORING = "monitoring"
    RESOLVED = "resolved"
    SUPERSEDED = "superseded"
    RETRACTED = "retracted"


class WeaknessSeverity(StrEnum):
    INFORMATIONAL = "informational"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class WeaknessConfidenceLevel(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    VERIFIED = "verified"


class WeaknessComponentType(StrEnum):
    CONTROLLER = "controller"
    CONTEXT = "context"
    RETRIEVAL = "retrieval"
    PROVIDER = "provider"
    MODEL = "model"
    TOOL = "tool"
    VERIFIER = "verifier"
    MEMORY = "memory"
    SEMANTIC_MEMORY = "semantic_memory"
    SKILL = "skill"
    STRATEGY = "strategy"
    EXPERIENCE = "experience"
    CORPUS = "corpus"
    ROUTING = "routing"
    SANDBOX = "sandbox"
    UNKNOWN = "unknown"


class WeaknessRelationType(StrEnum):
    SUPPORTS = "supports"
    COUNTEREXAMPLE = "counterexample"
    CONFLICTS = "conflicts"
    SUPERSEDES = "supersedes"


class WeaknessClusterMethod(StrEnum):
    EXACT_SIGNATURE = "exact_signature"
    NO_OP = "no_op"
    GRAPH_NEIGHBOURHOOD = "graph_neighbourhood"
    EMBEDDING_ADVISORY = "embedding_advisory"


class WeaknessReproductionStatus(StrEnum):
    NOT_ATTEMPTED = "not_attempted"
    REPRODUCIBLE = "reproducible"
    PARTIALLY_REPRODUCIBLE = "partially_reproducible"
    NOT_REPRODUCED = "not_reproduced"
    BLOCKED = "blocked"
    UNSAFE_TO_REPRODUCE = "unsafe_to_reproduce"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"


class WeaknessPriority(StrEnum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFORMATIONAL = "informational"


class WeaknessQueueStatus(StrEnum):
    QUEUED = "queued"
    BLOCKED = "blocked"
    DEFERRED = "deferred"
    MONITORING = "monitoring"
    REMOVED = "removed"
    SUPERSEDED = "superseded"


class WeaknessAccessType(StrEnum):
    SOURCE_RESOLUTION = "source_resolution"
    SIGNAL_READ = "signal_read"
    GROUP_QUERY = "group_query"
    CLUSTER_QUERY = "cluster_query"
    IMPACT_READ = "impact_read"
    EVIDENCE_READ = "evidence_read"
    WEAKNESS_READ = "weakness_read"
    QUEUE_READ = "queue_read"
    REPRODUCTION_READ = "reproduction_read"


class MiningRunStatus(StrEnum):
    REQUESTED = "requested"
    SNAPSHOT_CREATED = "snapshot_created"
    EXTRACTING_SIGNALS = "extracting_signals"
    GROUPING = "grouping"
    SCORING = "scoring"
    PACKAGING = "packaging"
    COMPLETED = "completed"
    COMPLETED_WITH_WARNINGS = "completed_with_warnings"
    FAILED = "failed"
    CANCELLED = "cancelled"


class SignalSourceType(StrEnum):
    CONTROLLER = "controller"
    ACCEPTANCE = "acceptance"
    VERIFIER = "verifier"
    USER_CORRECTION = "user_correction"
    CONTEXT = "context"
    RETRIEVAL = "retrieval"
    PROVIDER_REQUEST = "provider_request"
    PROVIDER_RESULT = "provider_result"
    TOOL = "tool"
    MEMORY = "memory"
    SEMANTIC = "semantic"
    SKILL = "skill"
    STRATEGY = "strategy"
    EXPERIENCE = "experience"
    CORPUS = "corpus"
    ROUTING_DECISION = "routing_decision"
    ROUTING_OUTCOME = "routing_outcome"
    ROUTING_SHADOW = "routing_shadow"
    BENCHMARK = "benchmark"
    ARTIFACT = "artifact"


class CausalRelationshipType(StrEnum):
    OBSERVED_FAILURE = "observed_failure"
    CONTRIBUTING_CONDITION = "contributing_condition"
    CORRELATED_CONDITION = "correlated_condition"
    UNKNOWN_CAUSAL_RELATIONSHIP = "unknown_causal_relationship"


class NextAnalysisType(StrEnum):
    COLLECT_MORE_EVIDENCE = "collect_more_evidence"
    RUN_BOUNDED_REPLAY = "run_bounded_replay"
    CREATE_BENCHMARK_CANDIDATE = "create_benchmark_candidate"
    INSPECT_CONTEXT_TRACE = "inspect_context_trace"
    INSPECT_RETRIEVAL = "inspect_retrieval"
    INSPECT_VERIFIER = "inspect_verifier"
    INSPECT_ROUTING = "inspect_routing"
    INSPECT_SKILL = "inspect_skill"
    INSPECT_STRATEGY = "inspect_strategy"
    INSPECT_PROVIDER_OR_TOOL = "inspect_provider_or_tool"
    OPERATOR_REVIEW = "operator_review"
    MONITOR = "monitor"
    NONE = "none"


class EvidenceRole(StrEnum):
    PRIMARY = "primary"
    CORROBORATING = "corroborating"
    COUNTEREXAMPLE = "counterexample"
    CONFLICTING = "conflicting"


class QueueBlockerType(StrEnum):
    REQUIRES_MORE_EVIDENCE = "requires_more_evidence"
    REQUIRES_REPRODUCTION = "requires_reproduction"
    DEPENDS_ON_OTHER_WEAKNESS = "depends_on_other_weakness"
    REQUIRES_OPERATOR_REVIEW = "requires_operator_review"
    SOURCE_UNAVAILABLE = "source_unavailable"
    SENSITIVITY_RESTRICTION = "sensitivity_restriction"


class ImpactDimension(StrEnum):
    FREQUENCY = "frequency"
    AFFECTED_TASK_COUNT = "affected_task_count"
    SEVERITY = "severity"
    SAFETY_IMPACT = "safety_impact"
    CORRECTNESS_IMPACT = "correctness_impact"
    USER_CORRECTION_COUNT = "user_correction_count"
    COST_IMPACT = "cost_impact"
    LATENCY_IMPACT = "latency_impact"
    REPAIR_ITERATION_IMPACT = "repair_iteration_impact"
    RECENCY = "recency"
    REPRODUCIBILITY = "reproducibility"
    EVIDENCE_CONFIDENCE = "evidence_confidence"
    STRATEGIC_REACH = "strategic_reach"


class MiningProfile(HashedExperienceContract):
    profile_id: NonEmptyStr
    version: int = Field(gt=0)
    enabled_source_types: Annotated[tuple[SignalSourceType, ...], Field(min_length=1)]
    enabled_extractors: Annotated[tuple[NonEmptyStr, ...], Field(min_length=1)]
    signature_profile: NonEmptyStr
    grouping_profile: NonEmptyStr
    clustering_profile: NonEmptyStr
    impact_profile: NonEmptyStr
    confirmation_policy: NonEmptyStr
    queue_policy: NonEmptyStr
    resource_limits: dict[NonEmptyStr, int]
    created_at: UtcDatetime

    @field_validator("enabled_source_types", "enabled_extractors")
    @classmethod
    def canonical_values(cls, value: tuple[object, ...]) -> tuple[object, ...]:
        return tuple(sorted(set(value), key=str))


class MiningRequest(HashedExperienceContract):
    mining_run_id: UUID
    scope: NonEmptyStr
    task_run_ids: tuple[UUID, ...] = ()
    time_range_start: UtcDatetime | None = None
    time_range_end: UtcDatetime | None = None
    source_filters: tuple[SignalSourceType, ...] = ()
    weakness_type_filters: tuple[WeaknessType, ...] = ()
    mining_profile_hash: Sha256Hex
    requested_by: NonEmptyStr
    idempotency_key: NonEmptyStr
    created_at: UtcDatetime

    @model_validator(mode="after")
    def require_bounded_selector(self) -> MiningRequest:
        if not self.task_run_ids and self.time_range_start is None and not self.source_filters:
            raise ValueError("mining request requires a bounded source selector")
        if (
            self.time_range_start
            and self.time_range_end
            and self.time_range_end < self.time_range_start
        ):
            raise ValueError("mining time range is reversed")
        return self


class MiningSourceReference(HashedExperienceContract):
    source_type: SignalSourceType
    source_id: NonEmptyStr
    source_revision: NonEmptyStr
    event_stream_id: UUID | None = None
    event_stream_version: int | None = Field(default=None, ge=0)
    artifact_id: UUID | None = None
    source_content_hash: Sha256Hex
    scope: NonEmptyStr
    sensitivity: MemorySensitivity
    required: bool = True
    authoritative: bool = True
    shadow: bool = False
    outcome_authority: bool = False
    contains_secret: bool = False

    @field_validator("source_id", "source_revision", "scope")
    @classmethod
    def reject_host_paths(cls, value: str) -> str:
        if (
            PurePosixPath(value).is_absolute()
            or PureWindowsPath(value).is_absolute()
            or re.match(r"^[A-Za-z]:[\\/]", value)
            or "/home/" in value
            or "\\Users\\" in value
        ):
            raise ValueError("source identities must not contain host paths")
        return value

    @model_validator(mode="after")
    def validate_authority(self) -> MiningSourceReference:
        if self.contains_secret:
            raise ValueError("secret-bearing sources cannot enter weakness metadata")
        if self.shadow and self.outcome_authority:
            raise ValueError("shadow routing evidence cannot claim an outcome")
        return self


class MiningSourceSnapshot(HashedExperienceContract):
    mining_run_id: UUID
    source_refs: Annotated[tuple[MiningSourceReference, ...], Field(min_length=1)]
    registry_snapshots: tuple[Sha256Hex, ...]
    profile_refs: tuple[Sha256Hex, ...]
    created_at: UtcDatetime

    @field_validator("source_refs")
    @classmethod
    def canonical_sources(
        cls, value: tuple[MiningSourceReference, ...]
    ) -> tuple[MiningSourceReference, ...]:
        ordered = tuple(
            sorted(value, key=lambda item: (item.source_type, item.source_id, item.source_revision))
        )
        identities = {(item.source_type, item.source_id, item.source_revision) for item in ordered}
        if len(identities) != len(ordered):
            raise ValueError("source snapshot contains duplicate exact sources")
        return ordered

    @field_validator("registry_snapshots", "profile_refs")
    @classmethod
    def canonical_hashes(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        return tuple(sorted(set(value)))


class WeaknessSignalEvidence(HashedExperienceContract):
    source_ref: MiningSourceReference
    role: EvidenceRole
    evidence_code: NonEmptyStr
    limitation: NonEmptyStr | None = None


class WeaknessCounterexample(HashedExperienceContract):
    counterexample_id: UUID
    signature_hash: Sha256Hex
    task_run_id: UUID
    source_refs: Annotated[tuple[MiningSourceReference, ...], Field(min_length=1)]
    compatibility_reason: NonEmptyStr
    observed_at: UtcDatetime


class WeaknessSignalConflict(HashedExperienceContract):
    conflict_id: UUID
    signal_ids: Annotated[tuple[UUID, ...], Field(min_length=2)]
    source_refs: Annotated[tuple[MiningSourceReference, ...], Field(min_length=1)]
    reason: NonEmptyStr


class WeaknessSignal(HashedExperienceContract):
    signal_id: UUID
    mining_run_id: UUID
    status: WeaknessSignalStatus = WeaknessSignalStatus.OBSERVED
    weakness_type: WeaknessType
    task_run_id: UUID
    source_refs: Annotated[tuple[MiningSourceReference, ...], Field(min_length=1, max_length=64)]
    task_signature: TaskSignature
    failure_code: NonEmptyStr
    component_type: WeaknessComponentType
    component_identity: NonEmptyStr
    skill_revision: NonEmptyStr | None = None
    strategy_revision: NonEmptyStr | None = None
    routing_decision: UUID | None = None
    verifier_reference: NonEmptyStr | None = None
    context_reference: NonEmptyStr | None = None
    severity: WeaknessSeverity
    confidence: WeaknessConfidenceLevel
    causal_relationship: CausalRelationshipType
    observed_at: UtcDatetime
    extractor_profile: NonEmptyStr
    limitations: tuple[NonEmptyStr, ...] = ()

    @model_validator(mode="after")
    def require_authoritative_evidence(self) -> WeaknessSignal:
        if not any(item.authoritative and not item.shadow for item in self.source_refs):
            raise ValueError("weakness signal requires non-shadow authoritative evidence")
        if all(item.source_type is SignalSourceType.PROVIDER_RESULT for item in self.source_refs):
            raise ValueError("provider prose alone cannot create a weakness signal")
        if any(item.shadow and item.outcome_authority for item in self.source_refs):
            raise ValueError("shadow evidence cannot claim task outcome")
        return self


class WeaknessSignature(HashedExperienceContract):
    weakness_type: WeaknessType
    normalized_problem_signature: Sha256Hex
    normalized_failure_code: NonEmptyStr
    component_type: WeaknessComponentType
    component_identity: NonEmptyStr
    skill_identity: NonEmptyStr | None = None
    strategy_identity: NonEmptyStr | None = None
    provider_identity: NonEmptyStr | None = None
    model_identity: NonEmptyStr | None = None
    tool_identity: NonEmptyStr | None = None
    verifier_identity: NonEmptyStr | None = None
    context_source_type: NonEmptyStr | None = None
    retrieval_identity: NonEmptyStr | None = None
    routing_policy_identity: NonEmptyStr | None = None
    corpus_destination: NonEmptyStr | None = None
    risk_class: NonEmptyStr
    scope: NonEmptyStr
    signature_version: NonEmptyStr = "weakness-signature-v1"


class WeaknessGroupMember(HashedExperienceContract):
    signal_id: UUID
    signal_hash: Sha256Hex
    task_run_id: UUID
    observed_at: UtcDatetime


class WeaknessGroup(HashedExperienceContract):
    group_id: UUID
    revision: int = Field(gt=0)
    signature: WeaknessSignature
    members: Annotated[tuple[WeaknessGroupMember, ...], Field(min_length=1)]
    distinct_task_count: int = Field(gt=0)
    distinct_component_count: int = Field(gt=0)
    first_seen: UtcDatetime
    last_seen: UtcDatetime
    counterexample_refs: tuple[Sha256Hex, ...] = ()

    @field_validator("members")
    @classmethod
    def canonical_members(
        cls, value: tuple[WeaknessGroupMember, ...]
    ) -> tuple[WeaknessGroupMember, ...]:
        ordered = tuple(sorted(value, key=lambda item: str(item.signal_id)))
        if len({item.signal_id for item in ordered}) != len(ordered):
            raise ValueError("weakness group contains duplicate signals")
        return ordered

    @model_validator(mode="after")
    def validate_counts(self) -> WeaknessGroup:
        if self.distinct_task_count != len({item.task_run_id for item in self.members}):
            raise ValueError("weakness group task count does not match members")
        if self.last_seen < self.first_seen:
            raise ValueError("weakness group time range is reversed")
        return self


class WeaknessGroupSnapshot(HashedExperienceContract):
    snapshot_id: UUID
    groups: tuple[WeaknessGroup, ...]
    source_signal_hash: Sha256Hex
    profile_hash: Sha256Hex
    created_at: UtcDatetime

    @field_validator("groups")
    @classmethod
    def canonical_groups(cls, value: tuple[WeaknessGroup, ...]) -> tuple[WeaknessGroup, ...]:
        return tuple(sorted(value, key=lambda item: item.signature.content_hash))


class WeaknessClusterMember(HashedExperienceContract):
    group_id: UUID
    group_revision: int = Field(gt=0)
    group_hash: Sha256Hex


class WeaknessCluster(HashedExperienceContract):
    cluster_id: UUID
    revision: int = Field(gt=0)
    method: WeaknessClusterMethod
    method_profile_hash: Sha256Hex
    members: tuple[WeaknessClusterMember, ...]
    advisory: bool = True
    created_at: UtcDatetime

    @model_validator(mode="after")
    def remain_advisory(self) -> WeaknessCluster:
        if not self.advisory:
            raise ValueError("weakness clusters are advisory only")
        return self


class WeaknessClusterSnapshot(HashedExperienceContract):
    snapshot_id: UUID
    group_snapshot_hash: Sha256Hex
    method: WeaknessClusterMethod
    clusters: tuple[WeaknessCluster, ...]
    created_at: UtcDatetime


class WeaknessClusterComparison(HashedExperienceContract):
    left_snapshot_hash: Sha256Hex
    right_snapshot_hash: Sha256Hex
    added_group_hashes: tuple[Sha256Hex, ...]
    removed_group_hashes: tuple[Sha256Hex, ...]
    stable_group_count: int = Field(ge=0)
    limitations: tuple[NonEmptyStr, ...] = ()


class ImpactEvidence(HashedExperienceContract):
    source_refs: Annotated[tuple[MiningSourceReference, ...], Field(min_length=1)]
    evidence_code: NonEmptyStr


class ImpactUncertainty(HashedExperienceContract):
    value: Decimal = Field(ge=0, le=1)
    missing_source_count: int = Field(ge=0)
    conflict_count: int = Field(ge=0)
    counterexample_count: int = Field(ge=0)
    limitations: tuple[NonEmptyStr, ...] = ()


class ImpactProfileReference(HashedExperienceContract):
    profile_id: NonEmptyStr
    version: int = Field(gt=0)
    weights: dict[ImpactDimension, Decimal]
    critical_safety_priority_floor: Decimal = Field(ge=0, le=100)
    high_correctness_priority_floor: Decimal = Field(ge=0, le=100)
    score_precision: int = Field(default=4, ge=0, le=8)

    @model_validator(mode="after")
    def require_complete_weights(self) -> ImpactProfileReference:
        if set(self.weights) != set(ImpactDimension):
            raise ValueError("impact profile must define all dimensions")
        if sum(self.weights.values(), Decimal()) != Decimal("1"):
            raise ValueError("impact weights must total one")
        return self


class ImpactDimensionResult(HashedExperienceContract):
    dimension: ImpactDimension
    raw_value: Decimal
    normalized_value: Decimal = Field(ge=0, le=1)
    weight: Decimal = Field(ge=0, le=1)
    weighted_value: Decimal = Field(ge=0, le=1)
    source_refs: tuple[Sha256Hex, ...]
    sample_count: int = Field(ge=0)
    uncertainty: Decimal = Field(ge=0, le=1)
    profile_version: int = Field(gt=0)

    @field_validator("raw_value", "normalized_value", "weight", "weighted_value", "uncertainty")
    @classmethod
    def finite_decimal(cls, value: Decimal) -> Decimal:
        if not math.isfinite(float(value)):
            raise ValueError("impact values must be finite")
        return value


class ImpactScore(HashedExperienceContract):
    impact_score_id: UUID
    weakness_id: UUID | None = None
    weakness_revision: int | None = Field(default=None, gt=0)
    group_snapshot_hash: Sha256Hex
    dimensions: Annotated[tuple[ImpactDimensionResult, ...], Field(min_length=13, max_length=13)]
    base_score: Decimal = Field(ge=0, le=100)
    priority_floor: Decimal = Field(ge=0, le=100)
    final_score: Decimal = Field(ge=0, le=100)
    priority: WeaknessPriority
    uncertainty: ImpactUncertainty
    profile: ImpactProfileReference
    created_at: UtcDatetime
    limitations: tuple[NonEmptyStr, ...] = ()

    @model_validator(mode="after")
    def validate_dimensions(self) -> ImpactScore:
        if {item.dimension for item in self.dimensions} != set(ImpactDimension):
            raise ValueError("impact score requires each dimension exactly once")
        if self.final_score < max(self.base_score, self.priority_floor):
            raise ValueError("final impact score cannot ignore its priority floor")
        return self


class WeaknessReproductionAttempt(HashedExperienceContract):
    attempt_id: UUID
    source_snapshot_hash: Sha256Hex
    environment_hash: Sha256Hex
    result: WeaknessReproductionStatus
    verifier_bundle_hash: Sha256Hex
    attempted_at: UtcDatetime
    limitations: tuple[NonEmptyStr, ...] = ()


class WeaknessReproductionAssessment(HashedExperienceContract):
    status: WeaknessReproductionStatus
    attempts: tuple[WeaknessReproductionAttempt, ...]
    required_safety_restrictions: tuple[NonEmptyStr, ...]
    limitations: tuple[NonEmptyStr, ...]
    assessed_at: UtcDatetime


class WeaknessReplayCandidate(HashedExperienceContract):
    candidate_id: UUID
    weakness_revision_hash: Sha256Hex
    source_snapshot_hash: Sha256Hex
    request_hash: Sha256Hex
    expected_result_hash: Sha256Hex
    proposal_only: bool = True

    @model_validator(mode="after")
    def remain_proposal_only(self) -> WeaknessReplayCandidate:
        if not self.proposal_only:
            raise ValueError("replay candidates cannot activate themselves")
        return self


class WeaknessBenchmarkCandidate(HashedExperienceContract):
    candidate_id: UUID
    weakness_revision_hash: Sha256Hex
    task_fixture_hash: Sha256Hex
    expected_outcome_hash: Sha256Hex
    required_verifiers: tuple[NonEmptyStr, ...]
    forbidden_operations: tuple[NonEmptyStr, ...]
    sensitivity: MemorySensitivity
    proposal_only: bool = True

    @model_validator(mode="after")
    def remain_proposal_only(self) -> WeaknessBenchmarkCandidate:
        if not self.proposal_only:
            raise ValueError("benchmark candidates cannot activate themselves")
        return self


class WeaknessEvidencePackage(HashedExperienceContract):
    evidence_package_id: UUID
    weakness_id: UUID | None = None
    weakness_revision: int | None = Field(default=None, gt=0)
    group_snapshot_hash: Sha256Hex
    source_manifest: tuple[MiningSourceReference, ...]
    representative_signal_hashes: tuple[Sha256Hex, ...]
    complete_source_count: int = Field(gt=0)
    counterexample_hashes: tuple[Sha256Hex, ...]
    task_refs: tuple[UUID, ...]
    event_refs: tuple[UUID, ...]
    artifact_refs: tuple[UUID, ...]
    component_sections: dict[NonEmptyStr, tuple[Sha256Hex, ...]]
    reproduction: WeaknessReproductionAssessment
    sensitivity: MemorySensitivity
    limitations: tuple[NonEmptyStr, ...]
    artifact_reference: UUID
    checksums: dict[NonEmptyStr, Sha256Hex]
    verification_hash: Sha256Hex

    @model_validator(mode="after")
    def require_complete_lineage(self) -> WeaknessEvidencePackage:
        if self.complete_source_count != len(self.source_manifest):
            raise ValueError("evidence package source count is incomplete")
        if not self.representative_signal_hashes or not self.checksums:
            raise ValueError("evidence package requires signals and checksums")
        return self


class WeaknessIdentity(HashedExperienceContract):
    weakness_id: UUID
    canonical_name: NonEmptyStr
    weakness_type: WeaknessType
    signature_hash: Sha256Hex
    scope: NonEmptyStr
    created_at: UtcDatetime
    created_by: NonEmptyStr


class WeaknessRevision(HashedExperienceContract):
    weakness_id: UUID
    revision: int = Field(gt=0)
    previous_revision: int | None = Field(default=None, gt=0)
    status: WeaknessStatus
    title: NonEmptyStr
    description: NonEmptyStr
    weakness_type: WeaknessType
    signature_hash: Sha256Hex
    group_snapshot_hash: Sha256Hex
    cluster_refs: tuple[Sha256Hex, ...]
    impact_score_hash: Sha256Hex
    evidence_package_hash: Sha256Hex
    reproduction_status: WeaknessReproductionStatus
    affected_components: tuple[NonEmptyStr, ...]
    source_refs: tuple[Sha256Hex, ...]
    counterexample_refs: tuple[Sha256Hex, ...]
    monitoring_policy: NonEmptyStr | None = None
    successor_weakness_id: UUID | None = None
    verifier_bundle_hash: Sha256Hex
    operator_approval_reference: NonEmptyStr | None = None
    created_at: UtcDatetime
    created_by: NonEmptyStr
    reason: NonEmptyStr

    @model_validator(mode="after")
    def validate_revision_chain(self) -> WeaknessRevision:
        if self.revision == 1 and self.previous_revision is not None:
            raise ValueError("initial weakness revision cannot have a predecessor")
        if self.revision > 1 and self.previous_revision != self.revision - 1:
            raise ValueError("weakness revisions must be contiguous")
        if self.status is WeaknessStatus.SUPERSEDED and self.successor_weakness_id is None:
            raise ValueError("superseded weakness requires a successor")
        return self


class WeaknessQueueDependency(HashedExperienceContract):
    blocker_type: QueueBlockerType
    blocked_by_weakness_id: UUID | None = None
    evidence_reference: Sha256Hex
    reason: NonEmptyStr


class WeaknessQueueDecision(HashedExperienceContract):
    eligible: bool
    priority: WeaknessPriority | None = None
    priority_reason: NonEmptyStr
    exclusion_reasons: tuple[NonEmptyStr, ...] = ()
    policy_hash: Sha256Hex


class WeaknessQueueEntry(HashedExperienceContract):
    queue_entry_id: UUID
    weakness_id: UUID
    weakness_revision: int = Field(gt=0)
    weakness_revision_hash: Sha256Hex
    weakness_status: WeaknessStatus
    priority: WeaknessPriority
    priority_reason: NonEmptyStr
    blocked_by: tuple[WeaknessQueueDependency, ...]
    recommended_next_analysis: NextAnalysisType
    status: WeaknessQueueStatus
    queue_policy_hash: Sha256Hex
    created_at: UtcDatetime


class WeaknessQueueSnapshot(HashedExperienceContract):
    snapshot_id: UUID
    queue_policy_hash: Sha256Hex
    entries: tuple[WeaknessQueueEntry, ...]
    exclusions: dict[NonEmptyStr, NonEmptyStr]
    created_at: UtcDatetime


class WeaknessAccessRecord(HashedExperienceContract):
    access_id: UUID
    access_type: WeaknessAccessType
    actor_id: NonEmptyStr
    subject_id: NonEmptyStr
    subject_revision: int | None = Field(default=None, gt=0)
    subject_hash: Sha256Hex
    accessed_at: UtcDatetime
    reason: NonEmptyStr


class MiningRunSummary(HashedExperienceContract):
    mining_run_id: UUID
    source_count: int = Field(ge=0)
    signal_count: int = Field(ge=0)
    signature_count: int = Field(ge=0)
    group_count: int = Field(ge=0)
    weakness_count: int = Field(ge=0)
    queue_entry_count: int = Field(ge=0)
    warnings: tuple[NonEmptyStr, ...]
    exclusions: tuple[NonEmptyStr, ...]


class MiningRunManifest(HashedExperienceContract):
    mining_run_id: UUID
    request_hash: Sha256Hex
    source_snapshot_hash: Sha256Hex
    registry_snapshot_hashes: tuple[Sha256Hex, ...]
    signal_hashes: tuple[Sha256Hex, ...]
    group_snapshot_hash: Sha256Hex
    cluster_snapshot_hash: Sha256Hex | None = None
    impact_hashes: tuple[Sha256Hex, ...]
    weakness_revision_hashes: tuple[Sha256Hex, ...]
    queue_snapshot_hash: Sha256Hex
    verifier_bundle_hash: Sha256Hex
    stage_hashes: dict[NonEmptyStr, Sha256Hex]
    summary: MiningRunSummary
    created_at: UtcDatetime


class MiningRunResult(HashedExperienceContract):
    status: MiningRunStatus
    manifest: MiningRunManifest | None = None
    failure_code: NonEmptyStr | None = None
    completed_at: UtcDatetime


class WeaknessVerificationSubject(HashedExperienceContract):
    subject_type: NonEmptyStr
    subject_id: NonEmptyStr
    subject_revision: int | None = Field(default=None, gt=0)
    subject_hash: Sha256Hex
    related_hashes: tuple[Sha256Hex, ...] = ()
    bounded_metadata: dict[NonEmptyStr, JsonValue] = Field(default_factory=dict)


PUBLIC_WEAKNESS_CONTRACTS = (
    MiningProfile,
    MiningRequest,
    MiningSourceReference,
    MiningSourceSnapshot,
    WeaknessSignalEvidence,
    WeaknessCounterexample,
    WeaknessSignalConflict,
    WeaknessSignal,
    WeaknessSignature,
    WeaknessGroupMember,
    WeaknessGroup,
    WeaknessGroupSnapshot,
    WeaknessClusterMember,
    WeaknessCluster,
    WeaknessClusterSnapshot,
    WeaknessClusterComparison,
    ImpactEvidence,
    ImpactUncertainty,
    ImpactProfileReference,
    ImpactDimensionResult,
    ImpactScore,
    WeaknessReproductionAttempt,
    WeaknessReproductionAssessment,
    WeaknessReplayCandidate,
    WeaknessBenchmarkCandidate,
    WeaknessEvidencePackage,
    WeaknessIdentity,
    WeaknessRevision,
    WeaknessQueueDependency,
    WeaknessQueueDecision,
    WeaknessQueueEntry,
    WeaknessQueueSnapshot,
    WeaknessAccessRecord,
    MiningRunSummary,
    MiningRunManifest,
    MiningRunResult,
    WeaknessVerificationSubject,
)
