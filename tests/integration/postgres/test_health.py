import pytest

from cognitive_os.infrastructure.postgres.health import check_postgres_health


@pytest.mark.asyncio
async def test_health_reports_database_and_migration_without_url(engines) -> None:
    app, _admin = engines
    health = await check_postgres_health(app)
    assert health.healthy
    assert health.database_version
    assert health.migration_revision == "0002"
