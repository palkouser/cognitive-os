"""Exact, non-executing source resolution for semantic observations and evidence."""

import json
from hashlib import sha256
from typing import Any

from cognitive_os.application.ports.artifact_store import ArtifactStorePort
from cognitive_os.application.ports.event_store import EventStorePort
from cognitive_os.application.ports.memory_repository import MemoryRepositoryPort
from cognitive_os.domain.memory import MemoryScope, MemorySensitivity, MemoryStatus
from cognitive_os.domain.semantic_memory import (
    GroundedSourceSpan,
    GroundingMode,
    SemanticSourceType,
)

from .errors import SemanticIntegrityError


class TrustedSourceResolver:
    def __init__(
        self,
        memory: MemoryRepositoryPort,
        *,
        artifacts: ArtifactStorePort | None = None,
        events: EventStorePort | None = None,
        maximum_excerpt_bytes: int = 16_384,
    ) -> None:
        self._memory = memory
        self._artifacts = artifacts
        self._events = events
        self._maximum_excerpt_bytes = maximum_excerpt_bytes

    async def validate_span(
        self,
        span: GroundedSourceSpan,
        *,
        scope: MemoryScope | None = None,
        sensitivity: MemorySensitivity | None = None,
    ) -> None:
        await self.resolve_span(span, scope=scope, sensitivity=sensitivity)

    async def resolve_span(
        self,
        span: GroundedSourceSpan,
        *,
        scope: MemoryScope | None = None,
        sensitivity: MemorySensitivity | None = None,
    ) -> bytes:
        source = span.source
        if source.source_type is SemanticSourceType.MEMORY_REVISION:
            if source.revision is None:
                raise SemanticIntegrityError("memory source revision is missing")
            revision = await self._memory.get_revision(source.source_id, source.revision)
            current = await self._memory.get_current(source.source_id)
            if revision is None or revision.content_hash != source.content_hash:
                raise SemanticIntegrityError("memory source revision hash mismatch")
            if current is None or current[0].status is MemoryStatus.RETRACTED:
                raise SemanticIntegrityError("semantic source memory is missing or retracted")
            if scope is not None and current[0].scope != scope:
                raise SemanticIntegrityError("semantic source scope is not authorized")
            if (
                sensitivity is not None
                and _SENSITIVITY_ORDER[revision.sensitivity] > _SENSITIVITY_ORDER[sensitivity]
            ):
                raise SemanticIntegrityError("semantic source sensitivity exceeds the target")
            return self._resolve_field(span, revision.model_dump(mode="json"))
        if source.source_type is SemanticSourceType.ARTIFACT:
            if self._artifacts is None or not await self._artifacts.verify(source.source_id):
                raise SemanticIntegrityError("artifact source is unavailable or corrupt")
            data = await self._artifacts.get_bytes(source.source_id)
            if sha256(data).hexdigest() != source.content_hash:
                raise SemanticIntegrityError("artifact source hash mismatch")
            return self._resolve_bytes(span, data)
        if source.source_type is SemanticSourceType.EVENT:
            if self._events is None:
                raise SemanticIntegrityError("event source resolver is unavailable")
            stored = await self._events.get_event(source.source_id)
            if stored is None or stored.envelope.payload_hash != source.content_hash:
                raise SemanticIntegrityError("event source hash mismatch")
            return self._resolve_field(span, stored.envelope.payload)
        raise SemanticIntegrityError("source type has no authoritative resolver")

    def _resolve_field(self, span: GroundedSourceSpan, value: Any) -> bytes:
        if (
            span.mode
            not in {
                GroundingMode.TYPED_FIELD,
                GroundingMode.EVENT_FIELD,
                GroundingMode.MEMORY_FIELD,
            }
            or not span.path
        ):
            raise SemanticIntegrityError("field source requires exact field grounding")
        current = value
        for part in span.path.split("."):
            if not isinstance(current, dict) or part not in current:
                raise SemanticIntegrityError("grounded source field does not exist")
            current = current[part]
        encoded = (
            current.encode()
            if isinstance(current, str)
            else json.dumps(current, sort_keys=True, separators=(",", ":")).encode()
        )
        self._check_excerpt(span, encoded)
        return encoded

    def _resolve_bytes(self, span: GroundedSourceSpan, data: bytes) -> bytes:
        if span.start is None or span.end is None:
            raise SemanticIntegrityError("artifact grounding requires an exact range")
        if span.mode is GroundingMode.ARTIFACT_BYTES:
            if span.end > len(data):
                raise SemanticIntegrityError("artifact byte range is out of bounds")
            excerpt = data[span.start : span.end]
        elif span.mode is GroundingMode.LINE_RANGE:
            lines = data.splitlines(keepends=True)
            if span.end > len(lines):
                raise SemanticIntegrityError("artifact line range is out of bounds")
            excerpt = b"".join(lines[span.start : span.end])
        else:
            raise SemanticIntegrityError("artifact source requires byte or line grounding")
        self._check_excerpt(span, excerpt)
        return excerpt

    def _check_excerpt(self, span: GroundedSourceSpan, excerpt: bytes) -> None:
        if len(excerpt) > self._maximum_excerpt_bytes:
            raise SemanticIntegrityError("grounded source excerpt exceeds the host limit")
        if sha256(excerpt).hexdigest() != span.excerpt_hash:
            raise SemanticIntegrityError("grounded source excerpt hash mismatch")


_SENSITIVITY_ORDER = {
    MemorySensitivity.PUBLIC: 0,
    MemorySensitivity.INTERNAL: 1,
    MemorySensitivity.CONFIDENTIAL: 2,
    MemorySensitivity.RESTRICTED: 3,
}
