"""Atomic PostgreSQL adapter for governed memory state."""

from __future__ import annotations

from collections.abc import Mapping
from hashlib import sha256
from typing import Any
from uuid import UUID

from pydantic import TypeAdapter, ValidationError
from sqlalchemy import and_, cast, insert, literal, select, text
from sqlalchemy.engine import RowMapping
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncEngine

from cognitive_os.application.ports.memory_repository import MemoryRepositoryPort
from cognitive_os.domain.common import utc_now
from cognitive_os.domain.memory import (
    MemoryAccessKind,
    MemoryAccessRecord,
    MemoryContent,
    MemoryCreator,
    MemoryEmbeddingRecord,
    MemoryProvenanceBundle,
    MemoryQuery,
    MemoryQueryPage,
    MemoryQueryResult,
    MemoryRecord,
    MemoryRevision,
    MemoryScope,
    MemorySourceIdentity,
    MemorySourceRef,
    MemoryWriteRequest,
    memory_revision_hash,
)
from cognitive_os.infrastructure.postgres.engine import postgres_transaction
from cognitive_os.memory.errors import MemoryConcurrencyError, MemoryIntegrityError
from cognitive_os.memory.governance import sensitivity_allows

from .statements import current_memory_statement
from .tables import (
    memory_accesses,
    memory_embeddings,
    memory_items,
    memory_revisions,
    memory_sources,
)

CONTENT_ADAPTER: TypeAdapter[MemoryContent] = TypeAdapter(MemoryContent)


def _revision_values(revision: MemoryRevision) -> dict[str, Any]:
    search_text = revision.content.render_search_text().encode()[:32_768].decode(errors="ignore")
    return {
        "memory_id": revision.memory_id,
        "revision": revision.revision,
        "previous_revision": revision.previous_revision,
        "content_json": revision.content.model_dump(mode="json"),
        "content_artifact_id": (
            revision.content_artifact.artifact_id if revision.content_artifact else None
        ),
        "content_hash": revision.content_hash,
        "search_text": search_text,
        "status": revision.status.value,
        "confidence": revision.confidence,
        "salience": revision.salience,
        "sensitivity": revision.sensitivity.value,
        "reason": revision.reason.value,
        "created_at": revision.created_at,
        "created_by_type": revision.created_by.creator_type.value,
        "created_by_id": revision.created_by.creator_id,
        "expires_at": revision.expires_at,
        "successor_memory_id": revision.successor_memory_id,
    }


def _source_values(
    memory_id: UUID, revision: int, source: MemorySourceRef, order: int
) -> dict[str, Any]:
    identity = source.identity
    return {
        "memory_id": memory_id,
        "revision": revision,
        "source_order": order,
        "source_type": identity.source_type.value,
        "source_id": identity.source_id,
        "source_memory_id": identity.memory_id,
        "source_memory_revision": identity.revision,
        "source_hash": source.source_hash,
        "relationship": source.relationship,
    }


def _row_to_revision(row: Mapping[Any, Any]) -> MemoryRevision:
    try:
        content = CONTENT_ADAPTER.validate_python(row["content_json"])
        return MemoryRevision(
            memory_id=row["memory_id"],
            revision=row["revision"],
            previous_revision=row["previous_revision"],
            content=content,
            content_artifact=None,
            content_hash=row["content_hash"],
            status=row["status"],
            confidence=row["confidence"],
            salience=row["salience"],
            sensitivity=row["sensitivity"],
            reason=row["reason"],
            created_at=row["created_at"],
            created_by=MemoryCreator(
                creator_type=row["created_by_type"], creator_id=row["created_by_id"]
            ),
            expires_at=row["expires_at"],
            successor_memory_id=row["successor_memory_id"],
        )
    except (ValidationError, ValueError, KeyError) as error:
        raise MemoryIntegrityError("stored memory revision failed validation") from error


class PostgresMemoryRepository(MemoryRepositoryPort):
    def __init__(self, engine: AsyncEngine) -> None:
        self._engine = engine

    async def create_memory(
        self, request: MemoryWriteRequest
    ) -> tuple[MemoryRecord, MemoryRevision]:
        async with self._engine.connect() as connection:
            existing_id = await connection.scalar(
                select(memory_items.c.memory_id).where(
                    memory_items.c.idempotency_key == request.idempotency_key
                )
            )
        if existing_id is not None:
            existing = await self.get_current(existing_id)
            if existing is None:
                raise MemoryIntegrityError("idempotency identity has no current memory")
            return existing
        now = utc_now()
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
            created_at=now,
            created_by=request.actor,
        )
        record = MemoryRecord(
            memory_id=request.memory_id,
            memory_type=request.memory_type,
            scope=request.scope,
            status=request.status,
            current_revision=1,
            title=request.title,
            created_at=now,
            created_by=request.actor,
        )
        try:
            async with postgres_transaction(self._engine) as connection:
                await connection.execute(
                    insert(memory_items).values(
                        memory_id=record.memory_id,
                        idempotency_key=request.idempotency_key,
                        memory_type=record.memory_type.value,
                        scope_type=record.scope.scope_type.value,
                        scope_id=record.scope.scope_id,
                        status=record.status.value,
                        current_revision=1,
                        title=record.title,
                        created_at=record.created_at,
                        created_by_type=record.created_by.creator_type.value,
                        created_by_id=record.created_by.creator_id,
                    )
                )
                await connection.execute(
                    insert(memory_revisions).values(**_revision_values(revision))
                )
                await connection.execute(
                    insert(memory_sources),
                    [
                        _source_values(record.memory_id, 1, source, order)
                        for order, source in enumerate(request.provenance.sources)
                    ],
                )
            return record, revision
        except IntegrityError as error:
            raise MemoryConcurrencyError("memory identity already exists") from error
        except SQLAlchemyError as error:
            raise MemoryIntegrityError("PostgreSQL memory creation failed") from error

    async def append_revision(
        self,
        revision: MemoryRevision,
        provenance: MemoryProvenanceBundle,
        *,
        expected_revision: int,
    ) -> MemoryRevision:
        try:
            async with postgres_transaction(self._engine) as connection:
                await connection.execute(
                    insert(memory_revisions).values(**_revision_values(revision))
                )
                await connection.execute(
                    insert(memory_sources),
                    [
                        _source_values(revision.memory_id, revision.revision, source, order)
                        for order, source in enumerate(provenance.sources)
                    ],
                )
                advanced = await connection.scalar(
                    text(
                        "SELECT cognitive_os.advance_memory_item("
                        ":memory_id, :expected_revision, :next_revision, :next_status)"
                    ),
                    {
                        "memory_id": revision.memory_id,
                        "expected_revision": expected_revision,
                        "next_revision": revision.revision,
                        "next_status": revision.status.value,
                    },
                )
                if not advanced:
                    raise MemoryConcurrencyError("stale expected memory revision")
            return revision
        except MemoryConcurrencyError:
            raise
        except IntegrityError as error:
            raise MemoryConcurrencyError("memory revision conflict") from error
        except SQLAlchemyError as error:
            raise MemoryIntegrityError("PostgreSQL memory revision failed") from error

    async def get_current(self, memory_id: UUID) -> tuple[MemoryRecord, MemoryRevision] | None:
        async with self._engine.connect() as connection:
            item_row = (
                (
                    await connection.execute(
                        select(memory_items).where(memory_items.c.memory_id == memory_id)
                    )
                )
                .mappings()
                .one_or_none()
            )
            if item_row is None:
                return None
            revision_row = (
                (
                    await connection.execute(
                        select(memory_revisions).where(
                            and_(
                                memory_revisions.c.memory_id == memory_id,
                                memory_revisions.c.revision == item_row["current_revision"],
                            )
                        )
                    )
                )
                .mappings()
                .one_or_none()
            )
        if revision_row is None:
            raise MemoryIntegrityError("current projection references a missing revision")
        revision = _row_to_revision(revision_row)
        record = MemoryRecord(
            memory_id=item_row["memory_id"],
            memory_type=item_row["memory_type"],
            scope=MemoryScope(scope_type=item_row["scope_type"], scope_id=item_row["scope_id"]),
            status=item_row["status"],
            current_revision=item_row["current_revision"],
            title=item_row["title"],
            created_at=item_row["created_at"],
            created_by=MemoryCreator(
                creator_type=item_row["created_by_type"],
                creator_id=item_row["created_by_id"],
            ),
        )
        if record.status is not revision.status:
            raise MemoryIntegrityError("current projection status mismatch")
        return record, revision

    async def get_revision(self, memory_id: UUID, revision: int) -> MemoryRevision | None:
        async with self._engine.connect() as connection:
            row = (
                (
                    await connection.execute(
                        select(memory_revisions).where(
                            and_(
                                memory_revisions.c.memory_id == memory_id,
                                memory_revisions.c.revision == revision,
                            )
                        )
                    )
                )
                .mappings()
                .one_or_none()
            )
        return _row_to_revision(row) if row is not None else None

    async def list_revisions(
        self, memory_id: UUID, *, limit: int = 100
    ) -> tuple[MemoryRevision, ...]:
        if limit < 1 or limit > 1000:
            raise ValueError("revision limit must be between 1 and 1000")
        async with self._engine.connect() as connection:
            rows = (
                (
                    await connection.execute(
                        select(memory_revisions)
                        .where(memory_revisions.c.memory_id == memory_id)
                        .order_by(memory_revisions.c.revision)
                        .limit(limit)
                    )
                )
                .mappings()
                .all()
            )
        return tuple(_row_to_revision(row) for row in rows)

    async def list_sources(
        self, memory_id: UUID, revision: int, *, limit: int = 64
    ) -> tuple[MemorySourceRef, ...]:
        if limit < 1 or limit > 64:
            raise ValueError("source limit must be between 1 and 64")
        async with self._engine.connect() as connection:
            rows = (
                (
                    await connection.execute(
                        select(memory_sources)
                        .where(
                            and_(
                                memory_sources.c.memory_id == memory_id,
                                memory_sources.c.revision == revision,
                            )
                        )
                        .order_by(memory_sources.c.source_order)
                        .limit(limit)
                    )
                )
                .mappings()
                .all()
            )
        return tuple(
            MemorySourceRef(
                identity=MemorySourceIdentity(
                    source_type=row["source_type"],
                    source_id=row["source_id"],
                    memory_id=row["source_memory_id"],
                    revision=row["source_memory_revision"],
                    content_hash=row["source_hash"],
                ),
                source_hash=row["source_hash"],
                relationship=row["relationship"],
            )
            for row in rows
        )

    async def search(self, query: MemoryQuery) -> MemoryQueryPage:
        vector_mode = query.vector is not None
        if vector_mode:
            if query.vector is None:
                raise ValueError("vector retrieval requires a vector query")
            vector_literal = "[" + ",".join(str(value) for value in query.vector.vector) + "]"
            distance = memory_embeddings.c.embedding.op("<=>")(
                cast(literal(vector_literal), memory_embeddings.c.embedding.type)
            )
            statement = (
                select(memory_items, memory_revisions, (1.0 - distance).label("vector_score"))
                .join(
                    memory_revisions,
                    and_(
                        memory_revisions.c.memory_id == memory_items.c.memory_id,
                        memory_revisions.c.revision == memory_items.c.current_revision,
                    ),
                )
                .join(
                    memory_embeddings,
                    and_(
                        memory_embeddings.c.memory_id == memory_revisions.c.memory_id,
                        memory_embeddings.c.revision == memory_revisions.c.revision,
                        memory_embeddings.c.content_hash == memory_revisions.c.content_hash,
                    ),
                )
                .where(
                    memory_embeddings.c.provider_id == query.vector.provider_id,
                    memory_embeddings.c.model_id == query.vector.model_id,
                    memory_embeddings.c.dimension == query.vector.dimension,
                    memory_items.c.status.in_([status.value for status in query.filters.statuses]),
                )
                .order_by(distance, memory_items.c.memory_id)
                .limit(query.budget.maximum_candidates)
            )
        else:
            statement = current_memory_statement(query)
        async with self._engine.connect() as connection:
            rows = (await connection.execute(statement)).mappings().all()
        scored: list[tuple[RowMapping, float]] = []
        for row in rows:
            revision = _row_to_revision(row)
            if not sensitivity_allows(revision.sensitivity, query.filters.sensitivity_ceiling):
                continue
            score = float(row["vector_score"]) if vector_mode else 1.0
            if not vector_mode and query.text is not None:
                score = float(
                    sum(
                        revision.content.render_search_text().casefold().count(term)
                        for term in query.text.text.casefold().split()
                    )
                )
            scored.append((row, score))
        scored.sort(key=lambda item: (-item[1], str(item[0]["memory_id"])))
        results = []
        for rank, (search_row, score) in enumerate(scored[: query.budget.maximum_results], start=1):
            sources = await self.list_sources(search_row["memory_id"], search_row["revision"])
            results.append(
                MemoryQueryResult(
                    memory_id=search_row["memory_id"],
                    revision=search_row["revision"],
                    title=search_row["title"],
                    score=score,
                    rank=rank,
                    scope=MemoryScope(
                        scope_type=search_row["scope_type"],
                        scope_id=search_row["scope_id"],
                    ),
                    status=search_row["status"],
                    sensitivity=search_row["sensitivity"],
                    provenance_summary=tuple(source.identity for source in sources),
                )
            )
        snapshot_hash = sha256(
            "|".join(f"{item.memory_id}:{item.revision}:{item.score}" for item in results).encode()
        ).hexdigest()
        return MemoryQueryPage(
            query_id=query.query_id,
            results=tuple(results),
            snapshot_hash=snapshot_hash,
        )

    async def record_access(self, records: tuple[MemoryAccessRecord, ...]) -> None:
        if not records:
            return
        values = [
            {
                "access_id": record.access_id,
                "query_id": record.query_id,
                "task_run_id": record.task_run_id,
                "memory_id": record.memory_id,
                "revision": record.revision,
                "retrieval_mode": record.retrieval_mode.value,
                "retrieval_rank": record.retrieval_rank,
                "retrieval_score": record.retrieval_score,
                "accessed_at": record.accessed_at,
                "used_in_context": int(record.access_kind is MemoryAccessKind.USED_IN_CONTEXT),
                "scope_type": record.scope.scope_type.value,
                "scope_id": record.scope.scope_id,
                "sensitivity": record.sensitivity.value,
                "query_hash": record.query_hash,
                "filter_hash": record.filter_hash,
            }
            for record in records
        ]
        async with postgres_transaction(self._engine) as connection:
            await connection.execute(insert(memory_accesses), values)

    async def record_embedding(self, embedding: MemoryEmbeddingRecord) -> None:
        vector_value = "[" + ",".join(str(value) for value in embedding.vector) + "]"
        statement = text(
            """
            INSERT INTO cognitive_os.memory_embeddings (
                embedding_id, memory_id, revision, provider_id, model_id,
                dimension, content_hash, embedding, created_at
            ) VALUES (
                :embedding_id, :memory_id, :revision, :provider_id, :model_id,
                :dimension, :content_hash, CAST(:embedding AS vector), :created_at
            )
            ON CONFLICT (memory_id, revision, provider_id, model_id, content_hash)
            DO NOTHING
            """
        )
        try:
            async with postgres_transaction(self._engine) as connection:
                await connection.execute(
                    statement,
                    {
                        "embedding_id": embedding.embedding_id,
                        "memory_id": embedding.memory_id,
                        "revision": embedding.revision,
                        "provider_id": embedding.provider_id,
                        "model_id": embedding.model_id,
                        "dimension": embedding.dimension,
                        "content_hash": embedding.content_hash,
                        "embedding": vector_value,
                        "created_at": embedding.created_at,
                    },
                )
        except IntegrityError as error:
            raise MemoryIntegrityError("embedding integrity constraint failed") from error
