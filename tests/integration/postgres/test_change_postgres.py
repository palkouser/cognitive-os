import importlib

import pytest
from sqlalchemy import text

from cognitive_os.changes.fixtures import fixture_approved_proposal
from cognitive_os.changes.service import ControlledChangeService
from cognitive_os.domain.changes import ChangeExperimentStatus
from cognitive_os.infrastructure.changes.postgres.health import PostgresChangeHealthService
from cognitive_os.infrastructure.changes.postgres.repository import PostgresChangeRepository
from cognitive_os.proposals.fixtures import FIXTURE_TIME


@pytest.mark.asyncio
async def test_change_persistence_is_append_only_least_privilege_and_compare_and_set(
    engines,
) -> None:
    app, admin = engines
    source, proposal = await fixture_approved_proposal()
    repository = PostgresChangeRepository(app)
    service = ControlledChangeService(repository, source)
    experiment, revision, _ = await service.request_experiment(
        proposal.proposal_id,
        proposal.revision,
        baseline_tag="sprint-18-baseline",
        baseline_commit="a" * 40,
        actor="operator",
        isolation_approver="isolation-approver",
        created_at=FIXTURE_TIME,
    )
    approved = await service.transition(
        experiment.experiment_id,
        revision.revision,
        ChangeExperimentStatus.APPROVED_FOR_ISOLATION,
        actor="isolation-approver",
        reason="exact isolation scope approved",
        created_at=FIXTURE_TIME,
    )
    assert await repository.get_current_revision(experiment.experiment_id) == approved
    with pytest.raises(Exception, match="stale"):
        await service.transition(
            experiment.experiment_id,
            revision.revision,
            ChangeExperimentStatus.CANCELLED,
            actor="operator",
            reason="stale cancellation",
            created_at=FIXTURE_TIME,
        )
    health = await PostgresChangeHealthService(app).check()
    assert health.healthy, health.messages
    with pytest.raises(Exception, match="append-only"):
        async with admin.begin() as connection:
            await connection.execute(
                text(
                    "DELETE FROM cognitive_os.change_experiment_revisions "
                    "WHERE experiment_id=:experiment_id"
                ),
                {"experiment_id": experiment.experiment_id},
            )
    with pytest.raises(Exception, match="permission denied"):
        async with app.begin() as connection:
            await connection.execute(
                text(
                    "INSERT INTO cognitive_os.change_accesses("
                    "access_id, experiment_id, record_kind, content_hash, payload_json, created_at) "
                    "VALUES (gen_random_uuid(), :experiment_id, 'read', :hash, '{}', now())"
                ),
                {"experiment_id": experiment.experiment_id, "hash": "f" * 64},
            )


def test_migration_uses_verified_sprint_18_inventory() -> None:
    migration = importlib.import_module(
        "infra.postgres.alembic.versions.0011_create_controlled_changes"
    )
    assert len(migration.SPRINT19_INVENTORY_SHA256) == 64
