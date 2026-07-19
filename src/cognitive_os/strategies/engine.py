"""Deterministic governance, graph, selection, and plan services."""

from __future__ import annotations

import json
from collections import defaultdict, deque
from decimal import ROUND_HALF_EVEN, Decimal
from hashlib import sha256
from math import sqrt
from uuid import NAMESPACE_URL, UUID, uuid5

from cognitive_os.config.strategy_config import StrategyConfiguration
from cognitive_os.domain.common import ActorRef
from cognitive_os.domain.enums import ActorType
from cognitive_os.domain.execution import ExecutionPlan, PlanStepDefinition
from cognitive_os.domain.skills import SkillRegistrySnapshot, SkillRevision, SkillStatus
from cognitive_os.domain.strategies import (
    ProblemClassDescriptor,
    ResolvedSkillBinding,
    StrategyApplicabilityCondition,
    StrategyApplicabilityConditionType,
    StrategyApplicabilityEvidence,
    StrategyApplicabilityInput,
    StrategyApplicabilityResult,
    StrategyApplicabilityStatus,
    StrategyBudgetProfile,
    StrategyColdStartStatus,
    StrategyComparisonRequest,
    StrategyComparisonResult,
    StrategyEdge,
    StrategyEdgeSet,
    StrategyEdgeType,
    StrategyExclusionReason,
    StrategyGraphSnapshot,
    StrategyItem,
    StrategyOutcome,
    StrategyOutcomeStatus,
    StrategyPlanInstantiation,
    StrategyPlanStepBinding,
    StrategyRegistrySnapshot,
    StrategyRevision,
    StrategySelectionCandidate,
    StrategySelectionDecision,
    StrategySelectionExclusion,
    StrategySelectionRequest,
    StrategySelectionStatus,
    StrategyStatistics,
    StrategyStatisticsSnapshot,
    StrategyStatus,
    StrategyTargetReference,
    StrategyTargetType,
)
from cognitive_os.memory.governance import sensitivity_allows
from cognitive_os.skills.registry import SkillRegistry

from .errors import StrategyError, StrategyPolicyError

_RISK = {"low": 0, "medium": 1, "high": 2, "critical": 3}
_LIFECYCLE = {
    StrategyStatus.DRAFT: {StrategyStatus.STAGED, StrategyStatus.RETRACTED},
    StrategyStatus.STAGED: {
        StrategyStatus.VERIFIED,
        StrategyStatus.DRAFT,
        StrategyStatus.RETRACTED,
    },
    StrategyStatus.VERIFIED: {
        StrategyStatus.DEPRECATED,
        StrategyStatus.SUPERSEDED,
        StrategyStatus.RETRACTED,
    },
    StrategyStatus.DEPRECATED: {StrategyStatus.RETRACTED},
    StrategyStatus.SUPERSEDED: {StrategyStatus.RETRACTED},
    StrategyStatus.RETRACTED: set(),
}
_RESTRICTED_CYCLE_EDGES = {
    StrategyEdgeType.FALLBACK_TO,
    StrategyEdgeType.SPECIALIZES,
    StrategyEdgeType.GENERALIZES,
    StrategyEdgeType.SUPERSEDES,
}


def _hash(value: object) -> str:
    return sha256(
        json.dumps(value, default=str, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


class ProblemClassRegistry:
    """Frozen exact-version Problem Class Registry."""

    def __init__(self) -> None:
        self._items: dict[tuple[str, int], ProblemClassDescriptor] = {}
        self._frozen = False

    def register(self, descriptor: ProblemClassDescriptor) -> None:
        if self._frozen:
            raise StrategyError("problem-class registry is frozen")
        key = descriptor.problem_class_id, descriptor.version
        if key in self._items:
            raise StrategyError("duplicate problem-class version")
        self._items[key] = descriptor

    def freeze(self) -> None:
        self._frozen = True

    def resolve(self, problem_class_id: str, version: int) -> ProblemClassDescriptor:
        try:
            return self._items[(problem_class_id, version)]
        except KeyError as error:
            raise StrategyError("problem-class version is unavailable") from error

    def snapshot_hash(self) -> str:
        return _hash([self._items[key].model_dump(mode="json") for key in sorted(self._items)])


class TargetResolverRegistry:
    """Frozen resolver set for cross-subsystem exact-revision references."""

    def __init__(self) -> None:
        self._targets: dict[tuple[StrategyTargetType, str, str], str] = {}
        self._frozen = False

    def register(self, reference: StrategyTargetReference) -> None:
        if self._frozen:
            raise StrategyError("strategy target registry is frozen")
        key = reference.target_type, reference.target_id, reference.target_revision
        existing = self._targets.get(key)
        if existing is not None and existing != reference.content_hash:
            raise StrategyError("strategy target revision changed content")
        self._targets[key] = reference.content_hash

    def freeze(self) -> None:
        self._frozen = True

    def resolve(self, reference: StrategyTargetReference) -> None:
        key = reference.target_type, reference.target_id, reference.target_revision
        if self._targets.get(key) != reference.content_hash:
            raise StrategyError("strategy edge target is unavailable or stale")

    def snapshot_hash(self) -> str:
        return _hash(
            [
                (key[0].value, key[1], key[2], value)
                for key, value in sorted(
                    self._targets.items(), key=lambda item: tuple(map(str, item[0]))
                )
            ]
        )


class StrategyRegistry:
    """Frozen registry preserving every exact strategy revision."""

    def __init__(self) -> None:
        self._items: dict[UUID, StrategyItem] = {}
        self._revisions: dict[tuple[UUID, int], StrategyRevision] = {}
        self._edges: dict[tuple[UUID, int], StrategyEdgeSet] = {}
        self._frozen = False

    def register(
        self,
        item: StrategyItem,
        revision: StrategyRevision,
        edge_set: StrategyEdgeSet | None = None,
    ) -> None:
        if self._frozen:
            raise StrategyError("strategy registry is frozen")
        if item.identity.strategy_id != revision.strategy_id:
            raise StrategyError("strategy item and revision identity mismatch")
        key = revision.strategy_id, revision.revision
        if key in self._revisions:
            raise StrategyError("duplicate strategy identity and revision")
        prior = self._items.get(revision.strategy_id)
        if prior is not None and prior.identity != item.identity:
            raise StrategyError("strategy identity changed across revisions")
        self._items[revision.strategy_id] = item
        self._revisions[key] = revision
        self._edges[key] = edge_set or StrategyEdgeSet(
            strategy_id=revision.strategy_id, revision=revision.revision
        )

    def freeze(self) -> None:
        self._frozen = True

    def resolve(self, strategy_id: UUID, revision: int) -> StrategyRevision:
        try:
            return self._revisions[(strategy_id, revision)]
        except KeyError as error:
            raise StrategyError("strategy revision is unavailable") from error

    def edge_set(self, strategy_id: UUID, revision: int) -> StrategyEdgeSet:
        self.resolve(strategy_id, revision)
        return self._edges[(strategy_id, revision)]

    def query(
        self,
        *,
        statuses: tuple[StrategyStatus, ...] = (StrategyStatus.VERIFIED,),
    ) -> tuple[tuple[StrategyItem, StrategyRevision], ...]:
        return tuple(
            (item, self.resolve(strategy_id, item.current_revision))
            for strategy_id, item in sorted(self._items.items(), key=lambda pair: str(pair[0]))
            if item.current_status in statuses
        )

    def snapshot_hash(self) -> str:
        return _hash(
            [
                {
                    "item": self._items[strategy_id].model_dump(mode="json"),
                    "revision": revision.model_dump(mode="json"),
                    "edges": self._edges[(strategy_id, number)].model_dump(mode="json"),
                }
                for (strategy_id, number), revision in sorted(
                    self._revisions.items(), key=lambda pair: (str(pair[0][0]), pair[0][1])
                )
            ]
        )


def validate_lifecycle_transition(current: StrategyStatus, target: StrategyStatus) -> None:
    if target not in _LIFECYCLE[current]:
        raise StrategyPolicyError(
            f"invalid strategy lifecycle transition: {current.value} -> {target.value}"
        )


def _condition_value(
    condition: StrategyApplicabilityCondition, value: StrategyApplicabilityInput
) -> bool:
    parameters = condition.parameters
    condition_type = condition.condition_type
    if condition_type is StrategyApplicabilityConditionType.PROBLEM_CLASS_MATCH:
        return value.problem_class_id == parameters["problem_class_id"]
    if condition_type is StrategyApplicabilityConditionType.PROBLEM_SIGNATURE_MATCH:
        return value.problem_signature.canonical_hash() == parameters["signature_hash"]
    if condition_type is StrategyApplicabilityConditionType.REPOSITORY_PROFILE_MATCH:
        allowed = parameters["allowed"]
        return (
            isinstance(allowed, list)
            and value.repository_profile is not None
            and value.repository_profile in map(str, allowed)
        )
    if condition_type is StrategyApplicabilityConditionType.RISK_RANGE:
        risk = _RISK.get(value.risk_level, 99)
        minimum = _RISK.get(str(parameters.get("minimum", "low")), -1)
        maximum = _RISK.get(str(parameters["maximum"]), -1)
        return minimum <= risk <= maximum
    if condition_type is StrategyApplicabilityConditionType.REQUIRED_OUTPUT:
        return value.required_output_type == parameters["output_type"]
    lookups = {
        StrategyApplicabilityConditionType.AVAILABLE_SKILL: (
            "binding_id",
            value.available_skill_bindings,
        ),
        StrategyApplicabilityConditionType.AVAILABLE_TOOL: (
            "capability_id",
            value.available_tool_capabilities,
        ),
        StrategyApplicabilityConditionType.AVAILABLE_VERIFIER: (
            "capability_id",
            value.available_verifier_capabilities,
        ),
        StrategyApplicabilityConditionType.PROVIDER_ROLE_AVAILABLE: (
            "role_id",
            value.available_model_roles,
        ),
        StrategyApplicabilityConditionType.CONTEXT_PROFILE_AVAILABLE: (
            "profile_id",
            value.available_context_profiles,
        ),
        StrategyApplicabilityConditionType.EXPLICIT_PERMISSION: (
            "permission",
            value.permissions,
        ),
        StrategyApplicabilityConditionType.FEATURE_FLAG: ("flag", value.feature_flags),
    }
    field, available = lookups[condition_type]
    return str(parameters[field]) in available


def evaluate_applicability(
    revision: StrategyRevision, value: StrategyApplicabilityInput
) -> StrategyApplicabilityResult:
    evidence = tuple(
        StrategyApplicabilityEvidence(
            condition_id=condition.condition_id,
            passed=(passed := _condition_value(condition, value)),
            reason_code="condition_matched" if passed else "condition_not_matched",
            evidence_hash=_hash(
                {
                    "condition": condition.model_dump(mode="json"),
                    "input": value.model_dump(mode="json"),
                    "passed": passed,
                }
            ),
        )
        for condition in revision.applicability_profile.conditions
    )
    required = {
        item.condition_id for item in revision.applicability_profile.conditions if item.required
    }
    failed = {item.condition_id for item in evidence if not item.passed}
    return StrategyApplicabilityResult(
        strategy_id=revision.strategy_id,
        revision=revision.revision,
        status=(
            StrategyApplicabilityStatus.INAPPLICABLE
            if required & failed
            else StrategyApplicabilityStatus.APPLICABLE
        ),
        evidence=evidence,
    )


def _wilson_lower_bound(successes: int, total: int) -> Decimal:
    if total == 0:
        return Decimal(0)
    z = 1.96
    ratio = successes / total
    denominator = 1 + z * z / total
    centre = ratio + z * z / (2 * total)
    margin = z * sqrt((ratio * (1 - ratio) + z * z / (4 * total)) / total)
    return Decimal(str((centre - margin) / denominator)).quantize(
        Decimal("0.000000001"), rounding=ROUND_HALF_EVEN
    )


def build_statistics(
    strategy_id: UUID,
    revision: int,
    outcomes: tuple[StrategyOutcome, ...],
    *,
    cohort_id: str = "all",
    projection_revision: int = 1,
    minimum_sample: int = 5,
) -> StrategyStatistics:
    ordered = tuple(sorted(outcomes, key=lambda item: str(item.outcome_id)))
    counts = {status: 0 for status in StrategyOutcomeStatus}
    for outcome in ordered:
        if outcome.strategy_id != strategy_id or outcome.strategy_revision != revision:
            raise StrategyError("statistics outcome belongs to another strategy revision")
        counts[outcome.status] += 1
    total = len(ordered)
    verifier_quality = Decimal(counts[StrategyOutcomeStatus.ACCEPTED]) / Decimal(total or 1)
    return StrategyStatistics(
        strategy_id=strategy_id,
        revision=revision,
        cohort_id=cohort_id,
        projection_revision=projection_revision,
        executions=total,
        accepted=counts[StrategyOutcomeStatus.ACCEPTED],
        rejected=counts[StrategyOutcomeStatus.REJECTED],
        unverifiable=counts[StrategyOutcomeStatus.UNVERIFIABLE],
        cancelled=counts[StrategyOutcomeStatus.CANCELLED],
        policy_denied=counts[StrategyOutcomeStatus.POLICY_DENIED],
        infrastructure_failures=counts[StrategyOutcomeStatus.INFRASTRUCTURE_FAILURE],
        verifier_quality=verifier_quality,
        repairs=sum(item.repair_count for item in ordered),
        fallbacks=sum(item.fallback_count for item in ordered),
        provider_calls=sum(len(item.provider_call_ids) for item in ordered),
        tool_calls=sum(len(item.tool_call_ids) for item in ordered),
        context_builds=sum(len(item.context_bundle_references) for item in ordered),
        token_usage=sum(item.usage.total_tokens or 0 for item in ordered),
        elapsed_ms=sum(item.elapsed_ms for item in ordered),
        safety_failures=sum(bool(item.safety_decision_ids) for item in ordered),
        confidence_lower_bound=_wilson_lower_bound(counts[StrategyOutcomeStatus.ACCEPTED], total),
        sparse_sample=total < minimum_sample,
        source_outcome_ids=tuple(item.outcome_id for item in ordered),
    )


def _statistics_map(
    snapshot: StrategyStatisticsSnapshot,
) -> dict[tuple[UUID, int], StrategyStatistics]:
    return {(item.strategy_id, item.revision): item for item in snapshot.statistics}


def _score(
    revision: StrategyRevision,
    statistics: StrategyStatistics | None,
    configuration: StrategyConfiguration,
) -> dict[str, Decimal]:
    if statistics is None or statistics.sparse_sample:
        return {"specificity": Decimal(len(revision.applicability_profile.conditions))}
    total = Decimal(statistics.executions or 1)
    return {
        "accepted_outcome": Decimal(statistics.accepted)
        / total
        * Decimal(str(configuration.accepted_outcome_weight)),
        "verifier_quality": statistics.verifier_quality
        * Decimal(str(configuration.verifier_quality_weight)),
        "repair_cost": Decimal(statistics.repairs)
        / total
        * Decimal(str(configuration.repair_cost_weight)),
        "latency": Decimal(statistics.elapsed_ms)
        / total
        / Decimal(1_000)
        * Decimal(str(configuration.latency_weight)),
        "token_cost": Decimal(statistics.token_usage)
        / total
        / Decimal(10_000)
        * Decimal(str(configuration.token_cost_weight)),
        "safety_failure": Decimal(statistics.safety_failures)
        / total
        * Decimal(str(configuration.safety_failure_weight)),
        "fallback_frequency": Decimal(statistics.fallbacks)
        / total
        * Decimal(str(configuration.fallback_frequency_weight)),
        "specificity": Decimal(len(revision.applicability_profile.conditions))
        * Decimal(str(configuration.specificity_weight)),
    }


def select_strategy(
    request: StrategySelectionRequest,
    registry: StrategyRegistry,
    statistics: StrategyStatisticsSnapshot,
    configuration: StrategyConfiguration,
) -> StrategySelectionDecision:
    candidates: list[StrategySelectionCandidate] = []
    exclusions: list[StrategySelectionExclusion] = []
    statistic_map = _statistics_map(statistics)
    for item, revision in registry.query(statuses=(StrategyStatus.VERIFIED,)):
        applicability = evaluate_applicability(revision, request.applicability_input)
        if item.identity.scope != request.applicability_input.scope:
            exclusions.append(
                StrategySelectionExclusion(
                    strategy_id=revision.strategy_id,
                    revision=revision.revision,
                    reason=StrategyExclusionReason.SCOPE,
                    detail_code="exact_scope_mismatch",
                )
            )
            continue
        if not sensitivity_allows(
            revision.sensitivity, request.applicability_input.sensitivity_limit
        ):
            exclusions.append(
                StrategySelectionExclusion(
                    strategy_id=revision.strategy_id,
                    revision=revision.revision,
                    reason=StrategyExclusionReason.SENSITIVITY,
                    detail_code="sensitivity_limit_exceeded",
                )
            )
            continue
        if applicability.status is not StrategyApplicabilityStatus.APPLICABLE:
            exclusions.append(
                StrategySelectionExclusion(
                    strategy_id=revision.strategy_id,
                    revision=revision.revision,
                    reason=StrategyExclusionReason.APPLICABILITY,
                    detail_code="required_condition_failed",
                )
            )
            continue
        current_statistics = statistic_map.get((revision.strategy_id, revision.revision))
        cold_start = (
            StrategyColdStartStatus.INSUFFICIENTLY_MEASURED
            if current_statistics is None or current_statistics.sparse_sample
            else StrategyColdStartStatus.MEASURED
        )
        breakdown = _score(revision, current_statistics, configuration)
        candidates.append(
            StrategySelectionCandidate(
                strategy_id=revision.strategy_id,
                revision=revision.revision,
                canonical_name=item.identity.canonical_name,
                applicability=applicability,
                cold_start_status=cold_start,
                score_breakdown=breakdown,
                total_score=sum(breakdown.values(), start=Decimal(0)),
            )
        )
    candidates.sort(key=lambda item: (-item.total_score, item.canonical_name, item.revision))
    candidates = candidates[: request.maximum_candidates]
    measured = [
        item for item in candidates if item.cold_start_status is StrategyColdStartStatus.MEASURED
    ]
    pool = measured or candidates
    selected = pool[0] if pool else None
    approval_required = bool(
        selected
        and selected.cold_start_status is StrategyColdStartStatus.INSUFFICIENTLY_MEASURED
        and configuration.cold_start_requires_approval
    )
    if approval_required and not request.approval_granted:
        status = StrategySelectionStatus.REQUIRES_APPROVAL
        selected = None
        reason = "cold_start_requires_operator_approval"
    elif selected is None:
        status = StrategySelectionStatus.NO_APPLICABLE_STRATEGY
        reason = "no_verified_applicable_strategy"
    else:
        status = StrategySelectionStatus.SELECTED
        reason = "deterministic_ranking_selected"
    profile = {
        name: getattr(configuration, name)
        for name in (
            "accepted_outcome_weight",
            "verifier_quality_weight",
            "repair_cost_weight",
            "latency_weight",
            "token_cost_weight",
            "safety_failure_weight",
            "fallback_frequency_weight",
            "specificity_weight",
        )
    }
    return StrategySelectionDecision(
        selection_id=request.selection_id,
        task_run_id=request.task_run_id,
        status=status,
        selected_strategy_id=selected.strategy_id if selected else None,
        selected_revision=selected.revision if selected else None,
        candidates=tuple(candidates),
        exclusions=tuple(exclusions),
        registry_snapshot=request.registry_snapshot,
        statistics_snapshot_hash=statistics.snapshot_hash,
        ranking_profile_id="strategy-ranking-v1",
        ranking_profile_hash=_hash(profile),
        cold_start_status=selected.cold_start_status if selected else None,
        approval_required=approval_required,
        reason=reason,
        created_at=request.created_at,
    )


def resolve_skill_bindings(
    revision: StrategyRevision, registry: SkillRegistry
) -> tuple[ResolvedSkillBinding, ...]:
    resolved: list[ResolvedSkillBinding] = []
    for binding in revision.skill_bindings:
        candidates: list[tuple[SkillRevision, bool]] = []
        if binding.skill_id is not None and binding.revision is not None:
            candidates.append((registry.resolve(binding.skill_id, binding.revision), False))
        elif binding.skill_id is not None:
            candidates.append((registry.current(binding.skill_id), False))
        else:
            for _, skill in registry.query(statuses=(SkillStatus.VERIFIED,)):
                if binding.selection_signature and any(
                    signature == binding.selection_signature
                    for signature in skill.problem_signatures
                ):
                    candidates.append((skill, False))
        for skill_id, skill_revision in binding.fallback_references:
            skill = (
                registry.resolve(skill_id, skill_revision)
                if skill_revision is not None
                else registry.current(skill_id)
            )
            candidates.append((skill, True))
        verified = next(
            (item for item in candidates if item[0].status is SkillStatus.VERIFIED), None
        )
        if verified is None:
            if binding.required:
                raise StrategyPolicyError(
                    f"required skill binding unavailable: {binding.binding_id}"
                )
            continue
        skill, fallback = verified
        resolved.append(
            ResolvedSkillBinding(
                binding_id=binding.binding_id,
                skill_id=skill.skill_id,
                revision=skill.revision,
                package_hash=skill.package_hash,
                fallback=fallback,
            )
        )
    return tuple(resolved)


def _minimum_budget(*budgets: StrategyBudgetProfile) -> StrategyBudgetProfile:
    return StrategyBudgetProfile(
        **{
            field: min(getattr(item, field) for item in budgets)
            for field in StrategyBudgetProfile.model_fields
        }
    )


def instantiate_controller_plan(
    request: StrategySelectionRequest,
    decision: StrategySelectionDecision,
    revision: StrategyRevision,
    resolved_skills: tuple[ResolvedSkillBinding, ...],
) -> StrategyPlanInstantiation:
    if decision.status is not StrategySelectionStatus.SELECTED:
        raise StrategyPolicyError("only a selected strategy can instantiate a plan")
    if (decision.selected_strategy_id, decision.selected_revision) != (
        revision.strategy_id,
        revision.revision,
    ):
        raise StrategyPolicyError("selection and strategy revision mismatch")
    bindings = {item.binding_id: item for item in resolved_skills}
    phase_steps: dict[str, UUID] = {
        phase.phase_id: uuid5(
            NAMESPACE_URL,
            f"strategy-step:{request.task_run_id}:{revision.strategy_id}:"
            f"{revision.revision}:{phase.phase_id}",
        )
        for phase in revision.phases
    }
    steps = tuple(
        PlanStepDefinition(
            step_id=phase_steps[phase.phase_id],
            sequence=phase.sequence,
            step_type=f"strategy.{phase.phase_type.value}",
            title=phase.display_name,
            description=phase.purpose,
            depends_on=tuple(phase_steps[item] for item in phase.dependencies),
            required_tool_ids=tuple(item.capability_id for item in phase.tool_requirements),
            required_verifier_ids=tuple(item.capability_id for item in phase.verifier_requirements),
        )
        for phase in sorted(revision.phases, key=lambda item: (item.sequence, item.phase_id))
    )
    plan_id = uuid5(
        NAMESPACE_URL,
        f"strategy-plan:{request.selection_id}:{revision.strategy_id}:{revision.revision}",
    )
    plan = ExecutionPlan(
        plan_id=plan_id,
        task_run_id=request.task_run_id,
        version=1,
        created_at=request.created_at,
        created_by=ActorRef(actor_type=ActorType.SYSTEM, actor_id="strategy-engine"),
        steps=steps,
    )
    provenance = tuple(
        StrategyPlanStepBinding(
            step_id=phase_steps[phase.phase_id],
            phase_id=phase.phase_id,
            skill_binding=(
                bindings[phase.skill_binding_ids[0]] if phase.skill_binding_ids else None
            ),
            model_role_id=phase.model_role_ids[0] if phase.model_role_ids else None,
            tool_capabilities=tuple(item.capability_id for item in phase.tool_requirements),
            verifier_capabilities=tuple(item.capability_id for item in phase.verifier_requirements),
            context_profile_id=phase.context_profile_id,
            effective_budget=_minimum_budget(
                request.controller_budget, revision.budget_profile, phase.budget
            ),
            branch_ids=tuple(
                item.branch_id
                for item in revision.branches
                if item.source_phase_id == phase.phase_id
            ),
            fallback_provenance=tuple(
                binding_id
                for binding_id in phase.skill_binding_ids
                if bindings.get(binding_id) and bindings[binding_id].fallback
            ),
        )
        for phase in sorted(revision.phases, key=lambda item: (item.sequence, item.phase_id))
    )
    return StrategyPlanInstantiation(
        instantiation_id=uuid5(NAMESPACE_URL, f"strategy-instantiation:{plan_id}"),
        selection_id=request.selection_id,
        strategy_id=revision.strategy_id,
        strategy_revision=revision.revision,
        task_run_id=request.task_run_id,
        plan=plan,
        step_bindings=provenance,
        registry_snapshot=request.registry_snapshot,
        created_at=request.created_at,
    )


class StrategyGraphService:
    """Bounded, deterministic graph validation and traversal."""

    def __init__(
        self,
        registry: StrategyRegistry,
        targets: TargetResolverRegistry,
        configuration: StrategyConfiguration,
    ) -> None:
        self._registry = registry
        self._targets = targets
        self._configuration = configuration

    def validate(self, edge_set: StrategyEdgeSet) -> None:
        if len(edge_set.edges) > self._configuration.maximum_graph_edges_per_revision:
            raise StrategyPolicyError("strategy edge set exceeds the configured bound")
        for edge in edge_set.edges:
            self._targets.resolve(edge.target)
        adjacency: dict[str, set[str]] = defaultdict(set)
        for edge in edge_set.edges:
            if edge.edge_type in _RESTRICTED_CYCLE_EDGES:
                source = f"{edge.source_strategy_id}@{edge.source_revision}"
                target = f"{edge.target.target_id}@{edge.target.target_revision}"
                adjacency[source].add(target)

        def visit(node: str, visiting: set[str], visited: set[str]) -> None:
            if node in visiting:
                raise StrategyPolicyError("restricted strategy relationship contains a cycle")
            if node in visited:
                return
            visiting.add(node)
            for target in sorted(adjacency[node]):
                visit(target, visiting, visited)
            visiting.remove(node)
            visited.add(node)

        visited: set[str] = set()
        for node in sorted(adjacency):
            visit(node, set(), visited)

    def snapshot(
        self,
        strategy_id: UUID,
        revision: int,
        registry_snapshot: StrategyRegistrySnapshot,
        *,
        depth: int = 3,
    ) -> StrategyGraphSnapshot:
        depth = min(depth, self._configuration.maximum_graph_query_depth)
        initial = self._registry.edge_set(strategy_id, revision)
        self.validate(initial)
        nodes: dict[tuple[str, str, str], StrategyTargetReference] = {}
        edges: dict[str, StrategyEdge] = {}
        queue: deque[tuple[UUID, int, int]] = deque([(strategy_id, revision, 0)])
        visited: set[tuple[UUID, int]] = set()
        while queue and len(nodes) < self._configuration.maximum_graph_query_nodes:
            current_id, current_revision, current_depth = queue.popleft()
            if (current_id, current_revision) in visited:
                continue
            visited.add((current_id, current_revision))
            edge_set = self._registry.edge_set(current_id, current_revision)
            for edge in edge_set.edges:
                nodes[
                    (
                        edge.target.target_type.value,
                        edge.target.target_id,
                        edge.target.target_revision,
                    )
                ] = edge.target
                edges[edge.edge_hash] = edge
                if (
                    current_depth < depth
                    and edge.target.target_type is StrategyTargetType.STRATEGY_REVISION
                ):
                    try:
                        queue.append(
                            (
                                UUID(edge.target.target_id),
                                int(edge.target.target_revision),
                                current_depth + 1,
                            )
                        )
                    except ValueError as error:
                        raise StrategyPolicyError(
                            "invalid strategy revision graph target"
                        ) from error
        if len(edges) > self._configuration.maximum_graph_query_edges:
            raise StrategyPolicyError("strategy graph query exceeds the edge bound")
        return StrategyGraphSnapshot(
            snapshot_id=uuid5(
                NAMESPACE_URL,
                f"strategy-graph:{strategy_id}:{revision}:{depth}:{registry_snapshot.strategy_registry_hash}",
            ),
            nodes=tuple(nodes[key] for key in sorted(nodes)),
            edges=tuple(edges[key] for key in sorted(edges)),
            query_parameters={"depth": depth},
            registry_snapshot=registry_snapshot,
            created_at=self._registry.resolve(strategy_id, revision).created_at,
        )


def empty_registry_snapshot(
    strategy_hash: str, problem_hash: str, target_hash: str
) -> StrategyRegistrySnapshot:
    """Build a stable credential-free snapshot for fixtures and offline commands."""
    empty = _hash([])
    return StrategyRegistrySnapshot(
        strategy_registry_hash=strategy_hash,
        problem_class_registry_hash=problem_hash,
        target_resolver_registry_hash=target_hash,
        skill_registry=SkillRegistrySnapshot(
            registry_hash=empty,
            precondition_registry_hash=empty,
            tool_registry_hash=empty,
            verifier_registry_hash=empty,
            provider_registry_hash=empty,
            context_registry_hash=empty,
        ),
        tool_registry_hash=empty,
        verifier_registry_hash=empty,
        provider_registry_hash=empty,
        context_registry_hash=empty,
    )


def render_graph_dot(snapshot: StrategyGraphSnapshot) -> str:
    """Render a stable analytical view without changing graph authority."""
    lines = ["digraph strategy_evolution {"]
    for node in snapshot.nodes:
        key = f"{node.target_type.value}:{node.target_id}@{node.target_revision}"
        lines.append(f'  "{key}";')
    for edge in snapshot.edges:
        source = f"strategy_revision:{edge.source_strategy_id}@{edge.source_revision}"
        target = (
            f"{edge.target.target_type.value}:{edge.target.target_id}@{edge.target.target_revision}"
        )
        lines.append(f'  "{source}" -> "{target}" [label="{edge.edge_type.value}"];')
    lines.append("}")
    return "\n".join(lines) + "\n"


def render_graph_mermaid(snapshot: StrategyGraphSnapshot) -> str:
    """Render the same exact snapshot as deterministic Mermaid flowchart data."""
    identities: dict[str, str] = {}
    labels = {
        f"{node.target_type.value}:{node.target_id}@{node.target_revision}"
        for node in snapshot.nodes
    }
    labels.update(
        f"strategy_revision:{edge.source_strategy_id}@{edge.source_revision}"
        for edge in snapshot.edges
    )
    for index, label in enumerate(sorted(labels), start=1):
        identities[label] = f"n{index}"
    lines = ["flowchart TD"]
    for label in sorted(labels):
        lines.append(f'  {identities[label]}["{label}"]')
    for edge in snapshot.edges:
        source = f"strategy_revision:{edge.source_strategy_id}@{edge.source_revision}"
        target = (
            f"{edge.target.target_type.value}:{edge.target.target_id}@{edge.target.target_revision}"
        )
        lines.append(f"  {identities[source]} -->|{edge.edge_type.value}| {identities[target]}")
    return "\n".join(lines) + "\n"


def compare_strategies(
    request: StrategyComparisonRequest,
    left: StrategyRevision,
    right: StrategyRevision,
    left_statistics: StrategyStatistics | None = None,
    right_statistics: StrategyStatistics | None = None,
) -> StrategyComparisonResult:
    if (left.strategy_id, left.revision) != (
        request.left_strategy_id,
        request.left_revision,
    ) or (right.strategy_id, right.revision) != (
        request.right_strategy_id,
        request.right_revision,
    ):
        raise StrategyError("strategy comparison request targets another revision")
    changes = []
    for name in (
        "applicability_profile",
        "phases",
        "branches",
        "skill_bindings",
        "model_role_bindings",
        "context_profiles",
        "budget_profile",
        "repair_policy",
        "stop_conditions",
    ):
        if getattr(left, name) != getattr(right, name):
            changes.append(name)
    statistics_delta: dict[str, Decimal] = {}
    source_ids: tuple[UUID, ...] = ()
    sufficient = False
    if left_statistics and right_statistics:
        for name in (
            "executions",
            "accepted",
            "repairs",
            "fallbacks",
            "token_usage",
            "elapsed_ms",
            "safety_failures",
        ):
            statistics_delta[name] = Decimal(getattr(right_statistics, name)) - Decimal(
                getattr(left_statistics, name)
            )
        source_ids = tuple(
            sorted(
                {
                    *left_statistics.source_outcome_ids,
                    *right_statistics.source_outcome_ids,
                },
                key=str,
            )
        )
        sufficient = not left_statistics.sparse_sample and not right_statistics.sparse_sample
    return StrategyComparisonResult(
        comparison_id=request.comparison_id,
        structural_changes=tuple(changes) or ("none",),
        statistics_delta=statistics_delta,
        sufficient_sample=sufficient,
        source_outcome_ids=source_ids,
    )


def optional_networkx_projection(snapshot: StrategyGraphSnapshot) -> object:
    """Build a disposable analytical projection when the optional extra exists."""
    try:
        import networkx as nx  # type: ignore[import-untyped]
    except ImportError as error:
        raise StrategyError("NetworkX analytical projection is unavailable") from error
    graph = nx.MultiDiGraph()
    for edge in snapshot.edges:
        source = ("strategy_revision", str(edge.source_strategy_id), str(edge.source_revision))
        target = (
            edge.target.target_type.value,
            edge.target.target_id,
            edge.target.target_revision,
        )
        graph.add_edge(source, target, key=edge.edge_hash, edge_type=edge.edge_type.value)
    return graph
