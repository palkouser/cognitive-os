import asyncio
from uuid import uuid4

import pytest

from cognitive_os.domain.model_requests import (
    ModelProviderRequest,
    ModelProviderResponse,
    ProviderMessage,
    ProviderMessageRole,
)
from cognitive_os.domain.provider import (
    ModelFinishReason,
    ProviderStreamEvent,
    ProviderStreamEventType,
)
from cognitive_os.providers.errors import (
    ProviderAuthenticationError,
    ProviderInvalidResponseError,
    ProviderTimeoutError,
)
from cognitive_os.providers.mock import MockProvider
from cognitive_os.providers.replay import (
    ReplayFixture,
    ReplayProvider,
    request_fingerprint,
)
from cognitive_os.providers.retry import RetryPolicy, execute_with_retry


def make_request() -> ModelProviderRequest:
    return ModelProviderRequest(
        model_call_id=uuid4(),
        task_run_id=uuid4(),
        correlation_id=uuid4(),
        requested_model="model",
        messages=(ProviderMessage(role=ProviderMessageRole.USER, content="hello"),),
    )


def make_response(request: ModelProviderRequest) -> ModelProviderResponse:
    return ModelProviderResponse(
        model_call_id=request.model_call_id,
        provider_id="source",
        requested_model=request.requested_model,
        resolved_model="resolved",
        content="answer",
        finish_reason=ModelFinishReason.COMPLETED,
        latency_ms=0,
    )


@pytest.mark.asyncio
async def test_mock_completion_capture_and_stream_are_deterministic() -> None:
    request = make_request()
    stream = (
        ProviderStreamEvent(
            sequence=1,
            event_type=ProviderStreamEventType.RESPONSE_STARTED,
        ),
        ProviderStreamEvent(
            sequence=2,
            event_type=ProviderStreamEventType.TEXT_DELTA,
            text_delta="answer",
        ),
    )
    provider = MockProvider(outcomes=(make_response(request), stream))
    assert (await provider.complete(request)).content == "answer"
    assert [event.sequence async for event in provider.stream(request)] == [1, 2]
    assert provider.call_count == 2


@pytest.mark.asyncio
async def test_replay_ignores_request_identity_but_requires_semantic_match() -> None:
    first = make_request()
    fixture = ReplayFixture(
        request_fingerprint=request_fingerprint(first),
        source_provider="minimax",
        response=make_response(first),
    )
    provider = ReplayProvider((fixture,))
    second = first.model_copy(
        update={
            "model_call_id": uuid4(),
            "task_run_id": uuid4(),
            "correlation_id": uuid4(),
        }
    )
    response = await provider.complete(second)
    assert response.model_call_id == second.model_call_id
    with pytest.raises(ProviderInvalidResponseError, match="no replay fixture"):
        await provider.complete(second.model_copy(update={"requested_model": "different"}))


@pytest.mark.asyncio
async def test_retry_is_bounded_and_non_retryable_errors_stop() -> None:
    attempts: list[int] = []
    delays: list[float] = []

    async def operation(attempt: int) -> str:
        attempts.append(attempt)
        if attempt < 3:
            raise ProviderTimeoutError(provider_id="test", message="temporary")
        return "ok"

    async def sleeper(delay: float) -> None:
        delays.append(delay)

    result = await execute_with_retry(
        operation,
        provider_id="test",
        policy=RetryPolicy(jitter_ratio=0),
        sleeper=sleeper,
    )
    assert result == "ok"
    assert attempts == [1, 2, 3]
    assert delays == [1, 2]

    async def authentication(_attempt: int) -> str:
        raise ProviderAuthenticationError(provider_id="test", message="denied")

    with pytest.raises(ProviderAuthenticationError) as failure:
        await execute_with_retry(
            authentication,
            provider_id="test",
            policy=RetryPolicy(),
            sleeper=sleeper,
        )
    assert failure.value.attempt == 1


@pytest.mark.asyncio
async def test_retry_cancellation_is_typed() -> None:
    async def operation(_attempt: int) -> str:
        raise asyncio.CancelledError

    with pytest.raises(Exception, match="cancelled"):
        await execute_with_retry(operation, provider_id="test", policy=RetryPolicy())
