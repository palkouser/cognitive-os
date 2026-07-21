"""Read-only Corpus Factory persistence health checks."""

from pydantic import Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from cognitive_os.domain.base import ImmutableContractModel


class CorpusHealthReport(ImmutableContractModel):
    healthy: bool
    migration_revision: str | None = None
    table_count: int = Field(ge=0)
    append_only_trigger_count: int = Field(ge=0)
    controlled_function_count: int = Field(ge=0)
    orphan_link_count: int = Field(ge=0)
    missing_manifest_item_count: int = Field(ge=0)
    access_gap_count: int = Field(ge=0)
    messages: tuple[str, ...] = ()


class PostgresCorpusHealthService:
    def __init__(self, engine: AsyncEngine) -> None:
        self._engine = engine

    async def check(self) -> CorpusHealthReport:
        async with self._engine.connect() as connection:
            revision = await connection.scalar(text("SELECT version_num FROM alembic_version"))
            table_count = int(
                await connection.scalar(
                    text(
                        "SELECT count(*) FROM information_schema.tables "
                        "WHERE table_schema='cognitive_os' "
                        "AND table_name LIKE 'corpus_%'"
                    )
                )
                or 0
            )
            triggers = int(
                await connection.scalar(
                    text(
                        "SELECT count(*) FROM pg_trigger WHERE NOT tgisinternal "
                        "AND tgname LIKE 'trg_corpus_%_append_only'"
                    )
                )
                or 0
            )
            functions = int(
                await connection.scalar(
                    text(
                        "SELECT count(*) FROM pg_proc p JOIN pg_namespace n "
                        "ON n.oid=p.pronamespace "
                        "WHERE n.nspname='cognitive_os' AND p.proname='advance_corpus_item'"
                    )
                )
                or 0
            )
            orphan_links = int(
                await connection.scalar(
                    text(
                        "SELECT count(*) FROM cognitive_os.corpus_item_sources s LEFT JOIN "
                        "cognitive_os.corpus_items i USING (corpus_item_id) LEFT JOIN "
                        "cognitive_os.corpus_sources c USING (source_manifest_id) WHERE "
                        "i.corpus_item_id IS NULL OR c.source_manifest_id IS NULL"
                    )
                )
                or 0
            )
            missing_items = int(
                await connection.scalar(
                    text(
                        "SELECT count(*) FROM cognitive_os.corpus_manifest_items mi LEFT JOIN "
                        "cognitive_os.corpus_items i USING (corpus_item_id) "
                        "WHERE i.corpus_item_id IS NULL"
                    )
                )
                or 0
            )
            access_gaps = int(
                await connection.scalar(
                    text(
                        "SELECT count(*) FROM cognitive_os.corpus_items i "
                        "WHERE i.current_status IN ('routed','exported') "
                        "AND NOT EXISTS (SELECT 1 FROM cognitive_os.corpus_accesses "
                        "a WHERE a.corpus_item_id=i.corpus_item_id)"
                    )
                )
                or 0
            )
        messages = []
        if revision != "0007":
            messages.append(f"Expected Alembic revision 0007, found {revision}")
        if table_count != 9:
            messages.append(f"Expected 9 Corpus Factory tables, found {table_count}")
        if triggers != 8:
            messages.append(f"Expected 8 append-only triggers, found {triggers}")
        if functions != 1:
            messages.append(f"Expected 1 controlled function, found {functions}")
        if orphan_links:
            messages.append(f"Found {orphan_links} orphan corpus source links")
        if missing_items:
            messages.append(f"Found {missing_items} missing manifest items")
        if access_gaps:
            messages.append(f"Found {access_gaps} routed items without access audit")
        return CorpusHealthReport(
            healthy=not messages,
            migration_revision=revision,
            table_count=table_count,
            append_only_trigger_count=triggers,
            controlled_function_count=functions,
            orphan_link_count=orphan_links,
            missing_manifest_item_count=missing_items,
            access_gap_count=access_gaps,
            messages=tuple(messages),
        )
