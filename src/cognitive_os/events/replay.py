"""Generic typed stream replay and state reconstruction."""

from __future__ import annotations

from typing import Protocol, TypeVar
from uuid import UUID

from pydantic import Field

from cognitive_os.application.ports.event_store import EventStorePort
from cognitive_os.domain.base import ImmutableContractModel
from cognitive_os.infrastructure.errors import StreamGapError
from cognitive_os.telemetry.base import TelemetryPort
from cognitive_os.telemetry.best_effort import BestEffortTelemetry
from cognitive_os.telemetry.noop import NoOpTelemetry

from .catalog import EventCatalog
from .migrations import MigrationRegistry
from .storage import DecodedStoredEvent, StoredEventDecoder

StateT = TypeVar("StateT")


class EventReducer(Protocol[StateT]):
    def __call__(self, state: StateT, event: DecodedStoredEvent) -> StateT: ...


class ReplayResult[StateT](ImmutableContractModel):
    state: StateT
    event_count: int = Field(ge=0)
    first_stream_version: int | None = Field(default=None, gt=0)
    last_stream_version: int | None = Field(default=None, gt=0)
    last_global_position: int | None = Field(default=None, gt=0)


class StreamReplayer:
    def __init__(
        self,
        event_store: EventStorePort,
        catalog: EventCatalog,
        migrations: MigrationRegistry | None = None,
        telemetry: TelemetryPort | None = None,
        *,
        page_size: int = 100,
    ) -> None:
        if page_size < 1:
            raise ValueError("page_size must be positive")
        self._event_store = event_store
        self._decoder = StoredEventDecoder(catalog, migrations)
        self._telemetry = BestEffortTelemetry(telemetry or NoOpTelemetry())
        self._page_size = page_size

    async def replay_stream(
        self,
        stream_id: UUID,
        *,
        initial_state: StateT,
        reducer: EventReducer[StateT],
        from_version: int = 1,
        target_version: int | None = None,
    ) -> ReplayResult[StateT]:
        if from_version < 1 or (target_version is not None and target_version < from_version):
            raise ValueError("invalid replay version bounds")
        state = initial_state
        expected_version = from_version
        count = 0
        first_version: int | None = None
        last_version: int | None = None
        last_position: int | None = None
        with self._telemetry.start_span("cognitive_os.event_replay.replay_stream"):
            while target_version is None or expected_version <= target_version:
                page = await self._event_store.read_stream(
                    stream_id,
                    from_version=expected_version,
                    to_version=target_version,
                    limit=self._page_size,
                )
                if not page:
                    break
                for stored in page:
                    version = stored.envelope.stream_version
                    if version != expected_version:
                        raise StreamGapError(expected_version, version)
                    decoded = self._decoder.decode_stored_event(stored)
                    state = reducer(state, decoded)
                    first_version = first_version or version
                    last_version = version
                    last_position = stored.global_position
                    count += 1
                    expected_version += 1
                if len(page) < self._page_size:
                    break
            self._telemetry.set_attribute("cogos.replay_event_count", count)
        return ReplayResult[StateT](
            state=state,
            event_count=count,
            first_stream_version=first_version,
            last_stream_version=last_version,
            last_global_position=last_position,
        )
