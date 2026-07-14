"""Pure mapping between Cognitive OS and OpenAI-compatible MiniMax records."""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from typing import cast

from jsonschema import ValidationError, validate

from cognitive_os.domain.common import JsonValue, TokenUsage
from cognitive_os.domain.model_requests import (
    ModelProviderRequest,
    ModelProviderResponse,
    NormalizedToolCall,
)
from cognitive_os.domain.provider import (
    ModelFinishReason,
    ResponseFormat,
    ToolChoiceMode,
)
from cognitive_os.providers.errors import ProviderInvalidResponseError


def map_request(request: ModelProviderRequest) -> dict[str, object]:
    messages: list[dict[str, object]] = []
    if request.system_instructions:
        messages.append({"role": "system", "content": request.system_instructions})
    for message in request.messages:
        mapped: dict[str, object] = {
            "role": message.role.value,
            "content": message.content,
        }
        if message.name is not None:
            mapped["name"] = message.name
        if message.tool_call_id is not None:
            mapped["tool_call_id"] = message.tool_call_id
        messages.append(mapped)
    payload: dict[str, object] = {
        "model": request.requested_model,
        "messages": messages,
    }
    if request.temperature is not None:
        payload["temperature"] = request.temperature
    if request.max_output_tokens is not None:
        payload["max_tokens"] = request.max_output_tokens
    if request.tools:
        payload["tools"] = [
            {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.input_schema,
                },
            }
            for tool in request.tools
        ]
        payload["tool_choice"] = _map_tool_choice(request)
    if request.response_format is ResponseFormat.JSON_OBJECT:
        payload["response_format"] = {"type": "json_object"}
    elif request.response_format is ResponseFormat.JSON_SCHEMA:
        payload["response_format"] = {
            "type": "json_schema",
            "json_schema": {
                "name": "cognitive_os_response",
                "strict": True,
                "schema": request.response_schema,
            },
        }
    return payload


def _map_tool_choice(request: ModelProviderRequest) -> object:
    if request.tool_choice is ToolChoiceMode.NONE:
        return "none"
    if request.tool_choice is ToolChoiceMode.AUTO:
        return "auto"
    if request.tool_choice is ToolChoiceMode.REQUIRED:
        return "required"
    return {
        "type": "function",
        "function": {"name": request.selected_tool_name},
    }


def _field(value: object, name: str, default: object = None) -> object:
    if isinstance(value, Mapping):
        return value.get(name, default)
    return cast(object, getattr(value, name, default))


def _sequence(value: object, *, field_name: str) -> Sequence[object]:
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        return value
    raise ValueError(f"{field_name} must be a sequence")


def map_response(
    response: object,
    request: ModelProviderRequest,
    *,
    provider_id: str,
    latency_ms: float,
) -> ModelProviderResponse:
    try:
        choices = _sequence(_field(response, "choices"), field_name="choices")
        if not choices:
            raise ValueError("response contains no choices")
        choice = choices[0]
        message = _field(choice, "message")
        resolved_model = _field(response, "model")
        if not isinstance(resolved_model, str) or not resolved_model:
            raise ValueError("response is missing model metadata")
        content_value = _field(message, "content")
        content = content_value if isinstance(content_value, str) else None
        tool_calls = _map_tool_calls(_field(message, "tool_calls", ()))
        if request.tool_choice in {ToolChoiceMode.REQUIRED, ToolChoiceMode.SPECIFIC}:
            if not tool_calls:
                raise ValueError("required tool choice returned no tool call")
            if (
                request.tool_choice is ToolChoiceMode.SPECIFIC
                and request.selected_tool_name not in {call.name for call in tool_calls}
            ):
                raise ValueError("provider did not call the specifically requested tool")
        raw_finish = _field(choice, "finish_reason")
        finish_reason, warnings = map_finish_reason(raw_finish)
        usage = _map_usage(_field(response, "usage"))
        structured = _map_structured_output(content, request)
        request_id_value = _field(response, "id")
        request_id = request_id_value if isinstance(request_id_value, str) else None
        return ModelProviderResponse(
            model_call_id=request.model_call_id,
            provider_id=provider_id,
            requested_model=request.requested_model,
            resolved_model=resolved_model,
            content=content,
            structured_output=structured,
            tool_calls=tool_calls,
            finish_reason=finish_reason,
            usage=usage,
            latency_ms=latency_ms,
            provider_request_id=request_id,
            warnings=warnings,
        )
    except (TypeError, ValueError, ValidationError, json.JSONDecodeError) as error:
        raise ProviderInvalidResponseError(
            provider_id=provider_id,
            message="MiniMax returned an invalid normalized response",
        ) from error


def _map_tool_calls(value: object) -> tuple[NormalizedToolCall, ...]:
    if value is None:
        return ()
    calls: list[NormalizedToolCall] = []
    for call in _sequence(value, field_name="tool_calls"):
        function = _field(call, "function")
        arguments = _field(function, "arguments")
        if not isinstance(arguments, str):
            raise ValueError("tool-call arguments must be JSON text")
        parsed = json.loads(arguments)
        if not isinstance(parsed, dict):
            raise ValueError("tool-call arguments must decode to an object")
        call_id = _field(call, "id")
        name = _field(function, "name")
        if not isinstance(call_id, str) or not isinstance(name, str):
            raise ValueError("tool call is missing ID or name")
        calls.append(
            NormalizedToolCall(
                tool_call_id=call_id,
                name=name,
                arguments=cast(dict[str, JsonValue], parsed),
            )
        )
    return tuple(calls)


def _map_usage(value: object) -> TokenUsage | None:
    if value is None:
        return None
    prompt = _field(value, "prompt_tokens")
    completion = _field(value, "completion_tokens")
    total = _field(value, "total_tokens")
    values = (prompt, completion, total)
    if any(item is not None and (not isinstance(item, int) or item < 0) for item in values):
        raise ValueError("usage values must be non-negative integers")
    return TokenUsage(
        input_tokens=prompt if isinstance(prompt, int) else None,
        output_tokens=completion if isinstance(completion, int) else None,
        total_tokens=total if isinstance(total, int) else None,
    )


def map_finish_reason(value: object) -> tuple[ModelFinishReason, tuple[str, ...]]:
    mapping = {
        "stop": ModelFinishReason.COMPLETED,
        "tool_calls": ModelFinishReason.TOOL_CALL,
        "length": ModelFinishReason.LENGTH,
        "content_filter": ModelFinishReason.CONTENT_FILTER,
    }
    if isinstance(value, str) and value in mapping:
        return mapping[value], ()
    return ModelFinishReason.UNKNOWN, (f"unknown provider finish reason: {value}",)


def _map_structured_output(
    content: str | None,
    request: ModelProviderRequest,
) -> dict[str, JsonValue] | list[JsonValue] | None:
    if request.response_format is ResponseFormat.TEXT:
        return None
    if content is None:
        raise ValueError("structured response has no content")
    parsed = json.loads(content)
    if not isinstance(parsed, (dict, list)):
        raise ValueError("structured response must decode to an object or array")
    if request.response_format is ResponseFormat.JSON_SCHEMA:
        schema = request.response_schema
        if schema is None:
            raise ValueError("JSON Schema response has no request schema")
        validate(instance=parsed, schema=schema)
    return cast(dict[str, JsonValue] | list[JsonValue], parsed)
