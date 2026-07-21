"""Deterministic capability estimation, routing, shadowing, and promotion."""

from __future__ import annotations

from collections import Counter, defaultdict
from decimal import ROUND_HALF_EVEN, Decimal
from hashlib import sha256
from math import sqrt
from statistics import median
from uuid import NAMESPACE_URL, UUID, uuid5

from cognitive_os.application.ports.capability_repository import CapabilityRepositoryPort
from cognitive_os.config.routing_config import RoutingConfiguration
from cognitive_os.domain.provider import ProviderStatus
from cognitive_os.domain.routing import (
    CapabilityCohort,
    CapabilityDimension,
    CapabilityEstimate,
    CapabilityEstimateSet,
    CapabilityEvidenceType,
    CapabilityRegistrySnapshot,
    CapabilitySupportStatus,
    ContextSizeClass,
    CostClass,
    ExecutionRole,
    LatencyClass,
    ModelCapabilityProfile,
    ModelProfileStatus,
    MultiModelExecutionPlan,
    MultiModelPattern,
    MultiModelRole,
    ProviderHealthSnapshot,
    RoutingAccessRecord,
    RoutingAccessType,
    RoutingBudget,
    RoutingCandidateScore,
    RoutingControlMode,
    RoutingDecision,
    RoutingDecisionStatus,
    RoutingExclusion,
    RoutingExclusionReason,
    RoutingExperimentResult,
    RoutingFallbackEntry,
    RoutingFallbackReason,
    RoutingObservation,
    RoutingObservationStatus,
    RoutingOutcome,
    RoutingOutcomeStatus,
    RoutingPolicyRevision,
    RoutingPolicyStatus,
    RoutingPromotionAssessment,
    RoutingRequest,
    RoutingStatistics,
    RoutingStatisticsSnapshot,
    TaskComplexityClass,
    TaskSignature,
)

from .errors import RoutingPolicyError

_Q = Decimal("0.000001")


def _quantize(value: Decimal | float) -> Decimal:
    return Decimal(str(value)).quantize(_Q, rounding=ROUND_HALF_EVEN)


def build_task_signature(
    *,
    problem_domain: str,
    problem_class: str,
    output_type: str,
    repository_profile: str = "unknown",
    estimated_complexity: TaskComplexityClass = TaskComplexityClass.UNKNOWN,
    required_tool_capabilities: tuple[str, ...] = (),
    required_structured_output: bool = False,
    context_size_class: ContextSizeClass = ContextSizeClass.UNKNOWN,
    risk_level: str = "standard",
    verifier_profile: str = "default",
    latency_class: LatencyClass = LatencyClass.UNKNOWN,
    cost_class: CostClass = CostClass.UNKNOWN,
    strategy_revisions: tuple[str, ...] = (),
    skill_revisions: tuple[str, ...] = (),
    execution_role: ExecutionRole = ExecutionRole.PRIMARY,
) -> TaskSignature:
    """Build a canonical signature without copying prompt or instruction text."""
    return TaskSignature(
        problem_domain=problem_domain,
        problem_class=problem_class,
        output_type=output_type,
        repository_profile=repository_profile,
        estimated_complexity=estimated_complexity,
        required_tool_capabilities=required_tool_capabilities,
        required_structured_output=required_structured_output,
        context_size_class=context_size_class,
        risk_level=risk_level,
        verifier_profile=verifier_profile,
        latency_class=latency_class,
        cost_class=cost_class,
        strategy_revisions=strategy_revisions,
        skill_revisions=skill_revisions,
        execution_role=execution_role,
    )


def cohort_chain(signature: TaskSignature) -> tuple[CapabilityCohort, ...]:
    """Return the fixed exact-to-global cohort order."""
    levels = (
        ("exact", signature.content_hash),
        (
            "without_skill_revisions",
            sha256(
                signature.canonical_json(exclude={"skill_revisions", "content_hash"}).encode()
            ).hexdigest(),
        ),
        (
            "problem_class_output_repository",
            sha256(
                f"{signature.problem_class}:{signature.output_type}:{signature.repository_profile}".encode()
            ).hexdigest(),
        ),
        (
            "domain_output_risk",
            sha256(
                f"{signature.problem_domain}:{signature.output_type}:{signature.risk_level}".encode()
            ).hexdigest(),
        ),
        ("domain", sha256(signature.problem_domain.encode()).hexdigest()),
        ("global", sha256(b"cognitive-os-routing-global").hexdigest()),
    )
    result = []
    parent = None
    for level, value in reversed(levels):
        result.append(
            CapabilityCohort(task_signature_hash=value, cohort_level=level, parent_hash=parent)
        )
        parent = result[-1].content_hash
    return tuple(reversed(result))


def wilson_interval(
    successes: int, total: int
) -> tuple[Decimal | None, Decimal | None, Decimal | None]:
    if total == 0:
        return None, None, None
    probability = successes / total
    z = 1.959963984540054
    denominator = 1 + z * z / total
    center = (probability + z * z / (2 * total)) / denominator
    margin = z * sqrt((probability * (1 - probability) + z * z / (4 * total)) / total) / denominator
    return (
        _quantize(probability),
        _quantize(max(0, center - margin)),
        _quantize(min(1, center + margin)),
    )


def intersect_budgets(*budgets: RoutingBudget) -> RoutingBudget:
    """Budgets can only shrink across Controller, policy, strategy, and role scopes."""
    costs = [item.maximum_cost_units for item in budgets if item.maximum_cost_units is not None]
    return RoutingBudget(
        maximum_calls=min(item.maximum_calls for item in budgets),
        maximum_tokens=min(item.maximum_tokens for item in budgets),
        maximum_tool_calls=min(item.maximum_tool_calls for item in budgets),
        maximum_seconds=min(item.maximum_seconds for item in budgets),
        maximum_cost_units=min(costs) if costs else None,
    )


def classify_failure(code: str) -> RoutingFallbackReason:
    mapping = {item.value: item for item in RoutingFallbackReason}
    return mapping.get(code, RoutingFallbackReason.UNKNOWN)


def fallback_allowed(reason: RoutingFallbackReason) -> bool:
    return reason not in {
        RoutingFallbackReason.TIMEOUT_AFTER_UNCERTAIN_SIDE_EFFECT,
        RoutingFallbackReason.POLICY_DENIAL,
        RoutingFallbackReason.SAFETY_DENIAL,
        RoutingFallbackReason.UNKNOWN,
    }


class RoutingService:
    def __init__(
        self,
        repository: CapabilityRepositoryPort,
        configuration: RoutingConfiguration | None = None,
    ) -> None:
        self.repository = repository
        self.configuration = configuration or RoutingConfiguration()

    async def register_profile(self, profile: ModelCapabilityProfile) -> None:
        if profile.status in {ModelProfileStatus.DEPRECATED, ModelProfileStatus.RETRACTED}:
            raise RoutingPolicyError("inactive profile cannot be registered for routing")
        await self.repository.register_profile(profile)

    async def create_policy(self, policy: RoutingPolicyRevision) -> None:
        await self.repository.create_policy(policy)

    async def route_static(
        self, request: RoutingRequest, policy: RoutingPolicyRevision
    ) -> RoutingDecision:
        if policy.policy_id != request.policy_id or policy.revision != request.policy_revision:
            raise RoutingPolicyError("routing request does not reference the exact policy")
        if policy.control_mode not in {
            RoutingControlMode.STATIC,
            RoutingControlMode.EXPLICIT_OVERRIDE,
            RoutingControlMode.LEGACY_STATIC,
        }:
            raise RoutingPolicyError("static routing requires a static control policy")
        if policy.status is not RoutingPolicyStatus.ENABLED:
            raise RoutingPolicyError("static routing policy is not enabled")
        persisted = await self.repository.get_policy(policy.policy_id, policy.revision)
        if persisted != policy:
            raise RoutingPolicyError("routing policy is not the exact persisted revision")
        profiles = await self.repository.query_profiles(
            limit=min(
                self.configuration.maximum_models,
                self.configuration.maximum_candidate_models,
            )
        )
        return await self._route(request, policy, profiles, adaptive=False)

    async def route_shadow(
        self,
        request: RoutingRequest,
        static_decision: RoutingDecision,
        shadow_policy: RoutingPolicyRevision,
    ) -> RoutingDecision:
        if static_decision.routing_request_id != request.routing_request_id:
            raise RoutingPolicyError("shadow decision must reference the static request")
        if shadow_policy.control_mode is not RoutingControlMode.SHADOW:
            raise RoutingPolicyError("shadow routing requires a shadow policy")
        if shadow_policy.status is not RoutingPolicyStatus.SHADOW:
            raise RoutingPolicyError("shadow policy is not in shadow state")
        persisted = await self.repository.get_policy(
            shadow_policy.policy_id, shadow_policy.revision
        )
        if persisted != shadow_policy:
            raise RoutingPolicyError("shadow policy is not the exact persisted revision")
        profiles = await self.repository.query_profiles(
            limit=min(
                self.configuration.maximum_models,
                self.configuration.maximum_candidate_models,
            )
        )
        return await self._route(
            request,
            shadow_policy,
            profiles,
            adaptive=True,
            static_reference=static_decision.decision_id,
        )

    async def route_explicit_override(
        self,
        request: RoutingRequest,
        policy: RoutingPolicyRevision,
        model_identity_hash: str,
        *,
        trusted_actor_ids: frozenset[str],
    ) -> RoutingDecision:
        restriction = request.operator_restriction
        if (
            policy.control_mode is not RoutingControlMode.EXPLICIT_OVERRIDE
            or restriction is None
            or restriction.actor_id != request.requested_by
            or request.requested_by not in trusted_actor_ids
        ):
            raise RoutingPolicyError("explicit override requires a trusted matching operator")
        payload = request.model_dump(mode="python", exclude={"content_hash"})
        restriction_payload = restriction.model_dump(mode="python", exclude={"content_hash"})
        restriction_payload.update(
            preferred_model_hashes=(model_identity_hash,),
            allowed_model_hashes=(model_identity_hash,),
        )
        payload["operator_restriction"] = restriction_payload
        decision = await self.route_static(RoutingRequest.model_validate(payload), policy)
        if (
            decision.selected_model is None
            or decision.selected_model.content_hash != model_identity_hash
        ):
            raise RoutingPolicyError("explicitly requested model failed hard filters")
        return decision

    async def route_adaptive(
        self, request: RoutingRequest, policy: RoutingPolicyRevision
    ) -> RoutingDecision:
        if policy.policy_id != request.policy_id or policy.revision != request.policy_revision:
            raise RoutingPolicyError("routing request does not reference the exact adaptive policy")
        if (
            policy.control_mode is not RoutingControlMode.ADAPTIVE
            or policy.status is not RoutingPolicyStatus.ENABLED
            or not policy.operator_approval_reference
        ):
            raise RoutingPolicyError("adaptive routing requires an enabled approved policy")
        if (
            policy.allowed_task_signature_hashes
            and request.task_signature.content_hash not in policy.allowed_task_signature_hashes
        ):
            raise RoutingPolicyError("task signature is outside the approved adaptive scope")
        persisted = await self.repository.get_policy(policy.policy_id, policy.revision)
        if persisted != policy:
            raise RoutingPolicyError("adaptive policy is not the exact persisted revision")
        profiles = await self.repository.query_profiles(
            limit=min(
                self.configuration.maximum_models,
                self.configuration.maximum_candidate_models,
            )
        )
        return await self._route(request, policy, profiles, adaptive=True)

    async def validate_context_fit(
        self, decision: RoutingDecision, actual_token_estimate: int
    ) -> bool:
        if decision.selected_model is None:
            return False
        profile = await self.repository.get_profile(decision.selected_model.content_hash)
        return bool(
            profile and profile.context_limit and actual_token_estimate <= profile.context_limit
        )

    async def route_fallback(
        self,
        request: RoutingRequest,
        policy: RoutingPolicyRevision,
        previous_decision: RoutingDecision,
        failure_reason: RoutingFallbackReason,
        *,
        depth: int,
    ) -> RoutingDecision:
        """Create a linked decision only for a bounded, retry-safe fallback."""
        if depth < 1 or depth > self.configuration.maximum_fallback_depth:
            raise RoutingPolicyError("fallback depth is outside the configured bound")
        if not fallback_allowed(failure_reason):
            raise RoutingPolicyError("failure class does not permit an automatic fallback")
        if not previous_decision.fallback_order:
            raise RoutingPolicyError("routing decision has no eligible fallback")
        profiles = []
        for entry in previous_decision.fallback_order:
            profile = await self.repository.get_profile(entry.model_identity_hash)
            if profile is not None:
                profiles.append(profile)
        decision = await self._route(
            request,
            policy,
            tuple(profiles),
            adaptive=policy.control_mode is RoutingControlMode.ADAPTIVE,
            previous_decision_id=previous_decision.decision_id,
            fallback_reason=failure_reason,
        )
        if decision.selected_model is None:
            raise RoutingPolicyError("no fallback remains eligible after hard-filter replay")
        return decision

    async def route_context_fallback(
        self,
        request: RoutingRequest,
        policy: RoutingPolicyRevision,
        previous_decision: RoutingDecision,
        actual_token_estimate: int,
        *,
        depth: int = 1,
    ) -> RoutingDecision:
        if await self.validate_context_fit(previous_decision, actual_token_estimate):
            raise RoutingPolicyError("selected model already fits the built Context Bundle")
        payload = request.model_dump(mode="python", exclude={"content_hash"})
        context_payload = request.context_requirement.model_dump(
            mode="python", exclude={"content_hash"}
        )
        context_payload["estimated_tokens"] = actual_token_estimate
        payload["context_requirement"] = context_payload
        return await self.route_fallback(
            RoutingRequest.model_validate(payload),
            policy,
            previous_decision,
            RoutingFallbackReason.CONTEXT_LIMIT_FAILURE,
            depth=depth,
        )

    async def _route(
        self,
        request: RoutingRequest,
        policy: RoutingPolicyRevision,
        profiles: tuple[ModelCapabilityProfile, ...],
        *,
        adaptive: bool,
        static_reference: UUID | None = None,
        previous_decision_id: UUID | None = None,
        fallback_reason: RoutingFallbackReason | None = None,
    ) -> RoutingDecision:
        health = {item.provider_id: item for item in request.provider_registry_snapshot.health}
        exclusions: list[RoutingExclusion] = []
        scores: list[RoutingCandidateScore] = []
        eligible: list[tuple[ModelCapabilityProfile, RoutingCandidateScore]] = []
        statistic_items = await self.repository.list_statistics()
        statistics = {item.statistics_id: item for item in statistic_items}
        for priority, profile in enumerate(profiles):
            reasons = self._filter(
                profile,
                request,
                policy,
                health.get(profile.model_identity.provider_id),
            )
            exclusions.extend(reasons)
            if reasons:
                continue
            score = (
                self._adaptive_score(profile, request, policy, statistics)
                if adaptive
                else RoutingCandidateScore(
                    model_identity_hash=profile.model_identity.content_hash,
                    eligible=True,
                    static_priority=self._static_priority(profile, request, priority),
                    dimensions={
                        "operator_priority": Decimal(
                            -self._static_priority(profile, request, priority)
                        )
                    },
                    uncertainty=Decimal("0"),
                    total=Decimal(-self._static_priority(profile, request, priority)),
                )
            )
            scores.append(score)
            eligible.append((profile, score))
        eligible.sort(key=lambda item: (-item[1].total, item[0].model_identity.content_hash))
        selected = eligible[0][0] if eligible else None
        fallback = tuple(
            RoutingFallbackEntry(
                position=index,
                model_identity_hash=profile.model_identity.content_hash,
            )
            for index, (profile, _) in enumerate(
                eligible[1 : policy.maximum_fallback_models + 1], start=1
            )
        )
        mode = (
            RoutingControlMode.SHADOW
            if static_reference is not None
            else RoutingControlMode.ADAPTIVE
            if adaptive
            else policy.control_mode
        )
        decision_id = uuid5(
            NAMESPACE_URL,
            "routing-decision:"
            f"{request.content_hash}:{policy.content_hash}:{mode.value}:"
            f"{previous_decision_id}:{fallback_reason}",
        )
        snapshot = CapabilityRegistrySnapshot(
            profile_hashes=tuple(profile.content_hash for profile in profiles)
        )
        statistic_hashes = tuple(sorted(item.content_hash for item in statistics.values()))
        decision = RoutingDecision(
            decision_id=decision_id,
            previous_decision_id=previous_decision_id,
            routing_request_id=request.routing_request_id,
            task_run_id=request.task_run_id,
            task_signature=request.task_signature,
            policy_id=policy.policy_id,
            policy_revision=policy.revision,
            control_mode=mode,
            status=(
                RoutingDecisionStatus.SELECTED
                if selected
                else RoutingDecisionStatus.NO_ELIGIBLE_MODEL
            ),
            candidate_models=tuple(profile.model_identity.content_hash for profile in profiles),
            candidate_scores=tuple(scores),
            exclusions=tuple(
                sorted(exclusions, key=lambda item: (item.model_identity_hash, item.reason))
            ),
            selected_model=selected.model_identity if selected else None,
            fallback_order=fallback,
            static_decision_reference=static_reference,
            reason=(
                f"bounded fallback after {fallback_reason.value}"
                if fallback_reason is not None
                else "deterministic adaptive shadow score"
                if adaptive
                else "deterministic static priority"
            )
            if selected
            else "no eligible model",
            provider_registry_snapshot=request.provider_registry_snapshot,
            capability_registry_snapshot=snapshot,
            statistics_snapshot=RoutingStatisticsSnapshot(statistic_hashes=statistic_hashes),
            created_at=request.created_at,
        )
        await self.repository.record_decision(decision)
        await self.repository.record_access(
            RoutingAccessRecord(
                access_id=uuid5(NAMESPACE_URL, f"routing-access:{decision.content_hash}"),
                access_type=(
                    RoutingAccessType.SHADOW_DECISION
                    if mode is RoutingControlMode.SHADOW
                    else RoutingAccessType.ROUTING_DECISION
                ),
                actor_id=request.requested_by,
                policy_id=policy.policy_id,
                policy_revision=policy.revision,
                decision_id=decision.decision_id,
                accessed_at=request.created_at,
                reason=decision.reason,
            )
        )
        return decision

    @staticmethod
    def _static_priority(
        profile: ModelCapabilityProfile, request: RoutingRequest, canonical_priority: int
    ) -> int:
        restriction = request.operator_restriction
        model_hash = profile.model_identity.content_hash
        if restriction and model_hash in restriction.preferred_model_hashes:
            return restriction.preferred_model_hashes.index(model_hash)
        preferred_count = len(restriction.preferred_model_hashes) if restriction else 0
        return preferred_count + canonical_priority

    def _filter(
        self,
        profile: ModelCapabilityProfile,
        request: RoutingRequest,
        policy: RoutingPolicyRevision,
        health: ProviderHealthSnapshot | None,
    ) -> tuple[RoutingExclusion, ...]:
        model_hash = profile.model_identity.content_hash
        reasons: list[tuple[RoutingExclusionReason, str]] = []
        if profile.status not in {ModelProfileStatus.REGISTERED, ModelProfileStatus.VERIFIED}:
            reasons.append((RoutingExclusionReason.MODEL_NOT_CONFIGURED, "profile is inactive"))
        constraints = request.provider_constraints
        provider_id = profile.model_identity.provider_id
        if constraints.allowed_provider_ids and provider_id not in constraints.allowed_provider_ids:
            reasons.append(
                (RoutingExclusionReason.PROVIDER_POLICY, "provider is outside allowlist")
            )
        if provider_id in constraints.denied_provider_ids:
            reasons.append((RoutingExclusionReason.PROVIDER_POLICY, "provider is denied"))
        restriction = request.operator_restriction
        if restriction is not None:
            if (
                restriction.allowed_model_hashes
                and model_hash not in restriction.allowed_model_hashes
            ):
                reasons.append(
                    (RoutingExclusionReason.PROVIDER_POLICY, "model is outside allowlist")
                )
            if model_hash in restriction.denied_model_hashes:
                reasons.append((RoutingExclusionReason.PROVIDER_POLICY, "model is operator-denied"))
        if health is None:
            reasons.append((RoutingExclusionReason.PROVIDER_DISABLED, "provider is not registered"))
        elif constraints.require_healthy and health.status is not ProviderStatus.AVAILABLE:
            reasons.append((RoutingExclusionReason.PROVIDER_UNHEALTHY, "provider is not healthy"))
        required_context = (
            request.context_requirement.estimated_tokens
            + request.context_requirement.reserved_output_tokens
        )
        if profile.context_limit is None or profile.context_limit < required_context:
            reasons.append(
                (RoutingExclusionReason.CONTEXT_LIMIT, "model Context limit is insufficient")
            )
        if request.task_signature.required_structured_output and (
            profile.structured_output_support is not CapabilitySupportStatus.SUPPORTED
        ):
            reasons.append(
                (RoutingExclusionReason.STRUCTURED_OUTPUT, "structured output is unsupported")
            )
        if request.task_signature.required_tool_capabilities and (
            profile.tool_call_support is not CapabilitySupportStatus.SUPPORTED
        ):
            reasons.append((RoutingExclusionReason.TOOL_CALLING, "tool calling is unsupported"))
        if not set(request.context_requirement.required_modalities).issubset(
            profile.input_modalities
        ):
            reasons.append(
                (RoutingExclusionReason.MODALITY, "required input modality is unsupported")
            )
        if (
            profile.supported_domains
            and request.task_signature.problem_domain not in profile.supported_domains
        ):
            reasons.append((RoutingExclusionReason.RISK, "task domain is unsupported"))
        if (
            policy.risk_constraints
            and request.task_signature.risk_level not in policy.risk_constraints
        ):
            reasons.append((RoutingExclusionReason.RISK, "task risk is outside policy scope"))
        declared = {item.dimension: item for item in profile.declared_capabilities.capabilities}
        for requirement in request.capability_requirements + policy.candidate_filters:
            if not requirement.hard:
                continue
            capability = declared.get(requirement.dimension)
            if capability is None:
                reasons.append(
                    (
                        RoutingExclusionReason.MODEL_NOT_CONFIGURED,
                        f"required capability {requirement.dimension} is unknown",
                    )
                )
                continue
            if (
                requirement.required_support is not None
                and capability.support is not requirement.required_support
            ):
                reasons.append(
                    (
                        RoutingExclusionReason.MODEL_NOT_CONFIGURED,
                        f"required capability {requirement.dimension} is unsupported",
                    )
                )
            if requirement.minimum_value is not None:
                try:
                    value = Decimal(str(capability.value))
                except (ArithmeticError, TypeError, ValueError):
                    reasons.append(
                        (
                            RoutingExclusionReason.MODEL_NOT_CONFIGURED,
                            f"required capability {requirement.dimension} is not measurable",
                        )
                    )
                else:
                    if value < requirement.minimum_value:
                        reasons.append(
                            (
                                RoutingExclusionReason.MODEL_NOT_CONFIGURED,
                                f"required capability {requirement.dimension} is below minimum",
                            )
                        )
        return tuple(
            RoutingExclusion(model_identity_hash=model_hash, reason=reason, detail=detail)
            for reason, detail in reasons
        )

    def _adaptive_score(
        self,
        profile: ModelCapabilityProfile,
        request: RoutingRequest,
        policy: RoutingPolicyRevision,
        statistics: dict[UUID, RoutingStatistics],
    ) -> RoutingCandidateScore:
        levels = cohort_chain(request.task_signature)
        if policy.risk_constraints:
            levels = levels[:4]
        minimum_samples = max(policy.minimum_samples, self.configuration.minimum_measured_samples)
        matching_by_cohort = {
            item.cohort.task_signature_hash: item
            for item in statistics.values()
            if item.model_identity_hash == profile.model_identity.content_hash
        }
        selected_statistics = next(
            (
                matching_by_cohort[item.task_signature_hash]
                for item in levels
                if item.task_signature_hash in matching_by_cohort
                and max(
                    (
                        estimate.effective_sample_count
                        for estimate in matching_by_cohort[
                            item.task_signature_hash
                        ].estimates.estimates
                    ),
                    default=0,
                )
                >= minimum_samples
            ),
            None,
        )
        matching = (selected_statistics,) if selected_statistics is not None else ()
        estimates = {
            estimate.dimension.value: estimate
            for item in matching
            for estimate in item.estimates.estimates
        }
        dimensions: dict[str, Decimal] = {}
        uncertainty = Decimal("1")
        for name, weight in policy.score_weights.items():
            estimate = estimates.get(name)
            value = estimate.estimate if estimate and estimate.estimate is not None else None
            if value is None:
                value = Decimal("1000000") if weight < 0 else Decimal("0")
            dimensions[name] = _quantize(value * weight)
            if estimate:
                uncertainty = min(uncertainty, estimate.uncertainty)
        if selected_statistics is not None:
            cohort_generality = next(
                index
                for index, cohort in enumerate(levels)
                if cohort.task_signature_hash == selected_statistics.cohort.task_signature_hash
            )
            uncertainty = min(
                Decimal("1"), uncertainty + Decimal(cohort_generality) * Decimal("0.05")
            )
        total = sum(dimensions.values(), Decimal("0")) - policy.uncertainty_penalty * uncertainty
        return RoutingCandidateScore(
            model_identity_hash=profile.model_identity.content_hash,
            eligible=True,
            dimensions=dimensions,
            uncertainty=uncertainty,
            total=_quantize(total),
            source_statistics_hash=(
                selected_statistics.content_hash if selected_statistics is not None else None
            ),
            source_cohort_level=(
                selected_statistics.cohort.cohort_level if selected_statistics is not None else None
            ),
        )

    async def record_outcome(self, outcome: RoutingOutcome) -> None:
        await self.repository.record_outcome(outcome)

    async def ingest_observation(self, observation: RoutingObservation) -> None:
        if observation.evidence_type in {
            CapabilityEvidenceType.PROVIDER_SELF_DESCRIPTION,
            CapabilityEvidenceType.PROVIDER_DOCUMENTATION,
        }:
            raise RoutingPolicyError("declared provider evidence cannot be ingested as measurement")
        await self.repository.record_observation(observation)

    async def project_verified_outcome(
        self,
        *,
        outcome: RoutingOutcome,
        decision: RoutingDecision,
        source_hash: str,
    ) -> RoutingObservation:
        if outcome.decision_id != decision.decision_id or decision.selected_model is None:
            raise RoutingPolicyError("outcome projection requires its exact selected decision")
        status = {
            RoutingOutcomeStatus.ACCEPTED: RoutingObservationStatus.ACCEPTED,
            RoutingOutcomeStatus.REJECTED: RoutingObservationStatus.REJECTED,
        }.get(outcome.status, RoutingObservationStatus.UNVERIFIABLE)
        observation = RoutingObservation(
            observation_id=uuid5(
                NAMESPACE_URL, f"routing-outcome-observation:{outcome.content_hash}"
            ),
            model_identity=decision.selected_model,
            task_signature=decision.task_signature,
            routing_policy_reference=f"{decision.policy_id}:{decision.policy_revision}",
            execution_role=decision.task_signature.execution_role,
            provider_call_reference=outcome.provider_request_reference,
            context_bundle_reference=outcome.context_bundle_reference,
            verifier_bundle_reference=outcome.verifier_bundle_reference or "unverifiable",
            acceptance_decision_reference=outcome.acceptance_decision_reference or "unverifiable",
            status=status,
            latency_ms=outcome.latency_ms,
            token_usage=outcome.token_usage,
            cost_units=outcome.cost_units,
            safety_passed=outcome.safety_result == "passed",
            source_refs=(source_hash,),
            evidence_type=CapabilityEvidenceType.VERIFIED_TASK_OUTCOME,
            created_at=outcome.created_at,
        )
        await self.repository.record_observation(observation)
        return observation

    async def rebuild_statistics(self) -> tuple[RoutingStatistics, ...]:
        observations = await self.repository.list_observations(
            limit=self.configuration.maximum_observations_per_import
        )
        grouped: dict[tuple[str, str], list[RoutingObservation]] = defaultdict(list)
        cohorts: dict[str, CapabilityCohort] = {}
        for observation in observations:
            for cohort in cohort_chain(observation.task_signature):
                grouped[(observation.model_identity.content_hash, cohort.content_hash)].append(
                    observation
                )
                cohorts[cohort.content_hash] = cohort
        if len(grouped) > self.configuration.maximum_statistics_cohorts:
            raise RoutingPolicyError("statistics cohort limit exceeded")
        results = []
        for (model_hash, cohort_hash), items in sorted(grouped.items()):
            ordered = tuple(sorted(items, key=lambda item: str(item.observation_id)))
            cohort = cohorts[cohort_hash]
            source_counts = Counter(item.evidence_type for item in ordered)
            estimates = [
                self._binary_estimate(
                    CapabilityDimension.ACCEPTED_TASK_RATE,
                    [item.status is RoutingObservationStatus.ACCEPTED for item in ordered],
                    source_counts,
                )
            ]
            binary_series: tuple[tuple[CapabilityDimension, list[bool | None]], ...] = (
                (
                    CapabilityDimension.STRUCTURED_OUTPUT_VALIDITY,
                    [item.structured_output_valid for item in ordered],
                ),
                (
                    CapabilityDimension.TOOL_CALL_VALIDITY,
                    [item.tool_calls_valid for item in ordered],
                ),
                (CapabilityDimension.CONTEXT_FIT, [True for _ in ordered]),
                (
                    CapabilityDimension.SAFETY_FAILURE_RATE,
                    [not item.safety_passed for item in ordered if item.safety_passed is not None],
                ),
            )
            for dimension, values in binary_series:
                estimates.append(self._binary_estimate(dimension, values, source_counts))
            estimates.extend(
                (
                    self._continuous_estimate(
                        CapabilityDimension.LATENCY,
                        [item.latency_ms for item in ordered],
                        source_counts,
                    ),
                    self._continuous_estimate(
                        CapabilityDimension.COST_UNITS,
                        [item.cost_units for item in ordered],
                        source_counts,
                    ),
                )
            )
            estimate_set = CapabilityEstimateSet(
                cohort=cohort,
                estimates=tuple(estimates),
                statistics_profile="routing-statistics-v1",
                source_observation_ids=tuple(item.observation_id for item in ordered),
            )
            statistic = RoutingStatistics(
                statistics_id=uuid5(
                    NAMESPACE_URL, f"routing-statistics:{model_hash}:{estimate_set.content_hash}"
                ),
                model_identity_hash=model_hash,
                cohort=cohort,
                estimates=estimate_set,
                source_observation_ids=estimate_set.source_observation_ids,
                rebuilt_at=max(item.created_at for item in ordered),
            )
            await self.repository.record_statistics(statistic)
            results.append(statistic)
        return tuple(results)

    @staticmethod
    def _binary_estimate(
        dimension: CapabilityDimension,
        raw_values: list[bool | None],
        source_counts: Counter[CapabilityEvidenceType],
    ) -> CapabilityEstimate:
        values = [value for value in raw_values if value is not None]
        estimate, lower, upper = wilson_interval(sum(values), len(values))
        width = upper - lower if upper is not None and lower is not None else Decimal("1")
        uncertainty = _quantize(
            min(Decimal("1"), width + Decimal(1) / Decimal(max(1, len(values))))
        )
        return CapabilityEstimate(
            dimension=dimension,
            sample_count=len(values),
            effective_sample_count=len(values),
            estimate=estimate,
            lower_bound=lower,
            upper_bound=upper,
            uncertainty=uncertainty,
            missing_count=len(raw_values) - len(values),
            source_class_counts=dict(source_counts),
        )

    @staticmethod
    def _continuous_estimate(
        dimension: CapabilityDimension,
        raw_values: list[Decimal | None],
        source_counts: Counter[CapabilityEvidenceType],
    ) -> CapabilityEstimate:
        values = sorted(value for value in raw_values if value is not None)
        estimate = _quantize(sum(values, Decimal("0")) / len(values)) if values else None
        center = _quantize(median(values)) if values else None
        uncertainty = _quantize(Decimal(1) / Decimal(max(1, len(values))))
        return CapabilityEstimate(
            dimension=dimension,
            sample_count=len(values),
            effective_sample_count=len(values),
            estimate=estimate,
            lower_bound=center,
            upper_bound=center,
            uncertainty=uncertainty,
            missing_count=len(raw_values) - len(values),
            source_class_counts=dict(source_counts),
        )

    def assess_promotion(
        self,
        *,
        policy: RoutingPolicyRevision,
        experiment: RoutingExperimentResult,
        sample_count: int,
        quality_improvement: Decimal,
        safety_regression: Decimal,
        policy_regression: Decimal,
        fallback_validated: bool,
        replay_validated: bool,
        approval_reference: str | None = None,
    ) -> RoutingPromotionAssessment:
        reasons = []
        if sample_count < self.configuration.minimum_adaptive_samples:
            reasons.append("insufficient_samples")
        if len(experiment.results) < self.configuration.minimum_shadow_cases:
            reasons.append("insufficient_shadow_cases")
        if quality_improvement < Decimal(
            str(self.configuration.minimum_required_quality_improvement)
        ):
            reasons.append("benchmark_regression")
        if safety_regression > Decimal(str(self.configuration.maximum_allowed_safety_regression)):
            reasons.append("safety_regression")
        if policy_regression > Decimal(str(self.configuration.maximum_allowed_policy_regression)):
            reasons.append("policy_regression")
        if not fallback_validated:
            reasons.append("fallback_not_validated")
        if not replay_validated:
            reasons.append("replay_failure")
        return RoutingPromotionAssessment(
            assessment_id=uuid5(
                NAMESPACE_URL, f"routing-promotion:{policy.content_hash}:{experiment.content_hash}"
            ),
            policy_id=policy.policy_id,
            policy_revision=policy.revision,
            eligible_for_approval=not reasons,
            reasons=tuple(reasons) or ("eligible_for_approval",),
            sample_count=sample_count,
            shadow_case_count=len(experiment.results),
            quality_improvement=quality_improvement,
            safety_regression=safety_regression,
            policy_regression=policy_regression,
            fallback_validated=fallback_validated,
            replay_validated=replay_validated,
            operator_approval_reference=approval_reference,
            assessed_at=experiment.completed_at,
        )

    async def approve_and_enable(
        self,
        policy: RoutingPolicyRevision,
        assessment: RoutingPromotionAssessment,
        *,
        approval_reference: str,
        task_signature_hashes: tuple[str, ...],
    ) -> RoutingPolicyRevision:
        if not assessment.eligible_for_approval or assessment.policy_id != policy.policy_id:
            raise RoutingPolicyError("adaptive policy has not passed its promotion gate")
        approved_payload = policy.model_dump(mode="python", exclude={"content_hash"})
        approved_payload.update(
            revision=policy.revision + 1,
            previous_revision=policy.revision,
            status=RoutingPolicyStatus.APPROVED,
            control_mode=RoutingControlMode.ADAPTIVE,
            operator_approval_reference=approval_reference,
            allowed_task_signature_hashes=task_signature_hashes,
            reason="promotion gate passed with explicit operator approval",
        )
        approved = RoutingPolicyRevision.model_validate(approved_payload)
        await self.repository.create_policy(approved)
        enabled_payload = approved.model_dump(mode="python", exclude={"content_hash"})
        enabled_payload.update(
            revision=approved.revision + 1,
            previous_revision=approved.revision,
            status=RoutingPolicyStatus.ENABLED,
            reason="bounded adaptive policy explicitly enabled",
        )
        enabled = RoutingPolicyRevision.model_validate(enabled_payload)
        await self.repository.create_policy(enabled)
        return enabled

    async def disable_adaptive_policy(
        self, policy: RoutingPolicyRevision, *, reason: str
    ) -> RoutingPolicyRevision:
        if policy.control_mode is not RoutingControlMode.ADAPTIVE:
            raise RoutingPolicyError("only an adaptive policy can be disabled here")
        payload = policy.model_dump(mode="python", exclude={"content_hash"})
        payload.update(
            revision=policy.revision + 1,
            previous_revision=policy.revision,
            status=RoutingPolicyStatus.DISABLED,
            reason=reason,
        )
        disabled = RoutingPolicyRevision.model_validate(payload)
        await self.repository.create_policy(disabled)
        return disabled

    @staticmethod
    def build_multi_model_plan(
        *,
        plan_id: UUID,
        pattern: MultiModelPattern,
        roles: tuple[MultiModelRole, ...],
        controller_budget: RoutingBudget,
        policy_budget: RoutingBudget,
        strategy_budget: RoutingBudget,
        pattern_budget: RoutingBudget,
        verifier_reference: str,
        controller_plan_reference: str,
    ) -> MultiModelExecutionPlan:
        effective = intersect_budgets(
            controller_budget, policy_budget, strategy_budget, pattern_budget
        )
        if len(roles) != len(pattern.roles) or len(roles) > effective.maximum_calls:
            raise RoutingPolicyError("multi-model roles exceed the effective Controller budget")
        if tuple(item.role for item in roles) != pattern.roles:
            raise RoutingPolicyError("multi-model roles do not match the governed pattern")
        return MultiModelExecutionPlan(
            plan_id=plan_id,
            pattern=pattern,
            roles=roles,
            effective_budget=effective,
            verifier_reference=verifier_reference,
            controller_plan_reference=controller_plan_reference,
        )
