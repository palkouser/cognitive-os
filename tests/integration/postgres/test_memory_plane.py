from uuid import UUID

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from cognitive_os.domain.memory import (
    MemoryCreator,
    MemoryCreatorType,
    MemoryMetadataFilter,
    MemoryProvenanceBundle,
    MemoryQuery,
    MemoryRetrievalMode,
    MemoryScope,
    MemoryScopeType,
    MemorySensitivity,
    MemorySourceIdentity,
    MemorySourceRef,
    MemorySourceType,
    MemoryTextQuery,
    MemoryType,
    MemoryVectorQuery,
    MemoryWriteRequest,
    ObservationMemoryContent,
)
from cognitive_os.infrastructure.embeddings import DeterministicEmbeddingProvider
from cognitive_os.infrastructure.memory.postgres.repository import PostgresMemoryRepository
from cognitive_os.memory.embeddings import MemoryEmbeddingService
from cognitive_os.memory.retrieval import MemoryRetrievalService

MEMORY_ID = UUID("00000000-0000-0000-0000-000000000941")
SOURCE_ID = UUID("00000000-0000-0000-0000-000000000942")


def write_request() -> MemoryWriteRequest:
    return MemoryWriteRequest(
        request_id=UUID("00000000-0000-0000-0000-000000000943"),
        idempotency_key="a" * 64,
        memory_id=MEMORY_ID,
        memory_type=MemoryType.OBSERVATION,
        scope=MemoryScope(scope_type=MemoryScopeType.PROJECT, scope_id="cognitive-os"),
        title="Deterministic PostgreSQL observation",
        content=ObservationMemoryContent(
            observation="PostgreSQL exact memory retrieval is deterministic.",
            evidence_summary="Validated by the isolated Sprint 9 integration test.",
        ),
        confidence=1.0,
        salience=0.8,
        sensitivity=MemorySensitivity.INTERNAL,
        provenance=MemoryProvenanceBundle(
            sources=(
                MemorySourceRef(
                    identity=MemorySourceIdentity(
                        source_type=MemorySourceType.EVENT,
                        source_id=SOURCE_ID,
                        content_hash="b" * 64,
                    ),
                    source_hash="b" * 64,
                ),
            )
        ),
        actor=MemoryCreator(
            creator_type=MemoryCreatorType.APPROVED_INTERNAL_SERVICE,
            creator_id="postgres-integration-test",
        ),
    )


@pytest.mark.asyncio
async def test_postgres_memory_exact_retrieval_and_access_audit(engines) -> None:
    app, admin = engines
    repository = PostgresMemoryRepository(app)
    record, revision = await repository.create_memory(write_request())
    duplicate = await repository.create_memory(write_request())
    assert duplicate == (record, revision)

    text_query = MemoryQuery(
        query_id=UUID("00000000-0000-0000-0000-000000000944"),
        mode=MemoryRetrievalMode.TEXT,
        text=MemoryTextQuery(text="exact deterministic retrieval"),
        filters=MemoryMetadataFilter(
            scopes=(MemoryScope(scope_type=MemoryScopeType.PROJECT, scope_id="cognitive-os"),)
        ),
    )
    text_page, _ = await MemoryRetrievalService(repository).retrieve(text_query)
    assert [result.memory_id for result in text_page.results] == [MEMORY_ID]

    provider = DeterministicEmbeddingProvider(dimension=16)
    embedding = await MemoryEmbeddingService(
        repository, {provider.identity.provider_id: provider}
    ).create(MEMORY_ID, 1, revision.content_hash, provider.identity.provider_id)
    vector = await provider.embed_query(revision.content.render_search_text())
    vector_query = MemoryQuery(
        query_id=UUID("00000000-0000-0000-0000-000000000945"),
        mode=MemoryRetrievalMode.VECTOR,
        vector=MemoryVectorQuery(
            provider_id=embedding.provider_id,
            model_id=embedding.model_id,
            dimension=embedding.dimension,
            vector=vector,
        ),
    )
    vector_page, _ = await MemoryRetrievalService(repository).retrieve(vector_query)
    assert [result.memory_id for result in vector_page.results] == [MEMORY_ID]
    assert vector_page.results[0].score == pytest.approx(1.0)

    async with admin.connect() as connection:
        access_count = await connection.scalar(
            text("SELECT count(*) FROM cognitive_os.memory_accesses")
        )
        approximate_indexes = await connection.scalar(
            text(
                "SELECT count(*) FROM pg_indexes WHERE schemaname='cognitive_os' "
                "AND (indexdef ILIKE '%hnsw%' OR indexdef ILIKE '%ivfflat%')"
            )
        )
    assert access_count == 2
    assert approximate_indexes == 0


@pytest.mark.asyncio
async def test_runtime_role_cannot_rewrite_or_delete_memory_history(engines) -> None:
    app, _admin = engines
    repository = PostgresMemoryRepository(app)
    await repository.create_memory(write_request())
    for statement in (
        "UPDATE cognitive_os.memory_revisions SET salience = 0",
        "DELETE FROM cognitive_os.memory_revisions",
        "DELETE FROM cognitive_os.memory_accesses",
    ):
        with pytest.raises(DBAPIError):
            async with app.begin() as connection:
                await connection.execute(text(statement))
