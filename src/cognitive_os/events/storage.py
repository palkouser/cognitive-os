"""Persistence-neutral event storage records and decoding."""

from __future__ import annotations

import re
from uuid import UUID

from pydantic import Field, SkipValidation, model_validator

from cognitive_os.domain.base import ImmutableContractModel
from cognitive_os.domain.common import UtcDatetime

from .base import EventEnvelope, EventPayload
from .catalog import EventCatalog, EventCatalogError
from .hashing import sha256_digest
from .migrations import MigrationRegistry, MissingMigrationPathError

TRACE_ID_PATTERN = re.compile(r"^[0-9a-f]{32}$")
SPAN_ID_PATTERN = re.compile(r"^[0-9a-f]{16}$")


class StoredEvent(ImmutableContractModel):
    global_position: int = Field(gt=0)
    stored_at: UtcDatetime
    envelope: EventEnvelope
    trace_id: str | None = Field(default=None, pattern=TRACE_ID_PATTERN.pattern)
    span_id: str | None = Field(default=None, pattern=SPAN_ID_PATTERN.pattern)

    @model_validator(mode="after")
    def trace_context_is_complete(self) -> StoredEvent:
        if (self.trace_id is None) != (self.span_id is None):
            raise ValueError("trace_id and span_id must either both be present or both be absent")
        return self


class AppendResult(ImmutableContractModel):
    stream_id: UUID
    previous_stream_version: int = Field(ge=0)
    current_stream_version: int = Field(gt=0)
    event_ids: tuple[UUID, ...]
    global_positions: tuple[int, ...]
    stored_at: UtcDatetime

    @model_validator(mode="after")
    def validate_result(self) -> AppendResult:
        if not self.event_ids:
            raise ValueError("append result must contain at least one event")
        if len(self.event_ids) != len(self.global_positions):
            raise ValueError("event_ids and global_positions must have equal lengths")
        if len(set(self.event_ids)) != len(self.event_ids):
            raise ValueError("event IDs must be unique")
        if any(position <= 0 for position in self.global_positions):
            raise ValueError("global positions must be positive")
        position_pairs = zip(self.global_positions, self.global_positions[1:], strict=False)
        if any(left >= right for left, right in position_pairs):
            raise ValueError("global positions must increase")
        expected_current = self.previous_stream_version + len(self.event_ids)
        if self.current_stream_version != expected_current:
            raise ValueError("current version must equal previous version plus event count")
        return self


class DecodedStoredEvent(ImmutableContractModel):
    stored_event: StoredEvent
    payload: SkipValidation[EventPayload]


class StoredEventDecoder:
    def __init__(self, catalog: EventCatalog, migrations: MigrationRegistry | None = None) -> None:
        self._catalog = catalog
        self._migrations = migrations or MigrationRegistry()

    def decode_stored_event(
        self,
        stored_event: StoredEvent,
        *,
        target_version: int | None = None,
    ) -> DecodedStoredEvent:
        envelope = stored_event.envelope
        if sha256_digest(envelope.payload) != envelope.payload_hash:
            from cognitive_os.infrastructure.errors import EventIntegrityError

            raise EventIntegrityError(f"payload hash mismatch for event {envelope.event_id}")
        version = envelope.schema_version
        payload_data = envelope.payload
        try:
            if target_version is not None and target_version != version:
                payload_data = self._migrations.migrate(
                    envelope.event_type, version, target_version, payload_data
                )
                version = target_version
            model = self._catalog.get_payload_model(envelope.event_type, version)
            payload = model.model_validate(payload_data)
        except (EventCatalogError, MissingMigrationPathError, ValueError) as error:
            from cognitive_os.infrastructure.errors import StoredEventDecodeError

            raise StoredEventDecodeError(
                f"cannot decode event {envelope.event_id}: {envelope.event_type} v{version}"
            ) from error
        return DecodedStoredEvent(stored_event=stored_event, payload=payload)

    def decode_stream(self, events: tuple[StoredEvent, ...]) -> tuple[DecodedStoredEvent, ...]:
        return tuple(self.decode_stored_event(event) for event in events)

    def decode_global_batch(
        self, events: tuple[StoredEvent, ...]
    ) -> tuple[DecodedStoredEvent, ...]:
        return self.decode_stream(events)
