"""Transactional PostgreSQL repository for governed harness proposals."""

from uuid import NAMESPACE_URL, UUID, uuid5

from sqlalchemy import Table, select, text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine

from cognitive_os.application.ports.proposals import ProposalRepositoryPort
from cognitive_os.domain.proposals import (
    HarnessProposalIdentity,
    HarnessProposalRevision,
    ProposalAccessRecord,
    ProposalQueueEntry,
    ProposalReview,
    ProposalRunManifest,
    ProposalSourceSnapshot,
)
from cognitive_os.infrastructure.postgres.engine import postgres_transaction
from cognitive_os.proposals.service import ProposalConflictError

from .tables import (
    harness_proposal_alternatives,
    harness_proposal_queue,
    harness_proposal_reviews,
    harness_proposal_risks,
    harness_proposal_rollback_plans,
    harness_proposal_sources,
    harness_proposal_validation_plans,
    harness_proposals,
)


class PostgresProposalRepository(ProposalRepositoryPort):
    def __init__(self, engine: AsyncEngine) -> None:
        self._engine = engine

    async def create(
        self, identity: HarnessProposalIdentity, revision: HarnessProposalRevision
    ) -> None:
        async with postgres_transaction(self._engine) as connection:
            created = await connection.scalar(
                text(
                    "SELECT cognitive_os.create_harness_proposal("
                    "CAST(:identity AS jsonb), CAST(:revision AS jsonb))"
                ),
                {
                    "identity": identity.model_dump_json(),
                    "revision": revision.model_dump_json(),
                },
            )
            if not created:
                raise ProposalConflictError("proposal creation conflict")
            await self._record_components(connection, revision)

    async def append(self, revision: HarnessProposalRevision, *, expected_revision: int) -> None:
        async with postgres_transaction(self._engine) as connection:
            advanced = await connection.scalar(
                text(
                    "SELECT cognitive_os.append_harness_proposal_revision("
                    ":proposal_id, :expected_revision, CAST(:payload AS jsonb))"
                ),
                {
                    "proposal_id": revision.proposal_id,
                    "expected_revision": expected_revision,
                    "payload": revision.model_dump_json(),
                },
            )
        if not advanced:
            raise ProposalConflictError("stale or illegal proposal revision")

    async def get_exact(self, proposal_id: UUID, revision: int) -> HarnessProposalRevision | None:
        from .tables import harness_proposal_revisions

        statement = select(harness_proposal_revisions.c.payload_json).where(
            harness_proposal_revisions.c.proposal_id == proposal_id,
            harness_proposal_revisions.c.revision == revision,
        )
        async with self._engine.connect() as connection:
            payload = await connection.scalar(statement)
        return HarnessProposalRevision.model_validate(payload) if payload else None

    async def get_current(self, proposal_id: UUID) -> HarnessProposalRevision | None:
        statement = select(harness_proposals.c.payload_json).where(
            harness_proposals.c.proposal_id == proposal_id
        )
        async with self._engine.connect() as connection:
            payload = await connection.scalar(statement)
        return HarnessProposalRevision.model_validate(payload) if payload else None

    async def find_active_signature(self, signature: str) -> HarnessProposalRevision | None:
        statement = select(harness_proposals.c.payload_json).where(
            harness_proposals.c.current_signature == signature,
            harness_proposals.c.current_status.not_in(("rejected", "superseded", "retracted")),
        )
        async with self._engine.connect() as connection:
            payload = await connection.scalar(statement)
        return HarnessProposalRevision.model_validate(payload) if payload else None

    async def record_source(self, snapshot: ProposalSourceSnapshot) -> None:
        await self._insert(
            harness_proposal_sources,
            {
                "source_record_id": uuid5(
                    NAMESPACE_URL, f"proposal-source:{snapshot.snapshot_hash}"
                ),
                "proposal_id": snapshot.proposal_id,
                "proposal_revision": 1,
                "content_hash": snapshot.snapshot_hash,
                "payload_json": snapshot.model_dump(mode="json"),
                "created_at": snapshot.created_at,
            },
        )

    async def record_review(self, review: ProposalReview) -> None:
        async with postgres_transaction(self._engine) as connection:
            recorded = await connection.scalar(
                text("SELECT cognitive_os.record_harness_proposal_review(CAST(:payload AS jsonb))"),
                {"payload": review.model_dump_json()},
            )
        if not recorded:
            raise ProposalConflictError("proposal review conflict")

    async def list_reviews(self) -> tuple[ProposalReview, ...]:
        statement = select(harness_proposal_reviews.c.payload_json).order_by(
            harness_proposal_reviews.c.created_at,
            harness_proposal_reviews.c.review_id,
        )
        async with self._engine.connect() as connection:
            payloads = (await connection.scalars(statement)).all()
        return tuple(ProposalReview.model_validate(item) for item in payloads)

    async def record_queue(self, entry: ProposalQueueEntry) -> None:
        function = (
            "enqueue_harness_proposal" if entry.active else "remove_harness_proposal_from_queue"
        )
        async with postgres_transaction(self._engine) as connection:
            recorded = await connection.scalar(
                text(f"SELECT cognitive_os.{function}(CAST(:payload AS jsonb))"),
                {"payload": entry.model_dump_json()},
            )
        if not recorded:
            raise ProposalConflictError("proposal queue conflict")

    async def list_queue(self) -> tuple[ProposalQueueEntry, ...]:
        statement = select(harness_proposal_queue.c.payload_json).order_by(
            harness_proposal_queue.c.created_at,
            harness_proposal_queue.c.queue_record_id,
        )
        async with self._engine.connect() as connection:
            payloads = (await connection.scalars(statement)).all()
        return tuple(ProposalQueueEntry.model_validate(item) for item in payloads)

    async def record_access(self, access: ProposalAccessRecord) -> None:
        async with postgres_transaction(self._engine) as connection:
            recorded = await connection.scalar(
                text("SELECT cognitive_os.record_harness_proposal_access(CAST(:payload AS jsonb))"),
                {"payload": access.model_dump_json()},
            )
        if not recorded:
            raise ProposalConflictError("proposal access conflict")

    async def record_manifest(self, manifest: ProposalRunManifest) -> None:
        await self._insert(
            harness_proposal_sources,
            {
                "source_record_id": uuid5(
                    NAMESPACE_URL,
                    f"proposal-manifest:{manifest.proposal_id}:{manifest.proposal_revision}",
                ),
                "proposal_id": manifest.proposal_id,
                "proposal_revision": manifest.proposal_revision,
                "content_hash": manifest.content_hash,
                "payload_json": manifest.model_dump(mode="json"),
                "created_at": manifest.created_at,
            },
        )

    async def list_current(self) -> tuple[HarnessProposalRevision, ...]:
        statement = select(harness_proposals.c.payload_json).order_by(
            harness_proposals.c.proposal_id
        )
        async with self._engine.connect() as connection:
            payloads = (await connection.scalars(statement)).all()
        return tuple(HarnessProposalRevision.model_validate(item) for item in payloads)

    async def _record_components(
        self, connection: AsyncConnection, revision: HarnessProposalRevision
    ) -> None:
        for alternative in revision.alternatives:
            await self._insert_with_connection(
                connection,
                harness_proposal_alternatives,
                {
                    "alternative_record_id": alternative.alternative_id,
                    "proposal_id": revision.proposal_id,
                    "proposal_revision": revision.revision,
                    "content_hash": alternative.content_hash,
                    "payload_json": alternative.model_dump(mode="json"),
                    "created_at": revision.created_at,
                },
            )
        records = (
            (
                harness_proposal_risks,
                "risk_record_id",
                revision.risk_assessment,
                "risk",
            ),
            (
                harness_proposal_validation_plans,
                "validation_plan_record_id",
                revision.validation_plan,
                "validation",
            ),
            (
                harness_proposal_rollback_plans,
                "rollback_plan_record_id",
                revision.rollback_plan,
                "rollback",
            ),
        )
        for table, key, value, kind in records:
            await self._insert_with_connection(
                connection,
                table,
                {
                    key: uuid5(
                        NAMESPACE_URL,
                        f"proposal-{kind}:{revision.proposal_id}:{revision.revision}",
                    ),
                    "proposal_id": revision.proposal_id,
                    "proposal_revision": revision.revision,
                    "content_hash": value.content_hash,
                    "payload_json": value.model_dump(mode="json"),
                    "created_at": revision.created_at,
                },
            )

    async def _insert(self, table: Table, values: dict[str, object]) -> None:
        async with postgres_transaction(self._engine) as connection:
            await self._insert_with_connection(connection, table, values)

    @staticmethod
    async def _insert_with_connection(
        connection: AsyncConnection, table: Table, values: dict[str, object]
    ) -> None:
        await connection.execute(pg_insert(table).values(**values).on_conflict_do_nothing())
        conditions = [column == values[column.name] for column in table.primary_key.columns]
        stored_hash = await connection.scalar(select(table.c.content_hash).where(*conditions))
        if stored_hash != values["content_hash"]:
            raise ProposalConflictError("proposal record idempotency conflict")
