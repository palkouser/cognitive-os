"""Deterministic in-memory repository used by core tests and narrow adapters."""

from __future__ import annotations

import math
from hashlib import sha256
from uuid import UUID

from cognitive_os.application.ports.memory_repository import MemoryRepositoryPort
from cognitive_os.domain.common import utc_now
from cognitive_os.domain.memory import (
    MemoryAccessRecord,
    MemoryEmbeddingRecord,
    MemoryProvenanceBundle,
    MemoryQuery,
    MemoryQueryPage,
    MemoryQueryResult,
    MemoryRecord,
    MemoryRetrievalMode,
    MemoryRevision,
    MemorySourceRef,
    MemoryWriteRequest,
    memory_revision_hash,
)

from .errors import MemoryConcurrencyError, MemoryIntegrityError
from .governance import sensitivity_allows


class InMemoryMemoryRepository(MemoryRepositoryPort):
    """Bounded reference implementation; not a production persistence authority."""

    def __init__(self) -> None:
        self.records: dict[UUID, MemoryRecord] = {}
        self.revisions: dict[UUID, list[MemoryRevision]] = {}
        self.sources: dict[tuple[UUID, int], tuple[MemorySourceRef, ...]] = {}
        self.idempotency: dict[str, UUID] = {}
        self.accesses: list[MemoryAccessRecord] = []
        self.embeddings: dict[tuple[UUID, int, str, str, str], MemoryEmbeddingRecord] = {}

    async def create_memory(
        self, request: MemoryWriteRequest
    ) -> tuple[MemoryRecord, MemoryRevision]:
        existing_id = self.idempotency.get(request.idempotency_key)
        if existing_id is not None:
            return await self.get_current(existing_id)  # type: ignore[return-value]
        if request.memory_id in self.records:
            raise MemoryConcurrencyError("memory identity already exists")
        revision = MemoryRevision(
            memory_id=request.memory_id,
            revision=1,
            content=request.content,
            content_hash=memory_revision_hash(
                memory_id=request.memory_id,
                revision=1,
                content=request.content,
                status=request.status,
                confidence=request.confidence,
                salience=request.salience,
                sensitivity=request.sensitivity,
            ),
            status=request.status,
            confidence=request.confidence,
            salience=request.salience,
            sensitivity=request.sensitivity,
            reason=request.reason,
            created_at=utc_now(),
            created_by=request.actor,
        )
        record = MemoryRecord(
            memory_id=request.memory_id,
            memory_type=request.memory_type,
            scope=request.scope,
            status=request.status,
            current_revision=1,
            title=request.title,
            created_at=revision.created_at,
            created_by=request.actor,
        )
        self.records[request.memory_id] = record
        self.revisions[request.memory_id] = [revision]
        self.sources[(request.memory_id, 1)] = request.provenance.sources
        self.idempotency[request.idempotency_key] = request.memory_id
        return record, revision

    async def append_revision(
        self,
        revision: MemoryRevision,
        provenance: MemoryProvenanceBundle,
        *,
        expected_revision: int,
    ) -> MemoryRevision:
        current = self.records.get(revision.memory_id)
        if current is None or current.current_revision != expected_revision:
            raise MemoryConcurrencyError("stale expected memory revision")
        if revision.revision != expected_revision + 1:
            raise MemoryConcurrencyError("next revision must increment exactly once")
        previous_sources = self.sources[(revision.memory_id, expected_revision)]
        previous_keys = {source.identity.sort_key() for source in previous_sources}
        next_keys = {source.identity.sort_key() for source in provenance.sources}
        if not previous_keys <= next_keys:
            raise MemoryIntegrityError("revision provenance cannot remove an existing source")
        self.revisions[revision.memory_id].append(revision)
        self.sources[(revision.memory_id, revision.revision)] = provenance.sources
        self.records[revision.memory_id] = current.model_copy(
            update={"current_revision": revision.revision, "status": revision.status}
        )
        return revision

    async def get_current(self, memory_id: UUID) -> tuple[MemoryRecord, MemoryRevision] | None:
        record = self.records.get(memory_id)
        if record is None:
            return None
        return record, self.revisions[memory_id][-1]

    async def get_revision(self, memory_id: UUID, revision: int) -> MemoryRevision | None:
        values = self.revisions.get(memory_id, ())
        return next((value for value in values if value.revision == revision), None)

    async def list_revisions(
        self, memory_id: UUID, *, limit: int = 100
    ) -> tuple[MemoryRevision, ...]:
        if limit < 1 or limit > 1000:
            raise ValueError("revision limit must be between 1 and 1000")
        return tuple(self.revisions.get(memory_id, ()))[:limit]

    async def list_sources(
        self, memory_id: UUID, revision: int, *, limit: int = 64
    ) -> tuple[MemorySourceRef, ...]:
        if limit < 1 or limit > 64:
            raise ValueError("source limit must be between 1 and 64")
        return self.sources.get((memory_id, revision), ())[:limit]

    async def search(self, query: MemoryQuery) -> MemoryQueryPage:
        candidates: list[tuple[MemoryRecord, MemoryRevision, float]] = []
        allowed_statuses = query.filters.statuses
        for memory_id in sorted(self.records, key=str):
            record = self.records[memory_id]
            revision = self.revisions[memory_id][-1]
            if revision.status not in allowed_statuses:
                continue
            if not sensitivity_allows(revision.sensitivity, query.filters.sensitivity_ceiling):
                continue
            if query.filters.memory_types and record.memory_type not in query.filters.memory_types:
                continue
            if query.filters.scopes and record.scope not in query.filters.scopes:
                continue
            if query.mode is MemoryRetrievalMode.TEXT:
                if query.text is None:
                    raise ValueError("text retrieval requires a text query")
                haystack = (record.title + "\n" + revision.content.render_search_text()).casefold()
                terms = query.text.text.casefold().split()
                score = sum(haystack.count(term) for term in terms) / max(len(terms), 1)
                if score == 0:
                    continue
            elif query.mode is MemoryRetrievalMode.VECTOR:
                if query.vector is None:
                    raise ValueError("vector retrieval requires a vector query")
                key_prefix = (
                    record.memory_id,
                    revision.revision,
                    query.vector.provider_id,
                    query.vector.model_id,
                    revision.content_hash,
                )
                embedding = self.embeddings.get(key_prefix)
                if embedding is None or embedding.dimension != query.vector.dimension:
                    continue
                dot = sum(
                    left * right
                    for left, right in zip(embedding.vector, query.vector.vector, strict=True)
                )
                left_norm = math.sqrt(sum(value * value for value in embedding.vector))
                right_norm = math.sqrt(sum(value * value for value in query.vector.vector))
                if left_norm == 0 or right_norm == 0:
                    continue
                score = max(0.0, dot / (left_norm * right_norm))
            else:
                score = 1.0
            candidates.append((record, revision, float(score)))
        candidates.sort(key=lambda item: (-item[2], str(item[0].memory_id), -item[1].revision))
        results = tuple(
            MemoryQueryResult(
                memory_id=record.memory_id,
                revision=revision.revision,
                title=record.title,
                score=score,
                rank=rank,
                scope=record.scope,
                status=revision.status,
                sensitivity=revision.sensitivity,
                provenance_summary=tuple(
                    source.identity
                    for source in self.sources[(record.memory_id, revision.revision)]
                ),
            )
            for rank, (record, revision, score) in enumerate(
                candidates[: query.budget.maximum_results], start=1
            )
        )
        snapshot = sha256(
            "|".join(f"{item.memory_id}:{item.revision}:{item.score}" for item in results).encode()
        ).hexdigest()
        return MemoryQueryPage(query_id=query.query_id, results=results, snapshot_hash=snapshot)

    async def record_access(self, records: tuple[MemoryAccessRecord, ...]) -> None:
        self.accesses.extend(records)

    async def record_embedding(self, embedding: MemoryEmbeddingRecord) -> None:
        revision = await self.get_revision(embedding.memory_id, embedding.revision)
        if revision is None or revision.content_hash != embedding.content_hash:
            raise MemoryIntegrityError("embedding content hash does not match memory revision")
        key = (
            embedding.memory_id,
            embedding.revision,
            embedding.provider_id,
            embedding.model_id,
            embedding.content_hash,
        )
        self.embeddings.setdefault(key, embedding)
