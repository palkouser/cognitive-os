from uuid import uuid4

import pytest

from cognitive_os.domain.model_requests import (
    ModelProviderRequest,
    ModelProviderResponse,
    ProviderMessage,
    ProviderMessageRole,
)
from cognitive_os.domain.provider import ModelFinishReason


@pytest.fixture
def provider_request() -> ModelProviderRequest:
    return ModelProviderRequest(
        model_call_id=uuid4(),
        task_run_id=uuid4(),
        correlation_id=uuid4(),
        requested_model="contract-model",
        messages=(ProviderMessage(role=ProviderMessageRole.USER, content="hello"),),
    )


@pytest.fixture
def provider_response(provider_request) -> ModelProviderResponse:
    return ModelProviderResponse(
        model_call_id=provider_request.model_call_id,
        provider_id="mock",
        requested_model=provider_request.requested_model,
        resolved_model="contract-model",
        content="answer",
        finish_reason=ModelFinishReason.COMPLETED,
        latency_ms=0,
    )
