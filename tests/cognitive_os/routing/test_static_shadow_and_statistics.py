import pytest

from cognitive_os.domain.routing import (
    CapabilitySupportStatus,
    ModelCapabilityRequirement,
    OperatorRoutingRestriction,
    RoutingControlMode,
    RoutingExclusionReason,
    RoutingFallbackReason,
    RoutingPolicyRevision,
)
from cognitive_os.routing.errors import RoutingPolicyError
from cognitive_os.routing.fixtures import (
    build_observations,
    build_routing_request,
    replay_profiles,
    shadow_policy,
    static_policy,
)
from cognitive_os.routing.repository import InMemoryCapabilityRepository
from cognitive_os.routing.service import RoutingService
from cognitive_os.verification.routing import verify_decision


@pytest.mark.asyncio
async def test_static_and_shadow_routing_are_deterministic_and_non_interfering() -> None:
    repository = InMemoryCapabilityRepository()
    service = RoutingService(repository)
    for profile in replay_profiles():
        await service.register_profile(profile)
    static = static_policy()
    shadow = shadow_policy()
    await service.create_policy(static)
    await service.create_policy(shadow)
    for observation in build_observations():
        await service.ingest_observation(observation)
    await service.rebuild_statistics()
    request = build_routing_request(2)
    first = await service.route_static(request, static)
    second = await service.route_static(request, static)
    assert first == second
    assert first.selected_model is not None
    assert any(
        item.reason is RoutingExclusionReason.PROVIDER_UNHEALTHY for item in first.exclusions
    )
    shadow_decision = await service.route_shadow(request, first, shadow)
    assert shadow_decision.control_mode is RoutingControlMode.SHADOW
    assert shadow_decision.static_decision_reference == first.decision_id
    assert verify_decision(shadow_decision) == ()
    assert len(repository.decisions) == 2


@pytest.mark.asyncio
async def test_statistics_rebuild_is_idempotent() -> None:
    repository = InMemoryCapabilityRepository()
    service = RoutingService(repository)
    for observation in build_observations(16):
        await service.ingest_observation(observation)
    first = await service.rebuild_statistics()
    second = await service.rebuild_statistics()
    assert first == second
    assert all(item.estimates.source_observation_ids for item in first)
    assert {item.cohort.cohort_level for item in first} == {
        "exact",
        "without_skill_revisions",
        "problem_class_output_repository",
        "domain_output_risk",
        "domain",
        "global",
    }


@pytest.mark.asyncio
async def test_hard_requirements_operator_priority_and_explicit_override() -> None:
    repository = InMemoryCapabilityRepository()
    service = RoutingService(repository)
    profiles = replay_profiles()
    for profile in profiles:
        await service.register_profile(profile)
    target = next(
        item for item in profiles if item.model_identity.model_id == "fixture-long-context"
    )
    base = build_routing_request()
    payload = base.model_dump(mode="python", exclude={"content_hash"})
    payload["operator_restriction"] = OperatorRoutingRestriction(
        preferred_model_hashes=(target.model_identity.content_hash,),
        actor_id=base.requested_by,
        reason="trusted fixture preference",
    )
    request = type(base).model_validate(payload)
    policy = static_policy()
    await service.create_policy(policy)
    preferred = await service.route_static(request, policy)
    assert preferred.selected_model == target.model_identity

    missing_payload = request.model_dump(mode="python", exclude={"content_hash"})
    missing_payload["capability_requirements"] = (
        ModelCapabilityRequirement(
            dimension="vision",
            required_support=CapabilitySupportStatus.SUPPORTED,
        ),
    )
    missing = await service.route_static(type(base).model_validate(missing_payload), policy)
    assert missing.selected_model is None
    assert sum(
        item.reason is RoutingExclusionReason.MODEL_NOT_CONFIGURED for item in missing.exclusions
    ) == len(profiles)

    override_policy_payload = policy.model_dump(mode="python", exclude={"content_hash"})
    override_policy_payload.update(
        policy_id="trusted-override",
        control_mode=RoutingControlMode.EXPLICIT_OVERRIDE,
    )
    override_policy = RoutingPolicyRevision.model_validate(override_policy_payload)
    await service.create_policy(override_policy)
    override_request_payload = request.model_dump(mode="python", exclude={"content_hash"})
    override_request_payload.update(policy_id=override_policy.policy_id)
    override = await service.route_explicit_override(
        type(base).model_validate(override_request_payload),
        override_policy,
        target.model_identity.content_hash,
        trusted_actor_ids=frozenset({base.requested_by}),
    )
    assert override.control_mode is RoutingControlMode.EXPLICIT_OVERRIDE
    assert override.selected_model == target.model_identity


@pytest.mark.asyncio
async def test_runtime_and_context_fallback_are_linked_bounded_and_safe() -> None:
    repository = InMemoryCapabilityRepository()
    service = RoutingService(repository)
    profiles = replay_profiles()
    for profile in profiles:
        await service.register_profile(profile)
    basic = next(item for item in profiles if item.model_identity.model_id == "fixture-basic")
    base = build_routing_request()
    payload = base.model_dump(mode="python", exclude={"content_hash"})
    payload["operator_restriction"] = OperatorRoutingRestriction(
        preferred_model_hashes=(basic.model_identity.content_hash,),
        actor_id=base.requested_by,
        reason="force bounded Context fallback",
    )
    request = type(base).model_validate(payload)
    policy = static_policy()
    await service.create_policy(policy)
    initial = await service.route_static(request, policy)
    assert initial.selected_model == basic.model_identity
    fallback = await service.route_fallback(
        request,
        policy,
        initial,
        RoutingFallbackReason.PROVIDER_UNAVAILABLE,
        depth=1,
    )
    assert fallback.previous_decision_id == initial.decision_id
    assert fallback.selected_model != initial.selected_model
    with pytest.raises(RoutingPolicyError, match="does not permit"):
        await service.route_fallback(
            request,
            policy,
            initial,
            RoutingFallbackReason.TIMEOUT_AFTER_UNCERTAIN_SIDE_EFFECT,
            depth=1,
        )
    context_fallback = await service.route_context_fallback(
        request, policy, initial, actual_token_estimate=20_000
    )
    assert context_fallback.previous_decision_id == initial.decision_id
    assert await service.validate_context_fit(context_fallback, 20_000)
