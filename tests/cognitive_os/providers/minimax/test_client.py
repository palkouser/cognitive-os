from types import SimpleNamespace
from uuid import uuid4

import pytest

from cognitive_os.config.provider_config import MiniMaxKeyType, MiniMaxProviderConfig
from cognitive_os.domain.model_requests import (
    ModelProviderRequest,
    ProviderMessage,
    ProviderMessageRole,
)
from cognitive_os.domain.provider import ProviderStatus
from cognitive_os.providers.minimax.client import MiniMaxProvider


class FakeCompletions:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    async def create(self, **kwargs: object) -> object:
        self.calls.append(kwargs)
        if kwargs.get("stream") is True:
            return FakeStream(
                (
                    SimpleNamespace(
                        choices=[
                            SimpleNamespace(
                                finish_reason=None,
                                delta=SimpleNamespace(content="ans", tool_calls=[]),
                            )
                        ]
                    ),
                    SimpleNamespace(
                        choices=[
                            SimpleNamespace(
                                finish_reason="stop",
                                delta=SimpleNamespace(content="wer", tool_calls=[]),
                            )
                        ]
                    ),
                )
            )
        return SimpleNamespace(
            id="request-1",
            model="MiniMax-M3-resolved",
            choices=[
                SimpleNamespace(
                    finish_reason="stop",
                    message=SimpleNamespace(content="answer", tool_calls=[]),
                )
            ],
            usage=SimpleNamespace(prompt_tokens=1, completion_tokens=1, total_tokens=2),
        )


class FakeStream:
    def __init__(self, values: tuple[object, ...]) -> None:
        self._values = iter(values)

    def __aiter__(self):
        return self

    async def __anext__(self) -> object:
        try:
            return next(self._values)
        except StopIteration as error:
            raise StopAsyncIteration from error


class FakeModels:
    async def list(self) -> object:
        return SimpleNamespace(data=[SimpleNamespace(id="MiniMax-M3")])


class FakeClient:
    def __init__(self) -> None:
        self.chat = SimpleNamespace(completions=FakeCompletions())
        self.models = FakeModels()
        self.closed = False

    async def close(self) -> None:
        self.closed = True


def request() -> ModelProviderRequest:
    return ModelProviderRequest(
        model_call_id=uuid4(),
        task_run_id=uuid4(),
        correlation_id=uuid4(),
        requested_model="MiniMax-M3",
        messages=(ProviderMessage(role=ProviderMessageRole.USER, content="hello"),),
    )


@pytest.mark.asyncio
async def test_minimax_client_completion_health_and_close() -> None:
    client = FakeClient()
    provider = MiniMaxProvider(
        MiniMaxProviderConfig(key_type=MiniMaxKeyType.SUBSCRIPTION),
        client=client,
    )
    response = await provider.complete(request())
    health = await provider.health_check()
    await provider.close()
    assert response.content == "answer"
    assert health.status is ProviderStatus.AVAILABLE
    assert client.chat.completions.calls[0]["model"] == "MiniMax-M3"
    assert client.closed is True


@pytest.mark.asyncio
async def test_minimax_stream_is_ordered_and_has_one_terminal_event() -> None:
    client = FakeClient()
    provider = MiniMaxProvider(
        MiniMaxProviderConfig(key_type=MiniMaxKeyType.SUBSCRIPTION),
        client=client,
    )
    events = [event async for event in provider.stream(request())]
    assert [event.sequence for event in events] == [1, 2, 3, 4]
    assert "".join(event.text_delta or "" for event in events) == "answer"
    assert events[-1].event_type.value == "response_completed"
    assert sum(event.event_type.value == "response_completed" for event in events) == 1


def test_minimax_provider_repr_contains_no_credentials() -> None:
    provider = MiniMaxProvider(MiniMaxProviderConfig(key_type=MiniMaxKeyType.PAY_AS_YOU_GO))
    assert "COGOS_MINIMAX_API_KEY" not in repr(provider)
    assert "api_key" not in repr(provider).lower()
