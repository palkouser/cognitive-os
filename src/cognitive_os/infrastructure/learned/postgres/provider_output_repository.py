"""PostgreSQL implementation of the provider-output governance port.

Every write goes through `cognitive_os.record_provider_output`, because `cogos_app` holds
SELECT plus EXECUTE and nothing else — so an application-role bug cannot rewrite a
governance decision even if it builds the SQL itself.

Reads return `payload_json` validated back into the contract. The typed columns exist for
constraints, indexes and health queries; the canonical payload is what round-trips, so a
column that drifted from its payload is a health failure rather than a silent lossy read.

Held to `ProviderOutputRepositoryContract`, the same suite the in-memory reference passes.
See ADR 0087.
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import func, select, text
from sqlalchemy.exc import DBAPIError, IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncEngine

from cognitive_os.domain.learned_evidence import GovernedOutcomeReference
from cognitive_os.domain.provider_output import (
    ProviderOutputConflict,
    ProviderOutputIntendedUse,
    ProviderOutputRecord,
    ProviderOutputRepositoryError,
    ProviderOutputVerifierStatus,
    SecretScanStatus,
    UsageRightsDecision,
)
from cognitive_os.infrastructure.learned.memory_provider_output import (
    MAX_PAGE_SIZE,
    build_source_reference,
)
from cognitive_os.infrastructure.postgres.engine import postgres_transaction

from .provider_output_tables import provider_output_records

#: Database error text mapped to the conflict a caller can act on. Matching on the message
#: is deliberate: these strings are raised by the controlled function in migration 0015,
#: they are part of that contract, and a test fails if one stops matching.
_CONFLICT_PATTERNS: tuple[tuple[re.Pattern[str], ProviderOutputConflict], ...] = (
    (re.compile(r"idempotency key reused"), ProviderOutputConflict.IDEMPOTENCY_KEY_REUSED),
    (re.compile(r"cannot be replaced with"), ProviderOutputConflict.IDEMPOTENCY_KEY_REUSED),
    (re.compile(r"revision conflict"), ProviderOutputConflict.REVISION_CONFLICT),
    (re.compile(r"broken lineage"), ProviderOutputConflict.BROKEN_LINEAGE),
    (
        re.compile(r"uq_provider_output_revision"),
        ProviderOutputConflict.REVISION_CONFLICT,
    ),
    (
        re.compile(r"uq_provider_output_idempotency"),
        ProviderOutputConflict.IDEMPOTENCY_KEY_REUSED,
    ),
    (
        re.compile(r"ck_provider_out_normalized_content_policy"),
        ProviderOutputConflict.RETENTION_REFUSED,
    ),
    (re.compile(r"ck_provider_out_\w+"), ProviderOutputConflict.RETENTION_REFUSED),
    (re.compile(r"violates foreign key"), ProviderOutputConflict.BROKEN_LINEAGE),
)


class PostgresProviderOutputRepository:
    """Durable provider-output governance, through the controlled function only."""

    def __init__(self, engine: AsyncEngine) -> None:
        self._engine = engine

    # ------------------------------------------------------------------- writing

    async def record_output(self, record: ProviderOutputRecord) -> ProviderOutputRecord:
        async with postgres_transaction(self._engine) as connection:
            try:
                await connection.scalar(
                    text("SELECT cognitive_os.record_provider_output(CAST(:payload AS jsonb))"),
                    {"payload": record.model_dump_json()},
                )
            except (IntegrityError, DBAPIError, SQLAlchemyError) as error:
                raise _translate(error) from error
        stored = await self.get_revision(record.provider_output_revision_id)
        if stored is None:
            # The function returned without raising and without a row, which the write path
            # cannot produce. Reporting it as an integrity failure rather than returning the
            # caller's own object keeps "what was stored" from being assumed.
            raise ProviderOutputRepositoryError(
                ProviderOutputConflict.INTEGRITY_FAILURE,
                "the controlled function reported success without persisting a revision",
            )
        if stored.content_hash != record.content_hash:
            raise ProviderOutputRepositoryError(
                ProviderOutputConflict.IDEMPOTENCY_KEY_REUSED,
                "an existing revision holds different content",
            )
        return stored

    # ------------------------------------------------------------------- reading

    async def get_revision(self, revision_id: UUID) -> ProviderOutputRecord | None:
        row = await self._one(
            select(provider_output_records.c.payload_json).where(
                provider_output_records.c.provider_output_revision_id == revision_id
            )
        )
        return _validate(row)

    async def get_latest(self, provider_output_id: UUID) -> ProviderOutputRecord | None:
        """The head of one output's revision chain, served by `ix_provider_output_latest`."""
        row = await self._one(
            select(provider_output_records.c.payload_json)
            .where(provider_output_records.c.provider_output_id == provider_output_id)
            .order_by(provider_output_records.c.revision.desc())
            .limit(1)
        )
        return _validate(row)

    async def revision_history(
        self, provider_output_id: UUID, *, limit: int = 100, offset: int = 0
    ) -> tuple[ProviderOutputRecord, ...]:
        statement = (
            select(provider_output_records.c.payload_json)
            .where(provider_output_records.c.provider_output_id == provider_output_id)
            .order_by(provider_output_records.c.revision)
        )
        rows = await self._page(statement, limit=limit, offset=offset)
        return tuple(ProviderOutputRecord.model_validate(row["payload_json"]) for row in rows)

    async def list_eligible(
        self,
        *,
        intended_use: ProviderOutputIntendedUse,
        moment: datetime,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[ProviderOutputRecord, ...]:
        """Latest revisions that may be newly selected. The narrowing is in SQL; the final
        refusal is the contract's own `is_selectable_at`, so the two can never disagree.
        """
        heads = (
            select(
                provider_output_records.c.provider_output_id,
                func.max(provider_output_records.c.revision).label("head"),
            )
            .group_by(provider_output_records.c.provider_output_id)
            .subquery()
        )
        statement = (
            select(provider_output_records.c.payload_json)
            .join(
                heads,
                (provider_output_records.c.provider_output_id == heads.c.provider_output_id)
                & (provider_output_records.c.revision == heads.c.head),
            )
            .where(
                # Enum values rather than string literals: the literals are the same
                # characters, but a bare `== "passed"` beside a column named
                # `secret_scan_status` reads to every credential scanner as a hardcoded
                # password, and silencing that with a pragma would train the scanner to be
                # ignored on the file that most needs it.
                provider_output_records.c.intended_use == intended_use.value,
                provider_output_records.c.rights_decision == UsageRightsDecision.VERIFIED.value,
                provider_output_records.c.secret_scan_status == SecretScanStatus.PASSED.value,
                provider_output_records.c.verifier_status
                == ProviderOutputVerifierStatus.PASSED.value,
                provider_output_records.c.physical_deletion_required.is_(False),
            )
            .order_by(
                provider_output_records.c.recorded_at,
                provider_output_records.c.provider_output_id,
            )
        )
        rows = await self._page(statement, limit=limit, offset=offset)
        records = (ProviderOutputRecord.model_validate(row["payload_json"]) for row in rows)
        return tuple(record for record in records if record.is_selectable_at(moment))

    async def resolve_source(
        self, provider_output_id: UUID, *, surface: str, moment: datetime
    ) -> GovernedOutcomeReference:
        record = await self.get_latest(provider_output_id)
        if record is None:
            raise ProviderOutputRepositoryError(
                ProviderOutputConflict.NOT_FOUND,
                f"no governance record for provider output {provider_output_id}",
            )
        return build_source_reference(record, surface=surface, moment=moment)

    async def count_revisions(self) -> int:
        async with self._engine.connect() as connection:
            total = await connection.scalar(
                select(func.count()).select_from(provider_output_records)
            )
        return int(total or 0)

    # ----------------------------------------------------------------- internals

    async def _one(self, statement: Any) -> Any:
        async with self._engine.connect() as connection:
            return (await connection.execute(statement)).mappings().one_or_none()

    async def _page(self, statement: Any, *, limit: int, offset: int) -> Any:
        if limit < 0 or offset < 0:
            raise ValueError("limit and offset must not be negative")
        bounded = statement.limit(min(limit, MAX_PAGE_SIZE)).offset(offset)
        async with self._engine.connect() as connection:
            return (await connection.execute(bounded)).mappings().all()


def _validate(row: Any) -> ProviderOutputRecord | None:
    if row is None:
        return None
    return ProviderOutputRecord.model_validate(row["payload_json"])


def _translate(error: Exception) -> ProviderOutputRepositoryError:
    """Turn a database refusal into the typed conflict a caller can branch on."""
    message = str(error)
    for pattern, conflict in _CONFLICT_PATTERNS:
        if pattern.search(message):
            return ProviderOutputRepositoryError(conflict, _detail(message))
    return ProviderOutputRepositoryError(ProviderOutputConflict.INTEGRITY_FAILURE, _detail(message))


def _detail(message: str) -> str:
    """The database's own sentence, without the SQL echo that repeats the whole record."""
    first = message.splitlines()[0]
    return first.split("[SQL:")[0].strip() or "the database refused the write"
