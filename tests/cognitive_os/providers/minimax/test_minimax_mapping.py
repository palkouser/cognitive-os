from copy import deepcopy
from uuid import uuid4

import pytest

from cognitive_os.domain.model_requests import (
    ModelProviderRequest,
    ProviderMessage,
    ProviderMessageRole,
    ProviderToolDefinition,
)
from cognitive_os.domain.provider import ResponseFormat, ToolChoiceMode
from cognitive_os.providers.errors import ProviderInvalidResponseError
from cognitive_os.providers.minimax.mapping import map_request, map_response


def request(**updates) -> ModelProviderRequest:
    values = {
        "model_call_id": uuid4(),
        "task_run_id": uuid4(),
        "correlation_id": uuid4(),
        "requested_model": "MiniMax-M3",
        "messages": (ProviderMessage(role=ProviderMessageRole.USER, content="hello"),),
    }
    values.update(updates)
    return ModelProviderRequest(**values)


def test_request_mapping_does_not_mutate_contract() -> None:
    tool = ProviderToolDefinition(
        name="lookup",
        description="Look up data",
        input_schema={"type": "object", "properties": {"key": {"type": "string"}}},
    )
    value = request(tools=(tool,), tool_choice=ToolChoiceMode.AUTO)
    before = deepcopy(value)
    payload = map_request(value)
    assert payload["tool_choice"] == "auto"
    assert value == before
    assert "metadata" not in payload


def test_response_normalizes_tool_calls_and_usage() -> None:
    value = request(
        tools=(
            ProviderToolDefinition(
                name="lookup",
                description="Look up data",
                input_schema={"type": "object"},
            ),
        ),
        tool_choice=ToolChoiceMode.AUTO,
    )
    response = map_response(
        {
            "id": "request-1",
            "model": "MiniMax-M3-2026",
            "choices": [
                {
                    "finish_reason": "tool_calls",
                    "message": {
                        "content": None,
                        "tool_calls": [
                            {
                                "id": "call-1",
                                "function": {
                                    "name": "lookup",
                                    "arguments": '{"key":"v"}',
                                },
                            }
                        ],
                    },
                }
            ],
            "usage": {"prompt_tokens": 2, "completion_tokens": 3, "total_tokens": 5},
        },
        value,
        provider_id="minimax",
        latency_ms=1,
    )
    assert response.tool_calls[0].arguments == {"key": "v"}
    assert response.usage is not None and response.usage.total_tokens == 5


def test_structured_response_is_validated_locally() -> None:
    value = request(
        response_format=ResponseFormat.JSON_SCHEMA,
        response_schema={
            "type": "object",
            "properties": {"status": {"const": "ok"}},
            "required": ["status"],
        },
    )
    raw = {
        "model": "MiniMax-M3",
        "choices": [{"finish_reason": "stop", "message": {"content": '{"status":"bad"}'}}],
    }
    with pytest.raises(ProviderInvalidResponseError):
        map_response(raw, value, provider_id="minimax", latency_ms=1)


def test_empty_choices_and_malformed_tool_arguments_fail() -> None:
    with pytest.raises(ProviderInvalidResponseError):
        map_response(
            {"model": "MiniMax-M3", "choices": []},
            request(),
            provider_id="minimax",
            latency_ms=1,
        )
