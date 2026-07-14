"""Provider-neutral model request and response contracts."""

from __future__ import annotations

import re
from enum import StrEnum
from typing import Any

from pydantic import Field, field_validator, model_validator

from .base import ImmutableContractModel
from .common import JsonValue, NonEmptyStr, TokenUsage
from .identifiers import ModelCallId, StepId, TaskRunId
from .provider import ModelFinishReason, ResponseFormat, ToolChoiceMode

_SECRET_KEY = re.compile(
    r"(^|[_-])(api[_-]?key|authorization|credential|passwd|password|secret|token)([_-]|$)",
    re.IGNORECASE,
)


def reject_secret_keys(value: object, *, path: str = "metadata") -> None:
    """Reject secret-like mapping keys recursively without inspecting values."""
    if isinstance(value, dict):
        for key, nested in value.items():
            if _SECRET_KEY.search(str(key)):
                raise ValueError(f"{path} contains a secret-like key")
            reject_secret_keys(nested, path=f"{path}.{key}")
    elif isinstance(value, list):
        for nested in value:
            reject_secret_keys(nested, path=path)


class ProviderMessageRole(StrEnum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


class ProviderMessage(ImmutableContractModel):
    role: ProviderMessageRole
    content: str
    name: NonEmptyStr | None = None
    tool_call_id: NonEmptyStr | None = None

    @model_validator(mode="after")
    def tool_messages_have_call_id(self) -> ProviderMessage:
        if self.role is ProviderMessageRole.TOOL and self.tool_call_id is None:
            raise ValueError("tool messages require tool_call_id")
        if self.role is not ProviderMessageRole.TOOL and self.tool_call_id is not None:
            raise ValueError("tool_call_id is valid only for tool messages")
        return self


class ProviderToolDefinition(ImmutableContractModel):
    name: NonEmptyStr
    description: NonEmptyStr
    input_schema: dict[str, JsonValue]

    @field_validator("input_schema", mode="before")
    @classmethod
    def copy_schema(cls, value: Any) -> Any:
        return dict(value) if isinstance(value, dict) else value


class ModelProviderRequest(ImmutableContractModel):
    model_call_id: ModelCallId
    task_run_id: TaskRunId
    step_id: StepId | None = None
    correlation_id: ModelCallId
    requested_model: NonEmptyStr
    messages: tuple[ProviderMessage, ...] = ()
    system_instructions: str | None = None
    tools: tuple[ProviderToolDefinition, ...] = ()
    tool_choice: ToolChoiceMode = ToolChoiceMode.NONE
    selected_tool_name: NonEmptyStr | None = None
    response_format: ResponseFormat = ResponseFormat.TEXT
    response_schema: dict[str, JsonValue] | None = None
    temperature: float | None = Field(default=None, ge=0, le=2)
    max_output_tokens: int | None = Field(default=None, gt=0)
    context_budget: int = Field(default=32768, gt=0, le=131072)
    timeout_seconds: float = Field(default=120, gt=0)
    metadata: dict[str, JsonValue] = Field(default_factory=dict)

    @field_validator("metadata", mode="before")
    @classmethod
    def validate_metadata(cls, value: Any) -> Any:
        if isinstance(value, dict):
            copied = dict(value)
            reject_secret_keys(copied)
            return copied
        return value

    @field_validator("response_schema", mode="before")
    @classmethod
    def copy_response_schema(cls, value: Any) -> Any:
        return dict(value) if isinstance(value, dict) else value

    @model_validator(mode="after")
    def validate_request(self) -> ModelProviderRequest:
        if not self.messages and not (self.system_instructions or "").strip():
            raise ValueError("at least one message or system instruction is required")
        if (
            self.tool_choice in {ToolChoiceMode.REQUIRED, ToolChoiceMode.SPECIFIC}
            and not self.tools
        ):
            raise ValueError("required tool choice needs at least one tool")
        if self.tool_choice is ToolChoiceMode.SPECIFIC:
            if self.selected_tool_name is None:
                raise ValueError("specific tool choice requires selected_tool_name")
            if self.selected_tool_name not in {tool.name for tool in self.tools}:
                raise ValueError("selected tool is not defined")
        elif self.selected_tool_name is not None:
            raise ValueError("selected_tool_name requires specific tool choice")
        if self.response_format is ResponseFormat.JSON_SCHEMA and self.response_schema is None:
            raise ValueError("JSON Schema response format requires response_schema")
        if (
            self.response_format is not ResponseFormat.JSON_SCHEMA
            and self.response_schema is not None
        ):
            raise ValueError("response_schema requires JSON Schema response format")
        if len({tool.name for tool in self.tools}) != len(self.tools):
            raise ValueError("tool names must be unique")
        return self


class NormalizedToolCall(ImmutableContractModel):
    tool_call_id: NonEmptyStr
    name: NonEmptyStr
    arguments: dict[str, JsonValue]


class ModelProviderResponse(ImmutableContractModel):
    model_call_id: ModelCallId
    provider_id: NonEmptyStr
    requested_model: NonEmptyStr
    resolved_model: NonEmptyStr
    content: str | None = None
    structured_output: dict[str, JsonValue] | list[JsonValue] | None = None
    tool_calls: tuple[NormalizedToolCall, ...] = ()
    finish_reason: ModelFinishReason
    usage: TokenUsage | None = None
    latency_ms: float = Field(ge=0)
    provider_request_id: NonEmptyStr | None = None
    warnings: tuple[str, ...] = ()

    @model_validator(mode="after")
    def validate_response(self) -> ModelProviderResponse:
        if self.finish_reason is ModelFinishReason.TOOL_CALL and not self.tool_calls:
            raise ValueError("tool-call finish reason requires a tool call")
        if len({call.tool_call_id for call in self.tool_calls}) != len(self.tool_calls):
            raise ValueError("tool-call IDs must be unique")
        return self
