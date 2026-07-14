from datetime import UTC, datetime
from pathlib import Path

import pytest

from cognitive_os.domain import StreamType
from cognitive_os.events.base import EventEnvelope
from cognitive_os.events.catalog import build_default_event_catalog
from cognitive_os.events.replay import StreamReplayer
from cognitive_os.events.storage import StoredEvent
from cognitive_os.infrastructure.errors import StreamGapError


def stored(version: int, position: int) -> StoredEvent:
    envelope = EventEnvelope.model_validate_json(
        Path("tests/fixtures/contracts/v1/task-created-envelope.json").read_bytes()
    )
    envelope = EventEnvelope.model_validate({**envelope.model_dump(), "stream_version": version})
    return StoredEvent(
        global_position=position,
        stored_at=datetime(2026, 7, 14, tzinfo=UTC),
        envelope=envelope,
    )


class FakeStore:
    def __init__(self, events):
        self.events = tuple(events)

    async def read_stream(self, stream_id, *, from_version=1, to_version=None, limit=None):
        selected = [
            event
            for event in self.events
            if event.envelope.stream_id == stream_id
            and event.envelope.stream_version >= from_version
            and (to_version is None or event.envelope.stream_version <= to_version)
        ]
        return tuple(selected[:limit])

    async def append(self, events, *, expected_version):
        raise NotImplementedError

    async def read_all(self, *, after_global_position=0, limit=100):
        raise NotImplementedError

    async def get_event(self, event_id):
        raise NotImplementedError

    async def get_stream_version(self, stream_id):
        return len(self.events)

    async def get_stream_type(self, stream_id):
        return StreamType.TASK


@pytest.mark.asyncio
async def test_empty_and_multipage_replay() -> None:
    first = stored(1, 1)
    replayer = StreamReplayer(
        FakeStore([first, stored(2, 2), stored(3, 3)]),
        build_default_event_catalog(),
        page_size=2,
    )
    result = await replayer.replay_stream(
        first.envelope.stream_id,
        initial_state=0,
        reducer=lambda state, _event: state + 1,
    )
    assert (result.state, result.event_count, result.last_stream_version) == (3, 3, 3)
    empty = await StreamReplayer(FakeStore([]), build_default_event_catalog()).replay_stream(
        first.envelope.stream_id, initial_state="initial", reducer=lambda state, _: state
    )
    assert empty.state == "initial" and empty.event_count == 0


@pytest.mark.asyncio
async def test_target_version_and_gap_detection() -> None:
    first = stored(1, 1)
    result = await StreamReplayer(
        FakeStore([first, stored(2, 2)]), build_default_event_catalog()
    ).replay_stream(
        first.envelope.stream_id,
        initial_state=(),
        reducer=lambda state, event: (*state, event.stored_event.envelope.stream_version),
        target_version=1,
    )
    assert result.state == (1,)
    with pytest.raises(StreamGapError):
        await StreamReplayer(
            FakeStore([first, stored(3, 3)]), build_default_event_catalog()
        ).replay_stream(
            first.envelope.stream_id,
            initial_state=0,
            reducer=lambda state, _: state,
        )
