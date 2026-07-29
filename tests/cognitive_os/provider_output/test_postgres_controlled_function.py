"""Direct coverage of the migration `0015` controlled write function.

This file exists because of a specific Sprint 21C1 defect. Migration `0014` applied cleanly,
its triggers inspected correctly, and its generic record functions produced PostgreSQL
`text` for every uuid, integer, boolean and timestamptz column — so every append failed the
first time the repository actually called one. Applying a migration is not evidence that its
functions work.

Every test here invokes `cognitive_os.record_provider_output` itself and asserts on the
*column types* the row came back with, not merely on the row's existence.
"""

from __future__ import annotations

import os
from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID, uuid4

import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from cognitive_os.domain.provider_output import (
    ProviderOutputRecord,
    ProviderOutputRetentionMode,
    UsageRightsDecision,
)
from cognitive_os.infrastructure.learned.postgres.provider_output_tables import (
    PROVIDER_OUTPUT_TABLES,
)
from cognitive_os.infrastructure.postgres.engine import create_postgres_engine

from . import fixtures as fx

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


async def _call(engine: AsyncEngine, record: ProviderOutputRecord) -> bool:
    async with engine.begin() as connection:
        appended = await connection.scalar(
            text("SELECT cognitive_os.record_provider_output(CAST(:payload AS jsonb))"),
            {"payload": record.model_dump_json()},
        )
    return bool(appended)


async def _row(engine: AsyncEngine, revision_id: UUID) -> dict[str, object]:
    async with engine.connect() as connection:
        result = await connection.execute(
            text(
                "SELECT * FROM cognitive_os.provider_output_records "
                "WHERE provider_output_revision_id = :id"
            ),
            {"id": str(revision_id)},
        )
        return dict(result.mappings().one())


@pytest.mark.asyncio
async def test_the_controlled_function_writes_every_declared_postgresql_type(
    engines: tuple[AsyncEngine, AsyncEngine], tmp_path: Path
) -> None:
    """The `0014` defect, asserted directly: uuid stays uuid, integer stays integer.

    The record deliberately fills every nullable column and every non-text type at once —
    uuid, integer, boolean, timestamptz, enum-constrained text, jsonb and an artifact
    reference — so one call covers the whole surface.
    """
    app, admin = engines
    model_call_id = uuid4()
    event_id = await fx.seed_completed_model_call(admin, model_call_id=model_call_id)
    artifact_id, artifact_hash = await fx.seed_artifact(admin, tmp_path / "artifacts")
    recorded_at = datetime(2026, 7, 27, 12, 0, tzinfo=UTC)
    record = fx.record(
        model_call_id=model_call_id,
        completed_event_id=event_id,
        retention_mode=ProviderOutputRetentionMode.NORMALIZED_CONTENT,
        response_artifact_id=artifact_id,
        response_artifact_hash=artifact_hash,
        recorded_at=recorded_at,
        expires_at=recorded_at + timedelta(days=30),
        prompt_template_id="synthetic-advisory",
        prompt_template_version="1",
        human_reviewer="operator",
        input_source_ids=("fixture:defect-1",),
        input_source_hashes=(fx.HASH_A,),
    )

    assert await _call(app, record) is True
    row = await _row(app, record.provider_output_revision_id)

    assert isinstance(row["provider_output_revision_id"], UUID)
    assert isinstance(row["provider_output_id"], UUID)
    assert isinstance(row["model_call_id"], UUID)
    assert isinstance(row["completed_event_id"], UUID)
    assert isinstance(row["response_artifact_id"], UUID)
    assert isinstance(row["revision"], int) and not isinstance(row["revision"], bool)
    assert row["physical_deletion_required"] is False
    assert isinstance(row["recorded_at"], datetime) and row["recorded_at"].tzinfo is not None
    assert isinstance(row["expires_at"], datetime) and row["expires_at"].tzinfo is not None
    assert isinstance(row["payload_json"], dict)
    assert row["previous_revision_id"] is None

    # The canonical payload is what round-trips; the typed columns exist for constraints,
    # indexes and health. A column that drifted from its payload is a health failure.
    restored = ProviderOutputRecord.model_validate(row["payload_json"])
    assert restored.content_hash == record.content_hash
    assert restored.input_source_ids == ("fixture:defect-1",)


@pytest.mark.asyncio
async def test_identical_replay_is_idempotent_and_changed_content_is_refused(
    engines: tuple[AsyncEngine, AsyncEngine],
) -> None:
    app, admin = engines
    model_call_id = uuid4()
    event_id = await fx.seed_completed_model_call(admin, model_call_id=model_call_id)
    record = fx.record(model_call_id=model_call_id, completed_event_id=event_id)

    assert await _call(app, record) is True
    assert await _call(app, record) is False

    conflicting = fx.record(
        model_call_id=model_call_id,
        completed_event_id=event_id,
        provider_output_revision_id=uuid4(),
        provider_output_id=uuid4(),
        resolved_model="vendor/other:free",
    )
    with pytest.raises(Exception, match="idempotency key reused"):
        await _call(app, conflicting)


@pytest.mark.asyncio
async def test_a_revision_must_follow_its_predecessor(
    engines: tuple[AsyncEngine, AsyncEngine],
) -> None:
    """A correction is a new revision, and a revision that skips or forks is refused."""
    app, admin = engines
    model_call_id = uuid4()
    event_id = await fx.seed_completed_model_call(admin, model_call_id=model_call_id)
    first = fx.record(model_call_id=model_call_id, completed_event_id=event_id)
    assert await _call(app, first) is True

    gap = fx.superseding_record(first, revision=3, idempotency_key="provider-output:fixture:r3")
    with pytest.raises(Exception, match="revision conflict"):
        await _call(app, gap)

    orphan = fx.superseding_record(
        first,
        previous_revision_id=uuid4(),
        idempotency_key="provider-output:fixture:orphan",
    )
    with pytest.raises(Exception, match="broken lineage"):
        await _call(app, orphan)

    second = fx.superseding_record(first, rights_decision=UsageRightsDecision.PROHIBITED)
    assert await _call(app, second) is True

    duplicate = fx.superseding_record(
        first,
        provider_output_revision_id=uuid4(),
        idempotency_key="provider-output:fixture:duplicate",
    )
    with pytest.raises(Exception, match="revision conflict"):
        await _call(app, duplicate)


@pytest.mark.asyncio
async def test_the_ledger_refuses_update_and_delete_and_the_app_role_cannot_insert(
    engines: tuple[AsyncEngine, AsyncEngine],
) -> None:
    """SELECT plus EXECUTE for the application role; append-only even for the owner."""
    app, admin = engines
    model_call_id = uuid4()
    event_id = await fx.seed_completed_model_call(admin, model_call_id=model_call_id)
    record = fx.record(model_call_id=model_call_id, completed_event_id=event_id)
    assert await _call(app, record) is True

    for engine, expected in ((app, "permission denied"), (admin, "append-only")):
        with pytest.raises(Exception, match=expected):
            async with engine.begin() as connection:
                await connection.execute(
                    text(
                        "UPDATE cognitive_os.provider_output_records "
                        "SET rights_decision = 'verified'"
                    )
                )
        with pytest.raises(Exception, match=expected):
            async with engine.begin() as connection:
                await connection.execute(text("DELETE FROM cognitive_os.provider_output_records"))

    with pytest.raises(Exception, match="permission denied"):
        async with app.begin() as connection:
            await connection.execute(
                text(
                    "INSERT INTO cognitive_os.provider_output_records "
                    "(provider_output_revision_id, provider_output_id, revision, "
                    "schema_version, model_call_id, provider_id, adapter_kind, "
                    "requested_model, resolved_model, request_hash, "
                    "normalized_response_hash, completed_event_id, parameter_hash, "
                    "intended_use, rights_decision, sensitivity, secret_scan_status, "
                    "retention_mode, physical_deletion_required, verifier_status, "
                    "recorded_by, idempotency_key, payload_json, content_hash) VALUES "
                    "(gen_random_uuid(), gen_random_uuid(), 1, '1', gen_random_uuid(), "
                    "'x', 'mock', 'm', 'm', :h, :h, :e, :h, 'transient_advice', "
                    "'unknown', 'public', 'not_run', 'none', false, 'not_run', 'x', "
                    "'direct-insert', '{}'::jsonb, :h)"
                ),
                {"h": "a" * 64, "e": str(event_id)},
            )


@pytest.mark.asyncio
async def test_a_governance_record_cannot_outlive_its_lifecycle_event(
    engines: tuple[AsyncEngine, AsyncEngine],
) -> None:
    """The foreign key is real: an unknown completed-event ID is refused at write time."""
    app, _ = engines
    record = fx.record(completed_event_id=uuid4(), idempotency_key="provider-output:no-event")
    with pytest.raises(Exception, match=r"foreign key|violates"):
        await _call(app, record)
