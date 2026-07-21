"""Read-only Weakness Mining persistence health checks."""

from pydantic import Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from cognitive_os.domain.base import ImmutableContractModel


class WeaknessHealthReport(ImmutableContractModel):
    healthy: bool
    migration_revision: str | None = None
    table_count: int = Field(ge=0)
    append_only_trigger_count: int = Field(ge=0)
    controlled_function_count: int = Field(ge=0)
    orphan_revision_count: int = Field(ge=0)
    orphan_queue_count: int = Field(ge=0)
    messages: tuple[str, ...] = ()


class PostgresWeaknessHealthService:
    def __init__(self, engine: AsyncEngine) -> None:
        self._engine = engine

    async def check(self) -> WeaknessHealthReport:
        async with self._engine.connect() as connection:
            revision = await connection.scalar(text("SELECT version_num FROM alembic_version"))
            table_count = int(
                await connection.scalar(
                    text(
                        "SELECT count(*) FROM information_schema.tables "
                        "WHERE table_schema='cognitive_os' "
                        "AND table_name LIKE 'weakness_%'"
                    )
                )
                or 0
            )
            trigger_count = int(
                await connection.scalar(
                    text(
                        "SELECT count(*) FROM pg_trigger WHERE NOT tgisinternal "
                        "AND tgname LIKE 'trg_weakness_%_append_only'"
                    )
                )
                or 0
            )
            function_count = int(
                await connection.scalar(
                    text(
                        "SELECT count(*) FROM pg_proc p JOIN pg_namespace n "
                        "ON n.oid=p.pronamespace WHERE n.nspname='cognitive_os' "
                        "AND p.proname IN ('advance_weakness_revision', "
                        "'advance_weakness_mining_status', 'queue_weakness', "
                        "'update_queue_status', 'supersede_queue_entry')"
                    )
                )
                or 0
            )
            orphan_revisions = int(
                await connection.scalar(
                    text(
                        "SELECT count(*) FROM cognitive_os.weakness_revisions r LEFT JOIN "
                        "cognitive_os.weakness_items i USING (weakness_id) "
                        "WHERE i.weakness_id IS NULL"
                    )
                )
                or 0
            )
            orphan_queue = int(
                await connection.scalar(
                    text(
                        "SELECT count(*) FROM cognitive_os.weakness_queue q LEFT JOIN "
                        "cognitive_os.weakness_items i USING (weakness_id) "
                        "WHERE q.record_kind='entry' AND i.weakness_id IS NULL"
                    )
                )
                or 0
            )
        messages = []
        if revision != "0009":
            messages.append(f"Expected Alembic revision 0009, found {revision}")
        if table_count != 10:
            messages.append(f"Expected 10 weakness tables, found {table_count}")
        if trigger_count != 8:
            messages.append(f"Expected 8 append-only triggers, found {trigger_count}")
        if function_count != 5:
            messages.append(f"Expected 5 controlled functions, found {function_count}")
        if orphan_revisions:
            messages.append(f"Found {orphan_revisions} orphan weakness revisions")
        if orphan_queue:
            messages.append(f"Found {orphan_queue} orphan weakness queue entries")
        return WeaknessHealthReport(
            healthy=not messages,
            migration_revision=revision,
            table_count=table_count,
            append_only_trigger_count=trigger_count,
            controlled_function_count=function_count,
            orphan_revision_count=orphan_revisions,
            orphan_queue_count=orphan_queue,
            messages=tuple(messages),
        )
