"""Append-only routing lifecycle evidence with bounded payloads."""

from uuid import UUID

from cognitive_os.domain.common import NonEmptyStr, Sha256Hex, UtcDatetime

from .base import EventPayload


class CapabilityProfileRegistered(EventPayload):
    event_type = "routing.capability_profile_registered"
    model_identity_hash: Sha256Hex
    profile_revision: int
    profile_hash: Sha256Hex
    occurred_at: UtcDatetime


class CapabilityRevisionAppended(EventPayload):
    event_type = "routing.capability_revision_appended"
    model_identity_hash: Sha256Hex
    profile_revision: int
    profile_hash: Sha256Hex
    occurred_at: UtcDatetime


class RoutingPolicyCreated(EventPayload):
    event_type = "routing.policy_created"
    policy_id: NonEmptyStr
    policy_revision: int
    policy_hash: Sha256Hex
    occurred_at: UtcDatetime


class RoutingPolicyRevisionAppended(EventPayload):
    event_type = "routing.policy_revision_appended"
    policy_id: NonEmptyStr
    policy_revision: int
    policy_hash: Sha256Hex
    occurred_at: UtcDatetime


class RoutingDecisionRecorded(EventPayload):
    event_type = "routing.decision_recorded"
    decision_id: UUID
    decision_hash: Sha256Hex
    occurred_at: UtcDatetime


class ShadowDecisionRecorded(EventPayload):
    event_type = "routing.shadow_decision_recorded"
    static_decision_id: UUID
    shadow_decision_id: UUID
    decision_hash: Sha256Hex
    occurred_at: UtcDatetime


class RoutingOutcomeRecorded(EventPayload):
    event_type = "routing.outcome_recorded"
    decision_id: UUID
    outcome_id: UUID
    outcome_hash: Sha256Hex
    occurred_at: UtcDatetime


class RoutingStatisticsRebuilt(EventPayload):
    event_type = "routing.statistics_rebuilt"
    statistics_id: UUID
    statistics_hash: Sha256Hex
    occurred_at: UtcDatetime


class RoutingExperimentCreated(EventPayload):
    event_type = "routing.experiment_created"
    experiment_id: UUID
    experiment_hash: Sha256Hex
    occurred_at: UtcDatetime


class RoutingExperimentCompleted(EventPayload):
    event_type = "routing.experiment_completed"
    experiment_id: UUID
    result_hash: Sha256Hex
    occurred_at: UtcDatetime


class AdaptivePolicyEnabled(EventPayload):
    event_type = "routing.adaptive_policy_enabled"
    policy_id: NonEmptyStr
    policy_revision: int
    approval_reference: NonEmptyStr
    occurred_at: UtcDatetime


class AdaptivePolicyDisabled(EventPayload):
    event_type = "routing.adaptive_policy_disabled"
    policy_id: NonEmptyStr
    policy_revision: int
    reason: NonEmptyStr
    occurred_at: UtcDatetime


ROUTING_EVENT_MODELS: tuple[type[EventPayload], ...] = (
    CapabilityProfileRegistered,
    CapabilityRevisionAppended,
    RoutingPolicyCreated,
    RoutingPolicyRevisionAppended,
    RoutingDecisionRecorded,
    ShadowDecisionRecorded,
    RoutingOutcomeRecorded,
    RoutingStatisticsRebuilt,
    RoutingExperimentCreated,
    RoutingExperimentCompleted,
    AdaptivePolicyEnabled,
    AdaptivePolicyDisabled,
)
