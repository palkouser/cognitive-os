"""Read-only controlled-change persistence and authority health checks."""

from hashlib import sha256

from pydantic import Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from cognitive_os.changes.service import (
    MANDATORY_ISOLATION_CAPABILITIES,
    ChangeSurfaceRegistry,
)
from cognitive_os.domain.base import ImmutableContractModel
from cognitive_os.events.catalog import build_default_event_catalog
from cognitive_os.events.change_events import CHANGE_EVENT_MODELS


class ChangeHealthReport(ImmutableContractModel):
    healthy: bool
    migration_revision: str | None = None
    table_count: int = Field(ge=0)
    append_only_trigger_count: int = Field(ge=0)
    controlled_function_count: int = Field(ge=0)
    forbidden_runtime_privilege_count: int = Field(ge=0)
    orphan_revision_count: int = Field(ge=0)
    projection_mismatch_count: int = Field(ge=0)
    event_type_count: int = Field(ge=0)
    isolation_capability_count: int = Field(ge=0)
    registry_hash: str
    isolation_registry_hash: str
    messages: tuple[str, ...] = ()


class PostgresChangeHealthService:
    def __init__(self, engine: AsyncEngine) -> None:
        self._engine = engine

    async def check(self) -> ChangeHealthReport:
        async with self._engine.connect() as connection:
            revision = await connection.scalar(text("SELECT version_num FROM alembic_version"))
            table_count = int(
                await connection.scalar(
                    text(
                        "SELECT count(*) FROM information_schema.tables "
                        "WHERE table_schema='cognitive_os' AND table_name LIKE 'change_%'"
                    )
                )
                or 0
            )
            trigger_count = int(
                await connection.scalar(
                    text(
                        "SELECT count(*) FROM pg_trigger WHERE NOT tgisinternal "
                        "AND tgname LIKE 'trg_change_%_append_only'"
                    )
                )
                or 0
            )
            function_count = int(
                await connection.scalar(
                    text(
                        "SELECT count(*) FROM pg_proc p JOIN pg_namespace n "
                        "ON n.oid=p.pronamespace WHERE n.nspname='cognitive_os' "
                        "AND p.proname IN ('create_change_experiment',"
                        "'append_change_experiment_revision','record_change_component',"
                        "'record_change_promotion','record_change_access')"
                    )
                )
                or 0
            )
            forbidden_privileges = int(
                await connection.scalar(
                    text(
                        "SELECT count(*) FROM information_schema.tables "
                        "WHERE table_schema='cognitive_os' AND table_name LIKE 'change_%' "
                        "AND (has_table_privilege('cogos_app', "
                        "quote_ident(table_schema)||'.'||quote_ident(table_name), 'UPDATE') "
                        "OR has_table_privilege('cogos_app', "
                        "quote_ident(table_schema)||'.'||quote_ident(table_name), 'DELETE') "
                        "OR has_table_privilege('cogos_app', "
                        "quote_ident(table_schema)||'.'||quote_ident(table_name), 'INSERT'))"
                    )
                )
                or 0
            )
            orphan_revisions = int(
                await connection.scalar(
                    text(
                        "SELECT count(*) FROM cognitive_os.change_experiment_revisions r "
                        "LEFT JOIN cognitive_os.change_experiments e USING (experiment_id) "
                        "WHERE e.experiment_id IS NULL"
                    )
                )
                or 0
            )
            projection_mismatches = int(
                await connection.scalar(
                    text(
                        "SELECT count(*) FROM cognitive_os.change_experiments e "
                        "LEFT JOIN cognitive_os.change_experiment_revisions r "
                        "ON r.experiment_id=e.experiment_id "
                        "AND r.revision=e.current_revision WHERE r.experiment_id IS NULL "
                        "OR r.content_hash<>e.current_content_hash"
                    )
                )
                or 0
            )
        catalog = build_default_event_catalog().list_event_types()
        event_count = sum((model.event_type, 1) in catalog for model in CHANGE_EVENT_MODELS)
        expected = (
            (revision, "0011", "migration revision"),
            (table_count, 11, "change table count"),
            (trigger_count, 10, "append-only trigger count"),
            (function_count, 5, "controlled function count"),
            (forbidden_privileges, 0, "forbidden runtime privilege count"),
            (orphan_revisions, 0, "orphan revision count"),
            (projection_mismatches, 0, "projection mismatch count"),
            (event_count, 14, "change event type count"),
            (
                len(MANDATORY_ISOLATION_CAPABILITIES),
                11,
                "isolation capability count",
            ),
        )
        messages = tuple(
            f"Expected {name} {wanted}, found {actual}"
            for actual, wanted, name in expected
            if actual != wanted
        )
        registry = ChangeSurfaceRegistry()
        return ChangeHealthReport(
            healthy=not messages,
            migration_revision=str(revision) if revision else None,
            table_count=table_count,
            append_only_trigger_count=trigger_count,
            controlled_function_count=function_count,
            forbidden_runtime_privilege_count=forbidden_privileges,
            orphan_revision_count=orphan_revisions,
            projection_mismatch_count=projection_mismatches,
            event_type_count=event_count,
            isolation_capability_count=len(MANDATORY_ISOLATION_CAPABILITIES),
            registry_hash=registry.content_hash,
            isolation_registry_hash=sha256(
                "|".join(MANDATORY_ISOLATION_CAPABILITIES).encode()
            ).hexdigest(),
            messages=messages,
        )
