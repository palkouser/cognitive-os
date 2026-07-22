"""Read-only Harness Proposal Engine persistence health checks."""

from pydantic import Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from cognitive_os.domain.base import ImmutableContractModel
from cognitive_os.events.catalog import build_default_event_catalog
from cognitive_os.events.proposal_events import PROPOSAL_EVENT_MODELS
from cognitive_os.proposals.service import MANDATORY_PROPOSAL_VERIFIERS, ProposalTypeRegistry


class ProposalHealthReport(ImmutableContractModel):
    healthy: bool
    migration_revision: str | None = None
    table_count: int = Field(ge=0)
    append_only_trigger_count: int = Field(ge=0)
    controlled_function_count: int = Field(ge=0)
    forbidden_runtime_privilege_count: int = Field(ge=0)
    orphan_revision_count: int = Field(ge=0)
    orphan_queue_count: int = Field(ge=0)
    projection_mismatch_count: int = Field(ge=0)
    event_type_count: int = Field(ge=0)
    verifier_capability_count: int = Field(ge=0)
    registry_hash: str
    verifier_registry_hash: str
    provider_assisted_available: bool = False
    messages: tuple[str, ...] = ()


class PostgresProposalHealthService:
    def __init__(self, engine: AsyncEngine) -> None:
        self._engine = engine

    async def check(self) -> ProposalHealthReport:
        async with self._engine.connect() as connection:
            revision = await connection.scalar(text("SELECT version_num FROM alembic_version"))
            table_count = int(
                await connection.scalar(
                    text(
                        "SELECT count(*) FROM information_schema.tables "
                        "WHERE table_schema='cognitive_os' "
                        "AND table_name LIKE 'harness_proposal%'"
                    )
                )
                or 0
            )
            trigger_count = int(
                await connection.scalar(
                    text(
                        "SELECT count(*) FROM pg_trigger WHERE NOT tgisinternal "
                        "AND tgname LIKE 'trg_harness_proposal%_append_only'"
                    )
                )
                or 0
            )
            function_count = int(
                await connection.scalar(
                    text(
                        "SELECT count(*) FROM pg_proc p JOIN pg_namespace n "
                        "ON n.oid=p.pronamespace "
                        "WHERE n.nspname='cognitive_os' AND p.proname IN ("
                        "'create_harness_proposal','append_harness_proposal_revision',"
                        "'transition_harness_proposal','record_harness_proposal_review',"
                        "'enqueue_harness_proposal','remove_harness_proposal_from_queue',"
                        "'record_harness_proposal_access')"
                    )
                )
                or 0
            )
            orphan_revisions = int(
                await connection.scalar(
                    text(
                        "SELECT count(*) FROM cognitive_os.harness_proposal_revisions r "
                        "LEFT JOIN cognitive_os.harness_proposals p USING (proposal_id) "
                        "WHERE p.proposal_id IS NULL"
                    )
                )
                or 0
            )
            orphan_queue = int(
                await connection.scalar(
                    text(
                        "SELECT count(*) FROM cognitive_os.harness_proposal_queue q "
                        "LEFT JOIN cognitive_os.harness_proposal_revisions r "
                        "ON r.proposal_id=q.proposal_id AND r.revision=q.proposal_revision "
                        "WHERE r.proposal_id IS NULL"
                    )
                )
                or 0
            )
            projection_mismatches = int(
                await connection.scalar(
                    text(
                        "SELECT count(*) FROM cognitive_os.harness_proposals p "
                        "LEFT JOIN cognitive_os.harness_proposal_revisions r "
                        "ON r.proposal_id=p.proposal_id AND r.revision=p.current_revision "
                        "WHERE r.proposal_id IS NULL OR r.content_hash<>p.current_content_hash"
                    )
                )
                or 0
            )
            forbidden_privileges = int(
                await connection.scalar(
                    text(
                        "SELECT count(*) FROM information_schema.tables "
                        "WHERE table_schema='cognitive_os' "
                        "AND table_name LIKE 'harness_proposal%' "
                        "AND (has_table_privilege('cogos_app', "
                        "quote_ident(table_schema)||'.'||quote_ident(table_name), 'UPDATE') "
                        "OR has_table_privilege('cogos_app', "
                        "quote_ident(table_schema)||'.'||quote_ident(table_name), 'DELETE'))"
                    )
                )
                or 0
            )
        catalog = build_default_event_catalog().list_event_types()
        event_count = sum((model.event_type, 1) in catalog for model in PROPOSAL_EVENT_MODELS)
        messages = []
        for actual, expected, name in (
            (revision, "0010", "migration revision"),
            (table_count, 10, "proposal table count"),
            (trigger_count, 9, "append-only trigger count"),
            (function_count, 7, "controlled function count"),
            (forbidden_privileges, 0, "forbidden runtime privilege count"),
            (orphan_revisions, 0, "orphan revision count"),
            (orphan_queue, 0, "orphan queue count"),
            (projection_mismatches, 0, "projection mismatch count"),
            (event_count, 10, "proposal event type count"),
            (len(MANDATORY_PROPOSAL_VERIFIERS), 22, "proposal verifier capability count"),
        ):
            if actual != expected:
                messages.append(f"Expected {name} {expected}, found {actual}")
        registry = ProposalTypeRegistry()
        return ProposalHealthReport(
            healthy=not messages,
            migration_revision=str(revision) if revision else None,
            table_count=table_count,
            append_only_trigger_count=trigger_count,
            controlled_function_count=function_count,
            forbidden_runtime_privilege_count=forbidden_privileges,
            orphan_revision_count=orphan_revisions,
            orphan_queue_count=orphan_queue,
            projection_mismatch_count=projection_mismatches,
            event_type_count=event_count,
            verifier_capability_count=len(MANDATORY_PROPOSAL_VERIFIERS),
            registry_hash=registry.snapshot_hash,
            verifier_registry_hash=__import__("hashlib")
            .sha256("\n".join(MANDATORY_PROPOSAL_VERIFIERS).encode())
            .hexdigest(),
            messages=tuple(messages),
        )
