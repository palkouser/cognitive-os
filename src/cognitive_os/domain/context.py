"""Immutable contracts for deterministic context construction."""

from __future__ import annotations

import json
import re
from decimal import Decimal
from enum import StrEnum
from hashlib import sha256
from pathlib import PurePosixPath, PureWindowsPath
from typing import Annotated
from uuid import UUID

from pydantic import Field, field_validator, model_validator

from .base import ImmutableContractModel
from .common import ArtifactRef, NonEmptyStr, Sha256Hex, UtcDatetime
from .memory import MemoryScope, MemorySensitivity, MemoryType


class ContextContract(ImmutableContractModel):
    """Contract with stable JSON and hash helpers."""

    def canonical_json(self, *, exclude: set[str] | None = None) -> str:
        return json.dumps(
            self.model_dump(mode="json", exclude=exclude or set()),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )

    def canonical_hash(self, *, exclude: set[str] | None = None) -> str:
        return sha256(self.canonical_json(exclude=exclude).encode()).hexdigest()


class ContextSourceType(StrEnum):
    TASK_STATE = "task_state"
    EXECUTION_PLAN = "execution_plan"
    EVENT = "event"
    PROVIDER_RESULT = "provider_result"
    TOOL_RESULT = "tool_result"
    ARTIFACT = "artifact"
    MEMORY = "memory"
    SEMANTIC_CLAIM = "semantic_claim"
    SEMANTIC_GRAPH = "semantic_graph"
    WIKI = "wiki"
    REPOSITORY_INDEX = "repository_index"
    WORKSPACE = "workspace"
    USER_CORRECTION = "user_correction"


class ContextTrustClass(StrEnum):
    SYSTEM = "system"
    VERIFIED = "verified"
    USER_PROVIDED = "user_provided"
    UNVERIFIED = "unverified"
    EXTERNAL = "external"
    DISPUTED = "disputed"


class ContextPurpose(StrEnum):
    PLANNING = "planning"
    EXECUTION = "execution"
    REPAIR = "repair"
    CODING = "coding"
    ADVISORY = "advisory"
    SEMANTIC_EXTRACTION = "semantic_extraction"


class ContextBuildStatus(StrEnum):
    REQUESTED = "requested"
    BUILDING = "building"
    CREATED = "created"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ContextBuildFailure(StrEnum):
    RETRY_SAFE = "retry_safe"
    NEEDS_CLARIFICATION = "needs_clarification"
    BUDGET_EXHAUSTED = "budget_exhausted"
    REQUIRED_SOURCE_MISSING = "required_source_missing"
    SAFETY_REJECTED = "safety_rejected"
    RETRIEVER_UNAVAILABLE = "retriever_unavailable"
    FAILED = "failed"


class ContextExclusionReason(StrEnum):
    SCOPE_MISMATCH = "scope_mismatch"
    SENSITIVITY_EXCEEDED = "sensitivity_exceeded"
    STATUS_NOT_ALLOWED = "status_not_allowed"
    DUPLICATE = "duplicate"
    LOWER_RANK = "lower_rank"
    SOURCE_LIMIT = "source_limit"
    TOKEN_BUDGET = "token_budget"  # nosec B105 - exclusion reason, not a credential
    SECRET_DETECTED = "secret_detected"  # nosec B105  # pragma: allowlist secret
    STALE_SOURCE = "stale_source"
    INVALID_PROVENANCE = "invalid_provenance"
    UNAVAILABLE_RETRIEVER = "unavailable_retriever"
    UNSAFE_CONTENT = "unsafe_content"


class ContextWarningType(StrEnum):
    SUSPICIOUS_INSTRUCTION = "suspicious_instruction"
    CONTRADICTION = "contradiction"
    OPTIONAL_SOURCE_UNAVAILABLE = "optional_source_unavailable"
    QUOTA_UNMET = "quota_unmet"
    CONTENT_TRUNCATED = "content_truncated"
    STALE_OPTIONAL_SOURCE = "stale_optional_source"


class RetrievalMode(StrEnum):
    METADATA = "metadata"
    LEXICAL = "lexical"
    EXACT_VECTOR = "exact_vector"
    GRAPH = "graph"
    RECENT = "recent"
    SOURCE_LOOKUP = "source_lookup"
    CODE = "code"


class HydrationLevel(StrEnum):
    METADATA = "metadata"
    SUMMARY = "summary"
    EXCERPT = "excerpt"
    FULL = "full"


class TokenEstimatorType(StrEnum):
    CONSERVATIVE_UTF8 = "conservative_utf8"
    PROVIDER = "provider"


class RerankerType(StrEnum):
    NONE = "none"
    LOCAL_CROSS_ENCODER = "local_cross_encoder"


class ContextComponentStatus(StrEnum):
    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"
    DEGRADED = "degraded"


class ContextComponentHealth(ContextContract):
    status: ContextComponentStatus
    reason: NonEmptyStr | None = None


class ContextRetrieverDescriptor(ContextContract):
    retriever_id: str = Field(pattern=r"^[a-z][a-z0-9]*(?:[._-][a-z0-9]+)+$")
    version: NonEmptyStr
    source_types: Annotated[tuple[ContextSourceType, ...], Field(min_length=1)]
    supported_modes: Annotated[tuple[RetrievalMode, ...], Field(min_length=1)]
    deterministic: bool = True
    requires_postgres: bool = False
    requires_artifact_store: bool = False
    requires_workspace: bool = False
    requires_network: bool = False
    default_trust_class: ContextTrustClass
    maximum_candidates: int = Field(ge=1, le=200)


class ContextRerankerDescriptor(ContextContract):
    reranker_id: NonEmptyStr
    version: NonEmptyStr
    reranker_type: RerankerType
    deterministic: bool
    requires_network: bool = False
    model_digest: Sha256Hex | None = None


class ContextBudget(ContextContract):
    provider_context_limit: int = Field(gt=0, le=1_000_000)
    reserved_output_tokens: int = Field(ge=0)
    system_instruction_tokens: int = Field(ge=0)
    task_and_plan_tokens: int = Field(ge=0)
    safety_margin_tokens: int = Field(ge=0)
    maximum_retriever_calls: int = Field(gt=0, le=24)
    maximum_candidates: int = Field(gt=0, le=1_000)
    maximum_items: int = Field(gt=0, le=64)
    maximum_items_per_source: int = Field(gt=0, le=64)
    minimum_recent_items: int = Field(ge=0, le=64)
    minimum_evidence_items: int = Field(ge=0, le=64)
    maximum_elapsed_seconds: float = Field(gt=0, le=300, allow_inf_nan=False)

    @property
    def available_tokens(self) -> int:
        return max(
            0,
            self.provider_context_limit
            - self.reserved_output_tokens
            - self.system_instruction_tokens
            - self.task_and_plan_tokens
            - self.safety_margin_tokens,
        )

    @model_validator(mode="after")
    def fixed_content_fits(self) -> ContextBudget:
        if self.available_tokens <= 0:
            raise ValueError("fixed context and reservations leave no retrieval budget")
        if self.maximum_items_per_source > self.maximum_items:
            raise ValueError("per-source item limit exceeds the total item limit")
        return self


class TemporalQuerySelector(ContextContract):
    valid_at: UtcDatetime | None = None
    known_at: UtcDatetime | None = None


class QueryTerm(ContextContract):
    value: Annotated[str, Field(min_length=1, max_length=512)]
    normalized: Annotated[str, Field(min_length=1, max_length=512)]


class CodeQuerySeed(ContextContract):
    paths: tuple[Annotated[str, Field(max_length=512)], ...] = Field(max_length=64)
    symbols: tuple[Annotated[str, Field(max_length=512)], ...] = Field(max_length=64)

    @field_validator("paths")
    @classmethod
    def paths_are_logical(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        for value in values:
            posix, windows = PurePosixPath(value), PureWindowsPath(value)
            if posix.is_absolute() or windows.is_absolute() or ".." in posix.parts:
                raise ValueError("code query paths must be logical relative paths")
        return values


class SemanticQuerySeed(ContextContract):
    subject_keys: tuple[Annotated[str, Field(max_length=1_024)], ...] = Field(max_length=64)
    predicate_ids: tuple[Annotated[str, Field(max_length=512)], ...] = Field(max_length=64)


class GraphQuerySeed(ContextContract):
    node_ids: tuple[NonEmptyStr, ...] = Field(max_length=64)
    maximum_depth: int = Field(default=3, ge=1, le=3)
    maximum_nodes: int = Field(default=500, ge=1, le=500)


class RetrievalSubquery(ContextContract):
    subquery_id: UUID
    source_type: ContextSourceType
    mode: RetrievalMode
    terms: tuple[QueryTerm, ...] = Field(max_length=64)
    code: CodeQuerySeed | None = None
    semantic: SemanticQuerySeed | None = None
    graph: GraphQuerySeed | None = None
    temporal: TemporalQuerySelector = TemporalQuerySelector()
    maximum_results: int = Field(default=100, ge=1, le=200)


class ContextQueryPlan(ContextContract):
    query_plan_id: UUID
    raw_query_hash: Sha256Hex
    normalized_query: Annotated[str, Field(min_length=1, max_length=8_192)]
    subqueries: Annotated[tuple[RetrievalSubquery, ...], Field(min_length=1, max_length=24)]

    @field_validator("subqueries")
    @classmethod
    def deterministic_unique_order(
        cls, values: tuple[RetrievalSubquery, ...]
    ) -> tuple[RetrievalSubquery, ...]:
        keys = [(item.source_type.value, item.mode.value, str(item.subquery_id)) for item in values]
        if keys != sorted(keys) or len({item.subquery_id for item in values}) != len(values):
            raise ValueError("subqueries must be unique and canonically ordered")
        return values


class EventStreamSnapshot(ContextContract):
    stream_id: UUID
    upper_version: int = Field(ge=0)


class ArtifactSnapshot(ContextContract):
    artifact_id: UUID
    content_hash: Sha256Hex


class MemoryRevisionSnapshot(ContextContract):
    memory_id: UUID
    revision: int = Field(ge=1)
    content_hash: Sha256Hex


class SemanticRevisionSnapshot(ContextContract):
    claim_id: UUID
    revision: int = Field(ge=1)
    content_hash: Sha256Hex


class RepositorySnapshot(ContextContract):
    repository_identity: Sha256Hex
    commit_hash: Annotated[str, Field(pattern=r"^[0-9a-f]{40}$")]
    index_hash: Sha256Hex


class WorkspaceSnapshot(ContextContract):
    workspace_id: UUID
    workspace_revision: int = Field(ge=0)
    diff_hash: Sha256Hex


class ContextSourceSnapshot(ContextContract):
    event_streams: tuple[EventStreamSnapshot, ...] = ()
    artifacts: tuple[ArtifactSnapshot, ...] = ()
    memory_revisions: tuple[MemoryRevisionSnapshot, ...] = ()
    semantic_revisions: tuple[SemanticRevisionSnapshot, ...] = ()
    repository: RepositorySnapshot | None = None
    workspace: WorkspaceSnapshot | None = None
    captured_at: UtcDatetime
    snapshot_hash: str = ""

    @model_validator(mode="after")
    def seal_hash(self) -> ContextSourceSnapshot:
        expected = self.canonical_hash(exclude={"snapshot_hash"})
        if self.snapshot_hash and self.snapshot_hash != expected:
            raise ValueError("source snapshot hash mismatch")
        object.__setattr__(self, "snapshot_hash", expected)
        return self


class ContextRequest(ContextContract):
    context_request_id: UUID
    task_run_id: UUID
    step_id: UUID
    context_purpose: ContextPurpose
    problem_reference: NonEmptyStr
    plan_reference: NonEmptyStr
    current_step_reference: NonEmptyStr
    query: Annotated[str, Field(min_length=1, max_length=8_192)]
    required_scopes: Annotated[tuple[MemoryScope, ...], Field(min_length=1, max_length=16)]
    allowed_source_types: Annotated[
        tuple[ContextSourceType, ...], Field(min_length=1, max_length=13)
    ]
    allowed_memory_types: tuple[MemoryType, ...] = ()
    valid_at: UtcDatetime
    known_at: UtcDatetime
    sensitivity_limit: MemorySensitivity
    provider_profile: NonEmptyStr
    budget: ContextBudget
    source_snapshot: ContextSourceSnapshot
    created_at: UtcDatetime

    @field_validator("allowed_source_types")
    @classmethod
    def source_types_are_unique(
        cls, values: tuple[ContextSourceType, ...]
    ) -> tuple[ContextSourceType, ...]:
        if len(values) != len(set(values)):
            raise ValueError("allowed source types must be unique")
        return values

    @model_validator(mode="after")
    def historical_selector_is_safe(self) -> ContextRequest:
        if self.known_at > self.created_at:
            raise ValueError("known_at cannot be later than request creation")
        if self.context_purpose is ContextPurpose.SEMANTIC_EXTRACTION and any(
            item in {ContextSourceType.SEMANTIC_CLAIM, ContextSourceType.SEMANTIC_GRAPH}
            for item in self.allowed_source_types
        ):
            raise ValueError("semantic extraction cannot recursively retrieve semantic knowledge")
        return self


class RetrieverRank(ContextContract):
    retriever_id: NonEmptyStr
    mode: RetrievalMode
    rank: int = Field(ge=1)
    raw_score: Decimal = Field(ge=0, allow_inf_nan=False)
    weight: Decimal = Field(default=Decimal("1"), ge=0, allow_inf_nan=False)


class RetrievalScoreSet(ContextContract):
    ranks: Annotated[tuple[RetrieverRank, ...], Field(min_length=1)]


class ContextScoreBreakdown(ContextContract):
    lexical: Decimal = Decimal(0)
    vector: Decimal = Decimal(0)
    graph_proximity: Decimal = Decimal(0)
    recency: Decimal = Decimal(0)
    trust: Decimal = Decimal(0)
    verification: Decimal = Decimal(0)
    scope: Decimal = Decimal(0)
    salience: Decimal = Decimal(0)
    contradiction_penalty: Decimal = Decimal(0)
    rrf_contribution: Decimal = Decimal(0)
    final_score: Decimal = Decimal(0)

    @field_validator("*", mode="before")
    @classmethod
    def finite_decimal(cls, value: object) -> Decimal:
        result = Decimal(str(value))
        if not result.is_finite():
            raise ValueError("context scores must be finite")
        return result


class RankingProfileReference(ContextContract):
    profile_id: NonEmptyStr
    version: NonEmptyStr
    weights: dict[str, Decimal]
    rrf_k: int = Field(ge=1)
    score_precision: int = Field(ge=1, le=18)
    profile_hash: str = ""

    @model_validator(mode="after")
    def seal_hash(self) -> RankingProfileReference:
        if any(not value.is_finite() or value < 0 for value in self.weights.values()):
            raise ValueError("ranking weights must be finite and non-negative")
        expected = self.canonical_hash(exclude={"profile_hash"})
        if self.profile_hash and self.profile_hash != expected:
            raise ValueError("ranking profile hash mismatch")
        object.__setattr__(self, "profile_hash", expected)
        return self


class ContextSourceReference(ContextContract):
    source_type: ContextSourceType
    source_identity: NonEmptyStr
    source_revision: NonEmptyStr
    content_hash: Sha256Hex
    artifact_id: UUID | None = None
    start: int | None = Field(default=None, ge=0)
    end: int | None = Field(default=None, ge=0)

    @field_validator("source_identity", "source_revision")
    @classmethod
    def reject_host_paths(cls, value: str) -> str:
        if (
            PurePosixPath(value).is_absolute()
            or PureWindowsPath(value).is_absolute()
            or re.match(r"^[A-Za-z]:[\\/]", value)
            or "/home/" in value
            or "\\Users\\" in value
        ):
            raise ValueError("source references must not contain raw host paths")
        return value

    @model_validator(mode="after")
    def valid_range(self) -> ContextSourceReference:
        if (self.start is None) != (self.end is None):
            raise ValueError("source ranges require both start and end")
        if self.start is not None and self.end is not None and self.end <= self.start:
            raise ValueError("source range must be non-empty")
        return self


class ContextWarning(ContextContract):
    warning_type: ContextWarningType
    code: NonEmptyStr
    message: NonEmptyStr
    candidate_id: UUID | None = None
    source_references: tuple[ContextSourceReference, ...] = ()


class SafetySignal(ContextContract):
    signal_type: NonEmptyStr
    detected: bool
    content_hash: Sha256Hex


class SuspiciousInstructionSignal(SafetySignal):
    matched_rule: NonEmptyStr


class ContextCandidate(ContextContract):
    candidate_id: UUID
    source_type: ContextSourceType
    source_identity: NonEmptyStr
    source_revision: NonEmptyStr
    content_hash: Sha256Hex
    content: str | None = Field(default=None, max_length=1_048_576)
    summary: str | None = Field(default=None, max_length=32_768)
    artifact_references: tuple[ArtifactRef, ...] = ()
    scopes: Annotated[tuple[MemoryScope, ...], Field(min_length=1, max_length=16)]
    sensitivity: MemorySensitivity
    trust_class: ContextTrustClass
    retrieval_routes: Annotated[tuple[RetrieverRank, ...], Field(min_length=1)]
    score_breakdown: ContextScoreBreakdown = ContextScoreBreakdown()
    provenance: Annotated[tuple[ContextSourceReference, ...], Field(min_length=1)]
    valid_at: UtcDatetime | None = None
    known_at: UtcDatetime | None = None
    available_hydration_levels: Annotated[
        tuple[HydrationLevel, ...], Field(min_length=1, max_length=4)
    ] = (HydrationLevel.METADATA,)
    selected_hydration_level: HydrationLevel = HydrationLevel.METADATA
    warnings: tuple[ContextWarning, ...] = ()
    token_estimate: int = Field(default=0, ge=0)
    pinned: bool = False
    required: bool = False
    evidence: bool = False
    recent: bool = False
    contradiction_group: NonEmptyStr | None = None
    wiki_claim_references: tuple[NonEmptyStr, ...] = ()
    access_audit_ids: tuple[UUID, ...] = ()

    @model_validator(mode="after")
    def validate_identity_hydration_and_hash(self) -> ContextCandidate:
        if self.selected_hydration_level not in self.available_hydration_levels:
            raise ValueError("selected hydration level is unavailable")
        if (
            self.content is not None
            and sha256(self.content.encode()).hexdigest() != self.content_hash
        ):
            raise ValueError("hydrated candidate content hash mismatch")
        if self.required and not self.pinned:
            raise ValueError("required candidates must be pinned")
        return self


class ContextExclusion(ContextContract):
    candidate_id: UUID | None = None
    source_identity_hash: Sha256Hex
    reason: ContextExclusionReason
    detail_code: NonEmptyStr


class ContextSection(ContextContract):
    section_id: UUID
    section_type: NonEmptyStr
    title: NonEmptyStr
    trust_class: ContextTrustClass
    content: str
    source_references: Annotated[tuple[ContextSourceReference, ...], Field(min_length=1)]
    candidate_references: Annotated[tuple[UUID, ...], Field(min_length=1)]
    token_estimate: int = Field(ge=0)
    content_hash: Sha256Hex
    warnings: tuple[ContextWarning, ...] = ()

    @model_validator(mode="after")
    def validate_content_hash(self) -> ContextSection:
        if sha256(self.content.encode()).hexdigest() != self.content_hash:
            raise ValueError("context section hash mismatch")
        return self


class TokenEstimatorProfile(ContextContract):
    estimator_type: TokenEstimatorType
    estimator_id: NonEmptyStr
    version: NonEmptyStr
    bytes_per_token: int = Field(default=3, ge=1, le=16)
    per_message_overhead: int = Field(default=4, ge=0, le=1_000)
    profile_hash: str = ""

    @model_validator(mode="after")
    def seal_hash(self) -> TokenEstimatorProfile:
        expected = self.canonical_hash(exclude={"profile_hash"})
        if self.profile_hash and self.profile_hash != expected:
            raise ValueError("token estimator profile hash mismatch")
        object.__setattr__(self, "profile_hash", expected)
        return self


class ProviderContextProfile(ContextContract):
    profile_id: NonEmptyStr
    maximum_context_tokens: int = Field(gt=0, le=1_000_000)
    maximum_output_tokens: int = Field(gt=0, le=1_000_000)
    safety_margin_tokens: int = Field(ge=0)
    estimator: TokenEstimatorProfile
    sensitivity_ceiling: MemorySensitivity
    section_policy_version: NonEmptyStr = "1"


class RetrieverCallTrace(ContextContract):
    retriever_id: NonEmptyStr
    subquery_id: UUID
    returned_count: int = Field(ge=0)
    elapsed_ms: float = Field(ge=0, allow_inf_nan=False)
    available: bool = True
    access_audit_ids: tuple[UUID, ...] = ()


class DeduplicationDecision(ContextContract):
    kept_candidate_id: UUID
    removed_candidate_id: UUID
    reason: ContextExclusionReason = ContextExclusionReason.DUPLICATE


class ContextRetrievalTrace(ContextContract):
    trace_id: UUID
    context_request_id: UUID
    query_hash: Sha256Hex
    registry_snapshot_hash: Sha256Hex
    retriever_calls: tuple[RetrieverCallTrace, ...]
    candidate_count: int = Field(ge=0)
    ranked_candidate_ids: tuple[UUID, ...]
    score_breakdowns: dict[str, ContextScoreBreakdown]
    deduplication_decisions: tuple[DeduplicationDecision, ...]
    selected_candidate_ids: tuple[UUID, ...]
    selected_access_audit_ids: tuple[UUID, ...] = ()
    exclusions: tuple[ContextExclusion, ...]
    token_estimates: dict[str, int]
    safety_warnings: tuple[ContextWarning, ...]
    source_snapshot: ContextSourceSnapshot
    elapsed_ms: float = Field(ge=0, allow_inf_nan=False)
    trace_hash: str = ""

    @model_validator(mode="after")
    def account_for_candidates_and_seal(self) -> ContextRetrievalTrace:
        selected = set(self.selected_candidate_ids)
        excluded = {item.candidate_id for item in self.exclusions if item.candidate_id is not None}
        if selected & excluded:
            raise ValueError("a candidate cannot be both selected and excluded")
        if len(selected | excluded) != self.candidate_count:
            raise ValueError("retrieval trace does not account for every candidate")
        expected = self.canonical_hash(exclude={"trace_hash"})
        if self.trace_hash and self.trace_hash != expected:
            raise ValueError("retrieval trace hash mismatch")
        object.__setattr__(self, "trace_hash", expected)
        return self


class ContextBundleRevision(ContextContract):
    context_bundle_id: UUID
    revision: int = Field(ge=1)
    previous_revision: int | None = Field(default=None, ge=1)
    context_request_id: UUID
    sections: tuple[ContextSection, ...]
    total_token_estimate: int = Field(ge=0)
    provider_profile: ProviderContextProfile
    source_snapshot: ContextSourceSnapshot
    retrieval_trace_reference: ArtifactRef | None = None
    rendered_context_reference: ArtifactRef | None = None
    excluded_candidates: tuple[ContextExclusion, ...] = ()
    warnings: tuple[ContextWarning, ...] = ()
    ranking_profile: RankingProfileReference
    token_estimator_profile: TokenEstimatorProfile
    created_at: UtcDatetime
    content_hash: str = ""

    @model_validator(mode="after")
    def chain_and_seal(self) -> ContextBundleRevision:
        expected_previous = None if self.revision == 1 else self.revision - 1
        if self.previous_revision != expected_previous:
            raise ValueError("bundle revision must reference its immediate predecessor")
        if self.total_token_estimate > self.provider_profile.maximum_context_tokens:
            raise ValueError("bundle token estimate exceeds the provider profile")
        expected = self.canonical_hash(exclude={"content_hash"})
        if self.content_hash and self.content_hash != expected:
            raise ValueError("Context Bundle hash mismatch")
        object.__setattr__(self, "content_hash", expected)
        return self


class ContextBundleReference(ContextContract):
    context_bundle_id: UUID
    context_bundle_revision: int = Field(ge=1)
    bundle_artifact_id: UUID
    rendered_context_artifact_id: UUID
    content_hash: Sha256Hex
    source_snapshot_hash: Sha256Hex


class ContextBuildResult(ContextContract):
    status: ContextBuildStatus
    request: ContextRequest
    bundle: ContextBundleRevision | None = None
    trace: ContextRetrievalTrace | None = None
    rendered_context: str | None = None
    bundle_reference: ContextBundleReference | None = None
    failure: ContextBuildFailure | None = None
    warnings: tuple[ContextWarning, ...] = ()

    @model_validator(mode="after")
    def terminal_shape(self) -> ContextBuildResult:
        created = self.status is ContextBuildStatus.CREATED
        if created != all(
            value is not None
            for value in (
                self.bundle,
                self.trace,
                self.rendered_context,
                self.bundle_reference,
            )
        ):
            raise ValueError("created context results require persisted bundle, trace, and content")
        if created == (self.failure is not None):
            raise ValueError("failed context results require exactly one failure")
        return self


PUBLIC_CONTEXT_CONTRACTS: tuple[type[ImmutableContractModel], ...] = (
    ContextComponentHealth,
    ContextRetrieverDescriptor,
    ContextRerankerDescriptor,
    ContextBudget,
    TemporalQuerySelector,
    QueryTerm,
    CodeQuerySeed,
    SemanticQuerySeed,
    GraphQuerySeed,
    RetrievalSubquery,
    ContextQueryPlan,
    EventStreamSnapshot,
    ArtifactSnapshot,
    MemoryRevisionSnapshot,
    SemanticRevisionSnapshot,
    RepositorySnapshot,
    WorkspaceSnapshot,
    ContextSourceSnapshot,
    ContextRequest,
    RetrieverRank,
    RetrievalScoreSet,
    ContextScoreBreakdown,
    RankingProfileReference,
    ContextSourceReference,
    ContextWarning,
    SafetySignal,
    SuspiciousInstructionSignal,
    ContextCandidate,
    ContextExclusion,
    ContextSection,
    TokenEstimatorProfile,
    ProviderContextProfile,
    RetrieverCallTrace,
    DeduplicationDecision,
    ContextRetrievalTrace,
    ContextBundleRevision,
    ContextBundleReference,
    ContextBuildResult,
)
