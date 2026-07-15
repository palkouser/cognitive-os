"""Replay reducers for append-only semantic streams."""

from dataclasses import dataclass
from uuid import UUID

from cognitive_os.domain.semantic_memory import BeliefStatus
from cognitive_os.events.semantic_memory_events import (
    SemanticClaimBeliefChanged,
    SemanticClaimCreated,
    SemanticClaimRevisionAppended,
)

from .beliefs import assert_legal_transition

SemanticClaimEvent = (
    SemanticClaimCreated | SemanticClaimRevisionAppended | SemanticClaimBeliefChanged
)


@dataclass(frozen=True)
class SemanticClaimReplayState:
    claim_id: UUID
    current_revision: int
    belief_status: BeliefStatus
    revision_hashes: tuple[str, ...]


class SemanticClaimStreamReducer:
    def reduce(
        self, events: tuple[SemanticClaimEvent, ...], initial_status: BeliefStatus
    ) -> SemanticClaimReplayState:
        if not events or not isinstance(events[0], SemanticClaimCreated):
            raise ValueError("claim stream must begin with claim creation")
        created = events[0]
        if created.revision != 1:
            raise ValueError("claim stream creation must contain revision one")
        state = SemanticClaimReplayState(
            created.claim_id, 1, initial_status, (created.content_hash,)
        )
        for event in events[1:]:
            if isinstance(event, SemanticClaimCreated):
                raise ValueError("duplicate semantic claim creation")
            if (
                event.claim_id != state.claim_id
                or event.expected_revision != state.current_revision
            ):
                raise ValueError("semantic claim expected-version mismatch")
            if event.revision != state.current_revision + 1:
                raise ValueError("semantic claim revision gap")
            if isinstance(event, SemanticClaimBeliefChanged):
                if event.previous_status is not state.belief_status:
                    raise ValueError("semantic belief replay status mismatch")
                assert_legal_transition(state.belief_status, event.status)
                state = SemanticClaimReplayState(
                    state.claim_id,
                    event.revision,
                    event.status,
                    state.revision_hashes,
                )
            else:
                state = SemanticClaimReplayState(
                    state.claim_id,
                    event.revision,
                    state.belief_status,
                    (*state.revision_hashes, event.content_hash),
                )
        return state
