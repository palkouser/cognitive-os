"""Cognitive OS deterministic JSON serialization."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from cognitive_os.domain.common import JsonValue

if TYPE_CHECKING:
    from .base import EventEnvelope


def canonical_json_bytes(value: JsonValue) -> bytes:
    """Encode JSON with stable key ordering and no insignificant whitespace."""
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def serialize_envelope(envelope: EventEnvelope) -> bytes:
    return canonical_json_bytes(envelope.model_dump(mode="json"))


def deserialize_envelope(data: bytes) -> EventEnvelope:
    from .base import EventEnvelope

    return EventEnvelope.model_validate_json(data)
