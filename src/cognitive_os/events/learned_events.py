"""Lifecycle evidence for the learning substrate.

Metadata only: datasets, model artifacts, and reports stay in the Artifact Store.

The Event Store is the cross-subsystem audit spine, not a second learned-state
authority: a missing correlated event is a warning, because the append-only learned
history remains complete and replayable. See ADR 0086.
"""

from cognitive_os.domain.common import NonEmptyStr, Sha256Hex, UtcDatetime

from .base import EventPayload


class LearnedEventPayload(EventPayload):
    component_id: NonEmptyStr
    surface: NonEmptyStr
    content_hash: Sha256Hex
    actor: NonEmptyStr
    authority: NonEmptyStr
    reason: NonEmptyStr
    occurred_at: UtcDatetime


class LearnedDatasetCreated(LearnedEventPayload):
    event_type = "learned.dataset_created"


class LearnedAblationLabelled(LearnedEventPayload):
    event_type = "learned.ablation_labelled"


class LearnedComponentRegistered(LearnedEventPayload):
    event_type = "learned.component_registered"


class LearnedShadowPredictionRecorded(LearnedEventPayload):
    event_type = "learned.shadow_prediction_recorded"


class LearnedForgettingAssessed(LearnedEventPayload):
    event_type = "learned.forgetting_assessed"


class LearnedInvarianceVerified(LearnedEventPayload):
    event_type = "learned.invariance_verified"


class LearnedDistributionCompared(LearnedEventPayload):
    event_type = "learned.distribution_compared"


class LearnedCapacityMeasured(LearnedEventPayload):
    event_type = "learned.capacity_measured"


class LearnedBaselineLadderEvaluated(LearnedEventPayload):
    event_type = "learned.baseline_ladder_evaluated"


class LearnedOutOfDistributionAssessed(LearnedEventPayload):
    event_type = "learned.out_of_distribution_assessed"


class LearnedPromotionAssessed(LearnedEventPayload):
    event_type = "learned.promotion_assessed"


class LearnedComponentEnabled(LearnedEventPayload):
    event_type = "learned.component_enabled"


class LearnedComponentDisabled(LearnedEventPayload):
    event_type = "learned.component_disabled"


class LearnedComponentRetracted(LearnedEventPayload):
    event_type = "learned.component_retracted"


class LearnedSubjectEventPayload(EventPayload):
    """A learned event whose subject need not be a component.

    `LearnedEventPayload` requires a component ID, which is right for lifecycle events
    and wrong for intake and dataset lineage: an observation arrives before anything has
    been learned from it, and a placeholder component ID would be a fabricated fact in
    the audit stream. The subject is named explicitly instead, and `component_id` stays
    optional so a component-bound subject can still be correlated.
    """

    subject_type: NonEmptyStr
    subject_id: NonEmptyStr
    component_id: NonEmptyStr | None = None
    surface: NonEmptyStr
    content_hash: Sha256Hex
    actor: NonEmptyStr
    authority: NonEmptyStr
    reason: NonEmptyStr
    occurred_at: UtcDatetime


class LearnedObservationRecorded(LearnedSubjectEventPayload):
    event_type = "learned.observation_recorded"


class LearnedArtifactLineageLinked(LearnedSubjectEventPayload):
    event_type = "learned.artifact_lineage_linked"


class LearnedActivationApprovalRecorded(LearnedEventPayload):
    """An approval decision, including a refusal.

    A refusal is evidence too, so it is appended rather than dropped; `content_hash`
    binds the event to the exact approval record that was decided.
    """

    event_type = "learned.activation_approval_recorded"


class LearnedComponentRolledBack(LearnedEventPayload):
    event_type = "learned.component_rolled_back"


class LearnedAccessRecorded(LearnedSubjectEventPayload):
    event_type = "learned.access_recorded"


LEARNED_EVENT_MODELS: tuple[type[EventPayload], ...] = (
    LearnedDatasetCreated,
    LearnedAblationLabelled,
    LearnedComponentRegistered,
    LearnedShadowPredictionRecorded,
    LearnedForgettingAssessed,
    LearnedInvarianceVerified,
    LearnedDistributionCompared,
    LearnedCapacityMeasured,
    LearnedBaselineLadderEvaluated,
    LearnedOutOfDistributionAssessed,
    LearnedPromotionAssessed,
    LearnedComponentEnabled,
    LearnedComponentDisabled,
    LearnedComponentRetracted,
    LearnedObservationRecorded,
    LearnedArtifactLineageLinked,
    LearnedActivationApprovalRecorded,
    LearnedComponentRolledBack,
    LearnedAccessRecorded,
)
