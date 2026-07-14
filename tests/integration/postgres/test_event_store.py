from __future__ import annotations

import asyncio
from uuid import uuid4

import pytest
from sqlalchemy import update

from cognitive_os.events.catalog import build_default_event_catalog
from cognitive_os.infrastructure.errors import (
    DuplicateEventError,
    EventIntegrityError,
    StreamTypeMismatchError,
    WrongExpectedVersionError,
)
from cognitive_os.infrastructure.postgres.event_store import PostgresEventStore
from cognitive_os.infrastructure.postgres.tables import events


@pytest.mark.asyncio
async def test_append_and_deterministic_reads(engines, make_envelope) -> None:
    app, _admin = engines
    store = PostgresEventStore(app, build_default_event_catalog())
    stream_id = uuid4()
    first = make_envelope(stream_id=stream_id, version=1)
    result = await store.append([first], expected_version=0)
    second = make_envelope(stream_id=stream_id, version=2)
    third = make_envelope(stream_id=stream_id, version=3)
    batch = await store.append([second, third], expected_version=1)
    assert result.global_positions[0] < batch.global_positions[0] < batch.global_positions[1]
    assert [item.envelope.stream_version for item in await store.read_stream(stream_id)] == [
        1,
        2,
        3,
    ]
    assert [
        item.envelope.stream_version
        for item in await store.read_stream(stream_id, from_version=2, to_version=2)
    ] == [2]
    assert (
        len(await store.read_all(after_global_position=result.global_positions[0], limit=10)) == 2
    )
    assert await store.get_event(first.event_id) is not None
    assert await store.get_stream_version(stream_id) == 3
    assert (await store.get_stream_type(stream_id)).value == "task"


@pytest.mark.asyncio
async def test_expected_version_stream_type_and_duplicate_event_failures(
    engines, make_envelope
) -> None:
    app, _admin = engines
    store = PostgresEventStore(app, build_default_event_catalog())
    stream_id = uuid4()
    first = make_envelope(stream_id=stream_id, version=1)
    await store.append([first], expected_version=0)
    with pytest.raises(WrongExpectedVersionError):
        await store.append([make_envelope(stream_id=stream_id, version=1)], expected_version=0)
    with pytest.raises(StreamTypeMismatchError):
        await store.append(
            [make_envelope(stream_id=stream_id, version=2, stream_type="system")],
            expected_version=1,
        )
    with pytest.raises(DuplicateEventError):
        await store.append(
            [make_envelope(stream_id=uuid4(), version=1, event_id=first.event_id)],
            expected_version=0,
        )


@pytest.mark.asyncio
@pytest.mark.concurrency
async def test_two_writers_cannot_commit_the_same_next_version(engines, make_envelope) -> None:
    app, _admin = engines
    stream_id = uuid4()
    left = PostgresEventStore(app, build_default_event_catalog())
    right = PostgresEventStore(app, build_default_event_catalog())
    results = await asyncio.gather(
        left.append([make_envelope(stream_id=stream_id, version=1)], expected_version=0),
        right.append([make_envelope(stream_id=stream_id, version=1)], expected_version=0),
        return_exceptions=True,
    )
    assert sum(not isinstance(result, BaseException) for result in results) == 1
    assert sum(isinstance(result, WrongExpectedVersionError) for result in results) == 1


@pytest.mark.asyncio
async def test_batch_rolls_back_after_late_duplicate(engines, make_envelope) -> None:
    app, _admin = engines
    store = PostgresEventStore(app, build_default_event_catalog())
    existing = make_envelope(stream_id=uuid4(), version=1)
    await store.append([existing], expected_version=0)
    stream_id = uuid4()
    batch = [
        make_envelope(stream_id=stream_id, version=1),
        make_envelope(stream_id=stream_id, version=2, event_id=existing.event_id),
    ]
    with pytest.raises(DuplicateEventError):
        await store.append(batch, expected_version=0)
    assert await store.get_stream_version(stream_id) is None
    assert await store.read_stream(stream_id) == ()


@pytest.mark.asyncio
async def test_corrupted_row_is_never_returned(engines, make_envelope) -> None:
    app, admin = engines
    store = PostgresEventStore(app, build_default_event_catalog())
    envelope = make_envelope(stream_id=uuid4(), version=1)
    await store.append([envelope], expected_version=0)
    async with admin.begin() as connection:
        await connection.execute(
            update(events)
            .where(events.c.event_id == envelope.event_id)
            .values(payload_hash="0" * 64)
        )
    with pytest.raises(EventIntegrityError):
        await store.get_event(envelope.event_id)
