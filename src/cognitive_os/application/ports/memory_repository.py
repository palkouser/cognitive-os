"""Persistence-neutral repository boundary for governed memory."""

from __future__ import annotations

from typing import Protocol
from uuid import UUID

from cognitive_os.domain.memory import (
    MemoryAccessRecord,
    MemoryEmbeddingRecord,
    MemoryProvenanceBundle,
    MemoryQuery,
    MemoryQueryPage,
    MemoryRecord,
    MemoryRevision,
    MemorySourceRef,
    MemoryWriteRequest,
)


class MemoryRepositoryPort(Protocol):
    async def create_memory(
        self, request: MemoryWriteRequest
    ) -> tuple[MemoryRecord, MemoryRevision]: ...

    async def append_revision(
        self,
        revision: MemoryRevision,
        provenance: MemoryProvenanceBundle,
        *,
        expected_revision: int,
    ) -> MemoryRevision: ...

    async def get_current(self, memory_id: UUID) -> tuple[MemoryRecord, MemoryRevision] | None: ...

    async def get_revision(self, memory_id: UUID, revision: int) -> MemoryRevision | None: ...

    async def list_revisions(
        self, memory_id: UUID, *, limit: int = 100
    ) -> tuple[MemoryRevision, ...]: ...

    async def list_sources(
        self, memory_id: UUID, revision: int, *, limit: int = 64
    ) -> tuple[MemorySourceRef, ...]: ...

    async def search(self, query: MemoryQuery) -> MemoryQueryPage: ...

    async def record_access(self, records: tuple[MemoryAccessRecord, ...]) -> None: ...

    async def record_embedding(self, embedding: MemoryEmbeddingRecord) -> None: ...
