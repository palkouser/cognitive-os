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


class DomainDescriptorRegistered(EventPayload):
    """One governed domain registration, as metadata over bytes held in the Artifact Store.

    Sprint 22A stores domains without a storage schema: the package bytes are a
    content-addressed artifact and *this* event is the index that finds them again. The
    event names the artifact rather than the artifact naming the event, so the bytes can be
    written first and a crash between the two writes leaves a harmless orphan blob instead
    of a registration whose package never arrived (Sprint 22A W1-F2).

    The two hashes are what make a rebuild safe to trust — `package_sha256` binds the bytes
    and `descriptor_content_hash` binds what those bytes mean, so a descriptor whose stored
    bytes no longer reproduce the hash this event recorded is refused rather than loaded.
    """

    event_type = "domain.descriptor_registered"

    domain_id: NonEmptyStr
    revision: int
    lifecycle: NonEmptyStr
    artifact_id: UUID
    descriptor_content_hash: Sha256Hex
    package_sha256: Sha256Hex
    actor: NonEmptyStr
    authority: NonEmptyStr
    reason: NonEmptyStr
    occurred_at: UtcDatetime


DOMAIN_EVENT_MODELS: tuple[type[EventPayload], ...] = (
    DomainDescriptorRegistered,
    DomainPilotStarted,
    DomainCaseStarted,
    DomainCaseCompleted,
    DomainCaseFailed,
    DomainTransferStarted,
    DomainTransferCompleted,
    DomainTransferFailed,
)
