from uuid import uuid4

import pytest

from cognitive_os.domain.coding import RepositoryProfile, RepositoryProfileStatus
from cognitive_os.events.catalog import build_default_event_catalog
from cognitive_os.events.coding_event_service import CodingEventService
from cognitive_os.events.coding_events import CodingRepositoryProfileDetected
from cognitive_os.events.storage import StoredEventDecoder
from cognitive_os.infrastructure.postgres.event_store import PostgresEventStore


@pytest.mark.asyncio
async def test_coding_lifecycle_event_round_trips_with_expected_version(engines) -> None:
    app, _admin = engines
    store = PostgresEventStore(app, build_default_event_catalog())
    service = CodingEventService(store)
    task_run_id = uuid4()
    profile = RepositoryProfile(
        status=RepositoryProfileStatus.SUPPORTED,
        git_repository=True,
        has_pyproject=True,
        python_version=">=3.12,<3.13",
        has_pytest=True,
        has_ruff=True,
        has_mypy=True,
        package_layout="src",
        rootless_docker=True,
    )
    await service.append(
        task_run_id,
        CodingRepositoryProfileDetected(task_run_id=task_run_id, profile=profile),
        correlation_id=task_run_id,
    )
    await service.append(
        task_run_id,
        CodingRepositoryProfileDetected(task_run_id=task_run_id, profile=profile),
        correlation_id=task_run_id,
    )

    stored = await store.read_stream(task_run_id)
    decoder = StoredEventDecoder(build_default_event_catalog())
    assert [item.envelope.stream_version for item in stored] == [1, 2]
    assert all(
        isinstance(decoder.decode_stored_event(item).payload, CodingRepositoryProfileDetected)
        for item in stored
    )
