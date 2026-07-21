"""Transactional PostgreSQL repository for Corpus Factory metadata."""

from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncEngine

from cognitive_os.application.ports.corpus_repository import CorpusRepositoryPort
from cognitive_os.corpus.errors import CorpusConflictError
from cognitive_os.domain.corpus import (
    CorpusAccessRecord,
    CorpusClassification,
    CorpusExportManifest,
    CorpusItem,
    CorpusManifest,
    CorpusRouteDecision,
    CorpusStatusTransition,
    SourceManifest,
)
from cognitive_os.infrastructure.postgres.engine import postgres_transaction

from .tables import (
    corpus_accesses,
    corpus_classifications,
    corpus_exports,
    corpus_item_sources,
    corpus_items,
    corpus_manifest_items,
    corpus_manifests,
    corpus_route_decisions,
    corpus_sources,
)


class PostgresCorpusRepository(CorpusRepositoryPort):
    def __init__(self, engine: AsyncEngine) -> None:
        self._engine = engine

    async def register_source(self, source: SourceManifest) -> None:
        values = dict(
            source_manifest_id=source.source_manifest_id,
            source_type=source.source_type.value,
            source_identity=source.source_identity,
            source_revision=source.source_revision,
            source_hash=source.content_hash,
            payload_json=source.model_dump(mode="json"),
            created_at=source.created_at,
        )
        async with postgres_transaction(self._engine) as connection:
            await connection.execute(
                pg_insert(corpus_sources).values(**values).on_conflict_do_nothing()
            )
        existing = await self.get_source_by_identity(source.source_identity, source.source_revision)
        if existing != source:
            raise CorpusConflictError("corpus source idempotency conflict")

    async def get_source(self, source_manifest_id: UUID) -> SourceManifest | None:
        statement = select(corpus_sources.c.payload_json).where(
            corpus_sources.c.source_manifest_id == source_manifest_id
        )
        async with self._engine.connect() as connection:
            payload = await connection.scalar(statement)
        return SourceManifest.model_validate(payload) if payload else None

    async def get_source_by_identity(self, identity: str, revision: str) -> SourceManifest | None:
        statement = select(corpus_sources.c.payload_json).where(
            corpus_sources.c.source_identity == identity,
            corpus_sources.c.source_revision == revision,
        )
        async with self._engine.connect() as connection:
            payload = await connection.scalar(statement)
        return SourceManifest.model_validate(payload) if payload else None

    async def create_item(self, item: CorpusItem) -> None:
        values = dict(
            corpus_item_id=item.corpus_item_id,
            current_revision=item.current_revision,
            current_status=item.current_status.value,
            canonical_content_hash=item.canonical_content_hash,
            item_hash=item.content_hash,
            scope=item.scope,
            sensitivity=item.sensitivity.value,
            payload_json=item.model_dump(mode="json"),
            status_actor=item.created_by,
            status_reason="received",
            created_at=item.created_at,
        )
        async with postgres_transaction(self._engine) as connection:
            await connection.execute(
                pg_insert(corpus_items).values(**values).on_conflict_do_nothing()
            )
        if await self.get_item(item.corpus_item_id) != item:
            raise CorpusConflictError("corpus item idempotency conflict")

    async def get_item(self, corpus_item_id: UUID) -> CorpusItem | None:
        statement = select(corpus_items.c.payload_json).where(
            corpus_items.c.corpus_item_id == corpus_item_id
        )
        async with self._engine.connect() as connection:
            payload = await connection.scalar(statement)
        return CorpusItem.model_validate(payload) if payload else None

    async def query_by_content_hash(
        self, content_hash: str, *, limit: int = 100
    ) -> tuple[CorpusItem, ...]:
        statement = (
            select(corpus_items.c.payload_json)
            .where(corpus_items.c.canonical_content_hash == content_hash)
            .order_by(corpus_items.c.corpus_item_id)
            .limit(limit)
        )
        async with self._engine.connect() as connection:
            payloads = (await connection.scalars(statement)).all()
        return tuple(CorpusItem.model_validate(payload) for payload in payloads)

    async def link_item_source(self, corpus_item_id: UUID, source_manifest_id: UUID) -> None:
        async with postgres_transaction(self._engine) as connection:
            await connection.execute(
                pg_insert(corpus_item_sources)
                .values(corpus_item_id=corpus_item_id, source_manifest_id=source_manifest_id)
                .on_conflict_do_nothing()
            )

    async def record_classification(self, classification: CorpusClassification) -> None:
        async with postgres_transaction(self._engine) as connection:
            await connection.execute(
                pg_insert(corpus_classifications)
                .values(
                    classification_id=classification.classification_id,
                    corpus_item_id=classification.corpus_item_id,
                    item_revision=classification.item_revision,
                    content_type=classification.content_type.value,
                    classification_hash=classification.content_hash,
                    payload_json=classification.model_dump(mode="json"),
                    created_at=classification.created_at,
                )
                .on_conflict_do_nothing()
            )

    async def record_route_decision(self, decision: CorpusRouteDecision) -> None:
        async with postgres_transaction(self._engine) as connection:
            await connection.execute(
                pg_insert(corpus_route_decisions)
                .values(
                    route_decision_id=decision.route_decision_id,
                    corpus_item_id=decision.corpus_item_id,
                    item_revision=decision.item_revision,
                    destination=decision.destination.value,
                    status=decision.status.value,
                    decision_hash=decision.content_hash,
                    payload_json=decision.model_dump(mode="json"),
                    created_at=decision.created_at,
                )
                .on_conflict_do_nothing()
            )

    async def advance_item_status(self, transition: CorpusStatusTransition) -> CorpusItem:
        current = await self.get_item(transition.corpus_item_id)
        if current is None:
            raise CorpusConflictError("corpus item is unavailable")
        payload = current.model_dump(mode="python", exclude={"content_hash"})
        payload.update(
            current_revision=transition.next_revision, current_status=transition.next_status
        )
        updated = CorpusItem.model_validate(payload)
        async with postgres_transaction(self._engine) as connection:
            advanced = await connection.scalar(
                text(
                    "SELECT cognitive_os.advance_corpus_item(:item_id, :expected_revision, "
                    ":expected_status, :next_revision, :next_status, :item_hash, "
                    "CAST(:payload AS jsonb), :actor, :reason)"
                ),
                dict(
                    item_id=transition.corpus_item_id,
                    expected_revision=transition.expected_revision,
                    expected_status=transition.expected_status.value,
                    next_revision=transition.next_revision,
                    next_status=transition.next_status.value,
                    item_hash=updated.content_hash,
                    payload=updated.model_dump_json(),
                    actor=transition.actor_id,
                    reason=transition.reason,
                ),
            )
        if not advanced:
            raise CorpusConflictError("stale or illegal corpus item transition")
        return updated

    async def create_manifest(self, manifest: CorpusManifest) -> None:
        async with postgres_transaction(self._engine) as connection:
            await connection.execute(
                pg_insert(corpus_manifests)
                .values(
                    corpus_id=manifest.corpus_id,
                    revision=manifest.revision,
                    previous_revision=manifest.previous_revision,
                    purpose=manifest.purpose.value,
                    manifest_hash=manifest.content_hash,
                    payload_json=manifest.model_dump(mode="json"),
                    created_at=manifest.created_at,
                )
                .on_conflict_do_nothing()
            )
            if manifest.items:
                await connection.execute(
                    pg_insert(corpus_manifest_items)
                    .values(
                        [
                            dict(
                                corpus_id=manifest.corpus_id,
                                corpus_revision=manifest.revision,
                                corpus_item_id=item.corpus_item_id,
                                item_revision=item.item_revision,
                                item_hash=item.item_hash,
                                split=item.split.value if item.split else None,
                            )
                            for item in manifest.items
                        ]
                    )
                    .on_conflict_do_nothing()
                )

    async def get_manifest(self, corpus_id: UUID, revision: int) -> CorpusManifest | None:
        statement = select(corpus_manifests.c.payload_json).where(
            corpus_manifests.c.corpus_id == corpus_id, corpus_manifests.c.revision == revision
        )
        async with self._engine.connect() as connection:
            payload = await connection.scalar(statement)
        return CorpusManifest.model_validate(payload) if payload else None

    async def create_export(self, export: CorpusExportManifest) -> None:
        async with postgres_transaction(self._engine) as connection:
            await connection.execute(
                pg_insert(corpus_exports)
                .values(
                    export_id=export.export_id,
                    corpus_id=export.corpus_id,
                    corpus_revision=export.corpus_revision,
                    export_type=export.export_type.value,
                    export_hash=export.content_hash,
                    payload_json=export.model_dump(mode="json"),
                    created_at=export.created_at,
                )
                .on_conflict_do_nothing()
            )

    async def record_access(self, records: tuple[CorpusAccessRecord, ...]) -> None:
        if not records:
            return
        async with postgres_transaction(self._engine) as connection:
            await connection.execute(
                pg_insert(corpus_accesses)
                .values(
                    [
                        dict(
                            access_id=item.access_id,
                            source_manifest_id=item.source_manifest_id,
                            corpus_item_id=item.corpus_item_id,
                            corpus_id=item.corpus_id,
                            export_id=item.export_id,
                            access_type=item.access_type.value,
                            access_hash=item.content_hash,
                            payload_json=item.model_dump(mode="json"),
                            accessed_at=item.accessed_at,
                        )
                        for item in records
                    ]
                )
                .on_conflict_do_nothing()
            )
