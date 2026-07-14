"""Typed persistence and artifact failures."""

from __future__ import annotations

from uuid import UUID


class PersistenceError(RuntimeError):
    """Base class for durable infrastructure failures."""


class EventStoreUnavailableError(PersistenceError):
    """The configured event store cannot serve the request."""


class InvalidEventBatchError(PersistenceError, ValueError):
    """An event batch violates append invariants."""


class WrongExpectedVersionError(PersistenceError):
    def __init__(self, stream_id: UUID, expected_version: int, actual_version: int | None) -> None:
        self.stream_id = stream_id
        self.expected_version = expected_version
        self.actual_version = actual_version
        super().__init__(
            f"wrong expected version for stream {stream_id}: "
            f"expected {expected_version}, actual {actual_version}"
        )


class StreamTypeMismatchError(PersistenceError):
    def __init__(self, stream_id: UUID, expected_type: str, actual_type: str) -> None:
        self.stream_id = stream_id
        self.expected_type = expected_type
        self.actual_type = actual_type
        super().__init__(
            f"stream type mismatch for {stream_id}: expected {expected_type}, actual {actual_type}"
        )


class DuplicateEventError(PersistenceError):
    def __init__(self, event_id: UUID) -> None:
        self.event_id = event_id
        super().__init__(f"event ID already exists: {event_id}")


class EventIntegrityError(PersistenceError):
    """Stored event content failed its integrity check."""


class StoredEventDecodeError(PersistenceError):
    """A stored envelope cannot be decoded into a supported typed payload."""


class StreamGapError(PersistenceError):
    def __init__(self, expected_version: int, actual_version: int) -> None:
        self.expected_version = expected_version
        self.actual_version = actual_version
        super().__init__(f"stream gap: expected version {expected_version}, got {actual_version}")


class ArtifactStoreError(PersistenceError):
    """Base class for artifact-storage failures."""


class ArtifactNotFoundError(ArtifactStoreError, FileNotFoundError):
    """An artifact record or blob does not exist."""


class ArtifactIntegrityError(ArtifactStoreError):
    """Artifact bytes do not match their declared content address."""


class ArtifactTooLargeError(ArtifactStoreError):
    def __init__(self, maximum_size_bytes: int) -> None:
        self.maximum_size_bytes = maximum_size_bytes
        super().__init__(f"artifact exceeds {maximum_size_bytes} bytes")


class ArtifactMetadataError(ArtifactStoreError):
    """Artifact metadata could not be persisted or validated."""
