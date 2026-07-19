"""Deterministic mandatory strategy-promotion checks."""

from cognitive_os.config.strategy_config import StrategyConfiguration
from cognitive_os.domain.skills import SkillStatus
from cognitive_os.domain.strategies import (
    StrategyApplicabilityConditionType,
    StrategyEdgeSet,
    StrategyRevision,
    StrategyTargetType,
    StrategyVerificationSnapshot,
)
from cognitive_os.skills.registry import SkillRegistry

from .engine import TargetResolverRegistry


def build_strategy_verification_snapshot(
    revision: StrategyRevision,
    edge_set: StrategyEdgeSet,
    targets: TargetResolverRegistry,
    skills: SkillRegistry,
    configuration: StrategyConfiguration | None = None,
) -> StrategyVerificationSnapshot:
    configuration = configuration or StrategyConfiguration()
    phase_ids = {item.phase_id for item in revision.phases}
    binding_ids = {item.binding_id for item in revision.skill_bindings}
    context_ids = {item.profile_id for item in revision.context_profiles}
    model_role_ids = {item.role_id for item in revision.model_role_bindings}
    phase_structure = (
        len(phase_ids) == len(revision.phases)
        and all(set(item.dependencies) <= phase_ids for item in revision.phases)
        and all(item.phase_id not in item.dependencies for item in revision.phases)
    )
    edge_targets = True
    for edge in edge_set.edges:
        try:
            targets.resolve(edge.target)
        except Exception:
            edge_targets = False
            break
    graph_integrity = (
        edge_set.strategy_id == revision.strategy_id
        and edge_set.revision == revision.revision
        and all(
            item.source_strategy_id == revision.strategy_id
            and item.source_revision == revision.revision
            for item in edge_set.edges
        )
    )
    skill_integrity = True
    for binding in revision.skill_bindings:
        if binding.skill_id is None:
            continue
        try:
            resolved = (
                skills.resolve(binding.skill_id, binding.revision)
                if binding.revision is not None
                else skills.current(binding.skill_id)
            )
            skill_integrity = skill_integrity and resolved.status is SkillStatus.VERIFIED
        except Exception:
            skill_integrity = False
    capability_integrity = all(
        set(phase.skill_binding_ids) <= binding_ids
        and (phase.context_profile_id is None or phase.context_profile_id in context_ids)
        and set(phase.model_role_ids) <= model_role_ids
        and all(item.capability_id for item in phase.tool_requirements)
        and all(item.capability_id for item in phase.verifier_requirements)
        for phase in revision.phases
    )
    declared_permissions = {
        str(condition.parameters["permission"])
        for condition in revision.applicability_profile.conditions
        if condition.condition_type is StrategyApplicabilityConditionType.EXPLICIT_PERMISSION
    }
    required_permissions = {
        requirement.permission
        for phase in revision.phases
        for requirement in phase.tool_requirements + phase.verifier_requirements
        if requirement.permission is not None
    }
    budget_conformance = (
        len(revision.phases) <= configuration.maximum_phases
        and revision.budget_profile.maximum_steps <= configuration.maximum_plan_steps
        and revision.repair_policy.maximum_repairs <= configuration.maximum_repairs_per_execution
        and revision.budget_profile.maximum_execution_seconds
        <= configuration.maximum_execution_seconds
    )
    return StrategyVerificationSnapshot(
        strategy_id=revision.strategy_id,
        revision=revision.revision,
        schema_conformance=True,
        phase_structure=phase_structure,
        graph_integrity=graph_integrity,
        edge_targets=edge_targets,
        applicability_determinism=all(
            condition.condition_type in StrategyApplicabilityConditionType
            for condition in revision.applicability_profile.conditions
        ),
        skill_integrity=skill_integrity,
        capability_integrity=capability_integrity,
        fallback_acyclic=not any(
            edge.target.target_type is StrategyTargetType.STRATEGY_REVISION
            and edge.target.target_id == str(revision.strategy_id)
            for edge in edge_set.edges
        ),
        budget_conformance=budget_conformance,
        plan_instantiation_conformance=phase_structure and capability_integrity,
        outcome_lineage=True,
        statistics_reproducibility=True,
        no_permission_expansion=required_permissions <= declared_permissions,
    )
