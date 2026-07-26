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
from cognitive_os.infrastructure.memory.postgres.tables import (
    APPROXIMATE_INDEX_DIMENSIONS,
    APPROXIMATE_INDEX_NAMES,
    approximate_index_name,
)
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
        # Sprint 21.3 replaced "no approximate index exists" with "exactly the declared
        # ones exist, and they are usable". An invalid index left behind by a failed
        # build satisfies a presence check but serves nothing, so validity is asserted.
        usable_indexes = set(
            (
                await connection.execute(
                    text(
                        "SELECT c.relname FROM pg_index i "
                        "JOIN pg_class c ON c.oid = i.indexrelid "
                        "JOIN pg_am a ON a.oid = c.relam "
                        "JOIN pg_namespace n ON n.oid = c.relnamespace "
                        "WHERE n.nspname='cognitive_os' AND a.amname IN ('hnsw','ivfflat') "
                        "AND i.indisvalid AND i.indisready"
                    )
                )
            ).scalars()
        )
    assert access_count == 2
    assert usable_indexes == set(APPROXIMATE_INDEX_NAMES)


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


@pytest.mark.asyncio
async def test_approximate_retrieval_reaches_the_index_and_exact_retrieval_cannot(engines) -> None:
    """Sprint 21.3's central claim, asserted against a real planner.

    Sprint 9's exhaustive guarantee is preserved by the *shape* of the SQL rather than by
    a flag: the exact query compares the undimensioned column, which no pgvector index
    can serve. This reads back both plans instead of trusting that.

    The corpus is a scratch table because the planner only prefers an approximate index
    once a scan is expensive, and populating `memory_embeddings` at that size means
    fabricating governed revisions. The expressions are taken from the repository itself,
    so a drift between the repository and the index shows up here.
    """
    _app, admin = engines
    dimension = APPROXIMATE_INDEX_DIMENSIONS[0]
    repository = PostgresMemoryRepository(admin, approximate_dimensions=frozenset({dimension}))
    rendered = {}
    for mode in (MemoryRetrievalMode.VECTOR, MemoryRetrievalMode.VECTOR_APPROXIMATE):
        query = MemoryQuery(
            query_id=UUID("00000000-0000-0000-0000-000000000946"),
            mode=mode,
            vector=MemoryVectorQuery(
                provider_id="deterministic-test",
                model_id="deterministic-v1",
                dimension=dimension,
                vector=tuple(0.1 + (index % 5) / 10 for index in range(dimension)),
            ),
        )
        expression = repository._vector_distance(query)
        rendered[mode] = str(
            expression.compile(dialect=admin.dialect, compile_kwargs={"literal_binds": True})
        )
    assert rendered[MemoryRetrievalMode.VECTOR] != rendered[MemoryRetrievalMode.VECTOR_APPROXIMATE]

    scratch = "memory_plane_ann_probe"
    index_name = f"{approximate_index_name(dimension)}_probe"
    rows = ",".join(
        "({dim}, '[{values}]')".format(
            dim=dimension,
            values=",".join(
                f"{((seed * 7 + axis * 13) % 97) / 97:.6f}" for axis in range(dimension)
            ),
        )
        for seed in range(4_000)
    )
    try:
        async with admin.begin() as connection:
            await connection.execute(
                text(
                    f"CREATE TABLE {scratch} "
                    "(id serial primary key, dimension int, embedding vector)"
                )
            )
            await connection.execute(
                text(f"INSERT INTO {scratch} (dimension, embedding) VALUES {rows}")
            )
            await connection.execute(
                text(
                    f"CREATE INDEX {index_name} ON {scratch} "
                    f"USING hnsw ((embedding::vector({dimension})) vector_cosine_ops) "
                    f"WHERE dimension = {dimension}"
                )
            )
            await connection.execute(text(f"ANALYZE {scratch}"))

        plans = {}
        async with admin.connect() as connection:
            for mode, expression in rendered.items():
                # enable_seqscan is disabled so the question asked is "can this plan use
                # the index", not "does the planner prefer it at this corpus size" —
                # which is a cost decision, and a separate measurement.
                await connection.execute(text("SET LOCAL enable_seqscan = off"))
                await connection.execute(text("SET LOCAL hnsw.ef_search = 200"))
                statement = expression.replace("cognitive_os.memory_embeddings.", "")
                plans[mode] = "\n".join(
                    (
                        await connection.execute(
                            text(
                                f"EXPLAIN (COSTS OFF) SELECT id FROM {scratch} "
                                f"WHERE dimension = {dimension} ORDER BY {statement} LIMIT 20"
                            )
                        )
                    ).scalars()
                )
    finally:
        async with admin.begin() as connection:
            await connection.execute(text(f"DROP TABLE IF EXISTS {scratch}"))

    assert f"Index Scan using {index_name}" in plans[MemoryRetrievalMode.VECTOR_APPROXIMATE], (
        "the approximate expression must match the partial expression index"
    )
    assert index_name not in plans[MemoryRetrievalMode.VECTOR], (
        "exact retrieval must remain unindexable, which is what preserves Sprint 9"
    )
    assert "Seq Scan" in plans[MemoryRetrievalMode.VECTOR]


@pytest.mark.asyncio
async def test_approximate_search_effort_applies_and_does_not_leak(engines) -> None:
    """`SET LOCAL` must take effect first-statement and must not survive the checkout.

    Both halves fail silently if wrong. Outside a transaction PostgreSQL warns and ignores
    the setting, leaving approximate queries on pgvector's default `ef_search` of 40 —
    which surfaces as unexplained poor recall. And a value that survived into the pool
    would hand an approximate search effort to the next caller's exact query.
    """
    _app, admin = engines
    async with admin.connect() as connection:
        # Exactly the repository's ordering: this is the first statement on the connection.
        await connection.execute(text("SET LOCAL hnsw.ef_search = 777"))
        assert await connection.scalar(text("SHOW hnsw.ef_search")) == "777"
    async with admin.connect() as connection:
        assert await connection.scalar(text("SHOW hnsw.ef_search")) != "777"
