from uuid import uuid4

import pytest

from cognitive_os.application.services.model_execution import ModelExecutionService
from cognitive_os.domain.model_requests import (
    ModelProviderRequest,
    ModelProviderResponse,
    ProviderMessage,
    ProviderMessageRole,
    ProviderToolDefinition,
)
from cognitive_os.domain.provider import (
    ModelCapabilities,
    ModelFinishReason,
    ProviderStreamEvent,
    ProviderStreamEventType,
)
from cognitive_os.providers.errors import (
    ProviderTimeoutError,
    ProviderUnsupportedCapabilityError,
)
from cognitive_os.providers.mock import MockProvider
from cognitive_os.providers.registry import ProviderRegistry
from cognitive_os.providers.retry import RetryPolicy


def request(**updates) -> ModelProviderRequest:
    values = {
        "model_call_id": uuid4(),
        "task_run_id": uuid4(),
        "correlation_id": uuid4(),
        "requested_model": "mock-model",
        "messages": (ProviderMessage(role=ProviderMessageRole.USER, content="hello"),),
    }
    values.update(updates)
    return ModelProviderRequest(**values)


def response(value: ModelProviderRequest) -> ModelProviderResponse:
    return ModelProviderResponse(
        model_call_id=value.model_call_id,
        provider_id="mock",
        requested_model=value.requested_model,
        resolved_model="mock-model",
        content="answer",
        finish_reason=ModelFinishReason.COMPLETED,
        latency_ms=0,
    )


@pytest.mark.asyncio
async def test_execution_selects_provider_and_measures_latency() -> None:
    value = request()
    provider = MockProvider(outcomes=(response(value),))
    clock = iter((10.0, 10.025))
    service = ModelExecutionService(
        ProviderRegistry((provider,)),
        default_provider_id="mock",
        monotonic_clock=lambda: next(clock),
    )
    result = await service.execute(value)
    assert result.content == "answer"
    assert result.latency_ms == pytest.approx(25)
    assert provider.received_requests == [value]


@pytest.mark.asyncio
async def test_capability_failure_prevents_provider_call() -> None:
    value = request(
        tools=(
            ProviderToolDefinition(
                name="tool",
                description="A tool",
                input_schema={"type": "object"},
            ),
        )
    )
    provider = MockProvider(
        outcomes=(response(value),),
        capabilities=ModelCapabilities(
            model_id="mock-model",
            provider_id="mock",
            supports_tool_calls=False,
        ),
    )
    service = ModelExecutionService(
        ProviderRegistry((provider,)),
        default_provider_id="mock",
    )
    with pytest.raises(ProviderUnsupportedCapabilityError):
        await service.execute(value)
    assert provider.call_count == 0


@pytest.mark.asyncio
async def test_streaming_retries_only_before_payload_and_renumbers_events() -> None:
    value = request()
    events = (
        ProviderStreamEvent(
            sequence=1,
            event_type=ProviderStreamEventType.RESPONSE_STARTED,
        ),
        ProviderStreamEvent(
            sequence=2,
            event_type=ProviderStreamEventType.TEXT_DELTA,
            text_delta="answer",
        ),
        ProviderStreamEvent(
            sequence=3,
            event_type=ProviderStreamEventType.RESPONSE_COMPLETED,
            finish_reason=ModelFinishReason.COMPLETED,
        ),
    )
    provider = MockProvider(
        outcomes=(
            ProviderTimeoutError(provider_id="mock", message="temporary"),
            events,
        )
    )
    service = ModelExecutionService(
        ProviderRegistry((provider,)),
        default_provider_id="mock",
        retry_policy=RetryPolicy(initial_delay_seconds=0, jitter_ratio=0),
    )
    received = [event async for event in service.stream(value)]
    assert [event.sequence for event in received] == [1, 2, 3]
    assert provider.call_count == 2
