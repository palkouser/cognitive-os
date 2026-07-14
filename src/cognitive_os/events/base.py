"""Typed event payload and stored-envelope contracts."""

from __future__ import annotations

import re
from typing import ClassVar
from uuid import UUID

from pydantic import Field, field_validator, model_validator

from cognitive_os.domain.base import ImmutableContractModel
from cognitive_os.domain.common import ActorRef, JsonValue, Sha256Hex, UtcDatetime, utc_now
from cognitive_os.domain.enums import PrivacyClass, StreamType
from cognitive_os.domain.identifiers import EventId, new_id

from .hashing import sha256_digest

EVENT_TYPE_PATTERN = re.compile(r"^[a-z][a-z0-9_]*(?:\.[a-z][a-z0-9_]*)+$")
COMPONENT_PATTERN = re.compile(r"^[a-z][a-z0-9]*(?:[-_.][a-z0-9]+)*$")


class EventPayload(ImmutableContractModel):
    """Base for typed payloads with class-level event metadata."""

    event_type: ClassVar[str]
    schema_version: ClassVar[int] = 1

    def to_payload(self) -> dict[str, JsonValue]:
        return self.model_dump(mode="json")


class EventEnvelope(ImmutableContractModel):
    event_id: EventId
    event_type: str
    schema_version: int = Field(ge=1)
    occurred_at: UtcDatetime
    recorded_at: UtcDatetime
    stream_id: UUID
    stream_type: StreamType
    stream_version: int = Field(ge=1)
    correlation_id: UUID
    causation_event_id: EventId | None = None
    actor: ActorRef
    source_component: str
    payload: dict[str, JsonValue]
    payload_hash: Sha256Hex
    privacy_class: PrivacyClass

    @field_validator("event_type")
    @classmethod
    def validate_event_type(cls, value: str) -> str:
        if not EVENT_TYPE_PATTERN.fullmatch(value):
            raise ValueError("event_type must be a lowercase dotted name")
        return value

    @field_validator("source_component")
    @classmethod
    def validate_source_component(cls, value: str) -> str:
        if not COMPONENT_PATTERN.fullmatch(value):
            raise ValueError("source_component must be a stable lowercase identifier")
        return value

    @field_validator("payload", mode="before")
    @classmethod
    def copy_payload(cls, value: object) -> object:
        return dict(value) if isinstance(value, dict) else value

    @model_validator(mode="after")
    def validate_envelope(self) -> EventEnvelope:
        if self.recorded_at < self.occurred_at:
            raise ValueError("recorded_at cannot be earlier than occurred_at")
        if sha256_digest(self.payload) != self.payload_hash:
            raise ValueError("payload hash mismatch")
        return self


def create_event_envelope(
    *,
    payload: EventPayload,
    stream_id: UUID,
    stream_type: StreamType,
    stream_version: int,
    correlation_id: UUID,
    causation_event_id: UUID | None,
    actor: ActorRef,
    source_component: str,
    privacy_class: PrivacyClass,
    occurred_at: UtcDatetime | None = None,
    recorded_at: UtcDatetime | None = None,
) -> EventEnvelope:
    occurred = occurred_at or utc_now()
    recorded = recorded_at or occurred
    encoded_payload = payload.to_payload()
    return EventEnvelope(
        event_id=new_id(),
        event_type=payload.event_type,
        schema_version=payload.schema_version,
        occurred_at=occurred,
        recorded_at=recorded,
        stream_id=stream_id,
        stream_type=stream_type,
        stream_version=stream_version,
        correlation_id=correlation_id,
        causation_event_id=causation_event_id,
        actor=actor,
        source_component=source_component,
        payload=encoded_payload,
        payload_hash=sha256_digest(encoded_payload),
        privacy_class=privacy_class,
    )
