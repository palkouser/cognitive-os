import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from cognitive_os.corpus.factory import CorpusFactory
from cognitive_os.corpus.fixtures import FixtureArtifactStore, build_corpus_fixture
from cognitive_os.infrastructure.corpus.postgres.health import PostgresCorpusHealthService
from cognitive_os.infrastructure.corpus.postgres.repository import PostgresCorpusRepository


@pytest.mark.asyncio
async def test_corpus_repository_pipeline_append_only_and_health(engines) -> None:
    app, admin = engines
    request, source = build_corpus_fixture("cognitive-os-export")
    repository = PostgresCorpusRepository(app)
    result = await CorpusFactory(repository, FixtureArtifactStore()).ingest(request, source)
    assert await repository.get_item(result.items[0].corpus_item_id) == result.items[0]
    assert await repository.get_manifest(result.manifest.corpus_id, 1) == result.manifest
    health = await PostgresCorpusHealthService(admin).check()
    assert health.healthy, health.messages
    for statement in (
        "UPDATE cognitive_os.corpus_sources SET source_identity='forged'",
        "DELETE FROM cognitive_os.corpus_classifications",
        "UPDATE cognitive_os.corpus_route_decisions SET status='allowed'",
        "DELETE FROM cognitive_os.corpus_accesses",
    ):
        with pytest.raises(DBAPIError):
            async with admin.begin() as connection:
                await connection.execute(text(statement))


@pytest.mark.asyncio
async def test_runtime_role_cannot_directly_route_or_create_late_revision(engines) -> None:
    app, _ = engines
    request, source = build_corpus_fixture("document")
    result = await CorpusFactory(
        PostgresCorpusRepository(app), FixtureArtifactStore()
    ).ingest(request, source)
    item_id = result.items[0].corpus_item_id
    for statement in (
        "UPDATE cognitive_os.corpus_items SET current_status='exported' "
        f"WHERE corpus_item_id='{item_id}'",
        "DELETE FROM cognitive_os.corpus_items",
        "INSERT INTO cognitive_os.corpus_manifests "
        "SELECT corpus_id, 3, 2, purpose, manifest_hash, payload_json, created_at "
        "FROM cognitive_os.corpus_manifests",
    ):
        with pytest.raises(DBAPIError):
            async with app.begin() as connection:
                await connection.execute(text(statement))
