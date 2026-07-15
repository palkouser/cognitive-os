"""Minimal authoritative Coding Agent lifecycle payloads."""

from uuid import UUID

from cognitive_os.domain.coding import (
    ChangedFileManifest,
    CodingPatchPlan,
    RepositoryProfile,
    WorkspaceCleanupResult,
    WorkspaceDescriptor,
)
from cognitive_os.domain.common import NonEmptyStr, Sha256Hex, UtcDatetime

from .base import EventPayload


class CodingRepositoryProfileDetected(EventPayload):
    event_type = "coding.repository_profile_detected"
    task_run_id: UUID
    profile: RepositoryProfile


class CodingRepositoryProfileRejected(EventPayload):
    event_type = "coding.repository_profile_rejected"
    task_run_id: UUID
    profile: RepositoryProfile
    rejected_at: UtcDatetime


class CodingWorkspacePrepared(EventPayload):
    event_type = "coding.workspace_prepared"
    descriptor: WorkspaceDescriptor


class CodingWorkspaceArchived(EventPayload):
    event_type = "coding.workspace_archived"
    result: WorkspaceCleanupResult


class CodingRepositoryIndexCreated(EventPayload):
    event_type = "coding.repository_index_created"
    task_run_id: UUID
    index_hash: Sha256Hex
    file_count: int
    truncated: bool


class CodingPatchPlanCreated(EventPayload):
    event_type = "coding.patch_plan_created"
    task_run_id: UUID
    plan: CodingPatchPlan
    plan_hash: Sha256Hex


class CodingPatchAttemptRecorded(EventPayload):
    event_type = "coding.patch_attempt_recorded"
    task_run_id: UUID
    attempt_number: int
    proposal_hash: Sha256Hex
    recorded_at: UtcDatetime


class CodingPatchApplied(EventPayload):
    event_type = "coding.patch_applied"
    task_run_id: UUID
    workspace_id: UUID
    workspace_revision: int
    manifest: ChangedFileManifest


class CodingPatchRejected(EventPayload):
    event_type = "coding.patch_rejected"
    task_run_id: UUID
    attempt_number: int
    reason_code: NonEmptyStr
    rejected_at: UtcDatetime


class CodingResultPackaged(EventPayload):
    event_type = "coding.result_packaged"
    task_run_id: UUID
    outcome_hash: Sha256Hex
    status: NonEmptyStr
    packaged_at: UtcDatetime


CODING_EVENT_MODELS: tuple[type[EventPayload], ...] = (
    CodingRepositoryProfileDetected,
    CodingRepositoryProfileRejected,
    CodingWorkspacePrepared,
    CodingWorkspaceArchived,
    CodingRepositoryIndexCreated,
    CodingPatchPlanCreated,
    CodingPatchAttemptRecorded,
    CodingPatchApplied,
    CodingPatchRejected,
    CodingResultPackaged,
)
