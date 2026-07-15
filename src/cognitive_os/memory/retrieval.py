"""Provider-neutral single-mode retrieval with mandatory access audit."""

from __future__ import annotations

from time import monotonic
from uuid import NAMESPACE_URL, UUID, uuid5

from cognitive_os.application.ports.memory_repository import MemoryRepositoryPort
from cognitive_os.domain.common import utc_now
from cognitive_os.domain.memory import (
    MemoryAccessRecord,
    MemoryQuery,
    MemoryQueryPage,
    MemoryRetrievalTrace,
)

from .errors import MemoryAuditError


class MemoryRetrievalService:
    def __init__(
        self,
        repository: MemoryRepositoryPort,
        *,
        fail_closed_on_audit_error: bool = True,
    ) -> None:
        self._repository = repository
        self._fail_closed_on_audit_error = fail_closed_on_audit_error

    async def retrieve(
        self, query: MemoryQuery, *, task_run_id: UUID | None = None
    ) -> tuple[MemoryQueryPage, MemoryRetrievalTrace]:
        started = monotonic()
        query_hash = query.model_copy(update={"cursor": None}).canonical_hash()
        filter_hash = query.filters.canonical_hash()
        page = await self._repository.search(query)
        records = tuple(
            MemoryAccessRecord(
                access_id=uuid5(
                    NAMESPACE_URL,
                    f"{query.query_id}:{result.memory_id}:{result.revision}:{result.rank}",
                ),
                query_id=query.query_id,
                task_run_id=task_run_id,
                memory_id=result.memory_id,
                revision=result.revision,
                retrieval_mode=query.mode,
                retrieval_rank=result.rank,
                retrieval_score=result.score,
                accessed_at=utc_now(),
                scope=result.scope,
                sensitivity=result.sensitivity,
                query_hash=query_hash,
                filter_hash=filter_hash,
            )
            for result in page.results
        )
        audit_succeeded = False
        try:
            await self._repository.record_access(records)
            audit_succeeded = True
        except Exception as error:
            if self._fail_closed_on_audit_error:
                raise MemoryAuditError("memory access audit failed") from error
        trace = MemoryRetrievalTrace(
            query_id=query.query_id,
            retrieval_mode=query.mode,
            resolved_scopes=query.filters.scopes,
            query_hash=query_hash,
            filter_hash=filter_hash,
            candidate_count=len(page.results),
            returned_count=len(page.results),
            access_audit_attempted=True,
            access_audit_succeeded=audit_succeeded,
            elapsed_ms=(monotonic() - started) * 1000,
        )
        return page, trace
