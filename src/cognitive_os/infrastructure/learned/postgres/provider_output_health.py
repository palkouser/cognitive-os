"""Read-only health for the provider-output governance ledger.

The same two-category split ADR 0086 established for learned evidence, applied to a ledger
whose availability question is different in kind. An **integrity failure** means the
governance authority is damaged: a missing controlled function, a broken revision chain, a
payload that no longer hashes to its record, a retained artifact that is not there. A
**provider warning** means a teacher is currently unreachable, which says nothing at all
about whether the recorded decisions are intact.

Collapsing the two would be the expensive mistake in exactly the way it was for C1: if an
OpenRouter outage made governance health unhealthy, the alarm that means "your retention
decisions are corrupt" would be the one nobody trusted.

Every query here reads. Nothing writes, so it is safe against a live database and is the
same check the operator CLI and the release evidence run. See ADR 0087.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime

from pydantic import Field
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncEngine

from cognitive_os.domain.base import ImmutableContractModel
from cognitive_os.domain.common import utc_now
from cognitive_os.domain.provider import ProviderHealth, ProviderStatus
from cognitive_os.domain.provider_output import ProviderOutputRecord
from cognitive_os.infrastructure.postgres.tables import EXPECTED_MIGRATION_REVISION

from .provider_output_tables import PROVIDER_OUTPUT_TABLES, provider_output_records

EXPECTED_TABLE_COUNT = len(PROVIDER_OUTPUT_TABLES)
EXPECTED_TRIGGER_COUNT = len(PROVIDER_OUTPUT_TABLES)

#: Named rather than counted, so a renamed function is reported as the one that went missing.
CONTROLLED_FUNCTIONS = ("record_provider_output",)

#: Indexes and constraints whose absence changes behaviour rather than only performance.
REQUIRED_INDEXES = (
    "uq_provider_output_revision",
    "uq_provider_output_idempotency",
    "ix_provider_output_latest",
)

#: How many rows the payload check re-validates. Health has to stay cheap enough to run
#: often; an unbounded scan would make the check the reason it stopped being run.
PAYLOAD_SAMPLE_LIMIT = 1000


class ProviderOutputHealthReport(ImmutableContractModel):
    """What the governance ledger looks like right now, and what is wrong with it."""

    healthy: bool
    migration_revision: str | None = None
    table_count: int = Field(ge=0)
    append_only_trigger_count: int = Field(ge=0)
    controlled_function_count: int = Field(ge=0)
    output_count: int = Field(ge=0)
    revision_count: int = Field(ge=0)
    retained_artifact_count: int = Field(ge=0)
    expired_count: int = Field(ge=0)
    payload_rows_verified: int = Field(default=0, ge=0)
    #: The ledger is damaged. These make `healthy` false.
    integrity_failures: tuple[str, ...] = ()
    #: A teacher is unreachable. These never make `healthy` false.
    provider_warnings: tuple[str, ...] = ()


class PostgresProviderOutputHealthService:
    """Read-only integrity inspection of the provider-output governance ledger."""

    def __init__(self, engine: AsyncEngine) -> None:
        self._engine = engine

    async def check(
        self,
        *,
        provider_health: Sequence[ProviderHealth] = (),
        moment: datetime | None = None,
    ) -> ProviderOutputHealthReport:
        now = moment or utc_now()
        failures: list[str] = []

        async with self._engine.connect() as connection:
            revision = await connection.scalar(text("SELECT version_num FROM alembic_version"))
            tables = await self._count(
                connection,
                "SELECT count(*) FROM information_schema.tables "
                "WHERE table_schema = 'cognitive_os' AND table_name = 'provider_output_records'",
            )
            triggers = await self._count(
                connection,
                "SELECT count(*) FROM pg_trigger WHERE NOT tgisinternal "
                "AND tgname LIKE 'trg_provider_output_%_append_only'",
            )
            functions = await self._count(
                connection,
                "SELECT count(*) FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace "
                "WHERE n.nspname = 'cognitive_os' AND p.proname = ANY(:names)",
                {"names": list(CONTROLLED_FUNCTIONS)},
            )
            missing_indexes = [
                name
                for name in REQUIRED_INDEXES
                if not await connection.scalar(
                    text(
                        "SELECT EXISTS (SELECT 1 FROM pg_indexes "
                        "WHERE schemaname = 'cognitive_os' AND indexname = :name) "
                        "OR EXISTS (SELECT 1 FROM pg_constraint WHERE conname = :name)"
                    ),
                    {"name": name},
                )
            ]

            revisions = await self._count(
                connection, "SELECT count(*) FROM cognitive_os.provider_output_records"
            )
            outputs = await self._count(
                connection,
                "SELECT count(DISTINCT provider_output_id) "
                "FROM cognitive_os.provider_output_records",
            )
            retained = await self._count(
                connection,
                "SELECT count(*) FROM cognitive_os.provider_output_records "
                "WHERE response_artifact_id IS NOT NULL",
            )
            expired = await self._count(
                connection,
                "SELECT count(*) FROM cognitive_os.provider_output_records "
                "WHERE expires_at IS NOT NULL AND expires_at <= :now",
                {"now": now},
            )

            # Revision continuity, in SQL rather than by loading the whole ledger: a chain
            # whose revisions do not run 1..N for one output is a fork or a gap, and either
            # means the audit history cannot be replayed.
            broken_chains = (
                (
                    await connection.execute(
                        text(
                            "SELECT provider_output_id FROM cognitive_os.provider_output_records "
                            "GROUP BY provider_output_id "
                            "HAVING count(*) <> max(revision) OR min(revision) <> 1"
                        )
                    )
                )
                .scalars()
                .all()
            )
            orphan_predecessors = (
                (
                    await connection.execute(
                        text(
                            "SELECT child.provider_output_revision_id "
                            "FROM cognitive_os.provider_output_records child "
                            "LEFT JOIN cognitive_os.provider_output_records parent "
                            "ON parent.provider_output_revision_id = child.previous_revision_id "
                            "WHERE child.previous_revision_id IS NOT NULL "
                            "AND parent.provider_output_revision_id IS NULL"
                        )
                    )
                )
                .scalars()
                .all()
            )
            # A retained artifact that is no longer in the Artifact Store. The join is the
            # check: the foreign key prevents deletion, so a miss means something bypassed it.
            missing_artifacts = (
                (
                    await connection.execute(
                        text(
                            "SELECT record.provider_output_revision_id "
                            "FROM cognitive_os.provider_output_records record "
                            "LEFT JOIN cognitive_os.artifacts artifact "
                            "ON artifact.artifact_id = record.response_artifact_id "
                            "WHERE record.response_artifact_id IS NOT NULL "
                            "AND artifact.artifact_id IS NULL"
                        )
                    )
                )
                .scalars()
                .all()
            )
            missing_events = (
                (
                    await connection.execute(
                        text(
                            "SELECT record.provider_output_revision_id "
                            "FROM cognitive_os.provider_output_records record "
                            "LEFT JOIN cognitive_os.events event "
                            "ON event.event_id = record.completed_event_id "
                            "WHERE event.event_id IS NULL"
                        )
                    )
                )
                .scalars()
                .all()
            )

            payload_rows = (
                (
                    await connection.execute(
                        select(provider_output_records.c.payload_json).limit(PAYLOAD_SAMPLE_LIMIT)
                    )
                )
                .mappings()
                .all()
            )

        verified = 0
        for row in payload_rows:
            try:
                # Re-validating *is* the hash check: the contract re-seals on load and
                # refuses a payload whose declared hash no longer matches its content.
                ProviderOutputRecord.model_validate(row["payload_json"])
            except ValueError as error:
                failures.append(f"a stored governance payload no longer validates: {error}")
            else:
                verified += 1

        if revision != EXPECTED_MIGRATION_REVISION:
            failures.append(
                f"expected Alembic revision {EXPECTED_MIGRATION_REVISION}, found {revision}"
            )
        if tables != EXPECTED_TABLE_COUNT:
            failures.append(f"expected {EXPECTED_TABLE_COUNT} governance table, found {tables}")
        if triggers != EXPECTED_TRIGGER_COUNT:
            failures.append(
                f"expected {EXPECTED_TRIGGER_COUNT} append-only trigger, found {triggers}"
            )
        if functions != len(CONTROLLED_FUNCTIONS):
            failures.append("the controlled write function is missing")
        for name in missing_indexes:
            failures.append(f"required index or constraint is missing: {name}")
        for output_id in broken_chains:
            failures.append(f"{output_id}: the revision chain has a gap or a fork")
        for revision_id in orphan_predecessors:
            failures.append(f"{revision_id}: names a predecessor that does not exist")
        for revision_id in missing_artifacts:
            failures.append(f"{revision_id}: retained artifact is missing from the Artifact Store")
        for revision_id in missing_events:
            failures.append(f"{revision_id}: the completed model-call event is missing")

        warnings = tuple(
            f"{item.provider_id} is {item.status.value}: {item.message}"
            for item in provider_health
            if item.status is not ProviderStatus.AVAILABLE
        )

        return ProviderOutputHealthReport(
            healthy=not failures,
            migration_revision=str(revision) if revision is not None else None,
            table_count=tables,
            append_only_trigger_count=triggers,
            controlled_function_count=functions,
            output_count=outputs,
            revision_count=revisions,
            retained_artifact_count=retained,
            expired_count=expired,
            payload_rows_verified=verified,
            integrity_failures=tuple(failures),
            provider_warnings=warnings,
        )

    @staticmethod
    async def _count(connection: object, statement: str, parameters: object = None) -> int:
        result = await connection.scalar(  # type: ignore[attr-defined]
            text(statement), parameters or {}
        )
        return int(result or 0)
