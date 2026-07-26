"""S21C1-034: learned persistence health, and one injected defect per check.

A health check that has only ever been run against a healthy database proves nothing.
Each test here damages exactly one thing and asserts that the report names it, so a check
that silently stopped working fails a test instead of quietly reporting success forever.

The other half of the contract is the split: a missing audit event is a warning and never
makes the store unhealthy, because the append-only history is still the authority.
"""

from __future__ import annotations

import os
from collections.abc import AsyncIterator
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from cognitive_os.events.learned_event_service import LearnedEventService
from cognitive_os.events.memory_store import MemoryEventStore
from cognitive_os.infrastructure.learned.postgres.health import (
    EXPECTED_TABLE_COUNT,
    EXPECTED_TRIGGER_COUNT,
    PostgresLearnedHealthService,
)
from cognitive_os.infrastructure.learned.postgres.repository import (
    PostgresLearnedEvidenceRepository,
)
from cognitive_os.infrastructure.learned.postgres.tables import LEARNED_EVIDENCE_TABLES

from . import fixtures as fx
from .repository_contract import drive_to_activated, drive_to_verified

pytestmark = [pytest.mark.integration, pytest.mark.postgres]

_TRUNCATE = ", ".join(f"cognitive_os.{table.name}" for table in LEARNED_EVIDENCE_TABLES)


@pytest_asyncio.fixture
async def engines() -> AsyncIterator[tuple[AsyncEngine, AsyncEngine]]:
    from cognitive_os.infrastructure.postgres.engine import create_postgres_engine

    app_url = os.environ.get("COGOS_DATABASE_URL")
    admin_url = os.environ.get("COGOS_DATABASE_ADMIN_URL")
    if not app_url or not admin_url:
        pytest.skip("PostgreSQL integration URLs are not configured")
    app = create_postgres_engine(app_url, pool_size=2, max_overflow=2)
    admin = create_postgres_engine(admin_url, pool_size=2, max_overflow=2)
    async with admin.connect() as connection:
        name = await connection.scalar(text("SELECT current_database()"))
        if not str(name).endswith("_test"):
            pytest.fail(f"refusing learned health tests against database: {name}")
    async with admin.begin() as connection:
        await connection.execute(text(f"TRUNCATE {_TRUNCATE} RESTART IDENTITY CASCADE"))
    try:
        yield app, admin
    finally:
        await app.dispose()
        await admin.dispose()


async def _populated(app: AsyncEngine) -> PostgresLearnedEvidenceRepository:
    repository = PostgresLearnedEvidenceRepository(app)
    await drive_to_verified(repository)
    await drive_to_activated(repository)
    return repository


class TestAHealthyStoreReportsNothingWrong:
    @pytest.mark.asyncio
    async def test_a_fresh_store_is_healthy_and_empty(
        self, engines: tuple[AsyncEngine, AsyncEngine]
    ) -> None:
        app, _ = engines
        report = await PostgresLearnedHealthService(app).check()
        assert report.healthy
        assert report.integrity_failures == ()
        assert report.migration_revision == "0014"
        assert report.table_count == EXPECTED_TABLE_COUNT
        assert report.append_only_trigger_count == EXPECTED_TRIGGER_COUNT
        assert report.controlled_function_count == 10
        assert report.component_count == 0
        assert report.active_component_count == 0

    @pytest.mark.asyncio
    async def test_a_populated_store_is_healthy_and_counts_what_it_holds(
        self, engines: tuple[AsyncEngine, AsyncEngine]
    ) -> None:
        app, _ = engines
        await _populated(app)
        report = await PostgresLearnedHealthService(app).check()
        assert report.healthy, report.integrity_failures
        assert report.component_count == 1
        assert report.active_component_count == 1
        assert report.revision_count == 4
        assert report.replay_matches

    @pytest.mark.asyncio
    async def test_health_writes_nothing(self, engines: tuple[AsyncEngine, AsyncEngine]) -> None:
        """Safe against a live database, which is the only way it gets run often."""
        app, admin = engines
        await _populated(app)
        service = PostgresLearnedHealthService(app)
        before = await _fingerprint(admin)
        await service.check()
        await service.check()
        assert await _fingerprint(admin) == before


class TestEachInjectedDefectChangesTheExpectedField:
    @pytest.mark.asyncio
    async def test_a_projection_row_without_history_is_an_integrity_failure(
        self, engines: tuple[AsyncEngine, AsyncEngine]
    ) -> None:
        """The authority is gone, not merely out of date. This is the severe case."""
        app, admin = engines
        await _populated(app)
        async with admin.begin() as connection:
            await connection.execute(
                text("ALTER TABLE cognitive_os.learned_component_revisions DISABLE TRIGGER USER")
            )
            await connection.execute(text("DELETE FROM cognitive_os.learned_component_revisions"))
            await connection.execute(
                text("ALTER TABLE cognitive_os.learned_component_revisions ENABLE TRIGGER USER")
            )
        report = await PostgresLearnedHealthService(app).check()
        assert not report.healthy
        assert any("no lifecycle history" in item for item in report.integrity_failures)

    @pytest.mark.asyncio
    async def test_a_projection_that_disagrees_with_replay_is_reported(
        self, engines: tuple[AsyncEngine, AsyncEngine]
    ) -> None:
        app, admin = engines
        await _populated(app)
        async with admin.begin() as connection:
            await connection.execute(
                text(
                    "UPDATE cognitive_os.learned_components SET current_state = 'disabled' "
                    "WHERE component_id = :component_id"
                ),
                {"component_id": fx.INERT.component_id},
            )
        report = await PostgresLearnedHealthService(app).check()
        assert not report.healthy
        assert not report.replay_matches
        assert any(item.startswith("replay:") for item in report.integrity_failures)

    @pytest.mark.asyncio
    async def test_a_gap_in_the_revision_sequence_is_reported(
        self, engines: tuple[AsyncEngine, AsyncEngine]
    ) -> None:
        app, admin = engines
        await _populated(app)
        async with admin.begin() as connection:
            await connection.execute(
                text("ALTER TABLE cognitive_os.learned_component_revisions DISABLE TRIGGER USER")
            )
            await connection.execute(
                text("DELETE FROM cognitive_os.learned_component_revisions WHERE revision = 2")
            )
            await connection.execute(
                text("ALTER TABLE cognitive_os.learned_component_revisions ENABLE TRIGGER USER")
            )
        report = await PostgresLearnedHealthService(app).check()
        assert not report.healthy
        assert any("gap in their sequence" in item for item in report.integrity_failures)

    @pytest.mark.asyncio
    async def test_a_payload_that_disagrees_with_its_hash_column_is_reported(
        self, engines: tuple[AsyncEngine, AsyncEngine]
    ) -> None:
        app, admin = engines
        repository = PostgresLearnedEvidenceRepository(app)
        await drive_to_verified(repository)
        await repository.record_access(_access())
        async with admin.begin() as connection:
            await connection.execute(
                text("ALTER TABLE cognitive_os.learned_accesses DISABLE TRIGGER USER")
            )
            await connection.execute(
                text("UPDATE cognitive_os.learned_accesses SET content_hash = :h"),
                {"h": "9" * 64},
            )
            await connection.execute(
                text("ALTER TABLE cognitive_os.learned_accesses ENABLE TRIGGER USER")
            )
        report = await PostgresLearnedHealthService(app).check()
        assert not report.healthy
        assert any("disagrees with its payload" in item for item in report.integrity_failures)

    @pytest.mark.asyncio
    async def test_two_active_components_on_one_surface_are_reported(
        self, engines: tuple[AsyncEngine, AsyncEngine]
    ) -> None:
        """Only reachable by dropping the index, which is exactly why health re-checks."""
        app, admin = engines
        await _populated(app)
        async with admin.begin() as connection:
            await connection.execute(
                text("DROP INDEX cognitive_os.uq_learned_components_active_surface")
            )
            await connection.execute(
                text(
                    "INSERT INTO cognitive_os.learned_components (component_id, surface, "
                    "descriptor_version, current_revision, current_state, descriptor_hash, "
                    "content_hash) VALUES ('intruder', :surface, '1', 1, 'active', :h, :h)"
                ),
                {"surface": fx.surface(), "h": "a" * 64},
            )
        try:
            report = await PostgresLearnedHealthService(app).check()
            assert not report.healthy
            assert any("more than one active" in item for item in report.integrity_failures)
            assert any("missing required indexes" in item for item in report.integrity_failures)
        finally:
            async with admin.begin() as connection:
                await connection.execute(
                    text(
                        "DELETE FROM cognitive_os.learned_components WHERE component_id='intruder'"
                    )
                )
                await connection.execute(
                    text(
                        "CREATE UNIQUE INDEX uq_learned_components_active_surface ON "
                        "cognitive_os.learned_components (surface) "
                        "WHERE current_state = 'active'"
                    )
                )

    @pytest.mark.asyncio
    async def test_a_missing_artifact_behind_a_lineage_row_is_reported(
        self, engines: tuple[AsyncEngine, AsyncEngine]
    ) -> None:
        app, admin = engines
        repository = PostgresLearnedEvidenceRepository(app)
        await drive_to_verified(repository)
        artifact_id = await _seed_artifact(admin)
        await repository.record_artifact_lineage(fx.lineage(artifact_id=artifact_id))
        # The foreign key makes this unreachable on a live database, which is why the
        # constraint has to come off first: the state health is checking for is one a
        # restored dump or a partially applied migration can produce, not one the
        # running system can.
        async with admin.begin() as connection:
            await connection.execute(
                text(
                    "ALTER TABLE cognitive_os.learned_artifacts "
                    "DROP CONSTRAINT learned_artifacts_artifact_id_fkey"
                )
            )
            await connection.execute(
                text("ALTER TABLE cognitive_os.learned_artifacts DISABLE TRIGGER USER")
            )
            await connection.execute(
                text("UPDATE cognitive_os.learned_artifacts SET artifact_id = :missing"),
                {"missing": uuid4()},
            )
            await connection.execute(
                text("ALTER TABLE cognitive_os.learned_artifacts ENABLE TRIGGER USER")
            )
        try:
            report = await PostgresLearnedHealthService(app).check()
            assert not report.healthy
            assert any("missing artifact" in item for item in report.integrity_failures)
        finally:
            async with admin.begin() as connection:
                await connection.execute(
                    text("ALTER TABLE cognitive_os.learned_artifacts DISABLE TRIGGER USER")
                )
                await connection.execute(text("DELETE FROM cognitive_os.learned_artifacts"))
                await connection.execute(
                    text("ALTER TABLE cognitive_os.learned_artifacts ENABLE TRIGGER USER")
                )
                await connection.execute(
                    text(
                        "ALTER TABLE cognitive_os.learned_artifacts ADD CONSTRAINT "
                        "learned_artifacts_artifact_id_fkey FOREIGN KEY (artifact_id) "
                        "REFERENCES cognitive_os.artifacts (artifact_id) ON DELETE RESTRICT"
                    )
                )

    @pytest.mark.asyncio
    async def test_a_training_dataset_holding_a_real_governed_run_is_reported(
        self, engines: tuple[AsyncEngine, AsyncEngine]
    ) -> None:
        """The training exclusion, checked after the fact as well as before the write."""
        app, admin = engines
        async with admin.begin() as connection:
            await connection.execute(
                text(
                    "INSERT INTO cognitive_os.learned_datasets (dataset_id, revision, surface, "
                    "corpus_role, feature_schema_hash, split_manifest_hash, "
                    "example_manifest_hash, provenance_counts, observation_count, "
                    "usage_rights_verified, sensitivity, payload_json, content_hash) VALUES "
                    "(gen_random_uuid(), 1, :surface, 'evaluation', :h, :h, :h, "
                    ":counts, 1, true, 'internal', '{}'::jsonb, :h)"
                ),
                {"surface": fx.surface(), "h": "a" * 64, "counts": '{"real_governed_run": 1}'},
            )
            # Flip the role after the CHECK has already accepted the row, which is what a
            # restored dump or a future migration can do to rows already in the table.
            await connection.execute(
                text(
                    "ALTER TABLE cognitive_os.learned_datasets "
                    "DROP CONSTRAINT ck_learned_training_excludes_real_runs"
                )
            )
            await connection.execute(
                text("ALTER TABLE cognitive_os.learned_datasets DISABLE TRIGGER USER")
            )
            await connection.execute(
                text("UPDATE cognitive_os.learned_datasets SET corpus_role = 'training'")
            )
            await connection.execute(
                text("ALTER TABLE cognitive_os.learned_datasets ENABLE TRIGGER USER")
            )
        try:
            report = await PostgresLearnedHealthService(app).check()
            assert not report.healthy
            assert any("real governed runs" in item for item in report.integrity_failures)
        finally:
            async with admin.begin() as connection:
                await connection.execute(
                    text("ALTER TABLE cognitive_os.learned_datasets DISABLE TRIGGER USER")
                )
                await connection.execute(text("DELETE FROM cognitive_os.learned_datasets"))
                await connection.execute(
                    text("ALTER TABLE cognitive_os.learned_datasets ENABLE TRIGGER USER")
                )
                await connection.execute(
                    text(
                        "ALTER TABLE cognitive_os.learned_datasets ADD CONSTRAINT "
                        "ck_learned_training_excludes_real_runs CHECK (corpus_role <> 'training' "
                        "OR NOT (provenance_counts ? 'real_governed_run'))"
                    )
                )

    @pytest.mark.asyncio
    async def test_a_dropped_append_only_trigger_is_reported(
        self, engines: tuple[AsyncEngine, AsyncEngine]
    ) -> None:
        app, admin = engines
        async with admin.begin() as connection:
            await connection.execute(
                text(
                    "DROP TRIGGER trg_learned_accesses_append_only ON cognitive_os.learned_accesses"
                )
            )
        try:
            report = await PostgresLearnedHealthService(app).check()
            assert not report.healthy
            assert any("append-only triggers" in item for item in report.integrity_failures)
        finally:
            async with admin.begin() as connection:
                await connection.execute(
                    text(
                        "CREATE TRIGGER trg_learned_accesses_append_only BEFORE UPDATE OR "
                        "DELETE ON cognitive_os.learned_accesses FOR EACH ROW EXECUTE "
                        "FUNCTION cognitive_os.reject_learned_evidence_mutation()"
                    )
                )


class TestCorrelationGapsAreWarningsNotFailures:
    @pytest.mark.asyncio
    async def test_an_empty_event_store_produces_warnings_and_a_healthy_report(
        self, engines: tuple[AsyncEngine, AsyncEngine]
    ) -> None:
        """The learned ledger is complete; only the audit stream is behind."""
        app, _ = engines
        await _populated(app)
        events = LearnedEventService(MemoryEventStore())
        report = await PostgresLearnedHealthService(app, events=events).check()
        assert report.healthy, report.integrity_failures
        assert report.correlation_checked
        assert report.correlation_warnings
        assert report.integrity_failures == ()

    @pytest.mark.asyncio
    async def test_correlation_is_not_checked_without_an_event_store(
        self, engines: tuple[AsyncEngine, AsyncEngine]
    ) -> None:
        """Unchecked is reported as unchecked, never as clean."""
        app, _ = engines
        await _populated(app)
        report = await PostgresLearnedHealthService(app).check()
        assert not report.correlation_checked
        assert report.correlation_warnings == ()


class TestQuarantinedObservationsStayAuditable:
    @pytest.mark.asyncio
    async def test_quarantined_and_rejected_observations_are_counted_and_healthy(
        self, engines: tuple[AsyncEngine, AsyncEngine]
    ) -> None:
        app, _ = engines
        repository = PostgresLearnedEvidenceRepository(app)
        from cognitive_os.domain.learned_evidence import ObservationStatus

        await repository.record_observation(
            fx.observation(
                status=ObservationStatus.QUARANTINED,
                evaluation_eligible=False,
                decision_reason="attribution could not be established",
                idempotency_key="quarantined-1",
            )
        )
        await repository.record_observation(
            fx.observation(
                status=ObservationStatus.REJECTED,
                evaluation_eligible=False,
                usage_rights_verified=False,
                decision_reason="usage rights were not verified",
                idempotency_key="rejected-1",
            )
        )
        report = await PostgresLearnedHealthService(app).check()
        assert report.healthy, report.integrity_failures
        assert report.observation_count == 2
        assert report.quarantined_observation_count == 1
        assert report.rejected_observation_count == 1


async def _fingerprint(admin: AsyncEngine) -> tuple[int, ...]:
    counts: list[int] = []
    async with admin.connect() as connection:
        for table in LEARNED_EVIDENCE_TABLES:
            value = await connection.scalar(text(f"SELECT count(*) FROM cognitive_os.{table.name}"))
            counts.append(int(value or 0))
    return tuple(counts)


async def _seed_artifact(admin: AsyncEngine) -> object:
    artifact_id = uuid4()
    async with admin.begin() as connection:
        await connection.execute(
            text(
                "INSERT INTO cognitive_os.artifact_blobs (content_hash, size_bytes, storage_key) "
                "VALUES (:h, :size, :key) ON CONFLICT DO NOTHING"
            ),
            {"h": fx.ARTIFACT_HASH, "size": fx.ARTIFACT_SIZE, "key": "cc/cc/" + fx.ARTIFACT_HASH},
        )
        await connection.execute(
            text(
                "INSERT INTO cognitive_os.artifacts (artifact_id, content_hash, media_type) "
                "VALUES (:a, :h, 'application/octet-stream')"
            ),
            {"a": artifact_id, "h": fx.ARTIFACT_HASH},
        )
    return artifact_id


def _access():  # type: ignore[no-untyped-def]
    from cognitive_os.domain.learned_evidence import LearnedAccessRecord

    return LearnedAccessRecord(
        access_id=uuid4(),
        actor="release-operator",
        authority="operator",
        target_type="component",
        target_id=fx.INERT.component_id,
        purpose="release evidence",
        decision="allowed",
        recorded_at=fx.FIXTURE_NOW,
    )
