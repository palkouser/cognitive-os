"""Persistence-neutral boundary for governed strategic memory."""

from typing import Protocol
from uuid import UUID

from cognitive_os.domain.strategies import (
    StrategyAccessRecord,
    StrategyEdgeSet,
    StrategyItem,
    StrategyOutcome,
    StrategyRevision,
    StrategySelectionDecision,
    StrategyStatistics,
)


class StrategyRepositoryPort(Protocol):
    async def create_strategy(
        self,
        item: StrategyItem,
        revision: StrategyRevision,
        edge_set: StrategyEdgeSet | None = None,
    ) -> StrategyItem: ...
    async def append_revision(
        self,
        revision: StrategyRevision,
        *,
        expected_revision: int,
        edge_set: StrategyEdgeSet | None = None,
    ) -> StrategyRevision: ...
    async def get_current(
        self, strategy_id: UUID
    ) -> tuple[StrategyItem, StrategyRevision] | None: ...
    async def get_revision(self, strategy_id: UUID, revision: int) -> StrategyRevision | None: ...
    async def list_revisions(
        self, strategy_id: UUID, *, limit: int = 100
    ) -> tuple[StrategyRevision, ...]: ...
    async def query_candidates(
        self, *, limit: int = 200
    ) -> tuple[tuple[StrategyItem, StrategyRevision], ...]: ...
    async def list_sources(
        self, strategy_id: UUID, revision: int
    ) -> tuple[dict[str, object], ...]: ...
    async def list_edges(self, strategy_id: UUID, revision: int) -> StrategyEdgeSet: ...
    async def write_edge_set(self, edge_set: StrategyEdgeSet) -> None: ...
    async def read_edge_set(self, strategy_id: UUID, revision: int) -> StrategyEdgeSet: ...
    async def record_selection(self, decision: StrategySelectionDecision) -> None: ...
    async def record_outcome(self, outcome: StrategyOutcome) -> StrategyOutcome: ...
    async def list_outcomes(
        self, strategy_id: UUID, revision: int
    ) -> tuple[StrategyOutcome, ...]: ...
    async def record_access(self, records: tuple[StrategyAccessRecord, ...]) -> None: ...
    async def list_accesses(
        self, strategy_id: UUID, revision: int, *, limit: int = 200
    ) -> tuple[StrategyAccessRecord, ...]: ...
    async def read_statistics(
        self, strategy_id: UUID, revision: int, cohort_id: str
    ) -> StrategyStatistics | None: ...
    async def write_statistics(self, statistics: StrategyStatistics) -> None: ...
