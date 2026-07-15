"""Bounded semantic lifecycle event payloads."""

from uuid import UUID

from cognitive_os.domain.common import NonEmptyStr, Sha256Hex, UtcDatetime
from cognitive_os.domain.semantic_memory import (
    BeliefStatus,
    ContradictionStatus,
)

from .base import EventPayload


class SemanticObservationRecorded(EventPayload):
    event_type = "semantic.observation_recorded"
    observation_id: UUID
    content_hash: Sha256Hex
    recorded_at: UtcDatetime


class SemanticExtractionCompleted(EventPayload):
    event_type = "semantic.extraction_completed"
    extraction_id: UUID
    manifest_hash: Sha256Hex
    observation_ids: tuple[UUID, ...]
    claim_ids: tuple[UUID, ...]
    completed_at: UtcDatetime


class SemanticExtractionRejected(EventPayload):
    event_type = "semantic.extraction_rejected"
    extraction_id: UUID
    reason_code: NonEmptyStr
    proposal_hash: Sha256Hex
    rejected_at: UtcDatetime


class SemanticClaimCreated(EventPayload):
    event_type = "semantic.claim_created"
    claim_id: UUID
    revision: int
    content_hash: Sha256Hex


class SemanticClaimRevisionAppended(EventPayload):
    event_type = "semantic.claim_revision_appended"
    claim_id: UUID
    expected_revision: int
    revision: int
    content_hash: Sha256Hex


class SemanticClaimBeliefChanged(EventPayload):
    event_type = "semantic.claim_belief_changed"
    claim_id: UUID
    expected_revision: int
    revision: int
    previous_status: BeliefStatus
    status: BeliefStatus
    decision_id: UUID | None = None


class SemanticContradictionOpened(EventPayload):
    event_type = "semantic.contradiction_opened"
    contradiction_id: UUID
    revision: int
    claim_ids: tuple[UUID, ...]
    content_hash: Sha256Hex


class SemanticContradictionCandidateRecorded(EventPayload):
    event_type = "semantic.contradiction_candidate_recorded"
    contradiction_id: UUID
    revision: int
    claim_ids: tuple[UUID, ...]
    content_hash: Sha256Hex


class SemanticContradictionResolved(EventPayload):
    event_type = "semantic.contradiction_resolved"
    contradiction_id: UUID
    expected_revision: int
    revision: int
    status: ContradictionStatus
    content_hash: Sha256Hex
    resolution_id: UUID


class SemanticWikiPageRendered(EventPayload):
    event_type = "semantic.wiki_page_rendered"
    page_id: UUID
    revision: int
    content_hash: Sha256Hex
    snapshot_hash: Sha256Hex


class SemanticWikiPageRegenerated(EventPayload):
    event_type = "semantic.wiki_page_regenerated"
    page_id: UUID
    revision: int
    content_hash: Sha256Hex
    identical: bool


SEMANTIC_EVENT_MODELS: tuple[type[EventPayload], ...] = (
    SemanticObservationRecorded,
    SemanticExtractionCompleted,
    SemanticExtractionRejected,
    SemanticClaimCreated,
    SemanticClaimRevisionAppended,
    SemanticClaimBeliefChanged,
    SemanticContradictionCandidateRecorded,
    SemanticContradictionOpened,
    SemanticContradictionResolved,
    SemanticWikiPageRendered,
    SemanticWikiPageRegenerated,
)
