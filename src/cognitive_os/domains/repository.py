"""Append-only in-memory store for pilot runs and transfer evidence.

Records are immutable: re-recording the same identity with different content is a
conflict, never a silent overwrite. The PostgreSQL adapter enforces the same rule
with constraints and append-only triggers.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, TypeVar
from uuid import UUID

from cognitive_os.domain.domains import (
    DomainAnswer,
    DomainDerivation,
    DomainPilotRun,
    DomainVerificationOutcome,
    TransferExperiment,
    TransferResult,
)

if TYPE_CHECKING:
    from .service import DomainPilotResult

#: Any immutable contract this repository stores.
_Record = TypeVar("_Record")


class DomainConflictError(Exception):
    """Raised when an immutable record would be replaced by different content."""


class InMemoryDomainRepository:
    def __init__(self) -> None:
        self.runs: dict[UUID, DomainPilotRun] = {}
        self.derivations: dict[UUID, DomainDerivation] = {}
        self.answers: dict[UUID, DomainAnswer] = {}
        self.outcomes: dict[UUID, DomainVerificationOutcome] = {}
        self.experiments: dict[UUID, TransferExperiment] = {}
        self.results: dict[UUID, TransferResult] = {}
        self.accesses: list[tuple[str, UUID]] = []

    async def record(self, result: DomainPilotResult) -> None:
        self._immutable(self.runs, result.run.run_id, result.run)
        if result.derivation is not None:
            self._immutable(self.derivations, result.derivation.derivation_id, result.derivation)
        if result.answer is not None:
            self._immutable(self.answers, result.run.run_id, result.answer)
        if result.outcome is not None:
            self._immutable(self.outcomes, result.run.run_id, result.outcome)
        self.accesses.append(("write:run", result.run.run_id))

    async def record_transfer(self, experiment: TransferExperiment, result: TransferResult) -> None:
        if result.experiment_id != experiment.experiment_id:
            raise DomainConflictError("transfer result does not belong to the experiment")
        self._immutable(self.experiments, experiment.experiment_id, experiment)
        self._immutable(self.results, experiment.experiment_id, result)
        self.accesses.append(("write:transfer", experiment.experiment_id))

    async def get_run(self, run_id: UUID) -> DomainPilotRun | None:
        self.accesses.append(("read:run", run_id))
        return self.runs.get(run_id)

    async def list_runs(self) -> tuple[DomainPilotRun, ...]:
        return tuple(self.runs[key] for key in sorted(self.runs, key=str))

    @staticmethod
    def _immutable(store: dict[UUID, _Record], key: UUID, value: _Record) -> None:
        existing = store.get(key)
        if existing is not None and existing != value:
            raise DomainConflictError(f"record {key} already exists with different content")
        store[key] = value
