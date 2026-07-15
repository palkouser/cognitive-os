"""Append-only governed lifecycle operations."""

from __future__ import annotations

from uuid import UUID

from cognitive_os.application.ports.memory_repository import MemoryRepositoryPort
from cognitive_os.domain.common import utc_now
from cognitive_os.domain.memory import (
    MemoryCreator,
    MemoryCreatorType,
    MemoryExpiryRequest,
    MemoryPromotionRequest,
    MemoryProvenanceBundle,
    MemoryRetractionRequest,
    MemoryRevision,
    MemorySourceRef,
    MemorySourceType,
    MemoryStatus,
    MemorySupersessionRequest,
    MemoryTransitionReason,
    memory_revision_hash,
)
from cognitive_os.events.memory_event_service import MemoryEventService
from cognitive_os.events.memory_events import (
    MemoryExpired,
    MemoryPromoted,
    MemoryRetracted,
    MemorySuperseded,
)

from .errors import MemoryNotFoundError
from .revisions import can_transition_memory


class MemoryLifecycleService:
    def __init__(
        self,
        repository: MemoryRepositoryPort,
        event_service: MemoryEventService | None = None,
    ) -> None:
        self._repository = repository
        self._event_service = event_service

    async def promote(self, request: MemoryPromotionRequest) -> MemoryRevision:
        if request.actor.creator_type is MemoryCreatorType.PROVIDER:
            raise ValueError("provider cannot authorize memory promotion")
        evidence_types = {source.identity.source_type for source in request.evidence.sources}
        if (
            not {
                MemorySourceType.ACCEPTANCE_DECISION,
                MemorySourceType.CODING_TRAJECTORY,
            }
            <= evidence_types
        ):
            raise ValueError("promotion requires accepted authoritative trajectory evidence")
        for source in request.evidence.sources:
            identity = source.identity
            if identity.source_type is MemorySourceType.MEMORY_REVISION:
                if identity.memory_id is None:
                    raise ValueError("memory revision evidence identity is incomplete")
                source_memory = await self._repository.get_current(identity.memory_id)
                if source_memory is None or source_memory[1].status in {
                    MemoryStatus.RETRACTED,
                    MemoryStatus.SUPERSEDED,
                    MemoryStatus.EXPIRED,
                }:
                    raise ValueError("promotion evidence contains an explicit source conflict")
        revision = await self._transition(
            request.memory_id,
            request.expected_revision,
            MemoryStatus.VERIFIED,
            request.actor,
            request.reason,
            extra_sources=request.evidence.sources,
        )
        if self._event_service is not None:
            await self._event_service.append(
                memory_id=request.memory_id,
                payload=MemoryPromoted(
                    memory_id=request.memory_id,
                    expected_revision=request.expected_revision,
                    revision=revision,
                    reason=request.reason.value,
                    transitioned_at=revision.created_at,
                ),
                expected_version=request.expected_revision,
                correlation_id=request.request_id,
            )
        return revision

    async def supersede(self, request: MemorySupersessionRequest) -> MemoryRevision:
        successor = await self._repository.get_current(request.successor_memory_id)
        if successor is None:
            raise MemoryNotFoundError("successor memory does not exist")
        revision = await self._transition(
            request.memory_id,
            request.expected_revision,
            MemoryStatus.SUPERSEDED,
            request.actor,
            request.reason,
            successor_memory_id=request.successor_memory_id,
        )
        if self._event_service is not None:
            await self._event_service.append(
                memory_id=request.memory_id,
                payload=MemorySuperseded(
                    memory_id=request.memory_id,
                    expected_revision=request.expected_revision,
                    revision=revision,
                    reason=request.reason.value,
                    transitioned_at=revision.created_at,
                    successor_memory_id=request.successor_memory_id,
                ),
                expected_version=request.expected_revision,
                correlation_id=request.request_id,
            )
        return revision

    async def retract(self, request: MemoryRetractionRequest) -> MemoryRevision:
        revision = await self._transition(
            request.memory_id,
            request.expected_revision,
            MemoryStatus.RETRACTED,
            request.actor,
            request.reason,
        )
        if self._event_service is not None:
            await self._event_service.append(
                memory_id=request.memory_id,
                payload=MemoryRetracted(
                    memory_id=request.memory_id,
                    expected_revision=request.expected_revision,
                    revision=revision,
                    reason=request.reason.value,
                    transitioned_at=revision.created_at,
                ),
                expected_version=request.expected_revision,
                correlation_id=request.request_id,
            )
        return revision

    async def expire(self, request: MemoryExpiryRequest) -> MemoryRevision:
        revision = await self._transition(
            request.memory_id,
            request.expected_revision,
            MemoryStatus.EXPIRED,
            request.actor,
            request.reason,
        )
        if self._event_service is not None:
            await self._event_service.append(
                memory_id=request.memory_id,
                payload=MemoryExpired(
                    memory_id=request.memory_id,
                    expected_revision=request.expected_revision,
                    revision=revision,
                    reason=request.reason.value,
                    transitioned_at=revision.created_at,
                ),
                expected_version=request.expected_revision,
                correlation_id=request.request_id,
            )
        return revision

    async def _transition(
        self,
        memory_id: UUID,
        expected_revision: int,
        target: MemoryStatus,
        actor: MemoryCreator,
        reason: MemoryTransitionReason,
        *,
        extra_sources: tuple[MemorySourceRef, ...] = (),
        successor_memory_id: UUID | None = None,
    ) -> MemoryRevision:
        current = await self._repository.get_current(memory_id)
        if current is None:
            raise MemoryNotFoundError("memory does not exist")
        _, previous = current
        if not can_transition_memory(previous.status, target):
            raise ValueError(f"illegal memory transition: {previous.status} -> {target}")
        sources = await self._repository.list_sources(memory_id, previous.revision)
        by_key = {source.identity.sort_key(): source for source in (*sources, *extra_sources)}
        provenance = MemoryProvenanceBundle(sources=tuple(by_key[key] for key in sorted(by_key)))
        revision_number = expected_revision + 1
        revision = MemoryRevision(
            memory_id=previous.memory_id,
            revision=revision_number,
            previous_revision=expected_revision,
            content=previous.content,
            content_artifact=previous.content_artifact,
            content_hash=memory_revision_hash(
                memory_id=previous.memory_id,
                revision=revision_number,
                content=previous.content,
                status=target,
                confidence=previous.confidence,
                salience=previous.salience,
                sensitivity=previous.sensitivity,
            ),
            status=target,
            confidence=previous.confidence,
            salience=previous.salience,
            sensitivity=previous.sensitivity,
            reason=reason,
            created_at=utc_now(),
            created_by=actor,
            expires_at=previous.expires_at,
            successor_memory_id=successor_memory_id,
        )
        return await self._repository.append_revision(
            revision, provenance, expected_revision=expected_revision
        )
