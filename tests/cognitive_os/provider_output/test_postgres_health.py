"""Provider-output governance health: integrity failures against provider availability.

The split is the point. A damaged ledger must be loud; an unreachable teacher must not be.
Sprint 21C1 established the rule for learned evidence and it holds here for the same reason:
if an OpenRouter outage made governance unhealthy, the alarm that means "your retention
decisions are corrupt" would be the one nobody trusted.
"""

from __future__ import annotations

import os
from collections.abc import AsyncIterator
from datetime import timedelta
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from cognitive_os.domain.common import ErrorInfo, utc_now
from cognitive_os.domain.provider import ProviderHealth, ProviderStatus
from cognitive_os.domain.provider_output import (
    ProviderOutputIntendedUse,
    ProviderOutputRetentionMode,
    UsageRightsDecision,
)
from cognitive_os.infrastructure.learned.postgres.provider_output_health import (
    PostgresProviderOutputHealthService,
)
from cognitive_os.infrastructure.learned.postgres.provider_output_repository import (
    PostgresProviderOutputRepository,
)
from cognitive_os.infrastructure.postgres.engine import (
    TruncationNotNominated,
    TruncationRefused,
    create_postgres_engine,
    require_nominated_for_truncation,
)

from . import fixtures as fx

pytestmark = [pytest.mark.integration, pytest.mark.postgres]


def _urls() -> tuple[str, str]:
    app = os.environ.get("COGOS_DATABASE_URL")
    admin = os.environ.get("COGOS_DATABASE_ADMIN_URL")
    if not app or not admin:
        pytest.skip("PostgreSQL integration URLs are not configured")
    return app, admin


@pytest_asyncio.fixture
async def engines() -> AsyncIterator[tuple[AsyncEngine, AsyncEngine]]:
    app_url, admin_url = _urls()
    app = create_postgres_engine(app_url, pool_size=2, max_overflow=2)
    admin = create_postgres_engine(admin_url, pool_size=2, max_overflow=2)
    async with admin.connect() as connection:
        name = await connection.scalar(text("SELECT current_database()"))
        if not str(name).endswith("_test"):
            pytest.fail(f"refusing governance health tests against database: {name}")
        # W7-F1. "Ends with `_test`" is a naming convention, not consent: every sprint's
        # evidence database ends in `_test` too, and on 2026-08-07 a release-matrix run with the
        # D4 environment sourced put one in front of this fixture, which truncated 1,076
        # committed observations. The rule is the one W6-F2 and D4-W0-F1 already established,
        # reached through its single implementation rather than copied beside a sixth TRUNCATE.
        try:
            require_nominated_for_truncation(str(name))
        except TruncationNotNominated as reason:
            pytest.skip(str(reason))
        except TruncationRefused as reason:
            pytest.fail(str(reason))
    async with admin.begin() as connection:
        await connection.execute(
            text("TRUNCATE cognitive_os.provider_output_records RESTART IDENTITY CASCADE")
        )
    try:
        yield app, admin
    finally:
        await app.dispose()
        await admin.dispose()


class TestAHealthyLedger:
    @pytest.mark.asyncio
    async def test_an_empty_ledger_is_healthy(
        self, engines: tuple[AsyncEngine, AsyncEngine]
    ) -> None:
        app, _ = engines
        report = await PostgresProviderOutputHealthService(app).check()
        assert report.healthy is True
        assert report.integrity_failures == ()
        assert report.migration_revision == "0015"
        assert report.table_count == 1
        assert report.append_only_trigger_count == 1
        assert report.controlled_function_count == 1

    @pytest.mark.asyncio
    async def test_counts_reflect_what_was_recorded(
        self, engines: tuple[AsyncEngine, AsyncEngine]
    ) -> None:
        app, admin = engines
        repository = PostgresProviderOutputRepository(app)
        event_id = await fx.seed_completed_model_call(admin, model_call_id=uuid4())
        first = await repository.record_output(fx.record(completed_event_id=event_id))
        await repository.record_output(
            fx.superseding_record(first, rights_decision=UsageRightsDecision.PROHIBITED)
        )
        report = await PostgresProviderOutputHealthService(app).check()
        assert report.healthy is True
        assert report.output_count == 1
        assert report.revision_count == 2
        assert report.payload_rows_verified == 2

    @pytest.mark.asyncio
    async def test_an_expired_revision_is_counted_not_treated_as_damage(
        self, engines: tuple[AsyncEngine, AsyncEngine]
    ) -> None:
        """Expiry is an eligibility rule. A lapsed decision is correctly recorded history."""
        app, admin = engines
        repository = PostgresProviderOutputRepository(app)
        event_id = await fx.seed_completed_model_call(admin, model_call_id=uuid4())
        expiry = fx.FIXTURE_NOW + timedelta(hours=1)
        await repository.record_output(fx.record(completed_event_id=event_id, expires_at=expiry))
        report = await PostgresProviderOutputHealthService(app).check(
            moment=expiry + timedelta(hours=1)
        )
        assert report.healthy is True
        assert report.expired_count == 1


class TestIntegrityFailuresAreLoud:
    @pytest.mark.asyncio
    async def test_a_payload_that_no_longer_hashes_is_an_integrity_failure(
        self, engines: tuple[AsyncEngine, AsyncEngine]
    ) -> None:
        app, admin = engines
        repository = PostgresProviderOutputRepository(app)
        event_id = await fx.seed_completed_model_call(admin, model_call_id=uuid4())
        record = await repository.record_output(fx.record(completed_event_id=event_id))
        await _tamper(
            admin,
            "SET payload_json = jsonb_set(payload_json, '{resolved_model}', "
            "'\"vendor/tampered\"') WHERE provider_output_revision_id = :id",
            {"id": str(record.provider_output_revision_id)},
        )
        report = await PostgresProviderOutputHealthService(app).check()
        assert report.healthy is False
        assert any("no longer validates" in failure for failure in report.integrity_failures)

    @pytest.mark.asyncio
    async def test_a_gap_in_a_revision_chain_is_an_integrity_failure(
        self, engines: tuple[AsyncEngine, AsyncEngine]
    ) -> None:
        """History that cannot be replayed is not history."""
        app, admin = engines
        repository = PostgresProviderOutputRepository(app)
        event_id = await fx.seed_completed_model_call(admin, model_call_id=uuid4())
        first = await repository.record_output(fx.record(completed_event_id=event_id))
        await repository.record_output(fx.superseding_record(first))
        await _tamper(
            admin,
            "DELETE_ROW WHERE provider_output_revision_id = :id",
            {"id": str(first.provider_output_revision_id)},
        )
        report = await PostgresProviderOutputHealthService(app).check()
        assert report.healthy is False
        assert any("gap or a fork" in failure for failure in report.integrity_failures)

    @pytest.mark.asyncio
    async def test_a_missing_controlled_function_is_an_integrity_failure(
        self, engines: tuple[AsyncEngine, AsyncEngine]
    ) -> None:
        app, admin = engines
        async with admin.begin() as connection:
            await connection.execute(
                text("ALTER FUNCTION cognitive_os.record_provider_output(jsonb) RENAME TO tmp_fn")
            )
        try:
            report = await PostgresProviderOutputHealthService(app).check()
            assert report.healthy is False
            assert any("controlled write function" in item for item in report.integrity_failures)
        finally:
            async with admin.begin() as connection:
                await connection.execute(
                    text(
                        "ALTER FUNCTION cognitive_os.tmp_fn(jsonb) RENAME TO record_provider_output"
                    )
                )


class TestProviderAvailabilityIsNotCorruption:
    @pytest.mark.asyncio
    async def test_an_unreachable_provider_is_a_warning_and_never_unhealthy(
        self, engines: tuple[AsyncEngine, AsyncEngine]
    ) -> None:
        app, _ = engines
        offline = ProviderHealth(
            provider_id="openrouter",
            status=ProviderStatus.UNAVAILABLE,
            checked_at=utc_now(),
            message="catalog is unreachable",
            error=ErrorInfo(code="provider_connection", message="catalog is unreachable"),
        )
        report = await PostgresProviderOutputHealthService(app).check(provider_health=(offline,))
        assert report.healthy is True
        assert report.integrity_failures == ()
        assert report.provider_warnings == ("openrouter is unavailable: catalog is unreachable",)

    @pytest.mark.asyncio
    async def test_an_available_provider_produces_no_warning(
        self, engines: tuple[AsyncEngine, AsyncEngine]
    ) -> None:
        app, _ = engines
        online = ProviderHealth(
            provider_id="codex-cli",
            status=ProviderStatus.AVAILABLE,
            checked_at=utc_now(),
            message="Codex 0.144.6 accepts the safety profile",
        )
        report = await PostgresProviderOutputHealthService(app).check(provider_health=(online,))
        assert report.provider_warnings == ()


class TestRestartAndResolution:
    @pytest.mark.asyncio
    async def test_source_resolution_still_works_after_a_new_connection_pool(
        self, engines: tuple[AsyncEngine, AsyncEngine]
    ) -> None:
        """Restart durability where it matters: the intake reference is still resolvable."""
        app, admin = engines
        repository = PostgresProviderOutputRepository(app)
        event_id = await fx.seed_completed_model_call(admin, model_call_id=uuid4())
        record = await repository.record_output(fx.record(completed_event_id=event_id))

        reopened = create_postgres_engine(os.environ["COGOS_DATABASE_URL"], pool_size=1)
        try:
            reference = await PostgresProviderOutputRepository(reopened).resolve_source(
                record.provider_output_id, surface="advisory", moment=fx.FIXTURE_NOW
            )
            eligible = await PostgresProviderOutputRepository(reopened).list_eligible(
                intended_use=ProviderOutputIntendedUse.CORPUS_CANDIDATE,
                moment=fx.FIXTURE_NOW,
            )
        finally:
            await reopened.dispose()
        assert reference.source_kind == "openrouter_advisory"
        assert len(eligible) == 1
        assert eligible[0].retention_mode is ProviderOutputRetentionMode.HASH_ONLY


async def _tamper(admin: AsyncEngine, clause: str, parameters: dict[str, str]) -> None:
    """Corrupt the ledger on purpose, which requires disabling the append-only trigger.

    That it takes this much to damage the store is itself part of the guarantee being
    tested: nothing an application role can do reaches here.
    """
    statement = (
        "DELETE FROM cognitive_os.provider_output_records " + clause.removeprefix("DELETE_ROW ")
        if clause.startswith("DELETE_ROW")
        else f"UPDATE cognitive_os.provider_output_records {clause}"
    )
    async with admin.begin() as connection:
        await connection.execute(
            text(
                "ALTER TABLE cognitive_os.provider_output_records "
                "DISABLE TRIGGER trg_provider_output_records_append_only"
            )
        )
        await connection.execute(text(statement), parameters)
        await connection.execute(
            text(
                "ALTER TABLE cognitive_os.provider_output_records "
                "ENABLE TRIGGER trg_provider_output_records_append_only"
            )
        )
