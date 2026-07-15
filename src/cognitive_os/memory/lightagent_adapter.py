"""Narrow governed adapter for LightAgent-facing memory operations."""

from __future__ import annotations

from uuid import UUID

from cognitive_os.application.services.memory_service import MemoryService
from cognitive_os.domain.memory import (
    MemoryQuery,
    MemoryQueryPage,
    MemoryRetrievalTrace,
    MemoryStatus,
    MemoryWriteDecision,
    MemoryWriteRequest,
)

from .retrieval import MemoryRetrievalService


class LightAgentMemoryAdapter:
    """No database access, automatic chat persistence, or verified-write authority."""

    def __init__(
        self, write_service: MemoryService, retrieval_service: MemoryRetrievalService
    ) -> None:
        self._write_service = write_service
        self._retrieval_service = retrieval_service

    async def read(
        self, query: MemoryQuery, *, task_run_id: UUID | None = None
    ) -> tuple[MemoryQueryPage, MemoryRetrievalTrace]:
        return await self._retrieval_service.retrieve(query, task_run_id=task_run_id)

    async def request_candidate_write(
        self, request: MemoryWriteRequest, *, dry_run: bool = False
    ) -> MemoryWriteDecision:
        if request.status is not MemoryStatus.CANDIDATE:
            raise ValueError("LightAgent adapter can request candidate memory only")
        decision, _ = await self._write_service.create(request, dry_run=dry_run)
        return decision
