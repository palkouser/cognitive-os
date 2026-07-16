"""Minimal Context Builder lifecycle event payloads."""

from uuid import UUID

from cognitive_os.domain.common import ArtifactRef, NonEmptyStr, Sha256Hex, UtcDatetime
from cognitive_os.domain.context import ContextBuildFailure

from .base import EventPayload


class ContextBuildRequested(EventPayload):
    event_type = "context.build_requested"
    context_request_id: UUID
    task_run_id: UUID
    step_id: UUID
    query_hash: Sha256Hex
    requested_at: UtcDatetime


class ContextBundleCreated(EventPayload):
    event_type = "context.bundle_created"
    context_request_id: UUID
    context_bundle_id: UUID
    revision: int
    bundle_artifact: ArtifactRef
    trace_artifact: ArtifactRef
    rendered_context_artifact: ArtifactRef
    content_hash: Sha256Hex
    created_at: UtcDatetime


class ContextBuildFailed(EventPayload):
    event_type = "context.build_failed"
    context_request_id: UUID
    failure: ContextBuildFailure
    reason_code: NonEmptyStr
    failed_at: UtcDatetime


class ContextBundleAttached(EventPayload):
    event_type = "context.bundle_attached"
    context_request_id: UUID
    context_bundle_id: UUID
    revision: int
    model_call_id: UUID
    content_hash: Sha256Hex
    attached_at: UtcDatetime


CONTEXT_EVENT_MODELS: tuple[type[EventPayload], ...] = (
    ContextBuildRequested,
    ContextBundleCreated,
    ContextBuildFailed,
    ContextBundleAttached,
)
