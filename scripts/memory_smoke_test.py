"""Run the credential-free governed-memory PostgreSQL smoke workflow."""

from __future__ import annotations

import asyncio
import json
import os
from uuid import NAMESPACE_URL, UUID, uuid5

from sqlalchemy import text

from cognitive_os.application.services.memory_service import MemoryService
from cognitive_os.domain.memory import (
    MemoryCreator,
    MemoryCreatorType,
    MemoryMetadataFilter,
    MemoryPromotionRequest,
    MemoryProvenanceBundle,
    MemoryQuery,
    MemoryRetractionRequest,
    MemoryRetrievalMode,
    MemoryScopeType,
    MemorySensitivity,
    MemoryTextQuery,
    MemoryTransitionReason,
    MemoryType,
    MemoryVectorQuery,
    MemoryWritePolicy,
)
from cognitive_os.events.catalog import build_default_event_catalog
from cognitive_os.events.memory_event_service import MemoryEventService
from cognitive_os.infrastructure.embeddings import DeterministicEmbeddingProvider
from cognitive_os.infrastructure.memory.postgres.repository import PostgresMemoryRepository
from cognitive_os.infrastructure.postgres.engine import create_postgres_engine
from cognitive_os.infrastructure.postgres.event_store import PostgresEventStore
from cognitive_os.memory.embeddings import MemoryEmbeddingService
from cognitive_os.memory.fixtures import accepted_coding_trajectory_fixture
from cognitive_os.memory.ingestion import CodingTrajectoryIngestionService
from cognitive_os.memory.lifecycle import MemoryLifecycleService
from cognitive_os.memory.retrieval import MemoryRetrievalService


async def run() -> int:
    database_url = os.environ.get("COGOS_DATABASE_URL")
    if not database_url:
        raise RuntimeError("COGOS_DATABASE_URL is required")
    engine = create_postgres_engine(database_url, pool_size=2, max_overflow=0)
    try:
        async with engine.connect() as connection:
            database_name = str(await connection.scalar(text("SELECT current_database()")))
        if not database_name.endswith("_test"):
            raise RuntimeError("memory smoke test requires an isolated _test database")
        repository = PostgresMemoryRepository(engine)
        event_service = MemoryEventService(
            PostgresEventStore(engine, build_default_event_catalog())
        )
        policy = MemoryWritePolicy(
            allowed_types=frozenset(MemoryType),
            allowed_scopes=frozenset(MemoryScopeType),
            maximum_sensitivity=MemorySensitivity.INTERNAL,
        )
        trajectory = accepted_coding_trajectory_fixture()
        manifest = await CodingTrajectoryIngestionService(
            MemoryService(repository, policy, event_service=event_service)
        ).ingest(trajectory, trajectory.canonical_hash())
        episode_id: UUID | None = None
        for memory_id in manifest.memory_ids:
            current = await repository.get_current(memory_id)
            if current is not None and current[0].memory_type is MemoryType.EPISODE:
                episode_id = memory_id
                break
        if episode_id is None:
            raise RuntimeError("episode projection is missing")
        actor = MemoryCreator(
            creator_type=MemoryCreatorType.OPERATOR,
            creator_id="sprint-9-smoke",
        )
        sources = await repository.list_sources(episode_id, 1)
        promoted = await MemoryLifecycleService(repository, event_service).promote(
            MemoryPromotionRequest(
                request_id=uuid5(NAMESPACE_URL, "sprint-9-smoke-promotion"),
                memory_id=episode_id,
                expected_revision=1,
                evidence=MemoryProvenanceBundle(sources=sources),
                actor=actor,
            )
        )
        provider = DeterministicEmbeddingProvider(dimension=64)
        embedding = await MemoryEmbeddingService(
            repository, {provider.identity.provider_id: provider}
        ).create(episode_id, 2, promoted.content_hash, provider.identity.provider_id)
        retrieval = MemoryRetrievalService(repository)
        text_page, _ = await retrieval.retrieve(
            MemoryQuery(
                query_id=uuid5(NAMESPACE_URL, "sprint-9-smoke-text"),
                mode=MemoryRetrievalMode.TEXT,
                text=MemoryTextQuery(text="deterministic fixture parsing"),
                filters=MemoryMetadataFilter(statuses=(promoted.status,)),
            )
        )
        vector = await provider.embed_query(promoted.content.render_search_text())
        vector_page, _ = await retrieval.retrieve(
            MemoryQuery(
                query_id=uuid5(NAMESPACE_URL, "sprint-9-smoke-vector"),
                mode=MemoryRetrievalMode.VECTOR,
                vector=MemoryVectorQuery(
                    provider_id=embedding.provider_id,
                    model_id=embedding.model_id,
                    dimension=embedding.dimension,
                    vector=vector,
                ),
                filters=MemoryMetadataFilter(statuses=(promoted.status,)),
            )
        )
        await MemoryLifecycleService(repository, event_service).retract(
            MemoryRetractionRequest(
                request_id=uuid5(NAMESPACE_URL, "sprint-9-smoke-retraction"),
                memory_id=episode_id,
                expected_revision=2,
                actor=actor,
                reason=MemoryTransitionReason.POLICY_RETRACTION,
            )
        )
        history = await repository.list_revisions(episode_id)
        async with engine.connect() as connection:
            access_count = int(
                await connection.scalar(
                    text(
                        "SELECT count(*) FROM cognitive_os.memory_accesses "
                        "WHERE query_id IN (:text_id, :vector_id)"
                    ),
                    {
                        "text_id": uuid5(NAMESPACE_URL, "sprint-9-smoke-text"),
                        "vector_id": uuid5(NAMESPACE_URL, "sprint-9-smoke-vector"),
                    },
                )
                or 0
            )
        result = {
            "access_records": access_count,
            "embedding_dimension": embedding.dimension,
            "history_revisions": len(history),
            "ingested_memories": len(manifest.memory_ids),
            "text_matches": len(text_page.results),
            "vector_matches": len(vector_page.results),
        }
        print(json.dumps(result, sort_keys=True, separators=(",", ":")))
        return (
            0
            if result
            == {
                "access_records": 2,
                "embedding_dimension": 64,
                "history_revisions": 3,
                "ingested_memories": 4,
                "text_matches": 1,
                "vector_matches": 1,
            }
            else 1
        )
    finally:
        await engine.dispose()


if __name__ == "__main__":
    raise SystemExit(asyncio.run(run()))
