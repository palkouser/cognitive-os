"""Provider identity, capability, health, and stream contracts."""

from __future__ import annotations

from enum import StrEnum

from pydantic import Field, model_validator

from .base import ImmutableContractModel
from .common import ErrorInfo, JsonValue, NonEmptyStr, TokenUsage, UtcDatetime


class ProviderKind(StrEnum):
    NETWORK_API = "network_api"
    LOCAL_API = "local_api"
    CLI_AGENT = "cli_agent"
    MOCK = "mock"
    REPLAY = "replay"


class ProviderStatus(StrEnum):
    AVAILABLE = "available"
    DEGRADED = "degraded"
    UNAVAILABLE = "unavailable"
    MISCONFIGURED = "misconfigured"
    UNAUTHENTICATED = "unauthenticated"


class ResponseFormat(StrEnum):
    TEXT = "text"
    JSON_OBJECT = "json_object"
    JSON_SCHEMA = "json_schema"


class ToolChoiceMode(StrEnum):
    NONE = "none"
    AUTO = "auto"
    REQUIRED = "required"
    SPECIFIC = "specific"


class ModelFinishReason(StrEnum):
    COMPLETED = "completed"
    TOOL_CALL = "tool_call"
    LENGTH = "length"
    CONTENT_FILTER = "content_filter"
    CANCELLED = "cancelled"
    ERROR = "error"
    UNKNOWN = "unknown"


class ProviderStreamEventType(StrEnum):
    RESPONSE_STARTED = "response_started"
    TEXT_DELTA = "text_delta"
    TOOL_CALL_DELTA = "tool_call_delta"
    USAGE = "usage"
    RESPONSE_COMPLETED = "response_completed"
    RESPONSE_FAILED = "response_failed"


class ProviderIdentity(ImmutableContractModel):
    provider_id: NonEmptyStr
    display_name: NonEmptyStr
    provider_kind: ProviderKind
    adapter_version: NonEmptyStr


class ModelCapabilities(ImmutableContractModel):
    model_id: NonEmptyStr
    provider_id: NonEmptyStr
    supports_streaming: bool = False
    supports_tool_calls: bool = False
    supports_parallel_tool_calls: bool = False
    supports_structured_output: bool = False
    supports_system_messages: bool = True
    supports_seed: bool = False
    maximum_context_tokens: int | None = Field(default=None, gt=0)
    maximum_output_tokens: int | None = Field(default=None, gt=0)
    supported_input_modalities: tuple[NonEmptyStr, ...] = ("text",)
    supported_output_modalities: tuple[NonEmptyStr, ...] = ("text",)


class ProviderHealth(ImmutableContractModel):
    provider_id: NonEmptyStr
    status: ProviderStatus
    checked_at: UtcDatetime
    latency_ms: float | None = Field(default=None, ge=0)
    configured_model: NonEmptyStr | None = None
    resolved_model: NonEmptyStr | None = None
    message: NonEmptyStr
    error: ErrorInfo | None = None


class ProviderStreamEvent(ImmutableContractModel):
    sequence: int = Field(gt=0)
    event_type: ProviderStreamEventType
    text_delta: str | None = None
    tool_call_delta: dict[str, JsonValue] | None = None
    usage: TokenUsage | None = None
    finish_reason: ModelFinishReason | None = None

    @model_validator(mode="after")
    def validate_event_shape(self) -> ProviderStreamEvent:
        if self.event_type is ProviderStreamEventType.TEXT_DELTA and self.text_delta is None:
            raise ValueError("text_delta events require text_delta")
        if (
            self.event_type is ProviderStreamEventType.TOOL_CALL_DELTA
            and self.tool_call_delta is None
        ):
            raise ValueError("tool_call_delta events require tool_call_delta")
        if self.event_type is ProviderStreamEventType.USAGE and self.usage is None:
            raise ValueError("usage events require usage")
        return self
