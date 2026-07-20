"""Bounded Experience Compiler lifecycle evidence."""

from uuid import UUID

from cognitive_os.domain.common import NonEmptyStr, Sha256Hex, UtcDatetime
from cognitive_os.domain.experience import (
    CompilationDecisionType,
    CompilationStatus,
    ExperienceCandidateStatus,
    ExperienceCandidateType,
)

from .base import EventPayload


class ExperienceCompilationRequested(EventPayload):
    event_type = "experience.compilation_requested"
    compilation_id: UUID
    task_run_id: UUID
    profile_hash: Sha256Hex
    request_hash: Sha256Hex
    status: CompilationStatus = CompilationStatus.REQUESTED
    occurred_at: UtcDatetime


class ExperienceSnapshotCreated(EventPayload):
    event_type = "experience.snapshot_created"
    compilation_id: UUID
    snapshot_hash: Sha256Hex
    source_count: int
    occurred_at: UtcDatetime


class ExperienceCompilationCompleted(EventPayload):
    event_type = "experience.compilation_completed"
    compilation_id: UUID
    manifest_hash: Sha256Hex
    decision: CompilationDecisionType
    occurred_at: UtcDatetime


class ExperienceCompilationFailed(EventPayload):
    event_type = "experience.compilation_failed"
    compilation_id: UUID
    reason_code: NonEmptyStr
    occurred_at: UtcDatetime


class ExperienceCompilationCancelled(EventPayload):
    event_type = "experience.compilation_cancelled"
    compilation_id: UUID
    reason_code: NonEmptyStr
    occurred_at: UtcDatetime


class ExperienceCandidateCreated(EventPayload):
    event_type = "experience.candidate_created"
    compilation_id: UUID
    candidate_id: UUID
    candidate_type: ExperienceCandidateType
    status: ExperienceCandidateStatus
    candidate_hash: Sha256Hex
    occurred_at: UtcDatetime


class ExperienceCandidateRejected(EventPayload):
    event_type = "experience.candidate_rejected"
    compilation_id: UUID
    candidate_id: UUID
    reason_code: NonEmptyStr
    occurred_at: UtcDatetime


class ExperienceCandidateRouted(EventPayload):
    event_type = "experience.candidate_routed"
    compilation_id: UUID
    candidate_id: UUID
    envelope_hash: Sha256Hex
    target_subsystem: NonEmptyStr
    occurred_at: UtcDatetime


EXPERIENCE_EVENT_MODELS: tuple[type[EventPayload], ...] = (
    ExperienceCompilationRequested,
    ExperienceSnapshotCreated,
    ExperienceCompilationCompleted,
    ExperienceCompilationFailed,
    ExperienceCompilationCancelled,
    ExperienceCandidateCreated,
    ExperienceCandidateRejected,
    ExperienceCandidateRouted,
)
