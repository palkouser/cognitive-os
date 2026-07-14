from pathlib import Path
from uuid import UUID, uuid4

import pytest

from cognitive_os.application.services.model_execution import ModelExecutionService
from cognitive_os.domain.model_requests import (
    ModelProviderRequest,
    ModelProviderResponse,
    ProviderMessage,
    ProviderMessageRole,
)
from cognitive_os.domain.provider import ModelFinishReason
from cognitive_os.events.catalog import build_default_event_catalog
from cognitive_os.events.provider_event_service import (
    ProviderArtifactService,
    ProviderEventService,
)
from cognitive_os.infrastructure.artifacts.filesystem import ContentAddressedFilesystem
from cognitive_os.infrastructure.artifacts.service import ArtifactService
from cognitive_os.infrastructure.postgres.artifact_repository import (
    PostgresArtifactRepository,
)
from cognitive_os.infrastructure.postgres.event_store import PostgresEventStore
from cognitive_os.providers.mock import MockProvider
from cognitive_os.providers.registry import ProviderRegistry


@pytest.mark.asyncio
async def test_provider_lifecycle_and_artifacts_persist_to_sprint_3_stores(
    engines, tmp_path: Path
) -> None:
    app_engine, _admin_engine = engines
    request = ModelProviderRequest(
        model_call_id=uuid4(),
        task_run_id=uuid4(),
        correlation_id=uuid4(),
        requested_model="mock-model",
        messages=(ProviderMessage(role=ProviderMessageRole.USER, content="hello"),),
    )
    response = ModelProviderResponse(
        model_call_id=request.model_call_id,
        provider_id="mock",
        requested_model=request.requested_model,
        resolved_model="mock-model",
        content="answer",
        finish_reason=ModelFinishReason.COMPLETED,
        latency_ms=0,
    )
    event_store = PostgresEventStore(app_engine, build_default_event_catalog())
    artifact_store = ArtifactService(
        ContentAddressedFilesystem(tmp_path / "artifacts", fsync=False),
        PostgresArtifactRepository(app_engine),
    )
    service = ModelExecutionService(
        ProviderRegistry((MockProvider(outcomes=(response,)),)),
        default_provider_id="mock",
        event_service=ProviderEventService(event_store),
        artifact_service=ProviderArtifactService(artifact_store),
    )
    result = await service.execute(request)
    persisted = await event_store.read_stream(request.model_call_id)
    assert result.content == "answer"
    assert [item.envelope.event_type for item in persisted] == [
        "model_call.requested",
        "model_call.started",
        "model_call.completed",
    ]
    requested_payload = persisted[0].envelope.payload
    completed_payload = persisted[-1].envelope.payload
    request_artifact_id = requested_payload["request"]["input_artifacts"][0]["artifact_id"]
    response_artifact_id = completed_payload["result"]["content_artifact"]["artifact_id"]
    assert await artifact_store.verify(UUID(str(request_artifact_id)))
    assert await artifact_store.verify(UUID(str(response_artifact_id)))
