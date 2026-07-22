"""Read-only consistency diagnostics for the procedural Skill Engine."""

from __future__ import annotations

from enum import StrEnum

from pydantic import Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from cognitive_os.domain.base import ImmutableContractModel


class SkillHealthSeverity(StrEnum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


class SkillHealthFinding(ImmutableContractModel):
    code: str
    severity: SkillHealthSeverity
    count: int = Field(ge=0)
    message: str


class SkillHealthReport(ImmutableContractModel):
    healthy: bool
    alembic_revision: str | None
    findings: tuple[SkillHealthFinding, ...]


class PostgresSkillHealthService:
    REQUIRED_TABLES = frozenset(
        {
            "skill_items",
            "skill_revisions",
            "skill_sources",
            "skill_requirements",
            "skill_package_artifacts",
            "skill_executions",
            "skill_execution_steps",
            "skill_statistics",
            "skill_accesses",
        }
    )

    def __init__(self, engine: AsyncEngine) -> None:
        self._engine = engine

    async def check(self) -> SkillHealthReport:
        async with self._engine.connect() as connection:
            revision = await connection.scalar(text("SELECT version_num FROM alembic_version"))
            tables = set(
                (
                    await connection.execute(
                        text(
                            "SELECT tablename FROM pg_tables "
                            "WHERE schemaname='cognitive_os' AND tablename LIKE 'skill_%'"
                        )
                    )
                ).scalars()
            )
            projection_errors = int(
                await connection.scalar(
                    text(
                        "SELECT count(*) FROM cognitive_os.skill_items i "
                        "LEFT JOIN cognitive_os.skill_revisions r "
                        "ON r.skill_id=i.skill_id AND r.revision=i.current_revision "
                        "WHERE r.skill_id IS NULL OR r.status<>i.current_status"
                    )
                )
                or 0
            )
            package_errors = int(
                await connection.scalar(
                    text(
                        "SELECT count(*) FROM cognitive_os.skill_revisions r "
                        "LEFT JOIN cognitive_os.skill_package_artifacts p "
                        "ON p.skill_id=r.skill_id AND p.revision=r.revision "
                        "LEFT JOIN cognitive_os.artifacts a ON a.artifact_id=p.artifact_id "
                        "WHERE p.skill_id IS NULL OR a.artifact_id IS NULL "
                        "OR p.package_hash<>r.package_hash"
                    )
                )
                or 0
            )
            missing_creation_events = int(
                await connection.scalar(
                    text(
                        "SELECT count(*) FROM cognitive_os.skill_items i WHERE NOT EXISTS ("
                        "SELECT 1 FROM cognitive_os.events e "
                        "WHERE e.event_type='skill.created' "
                        "AND e.payload_json->'record'->>'skill_id'=i.skill_id::text)"
                    )
                )
                or 0
            )
            orphan_lifecycle_events = int(
                await connection.scalar(
                    text(
                        "SELECT count(*) FROM cognitive_os.events e "
                        "WHERE e.event_type LIKE 'skill.%' "
                        "AND e.event_type NOT LIKE 'skill.execution_%' "
                        "AND NOT EXISTS (SELECT 1 FROM cognitive_os.skill_items i "
                        "WHERE i.skill_id=e.stream_id)"
                    )
                )
                or 0
            )
            execution_event_mismatch = int(
                await connection.scalar(
                    text(
                        "SELECT count(*) FROM cognitive_os.skill_executions x "
                        "WHERE NOT EXISTS (SELECT 1 FROM cognitive_os.events e "
                        "WHERE e.stream_id=x.execution_id "
                        "AND e.event_type IN "
                        "('skill.execution_completed','skill.execution_failed'))"
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
            ("projection_mismatch", projection_errors, "Current skill projection mismatch"),
            ("package_mismatch", package_errors, "Skill package artifact mismatch"),
            (
                "migration_head",
                int(revision != "0010"),
                f"Expected Alembic revision 0010, found {revision}",
            ),
        )
        findings = tuple(
            SkillHealthFinding(
                code=code,
                severity=SkillHealthSeverity.ERROR if count else SkillHealthSeverity.INFO,
                count=count,
                message=message,
            )
            for code, count, message in checks
        )
        findings += tuple(
            SkillHealthFinding(
                code=code,
                severity=SkillHealthSeverity.WARNING if count else SkillHealthSeverity.INFO,
                count=count,
                message=message,
            )
            for code, count, message in (
                (
                    "missing_creation_events",
                    missing_creation_events,
                    "Skill rows without creation events",
                ),
                (
                    "orphan_lifecycle_events",
                    orphan_lifecycle_events,
                    "Skill lifecycle events without skill rows",
                ),
                (
                    "execution_event_mismatch",
                    execution_event_mismatch,
                    "Skill executions without terminal events",
                ),
            )
        )
        return SkillHealthReport(
            healthy=not any(item.severity is SkillHealthSeverity.ERROR for item in findings),
            alembic_revision=str(revision) if revision is not None else None,
            findings=findings,
        )
