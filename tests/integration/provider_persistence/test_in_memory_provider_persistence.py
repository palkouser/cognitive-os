from uuid import UUID, uuid4

import pytest

from cognitive_os.application.services.model_execution import ModelExecutionService
from cognitive_os.domain.common import ArtifactRef, utc_now
from cognitive_os.domain.enums import StreamType
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
from cognitive_os.events.base import EventEnvelope
from cognitive_os.events.provider_event_service import (
    ProviderArtifactService,
    ProviderEventService,
)
from cognitive_os.events.storage import AppendResult
from cognitive_os.providers.errors import ProviderPersistenceError, ProviderTimeoutError
from cognitive_os.providers.mock import MockProvider
from cognitive_os.providers.registry import ProviderRegistry
from cognitive_os.providers.retry import RetryPolicy


class RecordingEventStore:
    def __init__(self, *, fail_on_event_type: str | None = None) -> None:
        self.events: list[EventEnvelope] = []
        self.fail_on_event_type = fail_on_event_type

    async def get_stream_version(self, stream_id: UUID) -> int | None:
        versions = [event.stream_version for event in self.events if event.stream_id == stream_id]
        return max(versions) if versions else None

    async def append(
        self, events: tuple[EventEnvelope, ...], *, expected_version: int
    ) -> AppendResult:
        event = events[0]
        if event.event_type == self.fail_on_event_type:
            raise RuntimeError("injected event-store failure")
        self.events.extend(events)
        return AppendResult(
            stream_id=event.stream_id,
            previous_stream_version=expected_version,
            current_stream_version=event.stream_version,
            event_ids=(event.event_id,),
            global_positions=(len(self.events),),
            stored_at=utc_now(),
        )


class RecordingArtifactStore:
    def __init__(self) -> None:
        self.values: list[tuple[bytes, str]] = []

    async def put_bytes(
        self, data: bytes, *, media_type: str, source_event_id: UUID | None = None
    ) -> ArtifactRef:
        del source_event_id
        self.values.append((data, media_type))
        return ArtifactRef(
            artifact_id=uuid4(),
            media_type=media_type,
            content_hash="0" * 64,
            size_bytes=len(data),
            storage_key=f"sha256/{len(self.values)}",
            created_at=utc_now(),
        )


def request() -> ModelProviderRequest:
    return ModelProviderRequest(
        model_call_id=uuid4(),
        task_run_id=uuid4(),
        correlation_id=uuid4(),
        requested_model="mock-model",
        messages=(ProviderMessage(role=ProviderMessageRole.USER, content="hello"),),
    )


def response(value: ModelProviderRequest) -> ModelProviderResponse:
    return ModelProviderResponse(
        model_call_id=value.model_call_id,
        provider_id="mock",
        requested_model=value.requested_model,
        resolved_model="mock-model",
        content="answer",
        finish_reason=ModelFinishReason.COMPLETED,
        latency_ms=1,
    )


@pytest.mark.asyncio
async def test_retry_attempts_artifacts_and_terminal_event_are_contiguous() -> None:
    value = request()
    provider = MockProvider(
        outcomes=(
            ProviderTimeoutError(provider_id="mock", message="temporary"),
            response(value),
        )
    )
    events = RecordingEventStore()
    artifacts = RecordingArtifactStore()

    service = ModelExecutionService(
        ProviderRegistry((provider,)),
        default_provider_id="mock",
        retry_policy=RetryPolicy(initial_delay_seconds=0, jitter_ratio=0),
        event_service=ProviderEventService(events),
        artifact_service=ProviderArtifactService(artifacts),
    )
    await service.execute(value)
    assert [event.event_type for event in events.events] == [
        "model_call.requested",
        "model_call.started",
        "model_call.retried",
        "model_call.started",
        "model_call.completed",
    ]
    assert [event.stream_version for event in events.events] == [1, 2, 3, 4, 5]
    assert all(event.stream_type is StreamType.MODEL_CALL for event in events.events)
    assert len(artifacts.values) == 2
    assert all(b"api_key" not in data.lower() for data, _media_type in artifacts.values)


@pytest.mark.asyncio
async def test_terminal_persistence_failure_does_not_repeat_successful_call() -> None:
    value = request()
    provider = MockProvider(outcomes=(response(value),))
    events = RecordingEventStore(fail_on_event_type="model_call.completed")
    service = ModelExecutionService(
        ProviderRegistry((provider,)),
        default_provider_id="mock",
        event_service=ProviderEventService(events),
    )
    with pytest.raises(ProviderPersistenceError):
        await service.execute(value)
    assert provider.call_count == 1


@pytest.mark.asyncio
async def test_streaming_uses_the_same_event_and_artifact_lifecycle() -> None:
    value = request()
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
        ProviderStreamEvent(
            sequence=3,
            event_type=ProviderStreamEventType.RESPONSE_COMPLETED,
            finish_reason=ModelFinishReason.COMPLETED,
        ),
    )
    events = RecordingEventStore()
    artifacts = RecordingArtifactStore()
    service = ModelExecutionService(
        ProviderRegistry((MockProvider(outcomes=(stream,)),)),
        default_provider_id="mock",
        event_service=ProviderEventService(events),
        artifact_service=ProviderArtifactService(artifacts),
    )
    received = [event async for event in service.stream(value)]
    assert [event.sequence for event in received] == [1, 2, 3]
    assert [event.event_type for event in events.events] == [
        "model_call.requested",
        "model_call.started",
        "model_call.completed",
    ]
    assert len(artifacts.values) == 2


@pytest.mark.asyncio
async def test_artifact_persistence_redacts_configured_environment_secrets(
    monkeypatch,
) -> None:
    secret = "provider-secret-value-12345"  # pragma: allowlist secret
    monkeypatch.setenv("COGOS_PROVIDER_TEST_TOKEN", secret)
    value = request().model_copy(
        update={
            "messages": (
                ProviderMessage(
                    role=ProviderMessageRole.USER,
                    content=f"Never persist {secret} in clear text.",
                ),
            )
        }
    )
    artifacts = RecordingArtifactStore()
    await ProviderArtifactService(artifacts).store_request(value)
    encoded, _media_type = artifacts.values[0]
    assert secret.encode() not in encoded
    assert b"<redacted>" in encoded
