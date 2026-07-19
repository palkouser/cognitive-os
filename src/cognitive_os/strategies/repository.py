"""Deterministic in-memory strategy repository for tests and offline operation."""

from uuid import UUID

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

from .errors import StrategyConcurrencyError


class InMemoryStrategyRepository(StrategyRepositoryPort):
    def __init__(self) -> None:
        self.items: dict[UUID, StrategyItem] = {}
        self.revisions: dict[UUID, list[StrategyRevision]] = {}
        self.edges: dict[tuple[UUID, int], StrategyEdgeSet] = {}
        self.selections: dict[UUID, StrategySelectionDecision] = {}
        self.outcomes: dict[UUID, StrategyOutcome] = {}
        self.accesses: list[StrategyAccessRecord] = []
        self.statistics: dict[tuple[UUID, int, str], list[StrategyStatistics]] = {}

    async def create_strategy(
        self,
        item: StrategyItem,
        revision: StrategyRevision,
        edge_set: StrategyEdgeSet | None = None,
    ) -> StrategyItem:
        existing = self.items.get(item.identity.strategy_id)
        if existing is not None:
            if existing.idempotency_key != item.idempotency_key:
                raise StrategyConcurrencyError("strategy identity already exists")
            return existing
        if revision.strategy_id != item.identity.strategy_id or revision.revision != 1:
            raise StrategyConcurrencyError("strategy creation requires matching revision one")
        self.items[item.identity.strategy_id] = item
        self.revisions[item.identity.strategy_id] = [revision]
        self.edges[(revision.strategy_id, revision.revision)] = edge_set or StrategyEdgeSet(
            strategy_id=revision.strategy_id, revision=revision.revision
        )
        return item

    async def append_revision(
        self,
        revision: StrategyRevision,
        *,
        expected_revision: int,
        edge_set: StrategyEdgeSet | None = None,
    ) -> StrategyRevision:
        item = self.items.get(revision.strategy_id)
        if item is None or item.current_revision != expected_revision:
            raise StrategyConcurrencyError("stale strategy revision")
        if revision.revision != expected_revision + 1:
            raise StrategyConcurrencyError("strategy revision sequence gap")
        history = self.revisions[revision.strategy_id]
        if any(value.revision == revision.revision for value in history):
            raise StrategyConcurrencyError("duplicate strategy revision")
        history.append(revision)
        self.items[revision.strategy_id] = item.model_copy(
            update={"current_revision": revision.revision, "current_status": revision.status}
        )
        self.edges[(revision.strategy_id, revision.revision)] = edge_set or StrategyEdgeSet(
            strategy_id=revision.strategy_id, revision=revision.revision
        )
        return revision

    async def get_current(self, strategy_id: UUID) -> tuple[StrategyItem, StrategyRevision] | None:
        item = self.items.get(strategy_id)
        if item is None:
            return None
        return item, self.revisions[strategy_id][-1]

    async def get_revision(self, strategy_id: UUID, revision: int) -> StrategyRevision | None:
        return next(
            (item for item in self.revisions.get(strategy_id, ()) if item.revision == revision),
            None,
        )

    async def list_revisions(
        self, strategy_id: UUID, *, limit: int = 100
    ) -> tuple[StrategyRevision, ...]:
        return tuple(self.revisions.get(strategy_id, ())[-limit:])

    async def query_candidates(
        self, *, limit: int = 200
    ) -> tuple[tuple[StrategyItem, StrategyRevision], ...]:
        rows = [
            (self.items[strategy_id], history[-1])
            for strategy_id, history in self.revisions.items()
        ]
        return tuple(
            sorted(rows, key=lambda row: (row[0].identity.canonical_name, row[1].revision))[:limit]
        )

    async def list_sources(self, strategy_id: UUID, revision: int) -> tuple[dict[str, object], ...]:
        value = await self.get_revision(strategy_id, revision)
        return tuple(item.model_dump(mode="python") for item in value.source_refs) if value else ()

    async def write_edge_set(self, edge_set: StrategyEdgeSet) -> None:
        existing = self.edges.get((edge_set.strategy_id, edge_set.revision))
        if existing is not None and existing != edge_set:
            raise StrategyConcurrencyError("strategy edge set is append-only")
        self.edges[(edge_set.strategy_id, edge_set.revision)] = edge_set

    async def read_edge_set(self, strategy_id: UUID, revision: int) -> StrategyEdgeSet:
        return self.edges.get(
            (strategy_id, revision),
            StrategyEdgeSet(strategy_id=strategy_id, revision=revision),
        )

    async def list_edges(self, strategy_id: UUID, revision: int) -> StrategyEdgeSet:
        return await self.read_edge_set(strategy_id, revision)

    async def record_selection(self, decision: StrategySelectionDecision) -> None:
        existing = self.selections.get(decision.selection_id)
        if existing is not None and existing.decision_hash != decision.decision_hash:
            raise StrategyConcurrencyError("strategy selection identity conflict")
        self.selections[decision.selection_id] = decision

    async def record_outcome(self, outcome: StrategyOutcome) -> StrategyOutcome:
        existing = self.outcomes.get(outcome.outcome_id)
        if existing is not None and existing.outcome_hash != outcome.outcome_hash:
            raise StrategyConcurrencyError("strategy outcome identity conflict")
        self.outcomes[outcome.outcome_id] = outcome
        return outcome

    async def list_outcomes(self, strategy_id: UUID, revision: int) -> tuple[StrategyOutcome, ...]:
        return tuple(
            sorted(
                (
                    item
                    for item in self.outcomes.values()
                    if item.strategy_id == strategy_id and item.strategy_revision == revision
                ),
                key=lambda item: str(item.outcome_id),
            )
        )

    async def record_access(self, records: tuple[StrategyAccessRecord, ...]) -> None:
        known = {item.access_id for item in self.accesses}
        self.accesses.extend(item for item in records if item.access_id not in known)

    async def list_accesses(
        self, strategy_id: UUID, revision: int, *, limit: int = 200
    ) -> tuple[StrategyAccessRecord, ...]:
        return tuple(
            item
            for item in sorted(self.accesses, key=lambda value: str(value.access_id))
            if item.strategy_id == strategy_id and item.revision == revision
        )[:limit]

    async def read_statistics(
        self, strategy_id: UUID, revision: int, cohort_id: str
    ) -> StrategyStatistics | None:
        rows = self.statistics.get((strategy_id, revision, cohort_id), ())
        return rows[-1] if rows else None

    async def write_statistics(self, statistics: StrategyStatistics) -> None:
        key = statistics.strategy_id, statistics.revision, statistics.cohort_id
        rows = self.statistics.setdefault(key, [])
        if any(item.projection_hash == statistics.projection_hash for item in rows):
            return
        if rows and statistics.projection_revision <= rows[-1].projection_revision:
            raise StrategyConcurrencyError("stale strategy statistics projection")
        rows.append(statistics)
