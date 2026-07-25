"""Lifecycle evidence for cross-domain pilot runs and transfer experiments."""

from uuid import UUID

from cognitive_os.domain.common import NonEmptyStr, Sha256Hex, UtcDatetime

from .base import EventPayload


class DomainEventPayload(EventPayload):
    """Metadata only: statements, derivations, and reports stay in the Artifact Store."""

    pilot_id: UUID
    domain: NonEmptyStr
    case_id: NonEmptyStr
    content_hash: Sha256Hex
    actor: NonEmptyStr
    authority: NonEmptyStr
    reason: NonEmptyStr
    occurred_at: UtcDatetime


class DomainPilotStarted(DomainEventPayload):
    event_type = "domain.pilot_started"


class DomainCaseStarted(DomainEventPayload):
    event_type = "domain.case_started"


class DomainCaseCompleted(DomainEventPayload):
    event_type = "domain.case_completed"


class DomainCaseFailed(DomainEventPayload):
    event_type = "domain.case_failed"


class DomainTransferStarted(DomainEventPayload):
    event_type = "domain.transfer_started"


class DomainTransferCompleted(DomainEventPayload):
    event_type = "domain.transfer_completed"


class DomainTransferFailed(DomainEventPayload):
    event_type = "domain.transfer_failed"


DOMAIN_EVENT_MODELS: tuple[type[EventPayload], ...] = (
    DomainPilotStarted,
    DomainCaseStarted,
    DomainCaseCompleted,
    DomainCaseFailed,
    DomainTransferStarted,
    DomainTransferCompleted,
    DomainTransferFailed,
)
