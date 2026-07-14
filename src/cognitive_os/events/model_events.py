"""Model-call lifecycle payloads."""

from cognitive_os.domain.common import ErrorInfo, UtcDatetime
from cognitive_os.domain.identifiers import ModelCallId
from cognitive_os.domain.model_calls import ModelCallRequestRecord, ModelCallResultRecord

from .base import EventPayload


class ModelCallRequested(EventPayload):
    event_type = "model_call.requested"
    request: ModelCallRequestRecord


class ModelCallStarted(EventPayload):
    event_type = "model_call.started"
    model_call_id: ModelCallId
    started_at: UtcDatetime


class ModelCallCompleted(EventPayload):
    event_type = "model_call.completed"
    result: ModelCallResultRecord


class ModelCallFailed(EventPayload):
    event_type = "model_call.failed"
    model_call_id: ModelCallId
    finished_at: UtcDatetime
    error: ErrorInfo


class ModelCallTimedOut(EventPayload):
    event_type = "model_call.timed_out"
    model_call_id: ModelCallId
    timed_out_at: UtcDatetime
    timeout_seconds: float


class ModelCallRetried(EventPayload):
    event_type = "model_call.retried"
    model_call_id: ModelCallId
    previous_attempt: int
    next_attempt: int
