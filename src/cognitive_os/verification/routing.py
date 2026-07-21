"""Deterministic verifier bundle for governed routing records."""

from cognitive_os.domain.routing import (
    ModelCapabilityProfile,
    RoutingControlMode,
    RoutingDecision,
    RoutingDecisionStatus,
    RoutingObservation,
    RoutingOutcome,
    RoutingOutcomeStatus,
    RoutingPolicyRevision,
    RoutingPolicyStatus,
)

MANDATORY_ROUTING_VERIFIERS = (
    "routing.model_identity",
    "routing.provider_reference",
    "routing.no_credentials",
    "routing.capability_evidence",
    "routing.task_signature_determinism",
    "routing.observation_provenance",
    "routing.statistics_reproducibility",
    "routing.policy_integrity",
    "routing.static_decision_integrity",
    "routing.adaptive_score_integrity",
    "routing.shadow_non_interference",
    "routing.outcome_integrity",
    "routing.promotion_gate",
    "routing.fallback_safety",
    "routing.multi_model_budget",
    "routing.context_fit",
    "routing.decision_replay",
    "routing.no_provider_authority",
)


def verify_profile(profile: ModelCapabilityProfile) -> tuple[str, ...]:
    failures = []
    if not profile.model_identity.provider_id:
        failures.append("routing.provider_reference")
    serialized = profile.model_dump_json().lower()
    if any(name in serialized for name in ('"api_key"', '"password"', '"credential"')):
        failures.append("routing.no_credentials")
    if any(not item.source.source_hash for item in profile.declared_capabilities.capabilities):
        failures.append("routing.capability_evidence")
    return tuple(failures)


def verify_decision(
    decision: RoutingDecision, *, executed_model_hash: str | None = None
) -> tuple[str, ...]:
    failures = []
    if decision.status is RoutingDecisionStatus.SELECTED and decision.selected_model is None:
        failures.append("routing.static_decision_integrity")
    if (
        decision.selected_model
        and decision.selected_model.content_hash not in decision.candidate_models
    ):
        failures.append("routing.static_decision_integrity")
    if decision.control_mode is RoutingControlMode.SHADOW and executed_model_hash is not None:
        failures.append("routing.shadow_non_interference")
    if len({item.model_identity_hash for item in decision.fallback_order}) != len(
        decision.fallback_order
    ):
        failures.append("routing.fallback_safety")
    if decision.content_hash != decision.canonical_hash(exclude={"content_hash"}):
        failures.append("routing.decision_replay")
    return tuple(failures)


def verify_observation(observation: RoutingObservation) -> tuple[str, ...]:
    required = (
        observation.provider_call_reference,
        observation.context_bundle_reference,
        observation.verifier_bundle_reference,
        observation.acceptance_decision_reference,
    )
    return () if all(required) and observation.source_refs else ("routing.observation_provenance",)


def verify_policy(policy: RoutingPolicyRevision) -> tuple[str, ...]:
    if (
        policy.control_mode is RoutingControlMode.ADAPTIVE
        and policy.status
        in {
            RoutingPolicyStatus.APPROVED,
            RoutingPolicyStatus.ENABLED,
        }
        and not policy.operator_approval_reference
    ):
        return ("routing.policy_integrity",)
    return ()


def verify_outcome(outcome: RoutingOutcome) -> tuple[str, ...]:
    if outcome.status is RoutingOutcomeStatus.ACCEPTED and (
        not outcome.provider_result_reference
        or not outcome.verifier_bundle_reference
        or not outcome.acceptance_decision_reference
    ):
        return ("routing.outcome_integrity",)
    return ()
