"""Tool-call lifecycle and permission payloads."""

from cognitive_os.domain.common import ErrorInfo, UtcDatetime
from cognitive_os.domain.identifiers import ToolCallId
from cognitive_os.domain.tool_calls import ToolCallRequestRecord, ToolCallResultRecord

from .base import EventPayload


class ToolCallRequested(EventPayload):
    event_type = "tool_call.requested"
    request: ToolCallRequestRecord


class ToolCallAuthorized(EventPayload):
    event_type = "tool_call.authorized"
    tool_call_id: ToolCallId
    authorized_at: UtcDatetime
    authorized_by: str


class ToolCallDenied(EventPayload):
    event_type = "tool_call.denied"
    tool_call_id: ToolCallId
    denied_at: UtcDatetime
    denied_by: str
    reason: str


class ToolCallStarted(EventPayload):
    event_type = "tool_call.started"
    tool_call_id: ToolCallId
    started_at: UtcDatetime


class ToolCallCompleted(EventPayload):
    event_type = "tool_call.completed"
    result: ToolCallResultRecord


class ToolCallFailed(EventPayload):
    event_type = "tool_call.failed"
    tool_call_id: ToolCallId
    finished_at: UtcDatetime
    error: ErrorInfo


class ToolCallTimedOut(EventPayload):
    event_type = "tool_call.timed_out"
    tool_call_id: ToolCallId
    timed_out_at: UtcDatetime
    timeout_seconds: float
