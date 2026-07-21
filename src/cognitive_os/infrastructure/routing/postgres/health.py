"""Read-only health checks for capability and routing persistence."""

from pydantic import Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from cognitive_os.domain.base import ImmutableContractModel


class RoutingHealthReport(ImmutableContractModel):
    healthy: bool
    migration_revision: str | None = None
    table_count: int = Field(ge=0)
    append_only_trigger_count: int = Field(ge=0)
    controlled_function_count: int = Field(ge=0)
    orphan_outcome_count: int = Field(ge=0)
    invalid_policy_count: int = Field(ge=0)
    access_gap_count: int = Field(ge=0)
    messages: tuple[str, ...] = ()


class PostgresRoutingHealthService:
    def __init__(self, engine: AsyncEngine) -> None:
        self._engine = engine

    async def check(self) -> RoutingHealthReport:
        async with self._engine.connect() as connection:
            revision = await connection.scalar(text("SELECT version_num FROM alembic_version"))
            table_count = int(
                await connection.scalar(
                    text(
                        "SELECT count(*) FROM information_schema.tables "
                        "WHERE table_schema='cognitive_os' AND "
                        "(table_name LIKE 'routing_%' OR table_name LIKE 'model_capability_%')"
                    )
                )
                or 0
            )
            triggers = int(
                await connection.scalar(
                    text(
                        "SELECT count(*) FROM pg_trigger WHERE NOT tgisinternal "
                        "AND tgname LIKE 'trg_%_append_only' AND tgrelid IN ("
                        "SELECT oid FROM pg_class WHERE relnamespace=("
                        "SELECT oid FROM pg_namespace WHERE nspname='cognitive_os'))"
                    )
                )
                or 0
            )
            functions = int(
                await connection.scalar(
                    text(
                        "SELECT count(*) FROM pg_proc p JOIN pg_namespace n "
                        "ON n.oid=p.pronamespace "
                        "WHERE n.nspname='cognitive_os' AND p.proname IN "
                        "('advance_model_capability_profile','advance_routing_policy')"
                    )
                )
                or 0
            )
            orphan_outcomes = int(
                await connection.scalar(
                    text(
                        "SELECT count(*) FROM cognitive_os.routing_outcomes o LEFT JOIN "
                        "cognitive_os.routing_decisions d USING (decision_id) "
                        "WHERE d.decision_id IS NULL"
                    )
                )
                or 0
            )
            invalid_policies = int(
                await connection.scalar(
                    text(
                        "SELECT count(*) FROM cognitive_os.routing_policies WHERE "
                        "(control_mode='shadow' AND current_status='enabled') OR "
                        "(control_mode='adaptive' AND current_status IN ('approved','enabled') "
                        "AND COALESCE(payload_json->>'operator_approval_reference','')='')"
                    )
                )
                or 0
            )
            access_gaps = int(
                await connection.scalar(
                    text(
                        "SELECT count(*) FROM cognitive_os.routing_decisions d WHERE NOT EXISTS "
                        "(SELECT 1 FROM cognitive_os.routing_accesses a "
                        "WHERE a.payload_json->>'decision_id'=d.decision_id::text)"
                    )
                )
                or 0
            )
        messages = []
        if revision != "0009":
            messages.append(f"Expected Alembic revision 0009, found {revision}")
        if table_count != 10:
            messages.append(f"Expected 10 routing tables, found {table_count}")
        if triggers < 8:
            messages.append(f"Expected at least 8 routing append-only triggers, found {triggers}")
        if functions != 2:
            messages.append(f"Expected 2 controlled routing functions, found {functions}")
        if orphan_outcomes:
            messages.append(f"Found {orphan_outcomes} orphan routing outcomes")
        if invalid_policies:
            messages.append(f"Found {invalid_policies} invalid routing policies")
        if access_gaps:
            messages.append(f"Found {access_gaps} decisions without access audit")
        return RoutingHealthReport(
            healthy=not messages,
            migration_revision=revision,
            table_count=table_count,
            append_only_trigger_count=triggers,
            controlled_function_count=functions,
            orphan_outcome_count=orphan_outcomes,
            invalid_policy_count=invalid_policies,
            access_gap_count=access_gaps,
            messages=tuple(messages),
        )
