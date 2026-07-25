"""Lifecycle evidence for the learning substrate.

Metadata only: datasets, model artifacts, and reports stay in the Artifact Store.
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
)
