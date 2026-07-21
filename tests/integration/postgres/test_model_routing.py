from decimal import Decimal
from uuid import NAMESPACE_URL, uuid5

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from cognitive_os.domain.routing import RoutingOutcome, RoutingOutcomeStatus
from cognitive_os.infrastructure.routing.postgres.health import PostgresRoutingHealthService
from cognitive_os.infrastructure.routing.postgres.repository import PostgresCapabilityRepository
from cognitive_os.routing.fixtures import (
    FIXTURE_TIME,
    build_routing_request,
    replay_profiles,
    static_policy,
)
from cognitive_os.routing.service import RoutingService


@pytest.mark.asyncio
async def test_postgres_routing_is_immutable_audited_and_healthy(engines) -> None:
    app, admin = engines
    repository = PostgresCapabilityRepository(app)
    service = RoutingService(repository)
    for profile in replay_profiles():
        await service.register_profile(profile)
    policy = static_policy()
    await service.create_policy(policy)
    decision = await service.route_static(build_routing_request(), policy)
    assert decision.selected_model is not None
    outcome = RoutingOutcome(
        outcome_id=uuid5(NAMESPACE_URL, "sprint16:postgres-outcome"),
        decision_id=decision.decision_id,
        task_run_id=decision.task_run_id,
        provider_request_reference="replay-request",
        provider_result_reference="replay-result",
        context_bundle_reference="context-bundle",
        verifier_bundle_reference="routing-verifiers",
        acceptance_decision_reference="acceptance",
        status=RoutingOutcomeStatus.ACCEPTED,
        latency_ms=Decimal("1"),
        safety_result="passed",
        created_at=FIXTURE_TIME,
    )
    await service.record_outcome(outcome)
    health = await PostgresRoutingHealthService(admin).check()
    assert health.healthy, health.messages
    for statement in (
        "UPDATE cognitive_os.model_capability_revisions SET status='retracted'",
        "DELETE FROM cognitive_os.routing_policy_revisions",
        "UPDATE cognitive_os.routing_decisions SET control_mode='adaptive'",
        "DELETE FROM cognitive_os.routing_outcomes",
        "UPDATE cognitive_os.routing_accesses SET access_type='outcome_read'",
    ):
        with pytest.raises(DBAPIError):
            async with admin.begin() as connection:
                await connection.execute(text(statement))


@pytest.mark.asyncio
async def test_runtime_cannot_rewrite_routing_authority(engines) -> None:
    app, _ = engines
    repository = PostgresCapabilityRepository(app)
    await repository.register_profile(replay_profiles()[0])
    await repository.create_policy(static_policy())
    for statement in (
        "UPDATE cognitive_os.model_capability_profiles SET current_status='verified'",
        "UPDATE cognitive_os.routing_policies SET control_mode='adaptive'",
        "DELETE FROM cognitive_os.routing_policies",
    ):
        with pytest.raises(DBAPIError):
            async with app.begin() as connection:
                await connection.execute(text(statement))
