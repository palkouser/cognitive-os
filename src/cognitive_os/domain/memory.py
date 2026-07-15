"""Governed Memory Plane v1 contracts and invariants."""

from __future__ import annotations

import json
import math
import re
from datetime import timedelta
from enum import StrEnum
from hashlib import sha256
from typing import Annotated, Literal
from uuid import UUID

from pydantic import Field, field_validator, model_validator

from .base import ImmutableContractModel
from .common import ArtifactRef, NonEmptyStr, Sha256Hex, UtcDatetime


class MemoryContract(ImmutableContractModel):
    """Immutable contract with deterministic canonical serialization."""

    def canonical_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))

    def canonical_hash(self) -> str:
        return sha256(self.canonical_json().encode()).hexdigest()


class MemoryType(StrEnum):
    EPISODE = "episode"
    OBSERVATION = "observation"
    DECISION = "decision"
    CORRECTION = "correction"
    TASK_SUMMARY = "task_summary"
    CODE_CONTEXT = "code_context"
    VERIFICATION_SUMMARY = "verification_summary"
    FAILURE_PATTERN = "failure_pattern"
    USER_INSTRUCTION = "user_instruction"


class MemoryScopeType(StrEnum):
    GLOBAL = "global"
    PROJECT = "project"
    REPOSITORY = "repository"
    TASK = "task"
    SESSION = "session"
    DOMAIN = "domain"


class MemoryStatus(StrEnum):
    CANDIDATE = "candidate"
    VERIFIED = "verified"
    SUPERSEDED = "superseded"
    RETRACTED = "retracted"
    EXPIRED = "expired"


class MemorySensitivity(StrEnum):
    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    RESTRICTED = "restricted"


class MemoryCreatorType(StrEnum):
    USER = "user"
    OPERATOR = "operator"
    CONTROLLER = "controller"
    INGESTION_SERVICE = "ingestion_service"
    APPROVED_INTERNAL_SERVICE = "approved_internal_service"
    PROVIDER = "provider"


class MemorySourceType(StrEnum):
    EVENT = "event"
    ARTIFACT = "artifact"
    TASK_RUN = "task_run"
    ACCEPTANCE_DECISION = "acceptance_decision"
    VERIFIER_RESULT = "verifier_result"
    CODING_TRAJECTORY = "coding_trajectory"
    USER_CORRECTION = "user_correction"
    MEMORY_REVISION = "memory_revision"
    SELECTED_DECISION = "selected_decision"


class MemoryRetrievalMode(StrEnum):
    METADATA = "metadata"
    TEXT = "text"
    VECTOR = "vector"


class MemoryTransitionReason(StrEnum):
    CREATED = "created"
    CONTENT_REVISED = "content_revised"
    METADATA_REVISED = "metadata_revised"
    AUTHORITATIVE_EVIDENCE_VERIFIED = "authoritative_evidence_verified"
    SUPERSEDED_BY_SUCCESSOR = "superseded_by_successor"
    USER_CORRECTION = "user_correction"
    SOURCE_RETRACTED = "source_retracted"
    POLICY_RETRACTION = "policy_retraction"
    RETENTION_EXPIRED = "retention_expired"
    EXPLICIT_EXPIRY = "explicit_expiry"


class MemoryWriteOutcome(StrEnum):
    ALLOW_CANDIDATE = "allow_candidate"
    ALLOW_VERIFIED = "allow_verified"
    REQUIRE_MANUAL_SELECTION = "require_manual_selection"
    DENY = "deny"


class MemoryAccessKind(StrEnum):
    RETRIEVED = "retrieved"
    USED_IN_CONTEXT = "used_in_context"


class MemoryScope(MemoryContract):
    scope_type: MemoryScopeType
    scope_id: Annotated[str, Field(min_length=1, max_length=512)]

    @model_validator(mode="after")
    def reject_host_repository_paths(self) -> MemoryScope:
        value = self.scope_id
        if self.scope_type is MemoryScopeType.REPOSITORY and (
            value.startswith(("/", "\\"))
            or re.match(r"^[A-Za-z]:[\\/]", value)
            or "/home/" in value
            or "\\Users\\" in value
        ):
            raise ValueError("repository scope must use a stable identity, not a host path")
        return self


class MemoryCreator(MemoryContract):
    creator_type: MemoryCreatorType
    creator_id: NonEmptyStr


class MemorySourceIdentity(MemoryContract):
    source_type: MemorySourceType
    source_id: UUID | None = None
    memory_id: UUID | None = None
    revision: int | None = Field(default=None, ge=1)
    content_hash: Sha256Hex | None = None

    @model_validator(mode="after")
    def identity_matches_source_type(self) -> MemorySourceIdentity:
        memory_source = self.source_type is MemorySourceType.MEMORY_REVISION
        if memory_source:
            if self.memory_id is None or self.revision is None or self.source_id is not None:
                raise ValueError("memory revision source requires memory_id and revision only")
        elif self.source_id is None or self.memory_id is not None or self.revision is not None:
            raise ValueError("non-memory source requires source_id only")
        return self

    def sort_key(self) -> tuple[str, str, int]:
        identity = str(self.memory_id if self.memory_id is not None else self.source_id)
        return self.source_type.value, identity, self.revision or 0


class MemorySourceRef(MemoryContract):
    identity: MemorySourceIdentity
    source_hash: Sha256Hex
    relationship: Annotated[str, Field(min_length=1, max_length=128)] = "derived_from"


class MemoryProvenanceBundle(MemoryContract):
    sources: Annotated[tuple[MemorySourceRef, ...], Field(min_length=1, max_length=64)]

    @field_validator("sources")
    @classmethod
    def canonical_unique_acyclic_sources(
        cls, sources: tuple[MemorySourceRef, ...]
    ) -> tuple[MemorySourceRef, ...]:
        keys = [source.identity.sort_key() for source in sources]
        if keys != sorted(keys) or len(set(keys)) != len(keys):
            raise ValueError("memory sources must be unique and canonically ordered")
        return sources

    def assert_no_cycle(self, memory_id: UUID, revision: int) -> None:
        for source in self.sources:
            identity = source.identity
            if identity.memory_id == memory_id and identity.revision == revision:
                raise ValueError("memory provenance cannot reference itself")


class MemorySourceValidationResult(MemoryContract):
    identity: MemorySourceIdentity
    valid: bool
    reason_code: NonEmptyStr
    authoritative_hash: Sha256Hex | None = None


class _BaseContent(MemoryContract):
    def render_search_text(self) -> str:
        values: list[str] = []
        for value in self.model_dump(mode="json").values():
            if isinstance(value, str):
                values.append(value)
            elif isinstance(value, list):
                values.extend(item for item in value if isinstance(item, str))
        return "\n".join(values)


class EpisodeMemoryContent(_BaseContent):
    memory_type: Literal[MemoryType.EPISODE] = MemoryType.EPISODE
    task_run_id: UUID
    title: NonEmptyStr
    problem_summary: Annotated[str, Field(max_length=8192)]
    repository_identity: Sha256Hex
    base_commit: Annotated[str, Field(pattern=r"^[0-9a-f]{40}$")]
    outcome: NonEmptyStr
    patch_attempt_count: int = Field(ge=0)
    repair_count: int = Field(ge=0)
    verifier_summary: Annotated[str, Field(max_length=8192)]
    artifact_ids: tuple[UUID, ...] = ()
    remaining_risks: tuple[Annotated[str, Field(max_length=2048)], ...] = ()
    trajectory_hash: Sha256Hex


class TaskSummaryMemoryContent(_BaseContent):
    memory_type: Literal[MemoryType.TASK_SUMMARY] = MemoryType.TASK_SUMMARY
    task_run_id: UUID
    goal: Annotated[str, Field(max_length=8192)]
    constraints: tuple[Annotated[str, Field(max_length=2048)], ...] = ()
    result: Annotated[str, Field(max_length=8192)]
    review_status: NonEmptyStr


class VerificationSummaryMemoryContent(_BaseContent):
    memory_type: Literal[MemoryType.VERIFICATION_SUMMARY] = MemoryType.VERIFICATION_SUMMARY
    task_run_id: UUID
    required_passed: tuple[NonEmptyStr, ...] = ()
    required_failed: tuple[NonEmptyStr, ...] = ()
    optional_results: tuple[NonEmptyStr, ...] = ()
    verifier_errors: tuple[NonEmptyStr, ...] = ()
    acceptance_decision_id: UUID
    registry_snapshot_hash: Sha256Hex


class CodeContextMemoryContent(_BaseContent):
    memory_type: Literal[MemoryType.CODE_CONTEXT] = MemoryType.CODE_CONTEXT
    repository_identity: Sha256Hex
    base_commit: Annotated[str, Field(pattern=r"^[0-9a-f]{40}$")]
    repository_profile: Annotated[str, Field(max_length=4096)]
    context_hash: Sha256Hex
    changed_paths: tuple[Annotated[str, Field(max_length=512)], ...] = ()
    symbol_references: tuple[Annotated[str, Field(max_length=512)], ...] = ()
    diff_artifact_id: UUID | None = None
    bounded_excerpt: Annotated[str | None, Field(max_length=16_384)] = None
    excerpt_hash: Sha256Hex | None = None

    @model_validator(mode="after")
    def excerpt_has_hash(self) -> CodeContextMemoryContent:
        if (self.bounded_excerpt is None) != (self.excerpt_hash is None):
            raise ValueError("code excerpt and hash must be supplied together")
        return self


class CorrectionMemoryContent(_BaseContent):
    memory_type: Literal[MemoryType.CORRECTION] = MemoryType.CORRECTION
    correction: Annotated[str, Field(max_length=16_384)]
    corrected_memory_id: UUID | None = None
    corrected_revision: int | None = Field(default=None, ge=1)


class DecisionMemoryContent(_BaseContent):
    memory_type: Literal[MemoryType.DECISION] = MemoryType.DECISION
    decision: Annotated[str, Field(max_length=16_384)]
    rationale: Annotated[str, Field(max_length=16_384)]
    selected_by: NonEmptyStr


class ObservationMemoryContent(_BaseContent):
    memory_type: Literal[MemoryType.OBSERVATION] = MemoryType.OBSERVATION
    observation: Annotated[str, Field(max_length=16_384)]
    evidence_summary: Annotated[str, Field(max_length=8192)]


class FailurePatternMemoryContent(_BaseContent):
    memory_type: Literal[MemoryType.FAILURE_PATTERN] = MemoryType.FAILURE_PATTERN
    failed_evidence: Annotated[str, Field(max_length=8192)]
    successful_correction: Annotated[str, Field(max_length=8192)]
    task_run_id: UUID


class UserInstructionMemoryContent(_BaseContent):
    memory_type: Literal[MemoryType.USER_INSTRUCTION] = MemoryType.USER_INSTRUCTION
    instruction: Annotated[str, Field(max_length=16_384)]
    instruction_scope: NonEmptyStr


MemoryContent = Annotated[
    EpisodeMemoryContent
    | TaskSummaryMemoryContent
    | VerificationSummaryMemoryContent
    | CodeContextMemoryContent
    | CorrectionMemoryContent
    | DecisionMemoryContent
    | ObservationMemoryContent
    | FailurePatternMemoryContent
    | UserInstructionMemoryContent,
    Field(discriminator="memory_type"),
]


def memory_revision_hash(
    *,
    memory_id: UUID,
    revision: int,
    content: MemoryContent,
    status: MemoryStatus,
    confidence: float,
    salience: float,
    sensitivity: MemorySensitivity,
) -> str:
    canonical = {
        "confidence": confidence,
        "content": content.model_dump(mode="json"),
        "memory_id": str(memory_id),
        "revision": revision,
        "salience": salience,
        "sensitivity": sensitivity.value,
        "status": status.value,
    }
    encoded = json.dumps(canonical, sort_keys=True, separators=(",", ":")).encode()
    return sha256(encoded).hexdigest()


class MemoryRecord(MemoryContract):
    memory_id: UUID
    memory_type: MemoryType
    scope: MemoryScope
    status: MemoryStatus
    current_revision: int = Field(ge=1, le=1000)
    title: Annotated[str, Field(min_length=1, max_length=1024)]
    created_at: UtcDatetime
    created_by: MemoryCreator


class MemoryRevision(MemoryContract):
    memory_id: UUID
    revision: int = Field(ge=1, le=1000)
    previous_revision: int | None = Field(default=None, ge=1, le=999)
    content: MemoryContent
    content_artifact: ArtifactRef | None = None
    content_hash: Sha256Hex
    status: MemoryStatus
    confidence: float = Field(ge=0.0, le=1.0, allow_inf_nan=False)
    salience: float = Field(ge=0.0, le=1.0, allow_inf_nan=False)
    sensitivity: MemorySensitivity
    reason: MemoryTransitionReason
    created_at: UtcDatetime
    created_by: MemoryCreator
    expires_at: UtcDatetime | None = None
    successor_memory_id: UUID | None = None

    @model_validator(mode="after")
    def validate_revision_chain_and_hash(self) -> MemoryRevision:
        expected_previous = None if self.revision == 1 else self.revision - 1
        if self.previous_revision != expected_previous:
            raise ValueError("revision must reference its immediate predecessor")
        if self.successor_memory_id == self.memory_id:
            raise ValueError("memory cannot supersede itself")
        expected_hash = memory_revision_hash(
            memory_id=self.memory_id,
            revision=self.revision,
            content=self.content,
            status=self.status,
            confidence=self.confidence,
            salience=self.salience,
            sensitivity=self.sensitivity,
        )
        if self.content_hash != expected_hash:
            raise ValueError("memory revision content hash mismatch")
        return self


class MemoryWritePolicy(MemoryContract):
    allowed_types: frozenset[MemoryType]
    allowed_scopes: frozenset[MemoryScopeType]
    maximum_sensitivity: MemorySensitivity
    allow_automatic_request: bool = False
    allow_provider_creator: bool = False
    allow_verified_creation: bool = False


class MemoryWriteDecision(MemoryContract):
    decision: MemoryWriteOutcome
    reason_codes: Annotated[tuple[NonEmptyStr, ...], Field(min_length=1)]
    policy_hash: Sha256Hex
    evaluated_at: UtcDatetime


class MemoryWriteRequest(MemoryContract):
    request_id: UUID
    idempotency_key: Sha256Hex
    memory_id: UUID
    memory_type: MemoryType
    scope: MemoryScope
    title: Annotated[str, Field(min_length=1, max_length=1024)]
    content: MemoryContent
    status: MemoryStatus = MemoryStatus.CANDIDATE
    confidence: float = Field(ge=0.0, le=1.0, allow_inf_nan=False)
    salience: float = Field(ge=0.0, le=1.0, allow_inf_nan=False)
    sensitivity: MemorySensitivity
    provenance: MemoryProvenanceBundle
    actor: MemoryCreator
    reason: MemoryTransitionReason = MemoryTransitionReason.CREATED
    automatic: bool = False
    expected_revision: Literal[0] = 0

    @model_validator(mode="after")
    def type_matches_content_and_provider_is_untrusted(self) -> MemoryWriteRequest:
        if self.memory_type != self.content.memory_type:
            raise ValueError("memory type must match typed content")
        if (
            self.actor.creator_type is MemoryCreatorType.PROVIDER
            and self.status is not MemoryStatus.CANDIDATE
        ):
            raise ValueError("provider requests cannot self-authorize verified memory")
        self.provenance.assert_no_cycle(self.memory_id, 1)
        return self


class MemoryRevisionRequest(MemoryContract):
    request_id: UUID
    memory_id: UUID
    expected_revision: int = Field(ge=1, le=999)
    content: MemoryContent
    confidence: float = Field(ge=0.0, le=1.0, allow_inf_nan=False)
    salience: float = Field(ge=0.0, le=1.0, allow_inf_nan=False)
    sensitivity: MemorySensitivity
    provenance: MemoryProvenanceBundle
    actor: MemoryCreator
    reason: MemoryTransitionReason


class MemoryPromotionRequest(MemoryContract):
    request_id: UUID
    memory_id: UUID
    expected_revision: int = Field(ge=1)
    evidence: MemoryProvenanceBundle
    actor: MemoryCreator
    reason: MemoryTransitionReason = MemoryTransitionReason.AUTHORITATIVE_EVIDENCE_VERIFIED


class MemorySupersessionRequest(MemoryContract):
    request_id: UUID
    memory_id: UUID
    successor_memory_id: UUID
    expected_revision: int = Field(ge=1)
    actor: MemoryCreator
    reason: MemoryTransitionReason = MemoryTransitionReason.SUPERSEDED_BY_SUCCESSOR

    @model_validator(mode="after")
    def different_successor(self) -> MemorySupersessionRequest:
        if self.memory_id == self.successor_memory_id:
            raise ValueError("successor must be a different memory")
        return self


class MemoryRetractionRequest(MemoryContract):
    request_id: UUID
    memory_id: UUID
    expected_revision: int = Field(ge=1)
    actor: MemoryCreator
    reason: MemoryTransitionReason


class MemoryExpiryRequest(MemoryContract):
    request_id: UUID
    memory_id: UUID
    expected_revision: int = Field(ge=1)
    actor: MemoryCreator
    reason: MemoryTransitionReason


class MemoryMetadataFilter(MemoryContract):
    memory_types: frozenset[MemoryType] = frozenset()
    scopes: tuple[MemoryScope, ...] = ()
    statuses: tuple[MemoryStatus, ...] = (
        MemoryStatus.CANDIDATE,
        MemoryStatus.VERIFIED,
    )
    sensitivity_ceiling: MemorySensitivity = MemorySensitivity.INTERNAL
    creator_types: frozenset[MemoryCreatorType] = frozenset()
    source_types: frozenset[MemorySourceType] = frozenset()
    task_run_id: UUID | None = None
    repository_identity: Sha256Hex | None = None
    include_historical: bool = False


class MemoryTextQuery(MemoryContract):
    text: Annotated[str, Field(min_length=1, max_length=512)]
    language: Literal["simple", "english"] = "english"


class MemoryVectorQuery(MemoryContract):
    provider_id: NonEmptyStr
    model_id: NonEmptyStr
    dimension: int = Field(ge=1, le=4096)
    vector: tuple[float, ...]

    @model_validator(mode="after")
    def valid_finite_dimension(self) -> MemoryVectorQuery:
        if len(self.vector) != self.dimension:
            raise ValueError("query vector dimension mismatch")
        if not all(math.isfinite(value) for value in self.vector):
            raise ValueError("query vector values must be finite")
        return self


class MemoryQueryBudget(MemoryContract):
    maximum_results: int = Field(default=20, ge=1, le=100)
    maximum_candidates: int = Field(default=1000, ge=1, le=1000)
    maximum_elapsed: timedelta = Field(default=timedelta(seconds=5), gt=timedelta(0))
    maximum_embedding_calls: int = Field(default=1, ge=0, le=1)
    maximum_scopes: int = Field(default=16, ge=1, le=64)
    maximum_source_filters: int = Field(default=16, ge=0, le=64)


class MemoryQuery(MemoryContract):
    query_id: UUID
    mode: MemoryRetrievalMode
    filters: MemoryMetadataFilter = MemoryMetadataFilter()
    text: MemoryTextQuery | None = None
    vector: MemoryVectorQuery | None = None
    budget: MemoryQueryBudget = MemoryQueryBudget()
    cursor: Annotated[str | None, Field(max_length=4096)] = None

    @model_validator(mode="after")
    def exactly_one_mode_payload(self) -> MemoryQuery:
        if self.mode is MemoryRetrievalMode.TEXT and (self.text is None or self.vector is not None):
            raise ValueError("text retrieval requires only a text query")
        if self.mode is MemoryRetrievalMode.VECTOR and (
            self.vector is None or self.text is not None
        ):
            raise ValueError("vector retrieval requires only a vector query")
        if self.mode is MemoryRetrievalMode.METADATA and (
            self.text is not None or self.vector is not None
        ):
            raise ValueError("metadata retrieval accepts no text or vector query")
        if len(self.filters.scopes) > self.budget.maximum_scopes:
            raise ValueError("scope count exceeds query budget")
        if len(self.filters.source_types) > self.budget.maximum_source_filters:
            raise ValueError("source-filter count exceeds query budget")
        return self


class MemoryQueryResult(MemoryContract):
    memory_id: UUID
    revision: int = Field(ge=1)
    title: NonEmptyStr
    score: float = Field(ge=0.0, allow_inf_nan=False)
    rank: int = Field(ge=1)
    scope: MemoryScope
    status: MemoryStatus
    sensitivity: MemorySensitivity
    provenance_summary: tuple[MemorySourceIdentity, ...]


class MemoryQueryPage(MemoryContract):
    query_id: UUID
    results: tuple[MemoryQueryResult, ...]
    next_cursor: str | None = None
    snapshot_hash: Sha256Hex


class MemoryAccessRecord(MemoryContract):
    access_id: UUID
    query_id: UUID
    task_run_id: UUID | None = None
    memory_id: UUID
    revision: int = Field(ge=1)
    retrieval_mode: MemoryRetrievalMode
    retrieval_rank: int = Field(ge=1)
    retrieval_score: float = Field(ge=0.0, allow_inf_nan=False)
    accessed_at: UtcDatetime
    access_kind: MemoryAccessKind = MemoryAccessKind.RETRIEVED
    scope: MemoryScope
    sensitivity: MemorySensitivity
    query_hash: Sha256Hex
    filter_hash: Sha256Hex


class MemoryEmbeddingRecord(MemoryContract):
    embedding_id: UUID
    memory_id: UUID
    revision: int = Field(ge=1)
    provider_id: NonEmptyStr
    model_id: NonEmptyStr
    dimension: int = Field(ge=1, le=4096)
    content_hash: Sha256Hex
    vector: tuple[float, ...]
    created_at: UtcDatetime

    @model_validator(mode="after")
    def finite_vector_matches_dimension(self) -> MemoryEmbeddingRecord:
        if len(self.vector) != self.dimension:
            raise ValueError("stored embedding dimension mismatch")
        if not all(math.isfinite(value) for value in self.vector):
            raise ValueError("stored embedding values must be finite")
        return self


class MemoryRetrievalTrace(MemoryContract):
    query_id: UUID
    retrieval_mode: MemoryRetrievalMode
    resolved_scopes: tuple[MemoryScope, ...]
    query_hash: Sha256Hex
    filter_hash: Sha256Hex
    candidate_count: int = Field(ge=0)
    returned_count: int = Field(ge=0)
    access_audit_attempted: bool
    access_audit_succeeded: bool
    elapsed_ms: float = Field(ge=0.0, allow_inf_nan=False)


PUBLIC_MEMORY_CONTRACTS: tuple[type[ImmutableContractModel], ...] = (
    MemoryScope,
    MemoryCreator,
    MemorySourceIdentity,
    MemorySourceRef,
    MemoryProvenanceBundle,
    MemorySourceValidationResult,
    EpisodeMemoryContent,
    TaskSummaryMemoryContent,
    VerificationSummaryMemoryContent,
    CodeContextMemoryContent,
    CorrectionMemoryContent,
    DecisionMemoryContent,
    ObservationMemoryContent,
    FailurePatternMemoryContent,
    UserInstructionMemoryContent,
    MemoryRecord,
    MemoryRevision,
    MemoryWritePolicy,
    MemoryWriteDecision,
    MemoryWriteRequest,
    MemoryRevisionRequest,
    MemoryPromotionRequest,
    MemorySupersessionRequest,
    MemoryRetractionRequest,
    MemoryExpiryRequest,
    MemoryMetadataFilter,
    MemoryTextQuery,
    MemoryVectorQuery,
    MemoryQueryBudget,
    MemoryQuery,
    MemoryQueryResult,
    MemoryQueryPage,
    MemoryAccessRecord,
    MemoryEmbeddingRecord,
    MemoryRetrievalTrace,
)
