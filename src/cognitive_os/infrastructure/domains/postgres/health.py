"""Read-only cross-domain pilot persistence health checks."""

from pydantic import Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from cognitive_os.domain.base import ImmutableContractModel
from cognitive_os.infrastructure.postgres.tables import EXPECTED_MIGRATION_REVISION


class DomainHealthReport(ImmutableContractModel):
    healthy: bool
    migration_revision: str | None = None
    table_count: int = Field(ge=0)
    append_only_trigger_count: int = Field(ge=0)
    controlled_function_count: int = Field(ge=0)
    orphan_evidence_count: int = Field(ge=0)
    orphan_transfer_result_count: int = Field(ge=0)
    hard_gate_violation_count: int = Field(ge=0)
    messages: tuple[str, ...] = ()


class PostgresDomainHealthService:
    def __init__(self, engine: AsyncEngine) -> None:
        self._engine = engine

    async def check(self) -> DomainHealthReport:
        messages: list[str] = []
        async with self._engine.connect() as connection:
            revision = await connection.scalar(text("SELECT version_num FROM alembic_version"))
            table_count = int(
                await connection.scalar(
                    text(
                        "SELECT count(*) FROM information_schema.tables "
                        "WHERE table_schema='cognitive_os' AND table_name LIKE 'domain_%'"
                    )
                )
                or 0
            )
            trigger_count = int(
                await connection.scalar(
                    text(
                        "SELECT count(*) FROM pg_trigger WHERE NOT tgisinternal "
                        "AND tgname LIKE 'trg_domain_%_append_only'"
                    )
                )
                or 0
            )
            function_count = int(
                await connection.scalar(
                    text(
                        "SELECT count(*) FROM pg_proc p JOIN pg_namespace n "
                        "ON n.oid=p.pronamespace WHERE n.nspname='cognitive_os' "
                        "AND p.proname IN ('record_domain_pilot_run', "
                        "'record_domain_transfer_result', 'record_domain_access')"
                    )
                )
                or 0
            )
            # Every reference row is bound to exactly one run by a foreign key, so a
            # non-zero count here means the constraint itself has been bypassed or
            # the restored dump omitted the parent row.
            orphan_evidence = int(
                await connection.scalar(
                    text(
                        "SELECT ("
                        "SELECT count(*) FROM cognitive_os.domain_problem_references p "
                        "LEFT JOIN cognitive_os.domain_pilot_runs run USING (run_id) "
                        "WHERE run.run_id IS NULL) + ("
                        "SELECT count(*) FROM cognitive_os.domain_derivation_references d "
                        "LEFT JOIN cognitive_os.domain_pilot_runs run USING (run_id) "
                        "WHERE run.run_id IS NULL) + ("
                        "SELECT count(*) FROM cognitive_os.domain_verification_results v "
                        "LEFT JOIN cognitive_os.domain_pilot_runs run USING (run_id) "
                        "WHERE run.run_id IS NULL) + ("
                        "SELECT count(*) FROM cognitive_os.domain_accesses a "
                        "LEFT JOIN cognitive_os.domain_pilot_runs run USING (run_id) "
                        "WHERE run.run_id IS NULL)"
                    )
                )
                or 0
            )
            orphan_transfer_results = int(
                await connection.scalar(
                    text(
                        "SELECT count(*) FROM cognitive_os.domain_transfer_results r "
                        "LEFT JOIN cognitive_os.domain_transfer_experiments e "
                        "USING (experiment_id) WHERE e.experiment_id IS NULL"
                    )
                )
                or 0
            )
            hard_gate_violations = int(
                await connection.scalar(
                    text(
                        "SELECT count(*) FROM cognitive_os.domain_transfer_results "
                        "WHERE hard_gate_failed AND disposition = 'positive_transfer'"
                    )
                )
                or 0
            )
        if revision != EXPECTED_MIGRATION_REVISION:
            messages.append(
                f"Expected Alembic revision {EXPECTED_MIGRATION_REVISION}, found {revision}"
            )
        if table_count != 7:
            messages.append(f"Expected 7 cross-domain pilot tables, found {table_count}")
        if trigger_count != 6:
            messages.append(f"Expected 6 append-only triggers, found {trigger_count}")
        if function_count != 3:
            messages.append(f"Expected 3 controlled functions, found {function_count}")
        if orphan_evidence:
            messages.append(f"Found {orphan_evidence} evidence rows without a parent run")
        if orphan_transfer_results:
            messages.append(
                f"Found {orphan_transfer_results} transfer results without an experiment"
            )
        if hard_gate_violations:
            messages.append(
                f"Found {hard_gate_violations} positive-transfer results with a hard gate failure"
            )
        return DomainHealthReport(
            healthy=not messages,
            migration_revision=revision,
            table_count=table_count,
            append_only_trigger_count=trigger_count,
            controlled_function_count=function_count,
            orphan_evidence_count=orphan_evidence,
            orphan_transfer_result_count=orphan_transfer_results,
            hard_gate_violation_count=hard_gate_violations,
            messages=tuple(messages),
        )
