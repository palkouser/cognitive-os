"""Provider-neutral deterministic routing boundary."""

from typing import Protocol

from cognitive_os.domain.routing import (
    RoutingDecision,
    RoutingFallbackReason,
    RoutingPolicyRevision,
    RoutingRequest,
)


class ModelRouterPort(Protocol):
    async def route_static(
        self, request: RoutingRequest, policy: RoutingPolicyRevision
    ) -> RoutingDecision: ...

    async def route_shadow(
        self,
        request: RoutingRequest,
        static_decision: RoutingDecision,
        shadow_policy: RoutingPolicyRevision,
    ) -> RoutingDecision: ...

    async def route_explicit_override(
        self,
        request: RoutingRequest,
        policy: RoutingPolicyRevision,
        model_identity_hash: str,
        *,
        trusted_actor_ids: frozenset[str],
    ) -> RoutingDecision: ...

    async def validate_context_fit(
        self, decision: RoutingDecision, actual_token_estimate: int
    ) -> bool: ...

    async def route_fallback(
        self,
        request: RoutingRequest,
        policy: RoutingPolicyRevision,
        previous_decision: RoutingDecision,
        failure_reason: RoutingFallbackReason,
        *,
        depth: int,
    ) -> RoutingDecision: ...

    async def route_context_fallback(
        self,
        request: RoutingRequest,
        policy: RoutingPolicyRevision,
        previous_decision: RoutingDecision,
        actual_token_estimate: int,
        *,
        depth: int = 1,
    ) -> RoutingDecision: ...
