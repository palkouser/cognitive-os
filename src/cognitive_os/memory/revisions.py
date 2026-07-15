"""Memory lifecycle transition and replay invariants."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from cognitive_os.domain.memory import MemoryStatus
from cognitive_os.events.memory_events import (
    MemoryExpired,
    MemoryItemCreated,
    MemoryPromoted,
    MemoryRetracted,
    MemoryRevisionAppended,
    MemorySuperseded,
)

MemoryReplayEvent = (
    MemoryItemCreated
    | MemoryRevisionAppended
    | MemoryPromoted
    | MemorySuperseded
    | MemoryRetracted
    | MemoryExpired
)

_LEGAL_TRANSITIONS = {
    MemoryStatus.CANDIDATE: frozenset(
        {
            MemoryStatus.CANDIDATE,
            MemoryStatus.VERIFIED,
            MemoryStatus.RETRACTED,
            MemoryStatus.EXPIRED,
        }
    ),
    MemoryStatus.VERIFIED: frozenset(
        {
            MemoryStatus.VERIFIED,
            MemoryStatus.SUPERSEDED,
            MemoryStatus.RETRACTED,
            MemoryStatus.EXPIRED,
        }
    ),
    MemoryStatus.SUPERSEDED: frozenset(),
    MemoryStatus.RETRACTED: frozenset(),
    MemoryStatus.EXPIRED: frozenset(),
}


def can_transition_memory(current: MemoryStatus, target: MemoryStatus) -> bool:
    return target in _LEGAL_TRANSITIONS[current]


@dataclass(frozen=True)
class MemoryReplayState:
    memory_id: UUID
    status: MemoryStatus
    current_revision: int
    revision_hashes: tuple[str, ...]


class MemoryStreamReducer:
    """Reconstruct lifecycle state while rejecting gaps and rewrites."""

    def reduce(self, events: tuple[MemoryReplayEvent, ...]) -> MemoryReplayState:
        if not events or not isinstance(events[0], MemoryItemCreated):
            raise ValueError("memory stream must begin with item creation")
        created = events[0]
        if created.record.current_revision != 1 or created.revision.revision != 1:
            raise ValueError("memory stream creation must contain revision one")
        if created.record.memory_id != created.revision.memory_id:
            raise ValueError("memory creation identity mismatch")
        state = MemoryReplayState(
            memory_id=created.record.memory_id,
            status=created.revision.status,
            current_revision=1,
            revision_hashes=(created.revision.content_hash,),
        )
        for event in events[1:]:
            state = self._apply(state, event)
        return state

    def _apply(self, state: MemoryReplayState, event: MemoryReplayEvent) -> MemoryReplayState:
        if isinstance(event, MemoryItemCreated):
            raise ValueError("duplicate memory creation event")
        if event.memory_id != state.memory_id:
            raise ValueError("event belongs to a different memory stream")
        if isinstance(event, MemoryRevisionAppended):
            if event.expected_revision != state.current_revision:
                raise ValueError("memory revision expected-version mismatch")
            if event.revision.revision != state.current_revision + 1:
                raise ValueError("memory revision gap or duplicate")
            if not can_transition_memory(state.status, event.revision.status):
                raise ValueError("illegal memory lifecycle transition")
            return MemoryReplayState(
                memory_id=state.memory_id,
                status=event.revision.status,
                current_revision=event.revision.revision,
                revision_hashes=(*state.revision_hashes, event.revision.content_hash),
            )
        if (
            event.expected_revision != state.current_revision
            or event.revision.revision != state.current_revision + 1
            or event.revision.memory_id != state.memory_id
        ):
            raise ValueError("memory transition revision mismatch")
        target = {
            MemoryPromoted: MemoryStatus.VERIFIED,
            MemorySuperseded: MemoryStatus.SUPERSEDED,
            MemoryRetracted: MemoryStatus.RETRACTED,
            MemoryExpired: MemoryStatus.EXPIRED,
        }.get(type(event))
        if (
            target is None
            or event.revision.status is not target
            or not can_transition_memory(state.status, target)
        ):
            raise ValueError("illegal memory lifecycle transition")
        return MemoryReplayState(
            memory_id=state.memory_id,
            status=target,
            current_revision=event.revision.revision,
            revision_hashes=(*state.revision_hashes, event.revision.content_hash),
        )
