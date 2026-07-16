"""Explicit event type and schema-version catalog."""

from __future__ import annotations

from cognitive_os.domain.common import JsonValue

from .base import EventEnvelope, EventPayload
from .benchmark_events import (
    BenchmarkCaseCompleted,
    BenchmarkCaseFailed,
    BenchmarkCaseStarted,
    BenchmarkRunCancelled,
    BenchmarkRunCompleted,
    BenchmarkRunFailed,
    BenchmarkRunStarted,
)
from .coding_events import CODING_EVENT_MODELS
from .context_events import CONTEXT_EVENT_MODELS
from .controller_events import (
    AcceptanceDecisionRecorded,
    ControllerBudgetExhaustedEvent,
    ControllerCancelled,
    ControllerCheckpointCreated,
    ControllerClarificationProvided,
    ControllerClarificationRequested,
    ControllerContinuationConsumed,
    ControllerContinuationIssued,
    ControllerDecisionRecorded,
    ControllerPaused,
    ControllerStateChanged,
    ProblemRepresentationCreated,
    ProblemRepresentationRevised,
)
from .execution_events import (
    CheckpointCreated,
    ExecutionStepCancelled,
    ExecutionStepCompleted,
    ExecutionStepCreated,
    ExecutionStepFailed,
    ExecutionStepRetried,
    ExecutionStepSkipped,
    ExecutionStepStarted,
    PlanCreated,
    PlanRevised,
    RunResumed,
)
from .memory_events import MEMORY_EVENT_MODELS
from .model_events import (
    ModelCallCompleted,
    ModelCallFailed,
    ModelCallRequested,
    ModelCallRetried,
    ModelCallStarted,
    ModelCallTimedOut,
)
from .semantic_memory_events import SEMANTIC_EVENT_MODELS
from .task_events import (
    TaskCancelled,
    TaskCreated,
    TaskRunCancelled,
    TaskRunCompleted,
    TaskRunFailed,
    TaskRunStarted,
    TaskRunWaiting,
    TaskUpdated,
)
from .tool_events import (
    ToolCallAuthorized,
    ToolCallCompleted,
    ToolCallDenied,
    ToolCallFailed,
    ToolCallRequested,
    ToolCallStarted,
    ToolCallTimedOut,
)
from .user_events import (
    UserApprovalDenied,
    UserApprovalGranted,
    UserApprovalRequested,
    UserCorrectionReceived,
)
from .verification_events import VerifierCompleted, VerifierFailed, VerifierStarted


class EventCatalogError(LookupError):
    """Base error for event catalog resolution."""


class UnknownEventTypeError(EventCatalogError):
    """Raised when an event type has no registration."""


class UnsupportedSchemaVersionError(EventCatalogError):
    """Raised when an event type exists but its schema version does not."""


class EventCatalog:
    def __init__(self) -> None:
        self._models: dict[tuple[str, int], type[EventPayload]] = {}

    def register(self, payload_model: type[EventPayload]) -> None:
        key = (payload_model.event_type, payload_model.schema_version)
        if key in self._models:
            raise ValueError(f"duplicate event registration: {key[0]} v{key[1]}")
        self._models[key] = payload_model

    def get_payload_model(self, event_type: str, schema_version: int) -> type[EventPayload]:
        key = (event_type, schema_version)
        if key in self._models:
            return self._models[key]
        if any(registered_type == event_type for registered_type, _ in self._models):
            message = f"unsupported schema version: {event_type} v{schema_version}"
            raise UnsupportedSchemaVersionError(message)
        raise UnknownEventTypeError(f"unknown event type: {event_type}")

    def encode_payload(self, payload: EventPayload) -> dict[str, JsonValue]:
        expected = self.get_payload_model(payload.event_type, payload.schema_version)
        if not isinstance(payload, expected):
            raise TypeError("payload class does not match its catalog registration")
        return payload.to_payload()

    def decode_payload(self, envelope: EventEnvelope) -> EventPayload:
        payload_model = self.get_payload_model(envelope.event_type, envelope.schema_version)
        return payload_model.model_validate(envelope.payload)

    def list_event_types(self) -> tuple[tuple[str, int], ...]:
        return tuple(sorted(self._models))


DEFAULT_EVENT_MODELS: tuple[type[EventPayload], ...] = (
    *CODING_EVENT_MODELS,
    *CONTEXT_EVENT_MODELS,
    *MEMORY_EVENT_MODELS,
    *SEMANTIC_EVENT_MODELS,
    BenchmarkRunStarted,
    BenchmarkCaseStarted,
    BenchmarkCaseCompleted,
    BenchmarkCaseFailed,
    BenchmarkRunCompleted,
    BenchmarkRunFailed,
    BenchmarkRunCancelled,
    ProblemRepresentationCreated,
    ProblemRepresentationRevised,
    ControllerStateChanged,
    ControllerDecisionRecorded,
    AcceptanceDecisionRecorded,
    ControllerClarificationRequested,
    ControllerClarificationProvided,
    ControllerCheckpointCreated,
    ControllerContinuationIssued,
    ControllerContinuationConsumed,
    ControllerBudgetExhaustedEvent,
    ControllerPaused,
    ControllerCancelled,
    TaskCreated,
    TaskUpdated,
    TaskCancelled,
    TaskRunStarted,
    TaskRunWaiting,
    TaskRunCompleted,
    TaskRunFailed,
    TaskRunCancelled,
    PlanCreated,
    PlanRevised,
    ExecutionStepCreated,
    ExecutionStepStarted,
    ExecutionStepCompleted,
    ExecutionStepFailed,
    ExecutionStepRetried,
    ExecutionStepSkipped,
    ExecutionStepCancelled,
    CheckpointCreated,
    RunResumed,
    ModelCallRequested,
    ModelCallStarted,
    ModelCallCompleted,
    ModelCallFailed,
    ModelCallTimedOut,
    ModelCallRetried,
    ToolCallRequested,
    ToolCallAuthorized,
    ToolCallDenied,
    ToolCallStarted,
    ToolCallCompleted,
    ToolCallFailed,
    ToolCallTimedOut,
    VerifierStarted,
    VerifierCompleted,
    VerifierFailed,
    UserApprovalRequested,
    UserApprovalGranted,
    UserApprovalDenied,
    UserCorrectionReceived,
)


def build_default_event_catalog() -> EventCatalog:
    catalog = EventCatalog()
    for payload_model in DEFAULT_EVENT_MODELS:
        catalog.register(payload_model)
    return catalog
