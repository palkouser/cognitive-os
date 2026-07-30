"""Minimal authoritative Coding Agent lifecycle payloads."""

from __future__ import annotations

from uuid import UUID

from pydantic import model_validator

from cognitive_os.domain.coding import (
    ChangedFileManifest,
    CodingOutcomeStatus,
    CodingPatchPlan,
    RepositoryProfile,
    WorkspaceCleanupResult,
    WorkspaceDescriptor,
)
from cognitive_os.domain.common import NonEmptyStr, Sha256Hex, UtcDatetime
from cognitive_os.domain.reality import RealityCandidateStrategy, RealityRunKind

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


class CodingOutcomeRecorded(EventPayload):
    """The authoritative identity of one executed coding run, Sprint 21C3.

    `CodingResultPackaged` carries an outcome hash and nothing that resolves it, so an
    outcome recorded under it is a claim about bytes nobody can fetch. This is a *new* event
    rather than extra fields on that one: `CodingResultPackaged` already has rows, and its
    payload hash is what the replay machinery checks, so widening it would rewrite the
    canonical hash of every historical envelope — the exact drift the hashing exists to
    catch.

    Every reference here is resolvable. The outcome artifact and the hidden-verifier evidence
    are named by ID *and* by hash, so an event cannot claim bytes that were never written and
    cannot survive those bytes changing underneath it.
    """

    event_type = "coding.outcome_recorded"
    task_run_id: UUID
    run_kind: RealityRunKind
    task_id: UUID
    task_manifest_hash: Sha256Hex
    candidate_id: UUID | None = None
    candidate_strategy: RealityCandidateStrategy | None = None
    outcome_hash: Sha256Hex
    outcome_artifact_id: UUID
    outcome_artifact_hash: Sha256Hex
    hidden_evidence_artifact_id: UUID
    hidden_evidence_hash: Sha256Hex
    final_status: CodingOutcomeStatus
    hidden_verification_passed: bool
    provider_output_id: UUID | None = None
    #: `RealityRunIdentity.key` when this run belongs to a campaign, absent otherwise.
    #:
    #: Resume needs one question answered from the Event Store alone — "has this exact planned
    #: run already produced a counted outcome?" — because a campaign that answered it from its
    #: own memory would lose the answer in the crash it is recovering from. Optional because a
    #: run recorded outside a campaign genuinely has no campaign identity, and inventing one
    #: would make it resumable against a campaign it was never part of.
    run_identity_key: Sha256Hex | None = None
    occurred_at: UtcDatetime

    @model_validator(mode="after")
    def candidate_identity_matches_run_kind(self) -> CodingOutcomeRecorded:
        if self.run_kind is RealityRunKind.BASELINE:
            if self.candidate_id is not None or self.candidate_strategy is not None:
                raise ValueError("a baseline run has no candidate")
        elif self.candidate_id is None or self.candidate_strategy is None:
            raise ValueError("a candidate run must name its candidate and strategy")
        return self


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
    CodingOutcomeRecorded,
)
