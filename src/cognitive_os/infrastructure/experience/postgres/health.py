"""Read-only Experience Compiler persistence health checks."""

from pydantic import Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from cognitive_os.domain.base import ImmutableContractModel


class ExperienceHealthReport(ImmutableContractModel):
    healthy: bool
    migration_revision: str | None = None
    table_count: int = Field(ge=0)
    append_only_trigger_count: int = Field(ge=0)
    controlled_function_count: int = Field(ge=0)
    orphan_source_count: int = Field(ge=0)
    missing_manifest_count: int = Field(ge=0)
    decision_without_verifier_count: int = Field(ge=0)
    access_gap_count: int = Field(ge=0)
    prohibited_configuration_enabled: bool = False
    messages: tuple[str, ...] = ()


class PostgresExperienceHealthService:
    def __init__(self, engine: AsyncEngine) -> None:
        self._engine = engine

    async def check(self) -> ExperienceHealthReport:
        messages: list[str] = []
        async with self._engine.connect() as connection:
            revision = await connection.scalar(text("SELECT version_num FROM alembic_version"))
            table_count = int(
                await connection.scalar(
                    text(
                        "SELECT count(*) FROM information_schema.tables "
                        "WHERE table_schema='cognitive_os' AND table_name LIKE 'experience_%'"
                    )
                )
                or 0
            )
            trigger_count = int(
                await connection.scalar(
                    text(
                        "SELECT count(*) FROM pg_trigger WHERE NOT tgisinternal "
                        "AND tgname LIKE 'trg_experience_%_append_only'"
                    )
                )
                or 0
            )
            function_count = int(
                await connection.scalar(
                    text(
                        "SELECT count(*) FROM pg_proc p JOIN pg_namespace n "
                        "ON n.oid=p.pronamespace "
                        "WHERE n.nspname='cognitive_os' AND p.proname IN "
                        "('finalize_experience_compilation','advance_experience_candidate')"
                    )
                )
                or 0
            )
            orphan_sources = int(
                await connection.scalar(
                    text(
                        "SELECT count(*) FROM cognitive_os.experience_sources s "
                        "LEFT JOIN cognitive_os.experience_compilations c USING (compilation_id) "
                        "WHERE c.compilation_id IS NULL"
                    )
                )
                or 0
            )
            missing_manifests = int(
                await connection.scalar(
                    text(
                        "SELECT count(*) FROM cognitive_os.experience_compilations "
                        "WHERE current_status='completed' AND manifest_hash IS NULL"
                    )
                )
                or 0
            )
            missing_verifiers = int(
                await connection.scalar(
                    text(
                        "SELECT count(*) FROM cognitive_os.experience_decisions "
                        "WHERE verifier_bundle_hash IS NULL "
                        "OR verifier_bundle_hash !~ '^[0-9a-f]{64}$'"
                    )
                )
                or 0
            )
            access_gaps = int(
                await connection.scalar(
                    text(
                        "SELECT count(*) FROM cognitive_os.experience_compilations c "
                        "WHERE c.current_status='completed' AND NOT EXISTS ("
                        "SELECT 1 FROM cognitive_os.experience_accesses a "
                        "WHERE a.compilation_id=c.compilation_id)"
                    )
                )
                or 0
            )
        if revision != "0007":
            messages.append(f"Expected Alembic revision 0007, found {revision}")
        if table_count != 9:
            messages.append(f"Expected 9 Experience Compiler tables, found {table_count}")
        if trigger_count != 7:
            messages.append(f"Expected 7 append-only triggers, found {trigger_count}")
        if function_count != 2:
            messages.append(f"Expected 2 controlled functions, found {function_count}")
        if orphan_sources:
            messages.append(f"Found {orphan_sources} orphan source rows")
        if missing_manifests:
            messages.append(f"Found {missing_manifests} completed compilations without manifests")
        if missing_verifiers:
            messages.append(f"Found {missing_verifiers} decisions without verifier evidence")
        if access_gaps:
            messages.append(f"Found {access_gaps} completed compilations without access audit")
        return ExperienceHealthReport(
            healthy=not messages,
            migration_revision=revision,
            table_count=table_count,
            append_only_trigger_count=trigger_count,
            controlled_function_count=function_count,
            orphan_source_count=orphan_sources,
            missing_manifest_count=missing_manifests,
            decision_without_verifier_count=missing_verifiers,
            access_gap_count=access_gaps,
            messages=tuple(messages),
        )
