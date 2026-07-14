import json
from uuid import uuid4

import pytest

from cognitive_os.domain.model_requests import (
    ModelProviderRequest,
    ProviderMessage,
    ProviderMessageRole,
)
from cognitive_os.providers.claude_code.mapping import map_advisory_response
from cognitive_os.providers.errors import ProviderInvalidResponseError


def request() -> ModelProviderRequest:
    return ModelProviderRequest(
        model_call_id=uuid4(),
        task_run_id=uuid4(),
        correlation_id=uuid4(),
        requested_model="claude-code",
        messages=(ProviderMessage(role=ProviderMessageRole.USER, content="analyze"),),
    )


def test_advisory_mapping_normalizes_owned_schema() -> None:
    raw = json.dumps(
        {
            "model": "claude-sonnet",
            "structured_output": {
                "summary": "Architecture is layered.",
                "findings": [],
                "recommendations": ["Keep boundaries explicit."],
                "risks": [],
                "verification_steps": ["Run tests."],
            },
            "usage": {"input_tokens": 4, "output_tokens": 5},
        }
    )
    response = map_advisory_response(raw, request(), provider_id="claude-code", duration_ms=10)
    assert response.content == "Architecture is layered."
    assert response.resolved_model == "claude-sonnet"


def test_advisory_mapping_rejects_malformed_output() -> None:
    with pytest.raises(ProviderInvalidResponseError):
        map_advisory_response("not-json", request(), provider_id="claude-code", duration_ms=1)
