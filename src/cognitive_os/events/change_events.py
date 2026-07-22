"""Versioned lifecycle evidence for regression-gated controlled changes."""

from uuid import UUID

from cognitive_os.domain.common import NonEmptyStr, Sha256Hex, UtcDatetime

from .base import EventPayload


class ChangeEventPayload(EventPayload):
    experiment_id: UUID
    experiment_revision: int
    experiment_content_hash: Sha256Hex
    actor: NonEmptyStr
    authority: NonEmptyStr
    reason: NonEmptyStr
    occurred_at: UtcDatetime


class ChangeExperimentCreated(ChangeEventPayload):
    event_type = "change.experiment_created"


class ChangeIsolationPrepared(ChangeEventPayload):
    event_type = "change.isolation_prepared"


class ChangeImplementationStarted(ChangeEventPayload):
    event_type = "change.implementation_started"


class ChangeImplementationCompleted(ChangeEventPayload):
    event_type = "change.implementation_completed"


class ChangeEvaluationStarted(ChangeEventPayload):
    event_type = "change.evaluation_started"


class ChangeEvaluationCompleted(ChangeEventPayload):
    event_type = "change.evaluation_completed"


class ChangePromotionAssessed(ChangeEventPayload):
    event_type = "change.promotion_assessed"


class ChangePromotionApproved(ChangeEventPayload):
    event_type = "change.promotion_approved"


class ChangePromoted(ChangeEventPayload):
    event_type = "change.promoted"


class ChangeRejected(ChangeEventPayload):
    event_type = "change.rejected"


class ChangeRollbackStarted(ChangeEventPayload):
    event_type = "change.rollback_started"


class ChangeRolledBack(ChangeEventPayload):
    event_type = "change.rolled_back"


class ChangeFailed(ChangeEventPayload):
    event_type = "change.failed"


class ChangeCancelled(ChangeEventPayload):
    event_type = "change.cancelled"


CHANGE_EVENT_MODELS: tuple[type[EventPayload], ...] = (
    ChangeExperimentCreated,
    ChangeIsolationPrepared,
    ChangeImplementationStarted,
    ChangeImplementationCompleted,
    ChangeEvaluationStarted,
    ChangeEvaluationCompleted,
    ChangePromotionAssessed,
    ChangePromotionApproved,
    ChangePromoted,
    ChangeRejected,
    ChangeRollbackStarted,
    ChangeRolledBack,
    ChangeFailed,
    ChangeCancelled,
)
