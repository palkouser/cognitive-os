"""Single governed application gateway for memory mutations."""

from __future__ import annotations

from cognitive_os.application.ports.memory_repository import MemoryRepositoryPort
from cognitive_os.domain.memory import (
    MemoryRecord,
    MemoryRevision,
    MemoryWriteDecision,
    MemoryWriteOutcome,
    MemoryWritePolicy,
    MemoryWriteRequest,
)
from cognitive_os.events.memory_event_service import MemoryEventService
from cognitive_os.memory.errors import MemoryPolicyDeniedError
from cognitive_os.memory.governance import MemoryWritePolicyEvaluator


class MemoryService:
    def __init__(
        self,
        repository: MemoryRepositoryPort,
        policy: MemoryWritePolicy,
        evaluator: MemoryWritePolicyEvaluator | None = None,
        maximum_inline_content_bytes: int = 65_536,
        event_service: MemoryEventService | None = None,
    ) -> None:
        self._repository = repository
        self._policy = policy
        self._evaluator = evaluator or MemoryWritePolicyEvaluator()
        if maximum_inline_content_bytes < 1:
            raise ValueError("maximum inline content bytes must be positive")
        self._maximum_inline_content_bytes = maximum_inline_content_bytes
        self._event_service = event_service

    async def create(
        self, request: MemoryWriteRequest, *, dry_run: bool = False
    ) -> tuple[MemoryWriteDecision, tuple[MemoryRecord, MemoryRevision] | None]:
        if len(request.content.canonical_json().encode()) > self._maximum_inline_content_bytes:
            raise MemoryPolicyDeniedError(("inline_content_limit_exceeded",))
        decision = self._evaluator.evaluate(request, self._policy)
        if decision.decision is MemoryWriteOutcome.DENY:
            raise MemoryPolicyDeniedError(decision.reason_codes)
        if dry_run:
            return decision, None
        record, revision = await self._repository.create_memory(request)
        if self._event_service is not None:
            await self._event_service.ensure_item_created(
                record=record,
                revision=await self._creation_revision(record, revision),
                correlation_id=request.request_id,
            )
        return decision, (record, revision)

    async def _creation_revision(
        self, record: MemoryRecord, revision: MemoryRevision
    ) -> MemoryRevision:
        """The revision a `memory.item_created` event describes: the first one.

        On the ordinary path the create returns revision 1 and this is the identity. On the
        repair path it returns whatever the record is at now, and an event announcing the
        creation must not carry a revision the creation did not have.
        """
        if revision.revision == 1:
            return revision
        first = await self._repository.get_revision(record.memory_id, 1)
        return first or revision
