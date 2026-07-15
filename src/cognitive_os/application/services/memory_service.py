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
from cognitive_os.events.memory_events import MemoryItemCreated
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
        existing = await self._repository.get_current(request.memory_id)
        created = await self._repository.create_memory(request)
        if existing is None and self._event_service is not None:
            await self._event_service.append(
                memory_id=request.memory_id,
                payload=MemoryItemCreated(record=created[0], revision=created[1]),
                expected_version=0,
                correlation_id=request.request_id,
            )
        return decision, created
