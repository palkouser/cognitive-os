"""The PostgreSQL implementation, bound to the same contract the in-memory one passes.

Beside the suite it binds rather than under `tests/integration/postgres`: a shared contract
that needs a copied import path tends to acquire a second, divergent copy. The cases skip
when the integration URLs are absent, so the credential-free lane collects them and runs
nothing.
"""

from __future__ import annotations

import os
from collections.abc import AsyncIterator
from typing import Any
from uuid import UUID, uuid4

import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from cognitive_os.application.ports.provider_output import ProviderOutputRepositoryPort
from cognitive_os.infrastructure.learned.postgres.provider_output_repository import (
    PostgresProviderOutputRepository,
)
from cognitive_os.infrastructure.learned.postgres.provider_output_tables import (
    PROVIDER_OUTPUT_TABLES,
)
from cognitive_os.infrastructure.postgres.engine import create_postgres_engine

from . import fixtures as fx
from .repository_contract import ProviderOutputRepositoryContract

pytestmark = [pytest.mark.integration, pytest.mark.postgres]

_TRUNCATE = ", ".join(f"cognitive_os.{table.name}" for table in PROVIDER_OUTPUT_TABLES)


def _urls() -> tuple[str, str]:
    app = os.environ.get("COGOS_DATABASE_URL")
    admin = os.environ.get("COGOS_DATABASE_ADMIN_URL")
    if not app or not admin:
        pytest.skip("PostgreSQL integration URLs are not configured")
    return app, admin


@pytest_asyncio.fixture
async def engines() -> AsyncIterator[tuple[AsyncEngine, AsyncEngine]]:
    app_url, admin_url = _urls()
    app = create_postgres_engine(app_url, pool_size=4, max_overflow=4)
    admin = create_postgres_engine(admin_url, pool_size=2, max_overflow=2)
    async with admin.connect() as connection:
        name = await connection.scalar(text("SELECT current_database()"))
        if not str(name).endswith("_test"):
            pytest.fail(f"refusing provider-output integration tests against database: {name}")
    async with admin.begin() as connection:
        await connection.execute(text(f"TRUNCATE {_TRUNCATE} RESTART IDENTITY CASCADE"))
    try:
        yield app, admin
    finally:
        await app.dispose()
        await admin.dispose()


class TestPostgresProviderOutputRepository(ProviderOutputRepositoryContract):
    """The whole shared suite, unchanged, against the real database."""

    @pytest.fixture(autouse=True)
    def _bind(self, engines: tuple[AsyncEngine, AsyncEngine], tmp_path_factory: Any) -> None:
        self._app, self._admin = engines
        self._artifacts = tmp_path_factory.mktemp("artifacts")

    async def make_repository(self) -> ProviderOutputRepositoryPort:
        return PostgresProviderOutputRepository(self._app)

    async def link_evidence(self) -> tuple[UUID, UUID | None, str | None]:
        """Real evidence, because the foreign keys are real.

        A hand-built `events` row would prove the constraint holds against a shape the
        application never produces, and a fabricated `artifacts` row would recreate the
        metadata-without-bytes drift Sprint 21C1 diagnosed. Both go through their services.
        """
        event_id = await fx.seed_completed_model_call(self._admin, model_call_id=uuid4())
        artifact_id, artifact_hash = await fx.seed_artifact(self._admin, self._artifacts)
        return event_id, artifact_id, artifact_hash


class TestTheApplicationRoleCannotRewriteGovernance:
    @pytest.mark.asyncio
    async def test_the_application_role_holds_select_and_execute_only(
        self, engines: tuple[AsyncEngine, AsyncEngine]
    ) -> None:
        """A code bug cannot become a governance rewrite, whatever SQL it constructs."""
        app, _ = engines
        for statement in (
            "UPDATE cognitive_os.provider_output_records SET rights_decision = 'verified'",
            "DELETE FROM cognitive_os.provider_output_records",
        ):
            with pytest.raises(Exception, match="permission denied"):
                async with app.begin() as connection:
                    await connection.execute(text(statement))

    @pytest.mark.asyncio
    async def test_records_survive_a_new_connection_pool(
        self, engines: tuple[AsyncEngine, AsyncEngine]
    ) -> None:
        """Durability, asserted through a genuinely separate engine rather than a cache."""
        app, admin = engines
        repository = PostgresProviderOutputRepository(app)
        event_id = await fx.seed_completed_model_call(admin, model_call_id=uuid4())
        record = await repository.record_output(fx.record(completed_event_id=event_id))

        reopened = create_postgres_engine(os.environ["COGOS_DATABASE_URL"], pool_size=1)
        try:
            restored = await PostgresProviderOutputRepository(reopened).get_latest(
                record.provider_output_id
            )
        finally:
            await reopened.dispose()
        assert restored is not None
        assert restored.content_hash == record.content_hash

    @pytest.mark.asyncio
    async def test_a_payload_that_drifted_from_its_columns_is_visible_on_read(
        self, engines: tuple[AsyncEngine, AsyncEngine]
    ) -> None:
        """The canonical payload is what round-trips; a corrupted one must not validate.

        Only the owner can do this, and doing it requires disabling the append-only trigger,
        which is itself part of the guarantee.
        """
        app, admin = engines
        repository = PostgresProviderOutputRepository(app)
        event_id = await fx.seed_completed_model_call(admin, model_call_id=uuid4())
        record = await repository.record_output(fx.record(completed_event_id=event_id))
        async with admin.begin() as connection:
            await connection.execute(
                text(
                    "ALTER TABLE cognitive_os.provider_output_records "
                    "DISABLE TRIGGER trg_provider_output_records_append_only"
                )
            )
            await connection.execute(
                text(
                    "UPDATE cognitive_os.provider_output_records "
                    "SET payload_json = jsonb_set(payload_json, '{resolved_model}', "
                    "'\"vendor/tampered\"') WHERE provider_output_revision_id = :id"
                ),
                {"id": str(record.provider_output_revision_id)},
            )
            await connection.execute(
                text(
                    "ALTER TABLE cognitive_os.provider_output_records "
                    "ENABLE TRIGGER trg_provider_output_records_append_only"
                )
            )
        with pytest.raises(ValueError, match="hash mismatch"):
            await repository.get_revision(record.provider_output_revision_id)
