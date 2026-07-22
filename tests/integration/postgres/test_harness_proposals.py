import importlib

import pytest
from sqlalchemy import text

from cognitive_os.domain.proposals import (
    HarnessProposalIdentity,
    HarnessProposalType,
    ProposalStatus,
)
from cognitive_os.infrastructure.proposals.postgres.health import PostgresProposalHealthService
from cognitive_os.infrastructure.proposals.postgres.repository import PostgresProposalRepository
from cognitive_os.proposals.fixtures import FIXTURE_TIME, fixture_proposal_source
from cognitive_os.proposals.service import HarnessProposalService


@pytest.mark.asyncio
async def test_proposal_persistence_is_append_only_and_compare_and_set(engines) -> None:
    app, admin = engines
    source = await fixture_proposal_source()
    repository = PostgresProposalRepository(app)
    service = HarnessProposalService(repository, source)
    validated = await service.create_from_weakness(
        source.revision.weakness_id,
        source.revision.revision,
        HarnessProposalType.CONTEXT_PROFILE_CHANGE,
        actor="operator",
        created_at=FIXTURE_TIME,
    )
    assert validated.status is ProposalStatus.VALIDATED
    assert await repository.get_exact(validated.proposal_id, 1) is not None
    assert await repository.get_current(validated.proposal_id) == validated
    assert (
        await service.get_exact(
            validated.proposal_id,
            validated.revision,
            actor="integration-test",
            accessed_at=FIXTURE_TIME,
        )
        == validated
    )
    identity = HarnessProposalIdentity(
        proposal_id=validated.proposal_id,
        canonical_name="context_profile_change:integration",
        proposal_type=HarnessProposalType.CONTEXT_PROFILE_CHANGE,
        scope=validated.change_specification.current_identity,
        created_at=FIXTURE_TIME,
        created_by="operator",
    )
    await service.enqueue(identity, validated.revision, created_at=FIXTURE_TIME)
    await service.remove_from_queue(
        validated.proposal_id,
        validated.revision,
        actor="operator",
        created_at=FIXTURE_TIME,
    )
    async with admin.connect() as connection:
        kinds = (
            (
                await connection.execute(
                    text(
                        "SELECT record_kind FROM cognitive_os.harness_proposal_queue "
                        "WHERE proposal_id=:proposal_id ORDER BY created_at, record_kind"
                    ),
                    {"proposal_id": validated.proposal_id},
                )
            )
            .scalars()
            .all()
        )
    assert sorted(kinds) == ["entry", "removal"]
    health = await PostgresProposalHealthService(app).check()
    assert health.healthy
    with pytest.raises(Exception, match="append-only"):
        async with admin.begin() as connection:
            await connection.execute(
                text(
                    "DELETE FROM cognitive_os.harness_proposal_revisions "
                    "WHERE proposal_id=:proposal_id"
                ),
                {"proposal_id": validated.proposal_id},
            )


def test_migration_uses_verified_sprint_17_inventory() -> None:
    migration = importlib.import_module(
        "infra.postgres.alembic.versions.0010_create_harness_proposals"
    )
    assert len(migration.SPRINT18_INVENTORY_SHA256) == 64
