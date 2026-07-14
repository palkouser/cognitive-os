from uuid import uuid4

import pytest
from pydantic import ValidationError

from cognitive_os.domain.model_requests import (
    ModelProviderRequest,
    ProviderMessage,
    ProviderMessageRole,
    ProviderToolDefinition,
)
from cognitive_os.domain.provider import ResponseFormat, ToolChoiceMode


def make_request(**updates) -> ModelProviderRequest:
    values = {
        "model_call_id": uuid4(),
        "task_run_id": uuid4(),
        "correlation_id": uuid4(),
        "requested_model": "model",
        "messages": (ProviderMessage(role=ProviderMessageRole.USER, content="hello"),),
    }
    values.update(updates)
    return ModelProviderRequest(**values)


def test_request_round_trip_and_unknown_fields() -> None:
    request = make_request()
    assert ModelProviderRequest.model_validate_json(request.model_dump_json()) == request
    with pytest.raises(ValidationError):
        make_request(unknown=True)


def test_request_rejects_secret_like_metadata_recursively() -> None:
    with pytest.raises(ValidationError, match="secret-like"):
        make_request(metadata={"nested": {"api_token": "not-inspected"}})


def test_tool_choice_and_schema_invariants() -> None:
    tool = ProviderToolDefinition(
        name="lookup",
        description="Look up a value",
        input_schema={"type": "object"},
    )
    with pytest.raises(ValidationError, match="at least one tool"):
        make_request(tool_choice=ToolChoiceMode.REQUIRED)
    with pytest.raises(ValidationError, match="selected_tool_name"):
        make_request(tools=(tool,), tool_choice=ToolChoiceMode.SPECIFIC)
    with pytest.raises(ValidationError, match="response_schema"):
        make_request(response_format=ResponseFormat.JSON_SCHEMA)


def test_tool_result_requires_call_id() -> None:
    with pytest.raises(ValidationError, match="tool_call_id"):
        ProviderMessage(role=ProviderMessageRole.TOOL, content="result")
