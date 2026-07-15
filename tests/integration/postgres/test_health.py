import pytest

from cognitive_os.infrastructure.postgres.health import check_postgres_health
from cognitive_os.infrastructure.semantic_memory.postgres.health import (
    PostgresSemanticHealthService,
)


@pytest.mark.asyncio
async def test_health_reports_database_and_migration_without_url(engines) -> None:
    app, _admin = engines
    health = await check_postgres_health(app)
    assert health.healthy
    assert health.database_version
    assert health.migration_revision == "0003"
    semantic = await PostgresSemanticHealthService(app).check()
    assert semantic.healthy
    assert semantic.alembic_revision == "0003"
    assert not any(
        finding.count
        for finding in semantic.findings
        if finding.severity.value == "error"
    )
