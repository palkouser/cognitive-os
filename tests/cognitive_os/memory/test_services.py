from uuid import UUID

import pytest

from cognitive_os.application.services.memory_service import MemoryService
from cognitive_os.domain.memory import (
    EpisodeMemoryContent,
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
    MemoryType,
    MemoryVectorQuery,
    MemoryWriteOutcome,
    MemoryWritePolicy,
    MemoryWriteRequest,
)
from cognitive_os.infrastructure.embeddings import DeterministicEmbeddingProvider
from cognitive_os.memory.embeddings import MemoryEmbeddingService
from cognitive_os.memory.errors import MemoryAuditError, MemoryPolicyDeniedError
from cognitive_os.memory.repository import InMemoryMemoryRepository
from cognitive_os.memory.retrieval import MemoryRetrievalService

MEMORY_ID = UUID("00000000-0000-0000-0000-000000000911")
TASK_RUN_ID = UUID("00000000-0000-0000-0000-000000000912")
SOURCE_ID = UUID("00000000-0000-0000-0000-000000000913")
HASH = "a" * 64


def request(
    *,
    actor_type: MemoryCreatorType = MemoryCreatorType.INGESTION_SERVICE,
    problem_summary: str = "Repair a bounded parser defect.",
    automatic: bool = False,
) -> MemoryWriteRequest:
    content = EpisodeMemoryContent(
        task_run_id=TASK_RUN_ID,
        title="Accepted coding task",
        problem_summary=problem_summary,
        repository_identity=HASH,
        base_commit="b" * 40,
        outcome="accepted",
        patch_attempt_count=1,
        repair_count=0,
        verifier_summary="Pytest and Ruff passed.",
        trajectory_hash="c" * 64,
    )
    provenance = MemoryProvenanceBundle(
        sources=(
            MemorySourceRef(
                identity=MemorySourceIdentity(
                    source_type=MemorySourceType.CODING_TRAJECTORY,
                    source_id=SOURCE_ID,
                    content_hash="c" * 64,
                ),
                source_hash="c" * 64,
            ),
        )
    )
    return MemoryWriteRequest(
        request_id=UUID("00000000-0000-0000-0000-000000000914"),
        idempotency_key="d" * 64,
        memory_id=MEMORY_ID,
        memory_type=MemoryType.EPISODE,
        scope=MemoryScope(scope_type=MemoryScopeType.REPOSITORY, scope_id=HASH),
        title="Accepted coding task",
        content=content,
        confidence=0.9,
        salience=0.7,
        sensitivity=MemorySensitivity.INTERNAL,
        provenance=provenance,
        actor=MemoryCreator(creator_type=actor_type, creator_id="test-caller"),
        automatic=automatic,
    )


def policy(*, allow_automatic: bool = False) -> MemoryWritePolicy:
    return MemoryWritePolicy(
        allowed_types=frozenset(MemoryType),
        allowed_scopes=frozenset(MemoryScopeType),
        maximum_sensitivity=MemorySensitivity.CONFIDENTIAL,
        allow_automatic_request=allow_automatic,
    )


@pytest.mark.asyncio
async def test_candidate_creation_is_governed_and_idempotent() -> None:
    repository = InMemoryMemoryRepository()
    service = MemoryService(repository, policy())
    decision, first = await service.create(request())
    _, second = await service.create(request())
    assert decision.decision is MemoryWriteOutcome.ALLOW_CANDIDATE
    assert first == second
    assert len(repository.records) == 1
    assert len(repository.revisions[MEMORY_ID]) == 1


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "denied_request,reason",
    [
        (request(actor_type=MemoryCreatorType.PROVIDER), "provider_direct_write_denied"),
        (request(automatic=True), "automatic_ingestion_denied"),
        (
            request(problem_summary="api_key=super-secret-value"),
            "secret_detected",
        ),
    ],
)
async def test_denied_writes_leave_repository_unchanged(
    denied_request: MemoryWriteRequest, reason: str
) -> None:
    repository = InMemoryMemoryRepository()
    with pytest.raises(MemoryPolicyDeniedError) as caught:
        await MemoryService(repository, policy()).create(denied_request)
    assert reason in caught.value.reason_codes
    assert not repository.records


@pytest.mark.asyncio
async def test_metadata_and_text_retrieval_create_complete_access_audit() -> None:
    repository = InMemoryMemoryRepository()
    await MemoryService(repository, policy()).create(request())
    retrieval = MemoryRetrievalService(repository)
    query = MemoryQuery(
        query_id=UUID("00000000-0000-0000-0000-000000000915"),
        mode=MemoryRetrievalMode.TEXT,
        text={"text": "parser pytest"},
        filters=MemoryMetadataFilter(
            scopes=(MemoryScope(scope_type=MemoryScopeType.REPOSITORY, scope_id=HASH),)
        ),
    )
    page, trace = await retrieval.retrieve(query, task_run_id=TASK_RUN_ID)
    assert [result.memory_id for result in page.results] == [MEMORY_ID]
    assert trace.access_audit_succeeded
    assert len(repository.accesses) == len(page.results) == 1
    assert repository.accesses[0].query_hash == trace.query_hash


class FailingAuditRepository(InMemoryMemoryRepository):
    async def record_access(self, records: object) -> None:
        raise RuntimeError("audit unavailable")


@pytest.mark.asyncio
async def test_retrieval_fails_closed_when_access_audit_fails() -> None:
    repository = FailingAuditRepository()
    await MemoryService(repository, policy()).create(request())
    query = MemoryQuery(
        query_id=UUID("00000000-0000-0000-0000-000000000916"),
        mode=MemoryRetrievalMode.METADATA,
    )
    with pytest.raises(MemoryAuditError):
        await MemoryRetrievalService(repository).retrieve(query)


@pytest.mark.asyncio
async def test_deterministic_embedding_is_reproducible_and_bounded() -> None:
    provider = DeterministicEmbeddingProvider(dimension=16, maximum_batch_size=2)
    first = await provider.embed_query("stable parser repair")
    second = await provider.embed_query("stable parser repair")
    different = await provider.embed_query("unrelated verifier output")
    assert first == second
    assert first != different
    assert len(first) == provider.identity.dimension == 16
    with pytest.raises(ValueError, match="exceeds"):
        await provider.embed_documents(("one", "two", "three"))


@pytest.mark.asyncio
async def test_embedding_is_revision_specific_and_exact_vector_retrieval_is_audited() -> None:
    repository = InMemoryMemoryRepository()
    _, created = await MemoryService(repository, policy()).create(request())
    assert created is not None
    revision = created[1]
    provider = DeterministicEmbeddingProvider(dimension=16)
    embedding = await MemoryEmbeddingService(
        repository, {provider.identity.provider_id: provider}
    ).create(MEMORY_ID, 1, revision.content_hash, provider.identity.provider_id)
    query_vector = await provider.embed_query(revision.content.render_search_text())
    query = MemoryQuery(
        query_id=UUID("00000000-0000-0000-0000-000000000917"),
        mode=MemoryRetrievalMode.VECTOR,
        vector=MemoryVectorQuery(
            provider_id=embedding.provider_id,
            model_id=embedding.model_id,
            dimension=embedding.dimension,
            vector=query_vector,
        ),
    )
    page, trace = await MemoryRetrievalService(repository).retrieve(query)
    assert [result.memory_id for result in page.results] == [MEMORY_ID]
    assert page.results[0].score == pytest.approx(1.0)
    assert trace.access_audit_succeeded
