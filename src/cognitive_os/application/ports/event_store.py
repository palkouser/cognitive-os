"""Application boundary for append-only event storage."""

from collections.abc import Sequence
from typing import Protocol
from uuid import UUID

from cognitive_os.domain.enums import StreamType
from cognitive_os.events.base import EventEnvelope
from cognitive_os.events.storage import AppendResult, StoredEvent


class EventStorePort(Protocol):
    async def append(
        self, events: Sequence[EventEnvelope], *, expected_version: int
    ) -> AppendResult: ...

    async def read_stream(
        self,
        stream_id: UUID,
        *,
        from_version: int = 1,
        to_version: int | None = None,
        limit: int | None = None,
    ) -> tuple[StoredEvent, ...]: ...

    async def read_all(
        self, *, after_global_position: int = 0, limit: int = 100
    ) -> tuple[StoredEvent, ...]: ...

    async def get_event(self, event_id: UUID) -> StoredEvent | None: ...

    async def get_stream_version(self, stream_id: UUID) -> int | None: ...

    async def get_stream_type(self, stream_id: UUID) -> StreamType | None: ...
