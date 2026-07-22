"""Read-only consistency diagnostics for the Strategy Evolution Graph."""

from enum import StrEnum

from pydantic import Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from cognitive_os.domain.base import ImmutableContractModel


class StrategyHealthSeverity(StrEnum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


class StrategyHealthFinding(ImmutableContractModel):
    code: str
    severity: StrategyHealthSeverity
    count: int = Field(ge=0)
    message: str


class StrategyHealthReport(ImmutableContractModel):
    healthy: bool
    alembic_revision: str | None
    findings: tuple[StrategyHealthFinding, ...]


class PostgresStrategyHealthService:
    REQUIRED_TABLES = frozenset(
        {
            "strategy_items",
            "strategy_revisions",
            "strategy_sources",
            "strategy_edges",
            "strategy_selections",
            "strategy_outcomes",
            "strategy_statistics",
            "strategy_accesses",
        }
    )

    def __init__(self, engine: AsyncEngine) -> None:
        self._engine = engine

    async def check(self) -> StrategyHealthReport:
        async with self._engine.connect() as connection:
            revision = await connection.scalar(text("SELECT version_num FROM alembic_version"))
            tables = set(
                (
                    await connection.execute(
                        text(
                            "SELECT tablename FROM pg_tables "
                            "WHERE schemaname='cognitive_os' "
                            "AND tablename LIKE 'strategy_%'"
                        )
                    )
                ).scalars()
            )
            projection_mismatch = int(
                await connection.scalar(
                    text(
                        "SELECT count(*) FROM cognitive_os.strategy_items i "
                        "LEFT JOIN cognitive_os.strategy_revisions r "
                        "ON r.strategy_id=i.strategy_id "
                        "AND r.revision=i.current_revision "
                        "WHERE r.strategy_id IS NULL OR r.status<>i.current_status"
                    )
                )
                or 0
            )
            outcome_without_selection = int(
                await connection.scalar(
                    text(
                        "SELECT count(*) FROM cognitive_os.strategy_outcomes o "
                        "LEFT JOIN cognitive_os.strategy_selections s "
                        "ON s.selection_id=o.selection_id WHERE s.selection_id IS NULL"
                    )
                )
                or 0
            )
            missing_creation_events = int(
                await connection.scalar(
                    text(
                        "SELECT count(*) FROM cognitive_os.strategy_items i WHERE NOT EXISTS ("
                        "SELECT 1 FROM cognitive_os.events e "
                        "WHERE e.event_type='strategy.created' "
                        "AND e.payload_json->'record'->>'strategy_id'=i.strategy_id::text)"
                    )
                )
                or 0
            )
            selections_without_snapshot = int(
                await connection.scalar(
                    text(
                        "SELECT count(*) FROM cognitive_os.strategy_selections "
                        "WHERE payload_json->'registry_snapshot' IS NULL"
                    )
                )
                or 0
            )
            append_only_triggers = int(
                await connection.scalar(
                    text(
                        "SELECT count(*) FROM pg_trigger t "
                        "JOIN pg_class c ON c.oid=t.tgrelid "
                        "JOIN pg_namespace n ON n.oid=c.relnamespace "
                        "WHERE n.nspname='cognitive_os' "
                        "AND t.tgname LIKE 'trg_strategy_%_append_only' "
                        "AND NOT t.tgisinternal"
                    )
                )
                or 0
            )
            excessive_app_grants = int(
                await connection.scalar(
                    text(
                        "SELECT count(*) FROM unnest(ARRAY["
                        "'strategy_items','strategy_revisions','strategy_sources',"
                        "'strategy_edges','strategy_selections','strategy_outcomes',"
                        "'strategy_statistics','strategy_accesses']) AS value(table_name) "
                        "WHERE has_table_privilege('cogos_app', "
                        "'cognitive_os.' || table_name, 'UPDATE, DELETE, TRUNCATE')"
                    )
                )
                or 0
            )
            missing_app_grants = int(
                await connection.scalar(
                    text(
                        "SELECT count(*) FROM unnest(ARRAY["
                        "'strategy_items','strategy_revisions','strategy_sources',"
                        "'strategy_edges','strategy_selections','strategy_outcomes',"
                        "'strategy_statistics','strategy_accesses']) AS value(table_name) "
                        "WHERE NOT has_table_privilege('cogos_app', "
                        "'cognitive_os.' || table_name, 'SELECT') "
                        "OR NOT has_table_privilege('cogos_app', "
                        "'cognitive_os.' || table_name, 'INSERT')"
                    )
                )
                or 0
            )
        checks = (
            (
                "missing_tables",
                len(self.REQUIRED_TABLES - tables),
                f"Missing tables: {sorted(self.REQUIRED_TABLES - tables)}",
            ),
            (
                "migration_head",
                int(revision != "0010"),
                f"Expected Alembic revision 0010, found {revision}",
            ),
            (
                "projection_mismatch",
                projection_mismatch,
                "Current strategy projection mismatch",
            ),
            (
                "outcome_without_selection",
                outcome_without_selection,
                "Strategy outcomes without exact selections",
            ),
            (
                "selection_without_registry_snapshot",
                selections_without_snapshot,
                "Strategy selections without registry snapshots",
            ),
            (
                "append_only_triggers",
                int(append_only_triggers != 7),
                f"Expected 7 append-only triggers, found {append_only_triggers}",
            ),
            (
                "missing_app_grants",
                missing_app_grants,
                "Runtime role lacks required strategy SELECT or INSERT grants",
            ),
            (
                "excessive_app_grants",
                excessive_app_grants,
                "Runtime role has forbidden strategy mutation grants",
            ),
        )
        findings = tuple(
            StrategyHealthFinding(
                code=code,
                severity=StrategyHealthSeverity.ERROR if count else StrategyHealthSeverity.INFO,
                count=count,
                message=message,
            )
            for code, count, message in checks
        )
        findings += (
            StrategyHealthFinding(
                code="missing_creation_events",
                severity=(
                    StrategyHealthSeverity.WARNING
                    if missing_creation_events
                    else StrategyHealthSeverity.INFO
                ),
                count=missing_creation_events,
                message="Strategy rows without creation events",
            ),
        )
        return StrategyHealthReport(
            healthy=not any(item.severity is StrategyHealthSeverity.ERROR for item in findings),
            alembic_revision=str(revision) if revision is not None else None,
            findings=findings,
        )
