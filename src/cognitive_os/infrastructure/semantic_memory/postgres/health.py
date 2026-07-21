"""Read-only semantic projection health diagnostics."""

from enum import StrEnum

from pydantic import Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from cognitive_os.domain.base import ImmutableContractModel


class SemanticHealthSeverity(StrEnum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


class SemanticHealthFinding(ImmutableContractModel):
    code: str
    severity: SemanticHealthSeverity
    count: int = Field(ge=0)
    message: str


class SemanticHealthReport(ImmutableContractModel):
    healthy: bool
    alembic_revision: str | None
    findings: tuple[SemanticHealthFinding, ...]


class PostgresSemanticHealthService:
    REQUIRED_TABLES = frozenset(
        {
            "semantic_observations",
            "semantic_claims",
            "semantic_claim_revisions",
            "semantic_claim_evidence",
            "semantic_claim_relations",
            "semantic_contradictions",
            "semantic_contradiction_revisions",
            "semantic_contradiction_claims",
            "wiki_pages",
            "wiki_page_revisions",
            "wiki_page_claims",
            "semantic_accesses",
        }
    )

    def __init__(self, engine: AsyncEngine) -> None:
        self._engine = engine

    async def check(self) -> SemanticHealthReport:
        async with self._engine.connect() as connection:
            revision = await connection.scalar(text("SELECT version_num FROM alembic_version"))
            tables = set(
                (
                    await connection.execute(
                        text(
                            "SELECT tablename FROM pg_tables WHERE schemaname='cognitive_os' "
                            "AND (tablename LIKE 'semantic_%' OR tablename LIKE 'wiki_%')"
                        )
                    )
                ).scalars()
            )
            counts = {
                "claim_projection_mismatch": await connection.scalar(
                    text(
                        "SELECT count(*) FROM cognitive_os.semantic_claims c LEFT JOIN "
                        "cognitive_os.semantic_claim_revisions r ON r.claim_id=c.claim_id "
                        "AND r.revision=c.current_revision WHERE r.claim_id IS NULL OR "
                        "r.belief_status<>c.current_belief_status"
                    )
                ),
                "invalid_temporal_interval": await connection.scalar(
                    text(
                        "SELECT count(*) FROM cognitive_os.semantic_claim_revisions "
                        "WHERE valid_to IS NOT NULL AND valid_to<=valid_from"
                    )
                ),
                "missing_evidence": await connection.scalar(
                    text(
                        "SELECT count(*) FROM cognitive_os.semantic_claim_revisions r "
                        "WHERE r.belief_status='supported' AND NOT EXISTS (SELECT 1 FROM "
                        "cognitive_os.semantic_claim_evidence e WHERE e.claim_id=r.claim_id "
                        "AND e.claim_revision=r.revision)"
                    )
                ),
                "retracted_evidence_source": await connection.scalar(
                    text(
                        "SELECT count(*) FROM cognitive_os.semantic_claim_evidence e JOIN "
                        "cognitive_os.memory_items m ON m.memory_id=e.source_id WHERE "
                        "e.source_type='memory_revision' AND m.status='retracted'"
                    )
                ),
                "wiki_lineage_gap": await connection.scalar(
                    text(
                        "SELECT count(*) FROM cognitive_os.wiki_page_claims w LEFT JOIN "
                        "cognitive_os.semantic_claim_revisions r ON r.claim_id=w.claim_id "
                        "AND r.revision=w.claim_revision WHERE r.claim_id IS NULL"
                    )
                ),
                "prohibited_indexes": await connection.scalar(
                    text(
                        "SELECT count(*) FROM pg_indexes WHERE schemaname='cognitive_os' "
                        "AND (indexdef ILIKE '%hnsw%' OR indexdef ILIKE '%ivfflat%')"
                    )
                ),
                "claim_revision_gap": await connection.scalar(
                    text(
                        "SELECT count(*) FROM cognitive_os.semantic_claims c WHERE "
                        "(SELECT count(*) FROM cognitive_os.semantic_claim_revisions r "
                        "WHERE r.claim_id=c.claim_id)<>c.current_revision"
                    )
                ),
                "contradiction_projection_mismatch": await connection.scalar(
                    text(
                        "SELECT count(*) FROM cognitive_os.semantic_contradictions c LEFT JOIN "
                        "cognitive_os.semantic_contradiction_revisions r ON "
                        "r.contradiction_id=c.contradiction_id AND "
                        "r.revision=c.current_revision WHERE r.contradiction_id IS NULL OR "
                        "r.status<>c.current_status OR r.severity<>c.severity"
                    )
                ),
                "contradiction_revision_gap": await connection.scalar(
                    text(
                        "SELECT count(*) FROM cognitive_os.semantic_contradictions c WHERE "
                        "(SELECT count(*) FROM cognitive_os.semantic_contradiction_revisions r "
                        "WHERE r.contradiction_id=c.contradiction_id)<>c.current_revision"
                    )
                ),
                "wiki_revision_gap": await connection.scalar(
                    text(
                        "SELECT count(*) FROM cognitive_os.wiki_pages p WHERE "
                        "(SELECT count(*) FROM cognitive_os.wiki_page_revisions r "
                        "WHERE r.page_id=p.page_id)<>p.current_revision"
                    )
                ),
                "graph_limit_exceeded": await connection.scalar(
                    text(
                        "SELECT CASE WHEN "
                        "(SELECT count(*) FROM cognitive_os.semantic_claim_relations)>10000 "
                        "OR (SELECT count(*) FROM cognitive_os.semantic_claims)>5000 "
                        "THEN 1 ELSE 0 END"
                    )
                ),
            }
            consistency_counts = {
                "missing_observation_events": await connection.scalar(
                    text(
                        "SELECT count(*) FROM cognitive_os.semantic_observations o WHERE "
                        "NOT EXISTS (SELECT 1 FROM cognitive_os.events e WHERE "
                        "e.event_type='semantic.observation_recorded' "
                        "AND e.stream_id=o.observation_id)"
                    )
                ),
                "missing_claim_events": await connection.scalar(
                    text(
                        "SELECT count(*) FROM cognitive_os.semantic_claims c WHERE "
                        "NOT EXISTS (SELECT 1 FROM cognitive_os.events e WHERE "
                        "e.event_type='semantic.claim_created' AND e.stream_id=c.claim_id)"
                    )
                ),
                "missing_contradiction_events": await connection.scalar(
                    text(
                        "SELECT count(*) FROM cognitive_os.semantic_contradictions c WHERE "
                        "NOT EXISTS (SELECT 1 FROM cognitive_os.events e WHERE "
                        "e.event_type IN ('semantic.contradiction_opened', "
                        "'semantic.contradiction_candidate_recorded') "
                        "AND e.stream_id=c.contradiction_id)"
                    )
                ),
                "missing_wiki_events": await connection.scalar(
                    text(
                        "SELECT count(*) FROM cognitive_os.wiki_pages p WHERE "
                        "NOT EXISTS (SELECT 1 FROM cognitive_os.events e WHERE "
                        "e.event_type='semantic.wiki_page_rendered' AND e.stream_id=p.page_id)"
                    )
                ),
                "semantic_events_without_projection": await connection.scalar(
                    text(
                        "SELECT count(*) FROM cognitive_os.events e WHERE "
                        "e.event_type LIKE 'semantic.%' AND ("
                        "(e.event_type='semantic.observation_recorded' AND NOT EXISTS "
                        "(SELECT 1 FROM cognitive_os.semantic_observations o "
                        "WHERE o.observation_id=e.stream_id)) OR "
                        "(e.event_type LIKE 'semantic.claim_%' AND "
                        "e.event_type<>'semantic.claim_promotion_decided' AND NOT EXISTS "
                        "(SELECT 1 FROM cognitive_os.semantic_claims c "
                        "WHERE c.claim_id=e.stream_id)) OR "
                        "(e.event_type LIKE 'semantic.contradiction_%' AND NOT EXISTS "
                        "(SELECT 1 FROM cognitive_os.semantic_contradictions c "
                        "WHERE c.contradiction_id=e.stream_id)) OR "
                        "(e.event_type LIKE 'semantic.wiki_%' AND NOT EXISTS "
                        "(SELECT 1 FROM cognitive_os.wiki_pages p "
                        "WHERE p.page_id=e.stream_id)))"
                    )
                ),
                "event_projection_version_mismatch": await connection.scalar(
                    text(
                        "SELECT count(*) FROM ("
                        "SELECT c.claim_id FROM cognitive_os.semantic_claims c JOIN "
                        "cognitive_os.event_streams s ON s.stream_id=c.claim_id "
                        "WHERE s.stream_type='semantic' AND "
                        "s.current_version<>c.current_revision UNION ALL "
                        "SELECT c.contradiction_id FROM "
                        "cognitive_os.semantic_contradictions c JOIN "
                        "cognitive_os.event_streams s ON s.stream_id=c.contradiction_id "
                        "WHERE s.stream_type='semantic' AND "
                        "s.current_version<>c.current_revision UNION ALL "
                        "SELECT p.page_id FROM cognitive_os.wiki_pages p WHERE "
                        "(SELECT count(*) FROM cognitive_os.events e WHERE "
                        "e.stream_id=p.page_id AND "
                        "e.event_type='semantic.wiki_page_rendered')<>p.current_revision"
                        ") mismatches"
                    )
                ),
            }
        findings: list[SemanticHealthFinding] = []
        missing = self.REQUIRED_TABLES - tables
        checks = {
            "missing_tables": len(missing),
            **{key: int(value or 0) for key, value in counts.items()},
        }
        for code, count in checks.items():
            findings.append(
                SemanticHealthFinding(
                    code=code,
                    severity=SemanticHealthSeverity.ERROR if count else SemanticHealthSeverity.INFO,
                    count=count,
                    message=code.replace("_", " "),
                )
            )
        for code, value in consistency_counts.items():
            count = int(value or 0)
            findings.append(
                SemanticHealthFinding(
                    code=code,
                    severity=(
                        SemanticHealthSeverity.WARNING if count else SemanticHealthSeverity.INFO
                    ),
                    count=count,
                    message=code.replace("_", " "),
                )
            )
        if revision != "0008":
            findings.append(
                SemanticHealthFinding(
                    code="migration_head",
                    severity=SemanticHealthSeverity.ERROR,
                    count=1,
                    message=f"Expected Alembic revision 0008, found {revision}",
                )
            )
        return SemanticHealthReport(
            healthy=not any(item.severity is SemanticHealthSeverity.ERROR for item in findings),
            alembic_revision=str(revision) if revision else None,
            findings=tuple(findings),
        )
