"""In-process append-only event store for offline runs and deterministic tests.

The PostgreSQL adapter remains the durable store. This one exists so a governed
run can be executed with no database — the mandatory benchmark path — while still
going through the real `EventStorePort` contract, including per-stream optimistic
concurrency.
"""

from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from cognitive_os.domain.common import utc_now
from cognitive_os.domain.enums import StreamType

from .base import EventEnvelope
from .storage import AppendResult, StoredEvent


class EventStoreConflictError(RuntimeError):
    """Raised when an append races another writer on the same stream."""


class MemoryEventStore:
    def __init__(self) -> None:
        self._events: list[StoredEvent] = []

    async def append(
        self, events: Sequence[EventEnvelope], *, expected_version: int
    ) -> AppendResult:
        if not events:
            raise ValueError("append requires at least one event")
        stream_id = events[0].stream_id
        current = self._version(stream_id)
        if current != expected_version:
            raise EventStoreConflictError(
                f"expected stream version {expected_version}, found {current}"
            )
        stored: list[StoredEvent] = []
        for envelope in events:
            if envelope.stream_id != stream_id:
                raise ValueError("a single append must target one stream")
            item = StoredEvent(
                global_position=len(self._events) + 1,
                stored_at=utc_now(),
                envelope=envelope,
            )
            self._events.append(item)
            stored.append(item)
        return AppendResult(
            stream_id=stream_id,
            previous_stream_version=current,
            current_stream_version=stored[-1].envelope.stream_version,
            event_ids=tuple(item.envelope.event_id for item in stored),
            global_positions=tuple(item.global_position for item in stored),
            stored_at=stored[-1].stored_at,
        )

    async def read_stream(
        self,
        stream_id: UUID,
        *,
        from_version: int = 1,
        to_version: int | None = None,
        limit: int | None = None,
    ) -> tuple[StoredEvent, ...]:
        values = [
            item
            for item in self._events
            if item.envelope.stream_id == stream_id
            and item.envelope.stream_version >= from_version
            and (to_version is None or item.envelope.stream_version <= to_version)
        ]
        return tuple(values[:limit] if limit else values)

    async def read_all(
        self, *, after_global_position: int = 0, limit: int = 100
    ) -> tuple[StoredEvent, ...]:
        values = [item for item in self._events if item.global_position > after_global_position]
        return tuple(values[:limit])

    async def get_event(self, event_id: UUID) -> StoredEvent | None:
        return next((item for item in self._events if item.envelope.event_id == event_id), None)

    async def get_stream_version(self, stream_id: UUID) -> int | None:
        version = self._version(stream_id)
        return version or None

    async def get_stream_type(self, stream_id: UUID) -> StreamType | None:
        return next(
            (
                item.envelope.stream_type
                for item in self._events
                if item.envelope.stream_id == stream_id
            ),
            None,
        )

    def _version(self, stream_id: UUID) -> int:
        versions = [
            item.envelope.stream_version
            for item in self._events
            if item.envelope.stream_id == stream_id
        ]
        return max(versions) if versions else 0

    def event_types(self) -> tuple[str, ...]:
        """Ordered event-type names, for replay assertions and reports."""
        return tuple(item.envelope.event_type for item in self._events)

    def __len__(self) -> int:
        return len(self._events)
