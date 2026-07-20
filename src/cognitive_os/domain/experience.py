"""Immutable contracts for governed experience compilation."""

from __future__ import annotations

import json
import re
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from hashlib import sha256
from pathlib import PurePosixPath, PureWindowsPath
from typing import Annotated
from uuid import UUID

from pydantic import Field, field_validator, model_validator

from .base import ImmutableContractModel
from .common import JsonValue, NonEmptyStr, Sha256Hex, UtcDatetime
from .memory import MemorySensitivity


class ExperienceContract(ImmutableContractModel):
    """Contract with canonical JSON and hashing."""

    def canonical_json(self, *, exclude: set[str] | None = None) -> str:
        return json.dumps(
            _canonicalize(self.model_dump(mode="python", exclude=exclude or set())),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )

    def canonical_hash(self, *, exclude: set[str] | None = None) -> str:
        return sha256(self.canonical_json(exclude=exclude).encode()).hexdigest()


def _canonicalize(value: object) -> object:
    if isinstance(value, dict):
        return {str(key): _canonicalize(item) for key, item in sorted(value.items())}
    if isinstance(value, (set, frozenset)):
        items = (_canonicalize(item) for item in value)
        return sorted(items, key=lambda item: json.dumps(item, sort_keys=True))
    if isinstance(value, (list, tuple)):
        return [_canonicalize(item) for item in value]
    if isinstance(value, StrEnum):
        return value.value
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, (UUID, Decimal)):
        return str(value)
    return value


class HashedExperienceContract(ExperienceContract):
    content_hash: str = ""

    @model_validator(mode="after")
    def seal_content(self) -> HashedExperienceContract:
        expected = self.canonical_hash(exclude={"content_hash"})
        if self.content_hash and self.content_hash != expected:
            raise ValueError("experience contract hash mismatch")
        object.__setattr__(self, "content_hash", expected)
        return self


class CompilationStatus(StrEnum):
    REQUESTED = "requested"
    SNAPSHOT_CREATED = "snapshot_created"
    RECONSTRUCTING = "reconstructing"
    ASSESSING = "assessing"
    GENERATING_CANDIDATES = "generating_candidates"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class CompilationDecisionType(StrEnum):
    COMPLETED = "completed"
    COMPLETED_WITH_WARNINGS = "completed_with_warnings"
    INSUFFICIENT_SOURCES = "insufficient_sources"
    INVALID_SOURCES = "invalid_sources"
    UNVERIFIABLE = "unverifiable"
    REJECTED = "rejected"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TrajectorySourceType(StrEnum):
    TASK = "task"
    PROBLEM = "problem"
    PLAN = "plan"
    CONTROLLER_EVENT = "controller_event"
    CONTEXT = "context"
    PROVIDER_CALL = "provider_call"
    TOOL_CALL = "tool_call"
    VERIFIER = "verifier"
    ACCEPTANCE = "acceptance"
    CODING_TRAJECTORY = "coding_trajectory"
    MEMORY_REVISION = "memory_revision"
    SEMANTIC_REVISION = "semantic_revision"
    SKILL_REVISION = "skill_revision"
    STRATEGY_REVISION = "strategy_revision"
    ROUTING_DECISION = "routing_decision"
    USER_CORRECTION = "user_correction"
    ARTIFACT = "artifact"
    BENCHMARK_CASE = "benchmark_case"


class TrajectoryCompleteness(StrEnum):
    COMPLETE = "complete"
    COMPLETE_WITH_WARNINGS = "complete_with_warnings"
    INCOMPLETE = "incomplete"
    CONFLICTED = "conflicted"
    INVALID = "invalid"


class TimelineEntryType(StrEnum):
    TASK = "task"
    PLAN = "plan"
    CONTROLLER = "controller"
    CONTEXT = "context"
    PROVIDER = "provider"
    TOOL = "tool"
    SKILL = "skill"
    STRATEGY = "strategy"
    VERIFIER = "verifier"
    ACCEPTANCE = "acceptance"
    CORRECTION = "correction"
    APPROVAL = "approval"
    CANCELLATION = "cancellation"
    UNKNOWN = "unknown"


class ExecutionSegmentType(StrEnum):
    PLANNING = "planning"
    CONTEXT_BUILD = "context_build"
    PROVIDER_EXECUTION = "provider_execution"
    TOOL_EXECUTION = "tool_execution"
    SKILL_EXECUTION = "skill_execution"
    STRATEGY_PHASE = "strategy_phase"
    VERIFICATION = "verification"
    REPAIR = "repair"
    FALLBACK = "fallback"
    CLARIFICATION = "clarification"
    APPROVAL = "approval"
    ACCEPTANCE = "acceptance"
    CANCELLATION = "cancellation"


class ExperienceStepStatus(StrEnum):
    NOT_STARTED = "not_started"
    STARTED = "started"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    SKIPPED = "skipped"
    DENIED = "denied"
    UNKNOWN = "unknown"


class StepCorrectness(StrEnum):
    CORRECT = "correct"
    INCORRECT = "incorrect"
    PARTIALLY_CORRECT = "partially_correct"
    UNVERIFIABLE = "unverifiable"
    NOT_APPLICABLE = "not_applicable"
    UNKNOWN = "unknown"


class StepNecessity(StrEnum):
    NECESSARY = "necessary"
    USEFUL = "useful"
    REDUNDANT = "redundant"
    UNNECESSARY = "unnecessary"
    UNKNOWN = "unknown"


class StepEfficiency(StrEnum):
    EFFICIENT = "efficient"
    ACCEPTABLE = "acceptable"
    INEFFICIENT = "inefficient"
    SEVERELY_INEFFICIENT = "severely_inefficient"
    UNKNOWN = "unknown"


class PolicyCompliance(StrEnum):
    COMPLIANT = "compliant"
    NON_COMPLIANT = "non_compliant"
    NOT_EVALUATED = "not_evaluated"
    UNKNOWN = "unknown"


class FirstIncorrectType(StrEnum):
    POLICY_VIOLATION = "policy_violation"
    INVALID_EVIDENCE = "invalid_evidence"
    OBJECTIVE_VERIFIER_FAILURE = "objective_verifier_failure"
    INCORRECT_TOOL_POSTCONDITION = "incorrect_tool_postcondition"
    CORRECTED_PROVIDER_PROPOSAL = "corrected_provider_proposal"
    UNNECESSARY_OR_INEFFICIENT = "unnecessary_or_inefficient"
    UNKNOWN_CAUSAL_ORIGIN = "unknown_causal_origin"


class ContributionType(StrEnum):
    HELPFUL = "helpful"
    NEUTRAL = "neutral"
    HARMFUL = "harmful"
    UNKNOWN = "unknown"


class ContributionSubjectType(StrEnum):
    MODEL_CALL = "model_call"
    TOOL_CALL = "tool_call"
    SKILL_REVISION = "skill_revision"
    STRATEGY_REVISION = "strategy_revision"
    CONTEXT_BUNDLE = "context_bundle"
    CONTEXT_CANDIDATE = "context_candidate"
    MEMORY_REVISION = "memory_revision"
    SEMANTIC_CLAIM_REVISION = "semantic_claim_revision"
    USER_CORRECTION = "user_correction"
    VERIFIER = "verifier"
    ARTIFACT = "artifact"


class GeneralizabilityLevel(StrEnum):
    TASK_SPECIFIC = "task_specific"
    REPOSITORY_SPECIFIC = "repository_specific"
    PROBLEM_CLASS_SPECIFIC = "problem_class_specific"
    CROSS_REPOSITORY_CANDIDATE = "cross_repository_candidate"
    CROSS_PROVIDER_CANDIDATE = "cross_provider_candidate"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"
    NOT_GENERALIZABLE = "not_generalizable"


class ExperienceCandidateType(StrEnum):
    MEMORY = "memory"
    SEMANTIC_OBSERVATION = "semantic_observation"
    SKILL = "skill"
    STRATEGY = "strategy"
    FAILURE_PATTERN = "failure_pattern"
    ROUTING_OBSERVATION = "routing_observation"
    BENCHMARK_CASE = "benchmark_case"
    NEGATIVE_EXAMPLE = "negative_example"
    CORPUS_ITEM = "corpus_item"


class ExperienceCandidateStatus(StrEnum):
    PROPOSED = "proposed"
    VALIDATED = "validated"
    REJECTED = "rejected"
    ROUTED = "routed"
    SUPERSEDED = "superseded"


class CandidateRejectionReason(StrEnum):
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"
    INVALID_PROVENANCE = "invalid_provenance"
    INVALID_SCHEMA = "invalid_schema"
    AUTHORITY_VIOLATION = "authority_violation"
    SENSITIVITY_VIOLATION = "sensitivity_violation"
    FABRICATED_EVIDENCE = "fabricated_evidence"
    CANCELLED = "cancelled"


class ExperienceAccessType(StrEnum):
    SOURCE_RESOLUTION = "source_resolution"
    SNAPSHOT_READ = "snapshot_read"
    ARTIFACT_READ = "artifact_read"
    RECONSTRUCTION_READ = "reconstruction_read"
    CANDIDATE_READ = "candidate_read"
    CANDIDATE_EXPORT = "candidate_export"
    MANIFEST_READ = "manifest_read"


class TrajectorySourceRef(HashedExperienceContract):
    source_type: TrajectorySourceType
    source_id: NonEmptyStr
    source_revision: NonEmptyStr
    artifact_id: UUID | None = None
    event_stream_id: UUID | None = None
    event_stream_version: int | None = Field(default=None, ge=1)
    source_content_hash: Sha256Hex
    scope: NonEmptyStr
    sensitivity: MemorySensitivity
    required: bool = True

    @field_validator("source_id", "source_revision", "scope")
    @classmethod
    def reject_host_paths(cls, value: str) -> str:
        if PurePosixPath(value).is_absolute() or PureWindowsPath(value).is_absolute():
            raise ValueError("trajectory source identity must be logical")
        if ".." in PurePosixPath(value).parts or ".." in PureWindowsPath(value).parts:
            raise ValueError("trajectory source identity must not traverse directories")
        return value

    @model_validator(mode="after")
    def validate_identity(self) -> TrajectorySourceRef:
        if self.source_type is TrajectorySourceType.CONTROLLER_EVENT and (
            self.event_stream_id is None or self.event_stream_version is None
        ):
            raise ValueError("event source requires an exact stream identity and version")
        if self.source_type is TrajectorySourceType.ARTIFACT and self.artifact_id is None:
            raise ValueError("artifact source requires artifact identity")
        return self


class CompilerResourceLimits(ExperienceContract):
    maximum_sources: int = Field(default=512, ge=1, le=512)
    maximum_events: int = Field(default=100_000, ge=1, le=100_000)
    maximum_steps: int = Field(default=10_000, ge=1, le=10_000)
    maximum_candidates: int = Field(default=256, ge=1, le=256)
    maximum_seconds: int = Field(default=1_800, ge=1, le=1_800)
    maximum_provider_calls: int = Field(default=0, ge=0, le=2)


class CompilerProfile(HashedExperienceContract):
    profile_id: NonEmptyStr
    version: int = Field(ge=1)
    enabled_source_types: frozenset[TrajectorySourceType]
    required_source_types: frozenset[TrajectorySourceType]
    candidate_types: frozenset[ExperienceCandidateType]
    assessment_policy: NonEmptyStr
    contribution_policy: NonEmptyStr
    generalizability_policy: NonEmptyStr
    provider_assistance_enabled: bool = False
    resource_limits: CompilerResourceLimits = CompilerResourceLimits()
    created_at: UtcDatetime

    @model_validator(mode="after")
    def required_sources_are_enabled(self) -> CompilerProfile:
        if not self.required_source_types <= self.enabled_source_types:
            raise ValueError("required source types must be enabled")
        if self.provider_assistance_enabled and self.resource_limits.maximum_provider_calls == 0:
            raise ValueError("provider assistance requires a positive provider call budget")
        return self


class ExperienceCompilationRequest(HashedExperienceContract):
    compilation_id: UUID
    task_run_id: UUID
    trajectory_sources: Annotated[
        tuple[TrajectorySourceRef, ...], Field(min_length=1, max_length=512)
    ]
    compiler_profile_id: NonEmptyStr
    compiler_profile_version: int = Field(ge=1)
    compiler_profile_hash: Sha256Hex
    candidate_types: Annotated[
        frozenset[ExperienceCandidateType], Field(min_length=1, max_length=9)
    ]
    budget: CompilerResourceLimits
    requested_by: NonEmptyStr
    idempotency_key: NonEmptyStr
    created_at: UtcDatetime

    @model_validator(mode="after")
    def source_identities_are_unique(self) -> ExperienceCompilationRequest:
        keys = [
            (item.source_type, item.source_id, item.source_revision)
            for item in self.trajectory_sources
        ]
        if len(keys) != len(set(keys)):
            raise ValueError("duplicate trajectory source")
        return self


class TimelineEntry(HashedExperienceContract):
    timeline_entry_id: UUID
    sequence: int = Field(ge=1)
    source_ref: TrajectorySourceRef
    entry_type: TimelineEntryType
    event_type: NonEmptyStr
    actor_type: NonEmptyStr
    actor_id: NonEmptyStr
    plan_revision: int | None = Field(default=None, ge=1)
    step_id: NonEmptyStr | None = None
    phase_id: NonEmptyStr | None = None
    skill_execution_id: UUID | None = None
    strategy_execution_id: UUID | None = None
    started_at: UtcDatetime
    finished_at: UtcDatetime | None = None
    causation_id: UUID | None = None
    correlation_id: UUID | None = None
    status: ExperienceStepStatus = ExperienceStepStatus.UNKNOWN
    payload_summary: NonEmptyStr
    evidence_refs: Annotated[tuple[Sha256Hex, ...], Field(min_length=1, max_length=64)]

    @model_validator(mode="after")
    def timestamps_are_ordered(self) -> TimelineEntry:
        if self.finished_at is not None and self.finished_at < self.started_at:
            raise ValueError("timeline entry finishes before it starts")
        return self


class TrajectoryGap(HashedExperienceContract):
    after_sequence: int = Field(ge=0)
    before_sequence: int = Field(ge=1)
    reason: NonEmptyStr


class TrajectoryConflict(HashedExperienceContract):
    sequence: int = Field(ge=1)
    source_refs: Annotated[tuple[TrajectorySourceRef, ...], Field(min_length=2, max_length=16)]
    reason: NonEmptyStr


class TrajectoryOrderingDecision(HashedExperienceContract):
    timeline_entry_id: UUID
    canonical_sequence: int = Field(ge=1)
    reason: NonEmptyStr


class TrajectorySnapshot(HashedExperienceContract):
    task_run_id: UUID
    terminal_state: NonEmptyStr
    source_refs: Annotated[tuple[TrajectorySourceRef, ...], Field(min_length=1, max_length=512)]
    event_stream_versions: dict[str, int] = Field(default_factory=dict)
    artifact_hashes: tuple[Sha256Hex, ...] = ()
    plan_revisions: tuple[int, ...] = ()
    context_bundle_revisions: tuple[NonEmptyStr, ...] = ()
    provider_call_ids: tuple[UUID, ...] = ()
    tool_call_ids: tuple[UUID, ...] = ()
    verifier_bundle_ids: tuple[UUID, ...] = ()
    memory_revision_refs: tuple[NonEmptyStr, ...] = ()
    semantic_revision_refs: tuple[NonEmptyStr, ...] = ()
    skill_revisions: tuple[NonEmptyStr, ...] = ()
    strategy_revisions: tuple[NonEmptyStr, ...] = ()
    routing_decisions: tuple[UUID, ...] = ()
    acceptance_decision_id: UUID | None = None
    user_corrections: tuple[UUID, ...] = ()
    benchmark_cases: tuple[UUID, ...] = ()
    completeness: TrajectoryCompleteness
    snapshot_created_at: UtcDatetime


class NormalizedTrajectory(HashedExperienceContract):
    task_run_id: UUID
    entries: Annotated[tuple[TimelineEntry, ...], Field(max_length=100_000)]
    gaps: tuple[TrajectoryGap, ...] = ()
    conflicts: tuple[TrajectoryConflict, ...] = ()
    ordering_decisions: tuple[TrajectoryOrderingDecision, ...] = ()
    completeness: TrajectoryCompleteness
    terminal_state: NonEmptyStr


class ExecutionSegment(HashedExperienceContract):
    segment_id: UUID
    segment_type: ExecutionSegmentType
    first_sequence: int = Field(ge=1)
    last_sequence: int = Field(ge=1)
    timeline_entry_ids: Annotated[tuple[UUID, ...], Field(min_length=1, max_length=10_000)]
    parent_segment_id: UUID | None = None
    status: ExperienceStepStatus

    @model_validator(mode="after")
    def sequence_range_is_valid(self) -> ExecutionSegment:
        if self.last_sequence < self.first_sequence:
            raise ValueError("segment sequence range is reversed")
        return self


class StepAssessment(HashedExperienceContract):
    step_id: NonEmptyStr
    sequence: int = Field(ge=1)
    intent: NonEmptyStr
    inputs: tuple[Sha256Hex, ...] = ()
    outputs: tuple[Sha256Hex, ...] = ()
    authoritative_evidence: Annotated[tuple[Sha256Hex, ...], Field(min_length=1, max_length=64)]
    status: ExperienceStepStatus
    correctness: StepCorrectness
    necessity: StepNecessity
    efficiency: StepEfficiency
    policy_compliance: PolicyCompliance
    first_incorrect_candidate: bool = False
    confidence: float = Field(ge=0, le=1)
    reason: NonEmptyStr
    limitations: tuple[NonEmptyStr, ...] = ()
    assessment_profile: NonEmptyStr


class CausalOriginAssessment(HashedExperienceContract):
    origin_type: FirstIncorrectType
    step_ids: tuple[NonEmptyStr, ...] = ()
    evidence_refs: tuple[Sha256Hex, ...] = ()
    causal_claim_supported: bool = False
    reason: NonEmptyStr

    @model_validator(mode="after")
    def evidence_is_required_for_causality(self) -> CausalOriginAssessment:
        if self.causal_claim_supported and not self.evidence_refs:
            raise ValueError("causal claim requires authoritative evidence")
        return self


class FirstIncorrectAssessment(HashedExperienceContract):
    first_observed_failure_step_id: NonEmptyStr | None = None
    candidates: tuple[NonEmptyStr, ...] = ()
    causal_origin: CausalOriginAssessment


class TrajectoryPath(HashedExperienceContract):
    path_id: UUID
    timeline_entry_ids: tuple[UUID, ...]
    segment_ids: tuple[UUID, ...]
    terminal_status: ExperienceStepStatus
    evidence_refs: tuple[Sha256Hex, ...]


class SuccessfulPath(TrajectoryPath):
    acceptance_decision_id: UUID | None = None


class FailedBranch(TrajectoryPath):
    trigger_step_id: NonEmptyStr
    failure_signal: NonEmptyStr
    recovery_path_id: UUID | None = None


class CorrectionRecord(HashedExperienceContract):
    correction_id: UUID
    source: NonEmptyStr
    before_evidence: tuple[Sha256Hex, ...]
    after_evidence: tuple[Sha256Hex, ...]
    changed_entry_ids: tuple[UUID, ...]
    effect: ContributionType
    limitations: tuple[NonEmptyStr, ...] = ()


class RecoveryPath(TrajectoryPath):
    failed_branch_id: UUID
    correction_ids: tuple[UUID, ...]
    resolved: bool


class ContributionRecord(HashedExperienceContract):
    contribution_id: UUID
    subject_type: ContributionSubjectType
    subject_id: NonEmptyStr
    assessment: ContributionType
    evidence_refs: Annotated[tuple[Sha256Hex, ...], Field(min_length=1, max_length=64)]
    causal_strength: NonEmptyStr = "correlated"
    reason: NonEmptyStr
    limitations: tuple[NonEmptyStr, ...] = ()

    @field_validator("causal_strength")
    @classmethod
    def causal_strength_is_conservative(cls, value: str) -> str:
        if value not in {"observed", "correlated", "unknown"}:
            raise ValueError("unsupported causal strength")
        return value


class GeneralizabilityAssessment(HashedExperienceContract):
    level: GeneralizabilityLevel
    problem_class_specificity: NonEmptyStr
    repository_specificity: NonEmptyStr
    provider_specificity: NonEmptyStr
    tool_specificity: NonEmptyStr
    skill_specificity: NonEmptyStr
    strategy_specificity: NonEmptyStr
    data_sensitivity: MemorySensitivity
    environmental_assumptions: tuple[NonEmptyStr, ...]
    sample_count: int = Field(ge=1)
    verifier_coverage: float = Field(ge=0, le=1)
    contradiction_state: NonEmptyStr
    reproducibility_count: int = Field(ge=0)
    limitations: tuple[NonEmptyStr, ...]


class ExperienceAnalysis(HashedExperienceContract):
    successful_path: SuccessfulPath | None = None
    failed_branches: tuple[FailedBranch, ...] = ()
    first_incorrect_step: FirstIncorrectAssessment
    corrections: tuple[CorrectionRecord, ...] = ()
    recovery_paths: tuple[RecoveryPath, ...] = ()
    contributions: tuple[ContributionRecord, ...] = ()
    verification_evidence: tuple[Sha256Hex, ...] = ()
    resource_summary: dict[str, int] = Field(default_factory=dict)
    safety_summary: tuple[NonEmptyStr, ...] = ()
    generalizability: GeneralizabilityAssessment
    limitations: tuple[NonEmptyStr, ...] = ()


class ExperienceCandidate(HashedExperienceContract):
    candidate_id: UUID
    candidate_revision: int = Field(default=1, ge=1)
    candidate_type: ExperienceCandidateType
    status: ExperienceCandidateStatus = ExperienceCandidateStatus.PROPOSED
    compilation_id: UUID
    task_run_id: UUID
    scope: NonEmptyStr
    sensitivity: MemorySensitivity
    summary: NonEmptyStr
    structured_body: dict[str, JsonValue]
    source_refs: Annotated[tuple[TrajectorySourceRef, ...], Field(min_length=1, max_length=128)]
    evidence_refs: Annotated[tuple[Sha256Hex, ...], Field(min_length=1, max_length=128)]
    limitations: tuple[NonEmptyStr, ...]
    generalizability: GeneralizabilityAssessment
    target_subsystem: NonEmptyStr
    target_schema_version: NonEmptyStr
    generator_profile: NonEmptyStr
    created_at: UtcDatetime
    created_by: NonEmptyStr = "experience-compiler"

    @model_validator(mode="after")
    def begins_proposed(self) -> ExperienceCandidate:
        if self.status is not ExperienceCandidateStatus.PROPOSED:
            raise ValueError("new experience candidates must begin as proposed")
        forbidden = {"verified", "promoted", "authority", "activate", "write_destination"}
        if forbidden & set(self.structured_body):
            raise ValueError("candidate body contains a forbidden authority field")
        if re.search(r"(?i)(api[_-]?key|password|secret|bearer\s+[a-z0-9._-]+)", self.summary):
            raise ValueError("candidate summary may contain credential material")
        return self


class CandidateRevision(HashedExperienceContract):
    candidate_id: UUID
    revision: int = Field(ge=1)
    previous_status: ExperienceCandidateStatus
    status: ExperienceCandidateStatus
    actor_id: NonEmptyStr
    reason: NonEmptyStr
    created_at: UtcDatetime


class CandidateRoutingEnvelope(HashedExperienceContract):
    candidate_id: UUID
    candidate_revision: int = Field(ge=1)
    candidate_hash: Sha256Hex
    artifact_hash: Sha256Hex
    target_subsystem: NonEmptyStr
    requested_by: NonEmptyStr
    created_at: UtcDatetime


class CandidateRoutingReceipt(HashedExperienceContract):
    envelope_hash: Sha256Hex
    destination_receipt_id: NonEmptyStr | None = None
    accepted_for_staging: bool
    created_at: UtcDatetime


class VerificationCapabilityResult(HashedExperienceContract):
    capability: NonEmptyStr
    passed: bool
    evidence_refs: tuple[Sha256Hex, ...] = ()
    reason: NonEmptyStr


class ExperienceVerifierBundle(HashedExperienceContract):
    bundle_id: UUID
    compilation_id: UUID
    registry_hash: Sha256Hex
    results: Annotated[tuple[VerificationCapabilityResult, ...], Field(min_length=1)]
    created_at: UtcDatetime

    @property
    def passed(self) -> bool:
        return all(item.passed for item in self.results)


class CompilationDecision(HashedExperienceContract):
    compilation_id: UUID
    decision: CompilationDecisionType
    verifier_bundle_id: UUID
    verifier_bundle_hash: Sha256Hex
    warnings: tuple[NonEmptyStr, ...] = ()
    reason_codes: tuple[NonEmptyStr, ...] = ()
    decided_at: UtcDatetime


class CompilationManifest(HashedExperienceContract):
    compilation_id: UUID
    source_snapshot_hash: Sha256Hex
    reconstruction_hash: Sha256Hex
    analysis_hash: Sha256Hex
    candidate_hashes: tuple[Sha256Hex, ...]
    verifier_bundle_hash: Sha256Hex
    compilation_decision: CompilationDecisionType
    warnings: tuple[NonEmptyStr, ...]
    usage: dict[str, int]
    created_at: UtcDatetime


class ExperienceAccessRecord(HashedExperienceContract):
    access_id: UUID
    compilation_id: UUID
    access_type: ExperienceAccessType
    source_type: TrajectorySourceType | None = None
    source_id: NonEmptyStr | None = None
    candidate_id: UUID | None = None
    actor_id: NonEmptyStr
    accessed_at: UtcDatetime


class ExperienceVerificationSubject(HashedExperienceContract):
    compilation_id: UUID
    artifact_hashes: tuple[Sha256Hex, ...]


class ExperienceSourceVerificationSubject(ExperienceVerificationSubject):
    source_snapshot_hash: Sha256Hex


class TrajectorySnapshotVerificationSubject(ExperienceVerificationSubject):
    source_snapshot_hash: Sha256Hex


class TrajectoryReconstructionVerificationSubject(ExperienceVerificationSubject):
    reconstruction_hash: Sha256Hex


class StepAssessmentVerificationSubject(ExperienceVerificationSubject):
    assessment_hashes: tuple[Sha256Hex, ...]


class ExperienceCandidateVerificationSubject(ExperienceVerificationSubject):
    candidate_hash: Sha256Hex


class CompilationManifestVerificationSubject(ExperienceVerificationSubject):
    manifest_hash: Sha256Hex


PUBLIC_EXPERIENCE_CONTRACTS: tuple[type[ImmutableContractModel], ...] = (
    TrajectorySourceRef,
    CompilerResourceLimits,
    CompilerProfile,
    ExperienceCompilationRequest,
    TimelineEntry,
    TrajectoryGap,
    TrajectoryConflict,
    TrajectoryOrderingDecision,
    TrajectorySnapshot,
    NormalizedTrajectory,
    ExecutionSegment,
    StepAssessment,
    CausalOriginAssessment,
    FirstIncorrectAssessment,
    SuccessfulPath,
    FailedBranch,
    CorrectionRecord,
    RecoveryPath,
    ContributionRecord,
    GeneralizabilityAssessment,
    ExperienceAnalysis,
    ExperienceCandidate,
    CandidateRevision,
    CandidateRoutingEnvelope,
    CandidateRoutingReceipt,
    VerificationCapabilityResult,
    ExperienceVerifierBundle,
    CompilationDecision,
    CompilationManifest,
    ExperienceAccessRecord,
    ExperienceSourceVerificationSubject,
    TrajectorySnapshotVerificationSubject,
    TrajectoryReconstructionVerificationSubject,
    StepAssessmentVerificationSubject,
    ExperienceCandidateVerificationSubject,
    CompilationManifestVerificationSubject,
)
