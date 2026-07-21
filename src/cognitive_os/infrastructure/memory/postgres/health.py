"""Read-only Memory Plane health and consistency diagnostics."""

from __future__ import annotations

from enum import StrEnum

from pydantic import Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from cognitive_os.domain.base import ImmutableContractModel


class MemoryHealthSeverity(StrEnum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


class MemoryHealthFinding(ImmutableContractModel):
    code: str
    severity: MemoryHealthSeverity
    count: int = Field(ge=0)
    message: str


class MemoryHealthReport(ImmutableContractModel):
    healthy: bool
    alembic_revision: str | None
    vector_version: str | None
    findings: tuple[MemoryHealthFinding, ...]


class PostgresMemoryHealthService:
    REQUIRED_TABLES = frozenset(
        {
            "memory_items",
            "memory_revisions",
            "memory_sources",
            "memory_embeddings",
            "memory_accesses",
        }
    )

    def __init__(self, engine: AsyncEngine) -> None:
        self._engine = engine

    async def check(self) -> MemoryHealthReport:
        findings: list[MemoryHealthFinding] = []
        async with self._engine.connect() as connection:
            revision = await connection.scalar(text("SELECT version_num FROM alembic_version"))
            vector_version = await connection.scalar(
                text("SELECT extversion FROM pg_extension WHERE extname='vector'")
            )
            tables = set(
                (
                    await connection.execute(
                        text(
                            "SELECT tablename FROM pg_tables "
                            "WHERE schemaname='cognitive_os' AND tablename LIKE 'memory_%'"
                        )
                    )
                ).scalars()
            )
            approximate_indexes = int(
                await connection.scalar(
                    text(
                        "SELECT count(*) FROM pg_indexes WHERE schemaname='cognitive_os' "
                        "AND (indexdef ILIKE '%hnsw%' OR indexdef ILIKE '%ivfflat%')"
                    )
                )
                or 0
            )
            projection_errors = int(
                await connection.scalar(
                    text(
                        "SELECT count(*) FROM cognitive_os.memory_items i "
                        "LEFT JOIN cognitive_os.memory_revisions r ON r.memory_id=i.memory_id "
                        "AND r.revision=i.current_revision "
                        "WHERE r.memory_id IS NULL OR r.status<>i.status"
                    )
                )
                or 0
            )
            missing_sources = int(
                await connection.scalar(
                    text(
                        "SELECT count(*) FROM cognitive_os.memory_revisions r "
                        "WHERE NOT EXISTS (SELECT 1 FROM cognitive_os.memory_sources s "
                        "WHERE s.memory_id=r.memory_id AND s.revision=r.revision)"
                    )
                )
                or 0
            )
            orphan_embeddings = int(
                await connection.scalar(
                    text(
                        "SELECT count(*) FROM cognitive_os.memory_embeddings e "
                        "LEFT JOIN cognitive_os.memory_revisions r ON r.memory_id=e.memory_id "
                        "AND r.revision=e.revision WHERE r.memory_id IS NULL "
                        "OR r.content_hash<>e.content_hash"
                    )
                )
                or 0
            )
            missing_creation_events = int(
                await connection.scalar(
                    text(
                        "SELECT count(*) FROM cognitive_os.memory_items i WHERE NOT EXISTS ("
                        "SELECT 1 FROM cognitive_os.events e "
                        "WHERE e.event_type='memory.item_created' "
                        "AND e.payload_json->'record'->>'memory_id'=i.memory_id::text)"
                    )
                )
                or 0
            )
            lifecycle_events_without_rows = int(
                await connection.scalar(
                    text(
                        "SELECT count(*) FROM cognitive_os.events e "
                        "WHERE e.event_type LIKE 'memory.%' "
                        "AND e.event_type NOT IN "
                        "('memory.ingestion_completed','memory.ingestion_rejected') "
                        "AND NOT EXISTS (SELECT 1 FROM cognitive_os.memory_items i "
                        "WHERE i.memory_id=e.stream_id)"
                    )
                )
                or 0
            )
        missing_tables = self.REQUIRED_TABLES - tables
        checks = (
            ("missing_tables", len(missing_tables), f"Missing tables: {sorted(missing_tables)}"),
            ("approximate_indexes", approximate_indexes, "Approximate indexes are forbidden"),
            ("projection_mismatch", projection_errors, "Current projection mismatch"),
            ("missing_provenance", missing_sources, "Revision without provenance"),
            ("orphan_embeddings", orphan_embeddings, "Embedding/revision mismatch"),
        )
        for code, count, message in checks:
            findings.append(
                MemoryHealthFinding(
                    code=code,
                    severity=(MemoryHealthSeverity.ERROR if count else MemoryHealthSeverity.INFO),
                    count=count,
                    message=message,
                )
            )
        for code, count, message in (
            (
                "missing_creation_events",
                missing_creation_events,
                "Table rows without memory creation events",
            ),
            (
                "lifecycle_events_without_rows",
                lifecycle_events_without_rows,
                "Memory lifecycle events without table rows",
            ),
        ):
            findings.append(
                MemoryHealthFinding(
                    code=code,
                    severity=(MemoryHealthSeverity.WARNING if count else MemoryHealthSeverity.INFO),
                    count=count,
                    message=message,
                )
            )
        if revision != "0007":
            findings.append(
                MemoryHealthFinding(
                    code="migration_head",
                    severity=MemoryHealthSeverity.ERROR,
                    count=1,
                    message=f"Expected Alembic revision 0007, found {revision}",
                )
            )
        if vector_version != "0.8.2":
            findings.append(
                MemoryHealthFinding(
                    code="vector_version",
                    severity=MemoryHealthSeverity.ERROR,
                    count=1,
                    message=f"Expected pgvector 0.8.2, found {vector_version}",
                )
            )
        healthy = not any(finding.severity is MemoryHealthSeverity.ERROR for finding in findings)
        return MemoryHealthReport(
            healthy=healthy,
            alembic_revision=str(revision) if revision is not None else None,
            vector_version=str(vector_version) if vector_version is not None else None,
            findings=tuple(findings),
        )
