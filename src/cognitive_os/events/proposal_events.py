"""Bounded lifecycle evidence for governed harness proposals."""

from uuid import UUID

from cognitive_os.domain.common import NonEmptyStr, Sha256Hex, UtcDatetime

from .base import EventPayload


class ProposalEventPayload(EventPayload):
    proposal_id: UUID
    proposal_revision: int
    source_snapshot_hash: Sha256Hex
    proposal_content_hash: Sha256Hex
    actor_identity: NonEmptyStr
    actor_authority: NonEmptyStr
    summary: NonEmptyStr
    occurred_at: UtcDatetime


class ProposalCreated(ProposalEventPayload):
    event_type = "proposal.created"


class ProposalRevisionAppended(ProposalEventPayload):
    event_type = "proposal.revision_appended"


class ProposalValidated(ProposalEventPayload):
    event_type = "proposal.validated"
    verifier_bundle_hash: Sha256Hex


class ProposalStagedForReview(ProposalEventPayload):
    event_type = "proposal.staged_for_review"


class ProposalApprovedForExperiment(ProposalEventPayload):
    event_type = "proposal.approved_for_experiment"
    review_hash: Sha256Hex


class ProposalRejected(ProposalEventPayload):
    event_type = "proposal.rejected"


class ProposalSuperseded(ProposalEventPayload):
    event_type = "proposal.superseded"


class ProposalRetracted(ProposalEventPayload):
    event_type = "proposal.retracted"


class ProposalQueued(ProposalEventPayload):
    event_type = "proposal.queued"
    queue_entry_hash: Sha256Hex


class ProposalQueueRemoved(ProposalEventPayload):
    event_type = "proposal.queue_removed"
    queue_entry_hash: Sha256Hex


PROPOSAL_EVENT_MODELS: tuple[type[EventPayload], ...] = (
    ProposalCreated,
    ProposalRevisionAppended,
    ProposalValidated,
    ProposalStagedForReview,
    ProposalApprovedForExperiment,
    ProposalRejected,
    ProposalSuperseded,
    ProposalRetracted,
    ProposalQueued,
    ProposalQueueRemoved,
)
