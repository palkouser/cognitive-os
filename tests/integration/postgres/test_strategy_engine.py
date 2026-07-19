import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from cognitive_os.application.services.strategy_service import StrategyService
from cognitive_os.events.catalog import build_default_event_catalog
from cognitive_os.events.strategy_event_service import StrategyEventService
from cognitive_os.infrastructure.postgres.event_store import PostgresEventStore
from cognitive_os.infrastructure.strategies.postgres.health import (
    PostgresStrategyHealthService,
)
from cognitive_os.infrastructure.strategies.postgres.repository import (
    PostgresStrategyRepository,
)
from cognitive_os.strategies.errors import StrategyConcurrencyError
from cognitive_os.strategies.fixtures import sprint13_verified_strategies


@pytest.mark.asyncio
async def test_postgres_strategy_lifecycle_health_and_append_only_history(engines) -> None:
    app, _admin = engines
    fixture_repository, _, _, _, _ = await sprint13_verified_strategies()
    fixture_item = next(iter(fixture_repository.items.values()))
    history = fixture_repository.revisions[fixture_item.identity.strategy_id]
    draft, staged, verified = history
    item = fixture_item.model_copy(
        update={"current_revision": 1, "current_status": draft.status}
    )
    repository = PostgresStrategyRepository(app)
    service = StrategyService(
        repository,
        events=StrategyEventService(PostgresEventStore(app, build_default_event_catalog())),
    )

    await service.create(
        item,
        draft,
        fixture_repository.edges[(draft.strategy_id, draft.revision)],
    )
    await repository.append_revision(
        staged,
        expected_revision=1,
        edge_set=fixture_repository.edges[(staged.strategy_id, staged.revision)],
    )
    await repository.append_revision(
        verified,
        expected_revision=2,
        edge_set=fixture_repository.edges[(verified.strategy_id, verified.revision)],
    )

    current = await repository.get_current(verified.strategy_id)
    assert current is not None and current[1] == verified
    assert len(await repository.list_revisions(verified.strategy_id)) == 3
    assert (await repository.read_edge_set(verified.strategy_id, 3)).edges
    with pytest.raises(StrategyConcurrencyError):
        await repository.append_revision(verified, expected_revision=1)
    assert (await PostgresStrategyHealthService(app).check()).healthy
    for statement in (
        "UPDATE cognitive_os.strategy_revisions SET status='draft'",
        "DELETE FROM cognitive_os.strategy_edges",
        "DELETE FROM cognitive_os.strategy_sources",
    ):
        with pytest.raises(DBAPIError):
            async with app.begin() as connection:
                await connection.execute(text(statement))
