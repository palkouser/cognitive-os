"""Transactional PostgreSQL repository for governed strategies."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import and_, insert, select, text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine

from cognitive_os.application.ports.strategy_repository import StrategyRepositoryPort
from cognitive_os.domain.strategies import (
    StrategyAccessRecord,
    StrategyEdgeSet,
    StrategyItem,
    StrategyOutcome,
    StrategyRevision,
    StrategySelectionDecision,
    StrategyStatistics,
)
from cognitive_os.infrastructure.postgres.engine import postgres_transaction
from cognitive_os.strategies.errors import StrategyConcurrencyError

from .tables import (
    strategy_accesses,
    strategy_edges,
    strategy_items,
    strategy_outcomes,
    strategy_revisions,
    strategy_selections,
    strategy_sources,
    strategy_statistics,
)


def _item_values(item: StrategyItem) -> dict[str, object]:
    identity = item.identity
    return {
        "strategy_id": identity.strategy_id,
        "canonical_name": identity.canonical_name,
        "scope_type": identity.scope.scope_type.value,
        "scope_id": identity.scope.scope_id,
        "problem_class_id": identity.problem_class_id,
        "current_revision": item.current_revision,
        "current_status": item.current_status.value,
        "idempotency_key": item.idempotency_key,
        "identity_json": identity.model_dump(mode="json"),
        "created_at": identity.created_at,
    }


def _revision_values(revision: StrategyRevision) -> dict[str, object]:
    problem_conditions = [
        condition.parameters["problem_class_id"]
        for condition in revision.applicability_profile.conditions
        if "problem_class_id" in condition.parameters
    ]
    return {
        "strategy_id": revision.strategy_id,
        "revision": revision.revision,
        "previous_revision": revision.previous_revision,
        "status": revision.status.value,
        "problem_class_id": problem_conditions[0] if problem_conditions else "unspecified",
        "content_hash": revision.content_hash,
        "sensitivity": revision.sensitivity.value,
        "payload_json": revision.model_dump(mode="json"),
        "created_at": revision.created_at,
    }


async def _insert_revision(
    connection: AsyncConnection,
    revision: StrategyRevision,
    edge_set: StrategyEdgeSet | None = None,
) -> None:
    await connection.execute(insert(strategy_revisions).values(**_revision_values(revision)))
    await connection.execute(
        insert(strategy_sources),
        [
            {
                "strategy_id": revision.strategy_id,
                "revision": revision.revision,
                "source_order": index,
                "source_type": source.source_type.value,
                "source_id": source.source_id,
                "source_revision": source.source_revision,
                "content_hash": source.content_hash,
            }
            for index, source in enumerate(revision.source_refs)
        ],
    )
    if edge_set and edge_set.edges:
        await connection.execute(
            insert(strategy_edges),
            [
                {
                    "edge_id": edge.edge_id,
                    "strategy_id": edge.source_strategy_id,
                    "revision": edge.source_revision,
                    "edge_type": edge.edge_type.value,
                    "target_type": edge.target.target_type.value,
                    "target_id": edge.target.target_id,
                    "target_revision": edge.target.target_revision,
                    "target_hash": edge.target.content_hash,
                    "weight": edge.weight,
                    "edge_hash": edge.edge_hash,
                    "payload_json": edge.model_dump(mode="json"),
                    "created_at": edge.created_at,
                }
                for edge in edge_set.edges
            ],
        )


class PostgresStrategyRepository(StrategyRepositoryPort):
    def __init__(self, engine: AsyncEngine) -> None:
        self._engine = engine

    async def create_strategy(
        self,
        item: StrategyItem,
        revision: StrategyRevision,
        edge_set: StrategyEdgeSet | None = None,
    ) -> StrategyItem:
        try:
            async with postgres_transaction(self._engine) as connection:
                await connection.execute(insert(strategy_items).values(**_item_values(item)))
                await _insert_revision(connection, revision, edge_set)
            return item
        except IntegrityError:
            current = await self.get_current(item.identity.strategy_id)
            if current is None or current[0].idempotency_key != item.idempotency_key:
                raise StrategyConcurrencyError("strategy identity conflict") from None
            return current[0]

    async def append_revision(
        self,
        revision: StrategyRevision,
        *,
        expected_revision: int,
        edge_set: StrategyEdgeSet | None = None,
    ) -> StrategyRevision:
        try:
            async with postgres_transaction(self._engine) as connection:
                await _insert_revision(connection, revision, edge_set)
                advanced = await connection.scalar(
                    text(
                        "SELECT cognitive_os.advance_strategy("
                        ":strategy_id, :expected_revision, :next_revision, :next_status)"
                    ),
                    {
                        "strategy_id": revision.strategy_id,
                        "expected_revision": expected_revision,
                        "next_revision": revision.revision,
                        "next_status": revision.status.value,
                    },
                )
                if not advanced:
                    raise StrategyConcurrencyError("stale strategy revision")
            return revision
        except IntegrityError as error:
            raise StrategyConcurrencyError("strategy revision conflict") from error

    async def get_current(self, strategy_id: UUID) -> tuple[StrategyItem, StrategyRevision] | None:
        statement = (
            select(strategy_items, strategy_revisions.c.payload_json)
            .join(
                strategy_revisions,
                and_(
                    strategy_items.c.strategy_id == strategy_revisions.c.strategy_id,
                    strategy_items.c.current_revision == strategy_revisions.c.revision,
                ),
            )
            .where(strategy_items.c.strategy_id == strategy_id)
        )
        async with self._engine.connect() as connection:
            row = (await connection.execute(statement)).mappings().one_or_none()
        if row is None:
            return None
        item = StrategyItem.model_validate(
            {
                "identity": row["identity_json"],
                "current_revision": row["current_revision"],
                "current_status": row["current_status"],
                "idempotency_key": row["idempotency_key"],
            }
        )
        return item, StrategyRevision.model_validate(row["payload_json"])

    async def get_revision(self, strategy_id: UUID, revision: int) -> StrategyRevision | None:
        statement = select(strategy_revisions.c.payload_json).where(
            strategy_revisions.c.strategy_id == strategy_id,
            strategy_revisions.c.revision == revision,
        )
        async with self._engine.connect() as connection:
            payload = await connection.scalar(statement)
        return StrategyRevision.model_validate(payload) if payload is not None else None

    async def list_revisions(
        self, strategy_id: UUID, *, limit: int = 100
    ) -> tuple[StrategyRevision, ...]:
        statement = (
            select(strategy_revisions.c.payload_json)
            .where(strategy_revisions.c.strategy_id == strategy_id)
            .order_by(strategy_revisions.c.revision.desc())
            .limit(limit)
        )
        async with self._engine.connect() as connection:
            values = (await connection.scalars(statement)).all()
        return tuple(StrategyRevision.model_validate(value) for value in reversed(values))

    async def query_candidates(
        self, *, limit: int = 200
    ) -> tuple[tuple[StrategyItem, StrategyRevision], ...]:
        statement = (
            select(strategy_items.c.strategy_id).order_by(strategy_items.c.strategy_id).limit(limit)
        )
        async with self._engine.connect() as connection:
            identities = (await connection.scalars(statement)).all()
        rows = [await self.get_current(strategy_id) for strategy_id in identities]
        return tuple(row for row in rows if row is not None)

    async def list_sources(self, strategy_id: UUID, revision: int) -> tuple[dict[str, object], ...]:
        statement = (
            select(strategy_sources)
            .where(
                strategy_sources.c.strategy_id == strategy_id,
                strategy_sources.c.revision == revision,
            )
            .order_by(strategy_sources.c.source_order)
        )
        async with self._engine.connect() as connection:
            rows = (await connection.execute(statement)).mappings().all()
        return tuple(dict(row) for row in rows)

    async def write_edge_set(self, edge_set: StrategyEdgeSet) -> None:
        if not edge_set.edges:
            return
        async with postgres_transaction(self._engine) as connection:
            await connection.execute(
                pg_insert(strategy_edges)
                .values(
                    [
                        {
                            "edge_id": edge.edge_id,
                            "strategy_id": edge.source_strategy_id,
                            "revision": edge.source_revision,
                            "edge_type": edge.edge_type.value,
                            "target_type": edge.target.target_type.value,
                            "target_id": edge.target.target_id,
                            "target_revision": edge.target.target_revision,
                            "target_hash": edge.target.content_hash,
                            "weight": edge.weight,
                            "edge_hash": edge.edge_hash,
                            "payload_json": edge.model_dump(mode="json"),
                            "created_at": edge.created_at,
                        }
                        for edge in edge_set.edges
                    ]
                )
                .on_conflict_do_nothing()
            )

    async def read_edge_set(self, strategy_id: UUID, revision: int) -> StrategyEdgeSet:
        statement = (
            select(strategy_edges.c.payload_json)
            .where(
                strategy_edges.c.strategy_id == strategy_id,
                strategy_edges.c.revision == revision,
            )
            .order_by(strategy_edges.c.edge_hash)
        )
        async with self._engine.connect() as connection:
            values = (await connection.scalars(statement)).all()
        from cognitive_os.domain.strategies import StrategyEdge

        return StrategyEdgeSet(
            strategy_id=strategy_id,
            revision=revision,
            edges=tuple(StrategyEdge.model_validate(value) for value in values),
        )

    async def list_edges(self, strategy_id: UUID, revision: int) -> StrategyEdgeSet:
        return await self.read_edge_set(strategy_id, revision)

    async def record_selection(self, decision: StrategySelectionDecision) -> None:
        values = {
            "selection_id": decision.selection_id,
            "task_run_id": decision.task_run_id,
            "status": decision.status.value,
            "selected_strategy_id": decision.selected_strategy_id,
            "selected_revision": decision.selected_revision,
            "decision_hash": decision.decision_hash,
            "payload_json": decision.model_dump(mode="json"),
            "created_at": decision.created_at,
        }
        async with postgres_transaction(self._engine) as connection:
            await connection.execute(
                pg_insert(strategy_selections).values(**values).on_conflict_do_nothing()
            )

    async def record_outcome(self, outcome: StrategyOutcome) -> StrategyOutcome:
        values = {
            "outcome_id": outcome.outcome_id,
            "execution_id": outcome.execution_id,
            "selection_id": outcome.selection_id,
            "task_run_id": outcome.task_run_id,
            "strategy_id": outcome.strategy_id,
            "revision": outcome.strategy_revision,
            "cohort_id": "all",
            "status": outcome.status.value,
            "outcome_hash": outcome.outcome_hash,
            "payload_json": outcome.model_dump(mode="json"),
            "finished_at": outcome.finished_at,
        }
        try:
            async with postgres_transaction(self._engine) as connection:
                await connection.execute(insert(strategy_outcomes).values(**values))
            return outcome
        except IntegrityError:
            statement = select(strategy_outcomes.c.payload_json).where(
                strategy_outcomes.c.outcome_id == outcome.outcome_id
            )
            async with self._engine.connect() as connection:
                payload = await connection.scalar(statement)
            if payload is None:
                raise StrategyConcurrencyError("strategy outcome conflict") from None
            existing = StrategyOutcome.model_validate(payload)
            if existing.outcome_hash != outcome.outcome_hash:
                raise StrategyConcurrencyError("strategy outcome identity conflict") from None
            return existing

    async def list_outcomes(self, strategy_id: UUID, revision: int) -> tuple[StrategyOutcome, ...]:
        statement = (
            select(strategy_outcomes.c.payload_json)
            .where(
                strategy_outcomes.c.strategy_id == strategy_id,
                strategy_outcomes.c.revision == revision,
            )
            .order_by(strategy_outcomes.c.outcome_id)
        )
        async with self._engine.connect() as connection:
            values = (await connection.scalars(statement)).all()
        return tuple(StrategyOutcome.model_validate(value) for value in values)

    async def record_access(self, records: tuple[StrategyAccessRecord, ...]) -> None:
        if not records:
            return
        values = [
            {
                "access_id": item.access_id,
                "strategy_id": item.strategy_id,
                "revision": item.revision,
                "access_type": item.access_type.value,
                "task_run_id": item.task_run_id,
                "context_request_id": item.context_request_id,
                "scope_type": item.scope.scope_type.value,
                "scope_id": item.scope.scope_id,
                "sensitivity": item.sensitivity.value,
                "accessed_at": item.accessed_at,
                "payload_json": item.model_dump(mode="json"),
            }
            for item in records
        ]
        async with postgres_transaction(self._engine) as connection:
            await connection.execute(
                pg_insert(strategy_accesses).values(values).on_conflict_do_nothing()
            )

    async def list_accesses(
        self, strategy_id: UUID, revision: int, *, limit: int = 200
    ) -> tuple[StrategyAccessRecord, ...]:
        statement = (
            select(strategy_accesses.c.payload_json)
            .where(
                strategy_accesses.c.strategy_id == strategy_id,
                strategy_accesses.c.revision == revision,
            )
            .order_by(strategy_accesses.c.accessed_at, strategy_accesses.c.access_id)
            .limit(limit)
        )
        async with self._engine.connect() as connection:
            values = (await connection.scalars(statement)).all()
        return tuple(StrategyAccessRecord.model_validate(value) for value in values)

    async def read_statistics(
        self, strategy_id: UUID, revision: int, cohort_id: str
    ) -> StrategyStatistics | None:
        statement = (
            select(strategy_statistics.c.payload_json)
            .where(
                strategy_statistics.c.strategy_id == strategy_id,
                strategy_statistics.c.revision == revision,
                strategy_statistics.c.cohort_id == cohort_id,
            )
            .order_by(strategy_statistics.c.projection_revision.desc())
            .limit(1)
        )
        async with self._engine.connect() as connection:
            payload = await connection.scalar(statement)
        return StrategyStatistics.model_validate(payload) if payload is not None else None

    async def write_statistics(self, statistics: StrategyStatistics) -> None:
        values = {
            "strategy_id": statistics.strategy_id,
            "revision": statistics.revision,
            "cohort_id": statistics.cohort_id,
            "projection_revision": statistics.projection_revision,
            "projection_hash": statistics.projection_hash,
            "executions": statistics.executions,
            "payload_json": statistics.model_dump(mode="json"),
        }
        async with postgres_transaction(self._engine) as connection:
            await connection.execute(
                pg_insert(strategy_statistics).values(**values).on_conflict_do_nothing()
            )
