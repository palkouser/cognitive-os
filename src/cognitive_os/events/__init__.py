"""Public Cognitive OS event contracts."""

from .base import EventEnvelope, EventPayload, create_event_envelope
from .catalog import (
    EventCatalog,
    UnknownEventTypeError,
    UnsupportedSchemaVersionError,
    build_default_event_catalog,
)
from .hashing import sha256_digest
from .migrations import MigrationRegistry, MissingMigrationPathError
from .serialization import canonical_json_bytes, deserialize_envelope, serialize_envelope

__all__ = [
    "EventCatalog",
    "EventEnvelope",
    "EventPayload",
    "MigrationRegistry",
    "MissingMigrationPathError",
    "UnknownEventTypeError",
    "UnsupportedSchemaVersionError",
    "build_default_event_catalog",
    "canonical_json_bytes",
    "create_event_envelope",
    "deserialize_envelope",
    "serialize_envelope",
    "sha256_digest",
]
