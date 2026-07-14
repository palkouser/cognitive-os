import os
from uuid import uuid4

import pytest
from sqlalchemy.exc import SQLAlchemyError

from cognitive_os.application.services.controller_recovery import ControllerRecoveryService
from cognitive_os.domain.common import utc_now
from cognitive_os.domain.controller import ControllerState
from cognitive_os.events.catalog import build_default_event_catalog
from cognitive_os.events.controller_event_service import ControllerEventService
from cognitive_os.events.controller_events import ControllerStateChanged
from cognitive_os.infrastructure.postgres.engine import create_postgres_engine
from cognitive_os.infrastructure.postgres.event_store import PostgresEventStore


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.postgres
async def test_postgres_controller_transition_replays() -> None:
    database_url = os.environ.get("COGOS_DATABASE_URL")
    if not database_url:
        pytest.skip("PostgreSQL integration URL is not configured")
    engine = create_postgres_engine(database_url, pool_size=1, max_overflow=0)
    task_run_id, decision_id = uuid4(), uuid4()
    try:
        store = PostgresEventStore(engine, build_default_event_catalog())
        await ControllerEventService(store).append(
            task_run_id=task_run_id,
            payload=ControllerStateChanged(
                previous_state=ControllerState.RECEIVED,
                current_state=ControllerState.REPRESENTING_PROBLEM,
                reason="integration test",
                decision_id=decision_id,
                changed_at=utc_now(),
            ),
            expected_version=0,
            correlation_id=task_run_id,
        )
        snapshot = await ControllerRecoveryService(store).replay(task_run_id)
        assert snapshot.state is ControllerState.REPRESENTING_PROBLEM
        assert snapshot.last_stream_version == 1
    except SQLAlchemyError as error:
        pytest.fail(f"PostgreSQL controller integration failed: {type(error).__name__}")
    finally:
        await engine.dispose()
