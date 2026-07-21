"""Credential-free deterministic Sprint 16 routing fixtures."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from hashlib import sha256
from uuid import NAMESPACE_URL, UUID, uuid5

from cognitive_os.domain.provider import ProviderStatus
from cognitive_os.domain.routing import (
    CapabilityEvidenceType,
    CapabilitySourceReference,
    CapabilitySupportStatus,
    ContextRequirement,
    DeclaredCapability,
    DeclaredCapabilitySet,
    ExecutionRole,
    ModelCapabilityProfile,
    ModelIdentity,
    ModelProfileStatus,
    ProviderHealthSnapshot,
    ProviderPolicyConstraint,
    ProviderRegistrySnapshot,
    RoutingBudget,
    RoutingControlMode,
    RoutingObservation,
    RoutingObservationStatus,
    RoutingPolicyRevision,
    RoutingPolicyStatus,
    RoutingRequest,
    TaskComplexityClass,
)

from .service import build_task_signature

FIXTURE_TIME = datetime(2026, 7, 21, 12, 0, tzinfo=UTC)


def _hash(value: str) -> str:
    return sha256(value.encode()).hexdigest()


def _id(kind: str, value: str) -> UUID:
    return uuid5(NAMESPACE_URL, f"sprint16:{kind}:{value}")


def replay_profiles() -> tuple[ModelCapabilityProfile, ...]:
    definitions = (
        ("basic", 8_192, False, False, ("text",)),
        ("structured", 16_384, True, False, ("extraction", "text")),
        ("tool", 32_768, True, True, ("coding", "tool")),
        ("long-context", 131_072, True, True, ("coding", "text")),
        ("low-latency", 8_192, True, False, ("text",)),
        ("unavailable", 32_768, True, True, ("coding", "text")),
        ("safety-restricted", 32_768, True, False, ("low-risk",)),
    )
    profiles = []
    for name, context_limit, structured, tools, domains in definitions:
        identity = ModelIdentity(
            provider_id=f"replay-{name}",
            model_id=f"fixture-{name}",
            model_revision="1",
            endpoint_profile="offline-replay",
            execution_mode="replay",
        )
        source = CapabilitySourceReference(
            evidence_type=CapabilityEvidenceType.OPERATOR_DECLARATION,
            source_id=f"fixtures/routing/{name}",
            source_revision="1",
            source_hash=_hash(f"profile:{name}"),
            actor_id="sprint-16-fixture",
        )
        declarations = DeclaredCapabilitySet(
            capabilities=(
                DeclaredCapability(
                    dimension="structured_output",
                    support=(
                        CapabilitySupportStatus.SUPPORTED
                        if structured
                        else CapabilitySupportStatus.UNSUPPORTED
                    ),
                    value=structured,
                    source=source,
                ),
                DeclaredCapability(
                    dimension="tool_calling",
                    support=(
                        CapabilitySupportStatus.SUPPORTED
                        if tools
                        else CapabilitySupportStatus.UNSUPPORTED
                    ),
                    value=tools,
                    source=source,
                ),
                DeclaredCapability(
                    dimension="context_limit",
                    support=CapabilitySupportStatus.SUPPORTED,
                    value=context_limit,
                    source=source,
                ),
            )
        )
        profiles.append(
            ModelCapabilityProfile(
                model_identity=identity,
                profile_revision=1,
                status=ModelProfileStatus.REGISTERED,
                declared_capabilities=declarations,
                supported_domains=domains,
                structured_output_support=(
                    CapabilitySupportStatus.SUPPORTED
                    if structured
                    else CapabilitySupportStatus.UNSUPPORTED
                ),
                tool_call_support=(
                    CapabilitySupportStatus.SUPPORTED
                    if tools
                    else CapabilitySupportStatus.UNSUPPORTED
                ),
                context_limit=context_limit,
                source_refs=(source.content_hash,),
                created_at=FIXTURE_TIME,
                created_by="sprint-16-fixture",
                reason="credential-free deterministic replay profile",
            )
        )
    return tuple(profiles)


def provider_snapshot() -> ProviderRegistrySnapshot:
    return ProviderRegistrySnapshot(
        health=tuple(
            ProviderHealthSnapshot(
                provider_id=profile.model_identity.provider_id,
                status=(
                    ProviderStatus.UNAVAILABLE
                    if "unavailable" in profile.model_identity.provider_id
                    else ProviderStatus.AVAILABLE
                ),
                checked_at=FIXTURE_TIME,
            )
            for profile in replay_profiles()
        )
    )


def static_policy() -> RoutingPolicyRevision:
    return RoutingPolicyRevision(
        policy_id="default-static",
        revision=1,
        status=RoutingPolicyStatus.ENABLED,
        control_mode=RoutingControlMode.STATIC,
        maximum_fallback_models=4,
        created_at=FIXTURE_TIME,
        created_by="sprint-16-fixture",
        reason="deterministic static control policy",
    )


def shadow_policy() -> RoutingPolicyRevision:
    return RoutingPolicyRevision(
        policy_id="quality-cost-shadow",
        revision=1,
        status=RoutingPolicyStatus.SHADOW,
        control_mode=RoutingControlMode.SHADOW,
        minimum_samples=5,
        score_weights={"accepted_task_rate": Decimal("0.7"), "latency": Decimal("-0.3")},
        maximum_fallback_models=4,
        created_at=FIXTURE_TIME,
        created_by="sprint-16-fixture",
        reason="non-interfering fixture shadow policy",
    )


def build_routing_request(index: int = 0) -> RoutingRequest:
    cases = (
        ("text", False, (), 2_000),
        ("extraction", True, (), 4_000),
        ("coding", True, ("workspace.patch",), 16_000),
        ("coding", True, ("workspace.patch",), 64_000),
    )
    domain, structured, tools, tokens = cases[index % len(cases)]
    signature = build_task_signature(
        problem_domain=domain,
        problem_class=f"fixture-{index % 8}",
        output_type="json" if structured else "text",
        repository_profile="python" if domain == "coding" else "none",
        estimated_complexity=TaskComplexityClass.SMALL,
        required_tool_capabilities=tools,
        required_structured_output=structured,
        risk_level="standard",
        execution_role=ExecutionRole.PRIMARY,
    )
    return RoutingRequest(
        routing_request_id=_id("request", str(index)),
        task_run_id=_id("task", str(index)),
        step_id=f"provider-step-{index}",
        task_signature=signature,
        execution_role=ExecutionRole.PRIMARY,
        provider_constraints=ProviderPolicyConstraint(),
        context_requirement=ContextRequirement(
            estimated_tokens=tokens,
            reserved_output_tokens=1_024,
        ),
        budget=RoutingBudget(maximum_calls=4, maximum_tokens=131_072),
        policy_id="default-static",
        policy_revision=1,
        provider_registry_snapshot=provider_snapshot(),
        requested_by="sprint-16-fixture",
        created_at=FIXTURE_TIME,
    )


def build_observations(count: int = 64) -> tuple[RoutingObservation, ...]:
    profiles = replay_profiles()
    observations = []
    for index in range(count):
        profile = profiles[index % 5]
        request = build_routing_request(index)
        accepted = index % 5 != 0
        observations.append(
            RoutingObservation(
                observation_id=_id("observation", str(index)),
                model_identity=profile.model_identity,
                task_signature=request.task_signature,
                routing_policy_reference="default-static:1",
                execution_role=ExecutionRole.PRIMARY,
                provider_call_reference=f"replay-call-{index}",
                context_bundle_reference=f"context-bundle-{index}",
                verifier_bundle_reference=f"verifier-bundle-{index}",
                acceptance_decision_reference=f"acceptance-{index}",
                status=(
                    RoutingObservationStatus.ACCEPTED
                    if accepted
                    else RoutingObservationStatus.REJECTED
                ),
                latency_ms=Decimal(50 + index % 20),
                cost_units=None if index % 7 == 0 else Decimal("0.001"),
                structured_output_valid=(index % 6 != 0),
                tool_calls_valid=(index % 8 != 0),
                safety_passed=True,
                source_refs=(_hash(f"routing-observation:{index}"),),
                evidence_type=CapabilityEvidenceType.DETERMINISTIC_BENCHMARK,
                created_at=FIXTURE_TIME,
            )
        )
    return tuple(observations)
