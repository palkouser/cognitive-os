import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from cognitive_os.infrastructure.weakness.postgres.health import (
    PostgresWeaknessHealthService,
)
from cognitive_os.infrastructure.weakness.postgres.repository import (
    PostgresWeaknessRepository,
)
from cognitive_os.weakness.fixtures import (
    FixtureSignalExtractor,
    FixtureSourceResolver,
    fixture_profile,
    fixture_request,
    fixture_sources,
)
from cognitive_os.weakness.service import (
    SignalExtractorRegistry,
    SourceResolverRegistry,
    WeaknessMiningService,
)


def _service(repository) -> tuple[WeaknessMiningService, object, object]:
    sources = fixture_sources(18)
    source_registry = SourceResolverRegistry()
    for source_type in sorted({item.source_type for item in sources}, key=str):
        source_registry.register(FixtureSourceResolver(source_type, sources))
    source_registry.freeze()
    extractors = SignalExtractorRegistry()
    extractors.register(FixtureSignalExtractor())
    extractors.freeze()
    profile = fixture_profile(sources)
    return WeaknessMiningService(repository, source_registry, extractors), fixture_request(
        profile, 18
    ), profile


@pytest.mark.asyncio
async def test_postgres_weakness_pipeline_is_immutable_and_healthy(engines) -> None:
    app, admin = engines
    repository = PostgresWeaknessRepository(app)
    service, request, profile = _service(repository)
    result = await service.mine(request, profile)
    assert result.manifest is not None
    assert result.manifest.summary.signal_count == 18
    health = await PostgresWeaknessHealthService(admin).check()
    assert health.healthy, health.messages
    for statement in (
        "UPDATE cognitive_os.weakness_signals SET weakness_type='unknown'",
        "DELETE FROM cognitive_os.weakness_revisions",
        "UPDATE cognitive_os.weakness_queue SET status='removed'",
        "DELETE FROM cognitive_os.weakness_accesses",
    ):
        with pytest.raises(DBAPIError):
            async with admin.begin() as connection:
                await connection.execute(text(statement))


@pytest.mark.asyncio
async def test_runtime_cannot_rewrite_weakness_authority(engines) -> None:
    app, _ = engines
    repository = PostgresWeaknessRepository(app)
    service, request, profile = _service(repository)
    result = await service.mine(request, profile)
    assert result.manifest is not None
    for statement in (
        "UPDATE cognitive_os.weakness_items SET current_status='confirmed'",
        "DELETE FROM cognitive_os.weakness_items",
        "INSERT INTO cognitive_os.weakness_queue SELECT * FROM cognitive_os.weakness_queue",
    ):
        with pytest.raises(DBAPIError):
            async with app.begin() as connection:
                await connection.execute(text(statement))
