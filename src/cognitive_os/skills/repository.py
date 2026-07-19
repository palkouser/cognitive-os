"""Deterministic in-memory SkillRepository for core and credential-free paths."""

from uuid import UUID

from cognitive_os.application.ports.skill_repository import SkillRepositoryPort
from cognitive_os.domain.skills import (
    SkillAccessRecord,
    SkillExecutionResult,
    SkillItem,
    SkillRevision,
    SkillStatistics,
)

from .errors import SkillConcurrencyError


class InMemorySkillRepository(SkillRepositoryPort):
    def __init__(self) -> None:
        self.items: dict[UUID, SkillItem] = {}
        self.revisions: dict[UUID, list[SkillRevision]] = {}
        self.executions: dict[UUID, SkillExecutionResult] = {}
        self.accesses: list[SkillAccessRecord] = []
        self.statistics: dict[tuple[UUID, int], SkillStatistics] = {}

    async def create_skill(self, item: SkillItem, revision: SkillRevision) -> SkillItem:
        if item.identity.skill_id in self.items:
            existing = self.items[item.identity.skill_id]
            if existing.idempotency_key != item.idempotency_key:
                raise SkillConcurrencyError("skill identity already exists")
            return existing
        if revision.skill_id != item.identity.skill_id or revision.revision != 1:
            raise SkillConcurrencyError("skill creation requires matching revision one")
        self.items[item.identity.skill_id] = item
        self.revisions[item.identity.skill_id] = [revision]
        return item

    async def append_revision(
        self, revision: SkillRevision, *, expected_revision: int
    ) -> SkillRevision:
        item = self.items.get(revision.skill_id)
        if item is None or item.current_revision != expected_revision:
            raise SkillConcurrencyError("stale skill revision")
        if revision.revision != expected_revision + 1:
            raise SkillConcurrencyError("skill revision sequence gap")
        history = self.revisions[revision.skill_id]
        if any(value.revision == revision.revision for value in history):
            raise SkillConcurrencyError("duplicate skill revision")
        history.append(revision)
        self.items[revision.skill_id] = item.model_copy(
            update={"current_revision": revision.revision, "current_status": revision.status}
        )
        return revision

    async def get_current(self, skill_id: UUID) -> tuple[SkillItem, SkillRevision] | None:
        item = self.items.get(skill_id)
        if item is None:
            return None
        return item, self.revisions[skill_id][-1]

    async def get_revision(self, skill_id: UUID, revision: int) -> SkillRevision | None:
        return next(
            (item for item in self.revisions.get(skill_id, ()) if item.revision == revision), None
        )

    async def list_revisions(
        self, skill_id: UUID, *, limit: int = 100
    ) -> tuple[SkillRevision, ...]:
        return tuple(self.revisions.get(skill_id, ())[-limit:])

    async def query_candidates(
        self, *, limit: int = 200
    ) -> tuple[tuple[SkillItem, SkillRevision], ...]:
        current = [
            (self.items[skill_id], values[-1]) for skill_id, values in self.revisions.items()
        ]
        return tuple(
            sorted(current, key=lambda item: (str(item[0].identity.skill_id), item[1].revision))[
                :limit
            ]
        )

    async def record_execution(self, result: SkillExecutionResult) -> SkillExecutionResult:
        existing = self.executions.get(result.execution_id)
        if existing is not None and existing.result_hash != result.result_hash:
            raise SkillConcurrencyError("skill execution identity conflict")
        self.executions[result.execution_id] = result
        return result

    async def get_execution(self, execution_id: UUID) -> SkillExecutionResult | None:
        return self.executions.get(execution_id)

    async def list_executions(
        self, skill_id: UUID, revision: int
    ) -> tuple[SkillExecutionResult, ...]:
        return tuple(
            sorted(
                (
                    item
                    for item in self.executions.values()
                    if item.skill_id == skill_id and item.skill_revision == revision
                ),
                key=lambda item: str(item.execution_id),
            )
        )

    async def record_access(self, records: tuple[SkillAccessRecord, ...]) -> None:
        known = {item.access_id for item in self.accesses}
        self.accesses.extend(item for item in records if item.access_id not in known)

    async def list_accesses(
        self, skill_id: UUID, revision: int, *, limit: int = 200
    ) -> tuple[SkillAccessRecord, ...]:
        return tuple(
            item
            for item in sorted(self.accesses, key=lambda value: str(value.access_id))
            if item.skill_id == skill_id and item.revision == revision
        )[:limit]

    async def read_statistics(self, skill_id: UUID, revision: int) -> SkillStatistics | None:
        return self.statistics.get((skill_id, revision))

    async def write_statistics(self, statistics: SkillStatistics) -> None:
        self.statistics[(statistics.skill_id, statistics.revision)] = statistics
