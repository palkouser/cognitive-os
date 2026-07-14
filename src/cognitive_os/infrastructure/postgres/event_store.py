"""Atomic async PostgreSQL event-store adapter."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any
from uuid import UUID

from pydantic import ValidationError
from sqlalchemy import and_, insert, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncEngine

from cognitive_os.domain.common import ActorRef
from cognitive_os.domain.enums import StreamType
from cognitive_os.events.base import EventEnvelope
from cognitive_os.events.batches import DEFAULT_MAXIMUM_BATCH_SIZE, validate_event_batch
from cognitive_os.events.catalog import EventCatalog, EventCatalogError
from cognitive_os.events.storage import AppendResult, StoredEvent
from cognitive_os.infrastructure.errors import (
    DuplicateEventError,
    EventIntegrityError,
    EventStoreUnavailableError,
    StreamTypeMismatchError,
    WrongExpectedVersionError,
)
from cognitive_os.telemetry.base import TelemetryPort
from cognitive_os.telemetry.best_effort import BestEffortTelemetry
from cognitive_os.telemetry.noop import NoOpTelemetry

from .engine import postgres_transaction
from .tables import event_streams, events


def event_envelope_to_insert_values(
    envelope: EventEnvelope, *, trace_id: str | None, span_id: str | None
) -> dict[str, Any]:
    return {
        "event_id": envelope.event_id,
        "stream_id": envelope.stream_id,
        "stream_type": envelope.stream_type.value,
        "stream_version": envelope.stream_version,
        "event_type": envelope.event_type,
        "schema_version": envelope.schema_version,
        "occurred_at": envelope.occurred_at,
        "recorded_at": envelope.recorded_at,
        "correlation_id": envelope.correlation_id,
        "causation_event_id": envelope.causation_event_id,
        "actor_json": envelope.actor.model_dump(mode="json"),
        "source_component": envelope.source_component,
        "payload_json": envelope.payload,
        "payload_hash": envelope.payload_hash,
        "privacy_class": envelope.privacy_class.value,
        "trace_id": trace_id,
        "span_id": span_id,
    }


def event_row_to_envelope(row: Mapping[str, Any]) -> EventEnvelope:
    return EventEnvelope(
        event_id=row["event_id"],
        event_type=row["event_type"],
        schema_version=row["schema_version"],
        occurred_at=row["occurred_at"],
        recorded_at=row["recorded_at"],
        stream_id=row["stream_id"],
        stream_type=row["stream_type"],
        stream_version=row["stream_version"],
        correlation_id=row["correlation_id"],
        causation_event_id=row["causation_event_id"],
        actor=ActorRef.model_validate(row["actor_json"]),
        source_component=row["source_component"],
        payload=row["payload_json"],
        payload_hash=row["payload_hash"],
        privacy_class=row["privacy_class"],
    )


class PostgresEventStore:
    def __init__(
        self,
        engine: AsyncEngine,
        catalog: EventCatalog,
        telemetry: TelemetryPort | None = None,
        *,
        maximum_batch_size: int = DEFAULT_MAXIMUM_BATCH_SIZE,
        maximum_read_limit: int = 1000,
    ) -> None:
        self._engine = engine
        self._catalog = catalog
        self._telemetry = BestEffortTelemetry(telemetry or NoOpTelemetry())
        self._maximum_batch_size = maximum_batch_size
        self._maximum_read_limit = maximum_read_limit

    async def append(
        self, events_to_append: Sequence[EventEnvelope], *, expected_version: int
    ) -> AppendResult:
        batch = validate_event_batch(
            events_to_append,
            expected_version=expected_version,
            catalog=self._catalog,
            maximum_batch_size=self._maximum_batch_size,
        )
        first = batch[0]
        try:
            with self._telemetry.start_span("cognitive_os.event_store.append"):
                self._telemetry.set_attribute("db.system", "postgresql")
                self._telemetry.set_attribute("cogos.stream_id", str(first.stream_id))
                self._telemetry.set_attribute("cogos.stream_type", first.stream_type.value)
                self._telemetry.set_attribute("cogos.expected_stream_version", expected_version)
                self._telemetry.set_attribute("cogos.event_count", len(batch))
                context = self._telemetry.get_current_context()
                async with postgres_transaction(self._engine) as connection:
                    await connection.execute(
                        pg_insert(event_streams)
                        .values(
                            stream_id=first.stream_id,
                            stream_type=first.stream_type.value,
                            current_version=0,
                        )
                        .on_conflict_do_nothing(index_elements=[event_streams.c.stream_id])
                    )
                    claim = await connection.execute(
                        update(event_streams)
                        .where(
                            and_(
                                event_streams.c.stream_id == first.stream_id,
                                event_streams.c.current_version == expected_version,
                                event_streams.c.stream_type == first.stream_type.value,
                            )
                        )
                        .values(
                            current_version=batch[-1].stream_version,
                            updated_at=first.recorded_at,
                        )
                        .returning(event_streams.c.current_version)
                    )
                    if claim.scalar_one_or_none() is None:
                        current = (
                            await connection.execute(
                                select(
                                    event_streams.c.stream_type,
                                    event_streams.c.current_version,
                                ).where(event_streams.c.stream_id == first.stream_id)
                            )
                        ).one_or_none()
                        if current is not None and current.stream_type != first.stream_type.value:
                            raise StreamTypeMismatchError(
                                first.stream_id, first.stream_type.value, current.stream_type
                            )
                        actual = current.current_version if current is not None else None
                        raise WrongExpectedVersionError(first.stream_id, expected_version, actual)
                    positions: list[int] = []
                    stored_at = None
                    for envelope in batch:
                        result = await connection.execute(
                            insert(events)
                            .values(
                                **event_envelope_to_insert_values(
                                    envelope,
                                    trace_id=context.trace_id,
                                    span_id=context.span_id,
                                )
                            )
                            .returning(events.c.global_position, events.c.stored_at)
                        )
                        inserted = result.one()
                        positions.append(inserted.global_position)
                        stored_at = inserted.stored_at
                if stored_at is None:
                    raise EventStoreUnavailableError("PostgreSQL did not return storage time")
                self._telemetry.set_attribute(
                    "cogos.committed_stream_version", batch[-1].stream_version
                )
                return AppendResult(
                    stream_id=first.stream_id,
                    previous_stream_version=expected_version,
                    current_stream_version=batch[-1].stream_version,
                    event_ids=tuple(event.event_id for event in batch),
                    global_positions=tuple(positions),
                    stored_at=stored_at,
                )
        except IntegrityError as error:
            if "event_id" in str(error.orig) or "events_event_id_key" in str(error.orig):
                raise DuplicateEventError(first.event_id) from error
            raise
        except (WrongExpectedVersionError, StreamTypeMismatchError, DuplicateEventError):
            raise
        except SQLAlchemyError as error:
            raise EventStoreUnavailableError("PostgreSQL append failed") from error

    async def read_stream(
        self,
        stream_id: UUID,
        *,
        from_version: int = 1,
        to_version: int | None = None,
        limit: int | None = None,
    ) -> tuple[StoredEvent, ...]:
        if from_version < 1 or (to_version is not None and to_version < from_version):
            raise ValueError("invalid stream version bounds")
        self._validate_limit(limit, optional=True)
        statement = select(events).where(
            and_(events.c.stream_id == stream_id, events.c.stream_version >= from_version)
        )
        if to_version is not None:
            statement = statement.where(events.c.stream_version <= to_version)
        statement = statement.order_by(events.c.stream_version)
        if limit is not None:
            statement = statement.limit(limit)
        return await self._read(statement, "cognitive_os.event_store.read_stream")

    async def read_all(
        self, *, after_global_position: int = 0, limit: int = 100
    ) -> tuple[StoredEvent, ...]:
        if after_global_position < 0:
            raise ValueError("after_global_position must be non-negative")
        self._validate_limit(limit, optional=False)
        statement = (
            select(events)
            .where(events.c.global_position > after_global_position)
            .order_by(events.c.global_position)
            .limit(limit)
        )
        return await self._read(statement, "cognitive_os.event_store.read_all")

    async def get_event(self, event_id: UUID) -> StoredEvent | None:
        rows = await self._read(
            select(events).where(events.c.event_id == event_id),
            "cognitive_os.event_store.get_event",
        )
        return rows[0] if rows else None

    async def get_stream_version(self, stream_id: UUID) -> int | None:
        async with self._engine.connect() as connection:
            value = await connection.scalar(
                select(event_streams.c.current_version).where(
                    event_streams.c.stream_id == stream_id
                )
            )
        return int(value) if value is not None else None

    async def get_stream_type(self, stream_id: UUID) -> StreamType | None:
        async with self._engine.connect() as connection:
            value = await connection.scalar(
                select(event_streams.c.stream_type).where(event_streams.c.stream_id == stream_id)
            )
        return StreamType(value) if value is not None else None

    async def _read(self, statement: Any, span_name: str) -> tuple[StoredEvent, ...]:
        try:
            with self._telemetry.start_span(span_name):
                self._telemetry.set_attribute("db.system", "postgresql")
                async with self._engine.connect() as connection:
                    result = await connection.execute(statement)
                    mappings = result.mappings().all()
                return tuple(self._row_to_stored(dict(row)) for row in mappings)
        except (EventIntegrityError, EventCatalogError, ValidationError):
            raise
        except SQLAlchemyError as error:
            raise EventStoreUnavailableError("PostgreSQL read failed") from error

    def _row_to_stored(self, row: Mapping[str, Any]) -> StoredEvent:
        try:
            envelope = event_row_to_envelope(row)
            payload_model = self._catalog.get_payload_model(
                envelope.event_type, envelope.schema_version
            )
            payload_model.model_validate(envelope.payload)
            return StoredEvent(
                global_position=row["global_position"],
                stored_at=row["stored_at"],
                envelope=envelope,
                trace_id=row["trace_id"],
                span_id=row["span_id"],
            )
        except (ValidationError, ValueError, EventCatalogError) as error:
            raise EventIntegrityError("stored event failed validation") from error

    def _validate_limit(self, limit: int | None, *, optional: bool) -> None:
        if limit is None and optional:
            return
        if limit is None or limit < 1 or limit > self._maximum_read_limit:
            raise ValueError(f"limit must be between 1 and {self._maximum_read_limit}")
