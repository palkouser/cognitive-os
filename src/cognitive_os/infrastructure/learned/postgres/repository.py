"""PostgreSQL implementation of the learned evidence ports.

Every mutation goes through a controlled `SECURITY DEFINER` function, because `cogos_app`
holds SELECT and EXECUTE and nothing else. That is not defence in depth for its own sake:
it means an application-role bug cannot rewrite evidence even if it constructs the SQL
itself, so the append-only guarantee survives the code that is supposed to honour it.

Reads go straight to `payload_json` and validate back into the contract. The typed
columns exist for constraints, indexes and health queries; the canonical payload is what
round-trips, so a column that drifted from its payload is a health failure rather than a
silent lossy read.

This class is held to `LearnedRepositoryContract`, the same suite the in-memory reference
passes. See ADR 0086.
"""

from __future__ import annotations

import json
import re
from typing import Any
from uuid import UUID

from sqlalchemy import Table, select, text
from sqlalchemy.exc import DBAPIError, IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine

from cognitive_os.domain.common import utc_now
from cognitive_os.domain.learned import LearnedComponentState
from cognitive_os.domain.learned_evidence import (
    LearnedAccessRecord,
    LearnedActivationApproval,
    LearnedActivationReceipt,
    LearnedArtifactLineage,
    LearnedComponentRevisionRecord,
    LearnedEvidenceKind,
    LearnedEvidenceRecord,
    LearnedObservationRecord,
    LearnedProjectionRow,
    LearnedReplayResult,
    LearnedRepositoryConflict,
    LearnedRepositoryError,
    ObservationStatus,
)
from cognitive_os.infrastructure.postgres.engine import postgres_transaction
from cognitive_os.learning.registry import durable_transition_is_legal

from .tables import (
    learned_accesses,
    learned_activation_approvals,
    learned_activation_history,
    learned_artifacts,
    learned_component_revisions,
    learned_components,
    learned_evidence_records,
    learned_observations,
)

#: The largest page any listing returns, matching the in-memory reference. Unbounded
#: reads over an append-only store are a denial-of-service surface, not a convenience.
MAX_PAGE_SIZE = 500

#: Database error text mapped to the conflict a caller can actually act on. Matching on
#: the message is deliberate: these strings are raised by the controlled functions in
#: migration 0014, they are part of that contract, and
#: `test_every_conflict_message_is_translated` fails if one stops matching.
_CONFLICT_PATTERNS: tuple[tuple[re.Pattern[str], LearnedRepositoryConflict], ...] = (
    (re.compile(r"idempotency key reused"), LearnedRepositoryConflict.IDEMPOTENCY_KEY_REUSED),
    (re.compile(r"is not registered"), LearnedRepositoryConflict.NOT_FOUND),
    (re.compile(r"stale revision for"), LearnedRepositoryConflict.STALE_REVISION),
    (re.compile(r"state before mismatch"), LearnedRepositoryConflict.STALE_REVISION),
    (re.compile(r"illegal learned transition"), LearnedRepositoryConflict.ILLEGAL_TRANSITION),
    (re.compile(r"cannot be replaced with"), LearnedRepositoryConflict.EVIDENCE_MISMATCH),
    (
        re.compile(r"uq_learned_components_active_surface"),
        LearnedRepositoryConflict.SURFACE_ALREADY_ACTIVE,
    ),
    (re.compile(r"uq_learned_\w+_idempotency"), LearnedRepositoryConflict.IDEMPOTENCY_KEY_REUSED),
    (re.compile(r"ck_learned_\w+"), LearnedRepositoryConflict.EVIDENCE_MISMATCH),
)


class PostgresLearnedEvidenceRepository:
    """Durable learned evidence over PostgreSQL, through controlled functions only."""

    def __init__(self, engine: AsyncEngine) -> None:
        self._engine = engine

    # ----------------------------------------------------------------- lifecycle

    async def register_component(
        self,
        *,
        revision: LearnedComponentRevisionRecord,
        descriptor_version: str,
    ) -> LearnedComponentRevisionRecord:
        payload = revision.model_dump(mode="json") | {"descriptor_version": descriptor_version}
        async with postgres_transaction(self._engine) as connection:
            await self._call(
                connection,
                "SELECT cognitive_os.register_learned_component(CAST(:payload AS jsonb))",
                {"payload": json.dumps(payload)},
            )
        stored = await self._revision_by_key(revision.idempotency_key)
        return stored if stored is not None else revision

    async def advance_component(
        self,
        *,
        revision: LearnedComponentRevisionRecord,
        expected_revision: int,
    ) -> LearnedComponentRevisionRecord:
        async with postgres_transaction(self._engine) as connection:
            await self._advance(connection, revision, expected_revision)
        stored = await self._revision_by_key(revision.idempotency_key)
        return stored if stored is not None else revision

    async def record_activation_step(
        self,
        *,
        revision: LearnedComponentRevisionRecord,
        expected_revision: int,
        receipt: LearnedActivationReceipt,
    ) -> tuple[LearnedComponentRevisionRecord, LearnedActivationReceipt]:
        """One transaction: no orphan receipt, and no state change without one.

        If either statement raises, the whole transaction rolls back, so the ledger never
        holds a receipt claiming an activation that did not happen.
        """
        async with postgres_transaction(self._engine) as connection:
            appended = await self._advance(connection, revision, expected_revision)
            if appended:
                await self._call(
                    connection,
                    "SELECT cognitive_os.record_learned_activation(CAST(:payload AS jsonb))",
                    {"payload": receipt.model_dump_json()},
                )
        stored_revision = await self._revision_by_key(revision.idempotency_key) or revision
        stored_receipt = await self.get_activation_receipt(receipt.receipt_id) or receipt
        return stored_revision, stored_receipt

    async def _advance(
        self,
        connection: AsyncConnection,
        revision: LearnedComponentRevisionRecord,
        expected_revision: int,
    ) -> bool:
        """Returns whether a new revision was appended, or False on an idempotent replay."""
        appended = await self._call(
            connection,
            "SELECT cognitive_os.advance_learned_component("
            "CAST(:payload AS jsonb), :expected_revision)",
            {
                "payload": revision.model_dump_json(),
                "expected_revision": expected_revision,
            },
        )
        return bool(appended)

    async def get_component(self, component_id: str) -> LearnedProjectionRow | None:
        row = await self._one(
            select(learned_components).where(learned_components.c.component_id == component_id)
        )
        return _projection(row) if row is not None else None

    async def list_components(
        self,
        *,
        surface: str | None = None,
        state: LearnedComponentState | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[LearnedProjectionRow, ...]:
        statement = select(learned_components)
        if surface is not None:
            statement = statement.where(learned_components.c.surface == surface)
        if state is not None:
            statement = statement.where(learned_components.c.current_state == state.value)
        statement = statement.order_by(learned_components.c.component_id)
        rows = await self._page(statement, limit=limit, offset=offset)
        return tuple(_projection(row) for row in rows)

    async def component_history(
        self, component_id: str, *, limit: int = 100, offset: int = 0
    ) -> tuple[LearnedComponentRevisionRecord, ...]:
        statement = (
            select(learned_component_revisions.c.payload_json)
            .where(learned_component_revisions.c.component_id == component_id)
            .order_by(learned_component_revisions.c.revision)
        )
        rows = await self._page(statement, limit=limit, offset=offset)
        return tuple(
            LearnedComponentRevisionRecord.model_validate(row["payload_json"]) for row in rows
        )

    async def active_component_for(self, surface: str) -> LearnedProjectionRow | None:
        row = await self._one(
            select(learned_components).where(
                learned_components.c.surface == surface,
                learned_components.c.current_state == LearnedComponentState.ACTIVE.value,
            )
        )
        return _projection(row) if row is not None else None

    # ------------------------------------------------------------------- lineage

    async def record_artifact_lineage(
        self, lineage: LearnedArtifactLineage
    ) -> LearnedArtifactLineage:
        await self._append("record_learned_artifact_lineage", lineage.model_dump_json())
        stored = await self.get_artifact_lineage(lineage.lineage_id)
        return stored if stored is not None else lineage

    async def get_artifact_lineage(self, lineage_id: UUID) -> LearnedArtifactLineage | None:
        payload = await self._payload(learned_artifacts, learned_artifacts.c.lineage_id, lineage_id)
        return LearnedArtifactLineage.model_validate(payload) if payload is not None else None

    # ------------------------------------------------------------------ evidence

    async def record_evidence(self, evidence: LearnedEvidenceRecord) -> LearnedEvidenceRecord:
        await self._append("record_learned_evidence", evidence.model_dump_json())
        payload = await self._payload(
            learned_evidence_records, learned_evidence_records.c.evidence_id, evidence.evidence_id
        )
        return LearnedEvidenceRecord.model_validate(payload) if payload is not None else evidence

    async def list_evidence(
        self,
        *,
        component_id: str | None = None,
        evidence_kind: LearnedEvidenceKind | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[LearnedEvidenceRecord, ...]:
        statement = select(learned_evidence_records.c.payload_json)
        if component_id is not None:
            statement = statement.where(learned_evidence_records.c.component_id == component_id)
        if evidence_kind is not None:
            statement = statement.where(
                learned_evidence_records.c.evidence_kind == evidence_kind.value
            )
        statement = statement.order_by(
            learned_evidence_records.c.recorded_at, learned_evidence_records.c.evidence_id
        )
        rows = await self._page(statement, limit=limit, offset=offset)
        return tuple(LearnedEvidenceRecord.model_validate(row["payload_json"]) for row in rows)

    # -------------------------------------------------------------------- intake

    async def record_observation(
        self, observation: LearnedObservationRecord
    ) -> LearnedObservationRecord:
        await self._append("record_learned_observation", observation.model_dump_json())
        payload = await self._one(
            select(learned_observations.c.payload_json).where(
                learned_observations.c.idempotency_key == observation.idempotency_key
            )
        )
        if payload is None:
            return observation
        stored = LearnedObservationRecord.model_validate(payload["payload_json"])
        if stored.content_hash != observation.content_hash:
            raise LearnedRepositoryError(
                LearnedRepositoryConflict.IDEMPOTENCY_KEY_REUSED,
                f"idempotency key {observation.idempotency_key!r} was used for a different "
                "observation",
            )
        return stored

    async def list_observations(
        self,
        *,
        surface: str | None = None,
        status: ObservationStatus | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[LearnedObservationRecord, ...]:
        statement = select(learned_observations.c.payload_json)
        if surface is not None:
            statement = statement.where(learned_observations.c.surface == surface)
        if status is not None:
            statement = statement.where(learned_observations.c.status == status.value)
        statement = statement.order_by(
            learned_observations.c.recorded_at, learned_observations.c.observation_id
        )
        rows = await self._page(statement, limit=limit, offset=offset)
        return tuple(LearnedObservationRecord.model_validate(row["payload_json"]) for row in rows)

    # ---------------------------------------------------------------- activation

    async def record_approval(
        self, approval: LearnedActivationApproval
    ) -> LearnedActivationApproval:
        await self._append("record_learned_approval", approval.model_dump_json())
        stored = await self.get_approval(approval.approval_id)
        return stored if stored is not None else approval

    async def get_approval(self, approval_id: UUID) -> LearnedActivationApproval | None:
        payload = await self._payload(
            learned_activation_approvals, learned_activation_approvals.c.approval_id, approval_id
        )
        return LearnedActivationApproval.model_validate(payload) if payload is not None else None

    async def record_activation(
        self, receipt: LearnedActivationReceipt
    ) -> LearnedActivationReceipt:
        await self._append("record_learned_activation", receipt.model_dump_json())
        stored = await self.get_activation_receipt(receipt.receipt_id)
        return stored if stored is not None else receipt

    async def get_activation_receipt(self, receipt_id: UUID) -> LearnedActivationReceipt | None:
        payload = await self._payload(
            learned_activation_history, learned_activation_history.c.receipt_id, receipt_id
        )
        return LearnedActivationReceipt.model_validate(payload) if payload is not None else None

    async def latest_activation_for(self, surface: str) -> LearnedActivationReceipt | None:
        """The head of the surface's receipt chain.

        Ordered by `(recorded_at, component_revision)` rather than by timestamp alone: two
        receipts written inside one transaction share a clock reading, and an ambiguous
        head would make the rollback target depend on row order.
        """
        row = await self._one(
            select(learned_activation_history.c.payload_json)
            .where(learned_activation_history.c.surface == surface)
            .order_by(
                learned_activation_history.c.recorded_at.desc(),
                learned_activation_history.c.component_revision.desc(),
            )
            .limit(1)
        )
        return (
            LearnedActivationReceipt.model_validate(row["payload_json"])
            if row is not None
            else None
        )

    # --------------------------------------------------------------------- audit

    async def record_access(self, access: LearnedAccessRecord) -> LearnedAccessRecord:
        await self._append("record_learned_access", access.model_dump_json())
        payload = await self._payload(
            learned_accesses, learned_accesses.c.access_id, access.access_id
        )
        return LearnedAccessRecord.model_validate(payload) if payload is not None else access

    # -------------------------------------------------------------------- replay

    async def replay(self) -> LearnedReplayResult:
        """Rebuild every projection from history and compare. Reads only, writes nothing.

        Safe to run against a live database, which is the point: it is the integrity
        check health calls, not a recovery script that has to be scheduled.
        """
        async with self._engine.connect() as connection:
            history_rows = (
                (
                    await connection.execute(
                        select(learned_component_revisions.c.payload_json).order_by(
                            learned_component_revisions.c.component_id,
                            learned_component_revisions.c.revision,
                        )
                    )
                )
                .mappings()
                .all()
            )
            projection_rows = (
                (await connection.execute(select(learned_components))).mappings().all()
            )

        history: dict[str, list[LearnedComponentRevisionRecord]] = {}
        failures: list[str] = []
        for row in history_rows:
            try:
                record = LearnedComponentRevisionRecord.model_validate(row["payload_json"])
            except ValueError as error:
                failures.append(f"a stored revision no longer validates: {error}")
                continue
            history.setdefault(record.component_id, []).append(record)

        rebuilt: dict[str, tuple[int, LearnedComponentState, str, UUID | None]] = {}
        revisions_seen = 0
        for component_id, records in sorted(history.items()):
            revisions_seen += len(records)
            rebuilt_row = _rebuild(component_id, records, failures)
            if rebuilt_row is not None:
                rebuilt[component_id] = rebuilt_row

        for row in sorted(projection_rows, key=lambda item: str(item["component_id"])):
            component_id = str(row["component_id"])
            expected = rebuilt.get(component_id)
            if expected is None:
                failures.append(
                    f"{component_id}: the projection holds a row that history cannot account for"
                )
                continue
            actual = (
                int(row["current_revision"]),
                LearnedComponentState(row["current_state"]),
                str(row["descriptor_hash"]),
                row["artifact_lineage_id"],
            )
            if actual != expected:
                failures.append(
                    f"{component_id}: the projection holds {actual}, history rebuilds {expected}"
                )
        projected = {str(row["component_id"]) for row in projection_rows}
        for component_id in sorted(set(rebuilt) - projected):
            failures.append(f"{component_id}: history exists with no projection row")

        hash_failures = [item for item in failures if "hash mismatch" in item]
        return LearnedReplayResult(
            replayed_components=len(history),
            replayed_revisions=revisions_seen,
            projection_matches=not failures,
            hash_chain_verified=not hash_failures,
            failures=tuple(failures),
            replayed_at=utc_now(),
        )

    # ------------------------------------------------------------------ internals

    async def _append(self, function: str, payload_json: str) -> None:
        async with postgres_transaction(self._engine) as connection:
            await self._call(
                connection,
                f"SELECT cognitive_os.{function}(CAST(:payload AS jsonb))",
                {"payload": payload_json},
            )

    async def _call(
        self, connection: AsyncConnection, statement: str, parameters: dict[str, Any]
    ) -> Any:
        try:
            return await connection.scalar(text(statement), parameters)
        except (IntegrityError, DBAPIError, SQLAlchemyError) as error:
            raise _translate(error) from error

    async def _one(self, statement: Any) -> Any:
        async with self._engine.connect() as connection:
            return (await connection.execute(statement)).mappings().one_or_none()

    async def _page(self, statement: Any, *, limit: int, offset: int) -> Any:
        if limit < 0 or offset < 0:
            raise ValueError("limit and offset must not be negative")
        bounded = statement.limit(min(limit, MAX_PAGE_SIZE)).offset(offset)
        async with self._engine.connect() as connection:
            return (await connection.execute(bounded)).mappings().all()

    async def _payload(self, table: Table, column: Any, key: UUID) -> Any:
        row = await self._one(select(table.c.payload_json).where(column == key))
        return row["payload_json"] if row is not None else None

    async def _revision_by_key(self, key: str) -> LearnedComponentRevisionRecord | None:
        row = await self._one(
            select(learned_component_revisions.c.payload_json).where(
                learned_component_revisions.c.idempotency_key == key
            )
        )
        if row is None:
            return None
        return LearnedComponentRevisionRecord.model_validate(row["payload_json"])


def _rebuild(
    component_id: str,
    records: list[LearnedComponentRevisionRecord],
    failures: list[str],
) -> tuple[int, LearnedComponentState, str, UUID | None] | None:
    """Walk one component's history, recording every disagreement it finds."""
    state: LearnedComponentState | None = None
    previous: LearnedComponentRevisionRecord | None = None
    lineage_id: UUID | None = None
    for expected, record in enumerate(records, start=1):
        if record.revision != expected:
            failures.append(f"{component_id}: revision {expected} is missing from history")
            break
        if record.content_hash != record.canonical_hash(exclude={"content_hash"}):
            failures.append(f"{component_id} revision {record.revision}: hash mismatch")
            break
        if previous is not None and record.previous_revision != previous.revision:
            failures.append(
                f"{component_id} revision {record.revision}: names predecessor "
                f"{record.previous_revision}, follows {previous.revision}"
            )
            break
        if record.state_before is not state:
            failures.append(
                f"{component_id} revision {record.revision}: left "
                f"{record.state_before.value if record.state_before else 'nothing'}, "
                f"history holds {state.value if state else 'nothing'}"
            )
            break
        if state is not None and not durable_transition_is_legal(
            state, record.state_after, rollback_target_revision=record.rollback_target_revision
        ):
            failures.append(
                f"{component_id} revision {record.revision}: illegal transition "
                f"{state.value} -> {record.state_after.value}"
            )
            break
        state, previous = record.state_after, record
        lineage_id = record.artifact_lineage_id or lineage_id
    if previous is None or state is None:
        return None
    return previous.revision, state, previous.descriptor_hash, lineage_id


def _projection(row: Any) -> LearnedProjectionRow:
    return LearnedProjectionRow(
        component_id=row["component_id"],
        surface=row["surface"],
        descriptor_version=row["descriptor_version"],
        current_revision=row["current_revision"],
        current_state=LearnedComponentState(row["current_state"]),
        descriptor_hash=row["descriptor_hash"],
        artifact_lineage_id=row["artifact_lineage_id"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def _translate(error: Exception) -> LearnedRepositoryError:
    """Turn a database refusal into the typed conflict a caller can branch on.

    An untranslated database error would reach the caller as an opaque driver exception,
    and the difference between "someone else moved first" and "this evidence does not
    match" is exactly the difference a caller needs in order to respond correctly.
    """
    message = str(error)
    for pattern, conflict in _CONFLICT_PATTERNS:
        if pattern.search(message):
            return LearnedRepositoryError(conflict, _detail(message))
    return LearnedRepositoryError(LearnedRepositoryConflict.INTEGRITY_FAILURE, _detail(message))


def _detail(message: str) -> str:
    """The database's own sentence, without the SQL echo that carries the payload.

    The `[SQL: ...]` and `[parameters: ...]` sections repeat the whole record, which for
    a learned observation can include sensitive references. An error message is not the
    place to widen exposure.
    """
    first = message.splitlines()[0]
    return first.split("[SQL:")[0].strip() or "the database refused the write"
