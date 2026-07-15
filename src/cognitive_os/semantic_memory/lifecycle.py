"""Replay reducers for append-only semantic streams."""

from dataclasses import dataclass
from uuid import UUID

from cognitive_os.domain.semantic_memory import BeliefStatus, ContradictionStatus
from cognitive_os.events.semantic_memory_events import (
    SemanticClaimBeliefChanged,
    SemanticClaimCreated,
    SemanticClaimRevisionAppended,
    SemanticContradictionCandidateRecorded,
    SemanticContradictionOpened,
    SemanticContradictionResolved,
    SemanticWikiPageRegenerated,
    SemanticWikiPageRendered,
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


@dataclass(frozen=True)
class SemanticContradictionReplayState:
    contradiction_id: UUID
    current_revision: int
    status: ContradictionStatus
    content_hash: str


class SemanticContradictionStreamReducer:
    def reduce(
        self,
        events: tuple[
            SemanticContradictionCandidateRecorded
            | SemanticContradictionOpened
            | SemanticContradictionResolved,
            ...,
        ],
    ) -> SemanticContradictionReplayState:
        if not events or not isinstance(
            events[0], (SemanticContradictionCandidateRecorded, SemanticContradictionOpened)
        ):
            raise ValueError("contradiction resolution requires prior creation")
        created = events[0]
        if created.revision != 1:
            raise ValueError("contradiction stream creation must contain revision one")
        state = SemanticContradictionReplayState(
            created.contradiction_id,
            1,
            (
                ContradictionStatus.CANDIDATE
                if isinstance(created, SemanticContradictionCandidateRecorded)
                else ContradictionStatus.OPEN
            ),
            created.content_hash,
        )
        for event in events[1:]:
            if isinstance(event, SemanticContradictionCandidateRecorded):
                raise ValueError("duplicate contradiction creation")
            if event.contradiction_id != state.contradiction_id:
                raise ValueError("contradiction stream identity changed")
            expected_revision = getattr(event, "expected_revision", event.revision - 1)
            if (
                expected_revision != state.current_revision
                or event.revision != state.current_revision + 1
            ):
                raise ValueError("contradiction revision gap")
            if isinstance(event, SemanticContradictionOpened):
                if state.status not in {
                    ContradictionStatus.CANDIDATE,
                    ContradictionStatus.RESOLVED,
                    ContradictionStatus.DISMISSED,
                }:
                    raise ValueError("illegal contradiction open transition")
                status = ContradictionStatus.OPEN
            else:
                if state.status is not ContradictionStatus.OPEN:
                    raise ValueError("contradiction resolution requires an open contradiction")
                status = event.status
            state = SemanticContradictionReplayState(
                state.contradiction_id,
                event.revision,
                status,
                event.content_hash,
            )
        return state


@dataclass(frozen=True)
class SemanticWikiReplayState:
    page_id: UUID
    current_revision: int
    content_hash: str
    snapshot_hash: str


class SemanticWikiStreamReducer:
    def reduce(
        self,
        events: tuple[SemanticWikiPageRendered | SemanticWikiPageRegenerated, ...],
    ) -> SemanticWikiReplayState:
        if not events or not isinstance(events[0], SemanticWikiPageRendered):
            raise ValueError("Wiki stream must begin with a rendered page")
        first = events[0]
        if first.revision != 1:
            raise ValueError("Wiki stream creation must contain revision one")
        state = SemanticWikiReplayState(
            first.page_id, first.revision, first.content_hash, first.snapshot_hash
        )
        for event in events[1:]:
            if event.page_id != state.page_id:
                raise ValueError("Wiki stream identity changed")
            if isinstance(event, SemanticWikiPageRendered):
                if event.revision != state.current_revision + 1:
                    raise ValueError("Wiki revision gap")
                state = SemanticWikiReplayState(
                    state.page_id,
                    event.revision,
                    event.content_hash,
                    event.snapshot_hash,
                )
            elif event.revision != state.current_revision or not event.identical:
                raise ValueError("Wiki regeneration does not match the current revision")
        return state
