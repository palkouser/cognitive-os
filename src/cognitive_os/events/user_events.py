"""User approval and correction payloads."""

from uuid import UUID

from cognitive_os.domain.common import ActorRef, JsonValue, UtcDatetime
from cognitive_os.domain.identifiers import TaskRunId, ToolCallId

from .base import EventPayload


class UserApprovalRequested(EventPayload):
    event_type = "user.approval_requested"
    approval_id: UUID
    task_run_id: TaskRunId
    tool_call_id: ToolCallId | None = None
    requested_at: UtcDatetime
    reason: str


class UserApprovalGranted(EventPayload):
    event_type = "user.approval_granted"
    approval_id: UUID
    granted_by: ActorRef
    granted_at: UtcDatetime


class UserApprovalDenied(EventPayload):
    event_type = "user.approval_denied"
    approval_id: UUID
    denied_by: ActorRef
    denied_at: UtcDatetime
    reason: str | None = None


class UserCorrectionReceived(EventPayload):
    event_type = "user.correction_received"
    task_run_id: TaskRunId
    correction: dict[str, JsonValue]
    received_from: ActorRef
    received_at: UtcDatetime
    source: str
