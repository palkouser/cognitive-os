"""Credential-free deterministic Sprint 13 strategy fixtures."""

from __future__ import annotations

from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

import yaml

from cognitive_os.application.services.strategy_service import StrategyService
from cognitive_os.context.fixtures import FixtureArtifactStore
from cognitive_os.domain.memory import MemorySensitivity
from cognitive_os.domain.skills import SkillRevision
from cognitive_os.domain.strategies import (
    ProblemClassDescriptor,
    StrategyActor,
    StrategyApplicabilityCondition,
    StrategyApplicabilityConditionType,
    StrategyApplicabilityProfile,
    StrategyBindingType,
    StrategyBranch,
    StrategyBranchCondition,
    StrategyBranchSignal,
    StrategyBudgetProfile,
    StrategyContextProfile,
    StrategyCreatorType,
    StrategyEdge,
    StrategyEdgeSet,
    StrategyEdgeType,
    StrategyExecutionStatus,
    StrategyIdentity,
    StrategyItem,
    StrategyModelRoleBinding,
    StrategyPhase,
    StrategyPhaseType,
    StrategyPromotionDecision,
    StrategyPromotionOutcome,
    StrategyRepairPolicy,
    StrategyRequirement,
    StrategyRevision,
    StrategyScope,
    StrategyScopeType,
    StrategySkillBinding,
    StrategySourceRef,
    StrategySourceType,
    StrategyStatus,
    StrategyStopCondition,
    StrategyTargetReference,
    StrategyTargetType,
)
from cognitive_os.skills.fixtures import sprint12_verified_skills

from .engine import ProblemClassRegistry, StrategyRegistry, TargetResolverRegistry
from .repository import InMemoryStrategyRepository
from .validation import build_strategy_verification_snapshot

FIXTURE_TIME = datetime(2026, 7, 19, tzinfo=UTC)
_SCOPE = StrategyScope(scope_type=StrategyScopeType.PROJECT, scope_id="cognitive-os")
_ACTOR = StrategyActor(creator_type=StrategyCreatorType.OPERATOR, creator_id="sprint-13-fixture")


def _phase_type(name: str) -> StrategyPhaseType:
    if "context" in name or "inspection" in name or "evidence" in name:
        return StrategyPhaseType.CONTEXT
    if "verification" in name or "reproduction" in name or "review" in name:
        return StrategyPhaseType.VERIFICATION
    if "provider" in name or "advisory" in name:
        return StrategyPhaseType.PROVIDER
    if "clarification" in name or "waiting" in name:
        return StrategyPhaseType.CLARIFICATION
    if "acceptance" in name:
        return StrategyPhaseType.ACCEPTANCE
    if "repair" in name or "implementation" in name or "correction" in name:
        return StrategyPhaseType.REPAIR
    if "packaging" in name or "reselection" in name:
        return StrategyPhaseType.TERMINAL
    return StrategyPhaseType.SKILL


def _skill_for_phase(name: str, skills: dict[str, SkillRevision]) -> SkillRevision | None:
    choices = (
        ("clarification", "clarification-request"),
        ("advisory", "claude-advisory-preparation"),
        ("inspection", "repository-inspection"),
        ("repair", "verification-driven-python-repair"),
        ("implementation", "safe-diff-preparation"),
        ("diff", "safe-diff-preparation"),
        ("verification", "focused-test-execution"),
        ("reproduction", "focused-test-execution"),
        ("evidence", "evidence-collection"),
        ("context", "evidence-collection"),
        ("review", "evidence-collection"),
        ("packaging", "evidence-collection"),
        ("acceptance", "evidence-collection"),
    )
    for token, skill_name in choices:
        if token in name and skill_name in skills:
            return skills[skill_name]
    return None


def load_strategy_definition(
    path: Path,
    skills: dict[str, SkillRevision],
) -> tuple[StrategyItem, StrategyRevision, StrategyEdgeSet, ProblemClassDescriptor]:
    raw_bytes = path.read_bytes()
    source_hash = sha256(raw_bytes).hexdigest()
    metadata = yaml.safe_load(raw_bytes)
    if not isinstance(metadata, dict) or metadata.get("format_version") != "1":
        raise ValueError(f"invalid strategy fixture: {path.as_posix()}")
    canonical_name = str(metadata["canonical_name"])
    problem_class_id = str(metadata["problem_class_id"])
    strategy_id = uuid5(
        NAMESPACE_URL, f"cognitive-os-strategy:{_SCOPE.canonical_hash()}:{canonical_name}"
    )
    source = StrategySourceRef(
        source_type=StrategySourceType.REPOSITORY,
        source_id=path.as_posix(),
        source_revision="1",
        content_hash=source_hash,
    )
    requested_skill_names = tuple(str(item) for item in metadata["skills"])
    unavailable = set(requested_skill_names) - skills.keys()
    if unavailable:
        raise ValueError(f"strategy references unavailable skills: {sorted(unavailable)}")
    bindings = tuple(
        StrategySkillBinding(
            binding_id=name,
            binding_type=StrategyBindingType.EXACT_SKILL_REVISION,
            skill_id=skills[name].skill_id,
            revision=skills[name].revision,
        )
        for name in requested_skill_names
    )
    available_strategy_skills = {name: skills[name] for name in requested_skill_names}
    phase_names = tuple(str(item) for item in metadata["phases"])
    phases = []
    for sequence, name in enumerate(phase_names, start=1):
        skill = _skill_for_phase(name, available_strategy_skills)
        tool_requirements = (
            (
                StrategyRequirement(
                    requirement_id=f"{name}-workspace",
                    capability_id="workspace.patch",
                    permission="workspace.write",
                ),
            )
            if any(token in name for token in ("repair", "implementation"))
            else ()
        )
        verifier_requirements = (
            (
                StrategyRequirement(
                    requirement_id=f"{name}-verifier",
                    capability_id=("coding.mypy" if "typed" in name else "coding.required-checks"),
                ),
            )
            if any(token in name for token in ("verification", "reproduction", "review"))
            else ()
        )
        phases.append(
            StrategyPhase(
                phase_id=name,
                sequence=sequence,
                phase_type=_phase_type(name),
                display_name=name.replace("-", " ").title(),
                purpose=f"Execute the bounded {name.replace('-', ' ')} phase.",
                dependencies=(phase_names[sequence - 2],) if sequence > 1 else (),
                skill_binding_ids=(
                    (next(key for key, value in skills.items() if value is skill),) if skill else ()
                ),
                model_role_ids=("advisory",)
                if any(token in name for token in ("provider", "advisory"))
                else (),
                tool_requirements=tool_requirements,
                verifier_requirements=verifier_requirements,
                context_profile_id="strategy-context-v1" if "context" in name else None,
                budget=StrategyBudgetProfile(maximum_repairs=int(metadata["maximum_repairs"])),
            )
        )
    branches: tuple[StrategyBranch, ...] = ()
    if canonical_name == "verification-driven-repair":
        branches = (
            StrategyBranch(
                branch_id="focused-failure-to-repair",
                source_phase_id="focused-verification",
                target_phase_id="bounded-repair",
                condition=StrategyBranchCondition(
                    signal=StrategyBranchSignal.VERIFIER_OUTCOME,
                    expected_value="failed",
                ),
            ),
        )
    identity = StrategyIdentity(
        strategy_id=strategy_id,
        canonical_name=canonical_name,
        scope=_SCOPE,
        problem_class_id=problem_class_id,
        created_at=FIXTURE_TIME,
        created_by=_ACTOR,
    )
    permission_conditions = (
        (
            StrategyApplicabilityCondition(
                condition_id="workspace-permission",
                condition_type=StrategyApplicabilityConditionType.EXPLICIT_PERMISSION,
                parameters={"permission": "workspace.write"},
            ),
        )
        if any(phase.tool_requirements for phase in phases)
        else ()
    )
    uses_provider = any(phase.model_role_ids for phase in phases)
    uses_context = any(phase.context_profile_id for phase in phases)
    revision = StrategyRevision(
        strategy_id=strategy_id,
        revision=1,
        status=StrategyStatus.DRAFT,
        display_name=str(metadata["display_name"]),
        description=str(metadata["description"]),
        applicability_profile=StrategyApplicabilityProfile(
            conditions=(
                StrategyApplicabilityCondition(
                    condition_id="problem-class",
                    condition_type=StrategyApplicabilityConditionType.PROBLEM_CLASS_MATCH,
                    parameters={"problem_class_id": problem_class_id},
                ),
                *permission_conditions,
            )
        ),
        phases=tuple(phases),
        branches=branches,
        skill_bindings=bindings,
        model_role_bindings=(
            (
                StrategyModelRoleBinding(
                    role_id="advisory",
                    provider_profile_id="host-configured-advisory",
                ),
            )
            if uses_provider
            else ()
        ),
        context_profiles=(
            (
                StrategyContextProfile(
                    profile_id="strategy-context-v1",
                    context_purpose="strategy_execution",
                ),
            )
            if uses_context
            else ()
        ),
        budget_profile=StrategyBudgetProfile(maximum_repairs=int(metadata["maximum_repairs"])),
        repair_policy=StrategyRepairPolicy(maximum_repairs=int(metadata["maximum_repairs"])),
        stop_conditions=(
            StrategyStopCondition(
                condition_id="acceptance-terminal",
                signal=StrategyBranchSignal.ACCEPTANCE_STATUS,
                expected_value="accepted",
                terminal_status=StrategyExecutionStatus.ACCEPTED,
            ),
        ),
        source_refs=(source,),
        sensitivity=MemorySensitivity.INTERNAL,
        regression_profile=str(metadata["regression_profile"]),
        created_at=FIXTURE_TIME,
        created_by=_ACTOR,
        reason="Sprint 13 manually authored seed",
    )
    item = StrategyItem(
        identity=identity,
        current_revision=1,
        current_status=StrategyStatus.DRAFT,
        idempotency_key=sha256(
            f"{identity.canonical_hash()}:{revision.content_hash}".encode()
        ).hexdigest(),
    )
    descriptor = ProblemClassDescriptor(
        problem_class_id=problem_class_id,
        version=1,
        display_name=problem_class_id.replace(".", " ").title(),
        description=f"Frozen problem class for {revision.display_name}.",
        problem_domains=(problem_class_id.split(".")[0],),
        created_at=FIXTURE_TIME,
        created_by=_ACTOR,
    )
    targets = [
        StrategyTargetReference(
            target_type=StrategyTargetType.PROBLEM_CLASS,
            target_id=problem_class_id,
            target_revision="1",
            content_hash=descriptor.content_hash,
            scope=_SCOPE,
        )
    ]
    targets.extend(
        StrategyTargetReference(
            target_type=StrategyTargetType.SKILL_REVISION,
            target_id=str(skills[name].skill_id),
            target_revision=str(skills[name].revision),
            content_hash=skills[name].content_hash,
            scope=_SCOPE,
        )
        for name in requested_skill_names
    )
    edges = tuple(
        StrategyEdge(
            edge_id=uuid5(
                NAMESPACE_URL,
                f"strategy-edge:{strategy_id}:1:{target.target_type.value}:"
                f"{target.target_id}:{target.target_revision}",
            ),
            source_strategy_id=strategy_id,
            source_revision=1,
            target=target,
            edge_type=(
                StrategyEdgeType.APPLIES_TO_PROBLEM_CLASS
                if target.target_type is StrategyTargetType.PROBLEM_CLASS
                else StrategyEdgeType.USES_SKILL
            ),
            source_refs=(source,),
            created_at=FIXTURE_TIME,
        )
        for target in targets
    )
    return (
        item,
        revision,
        StrategyEdgeSet(strategy_id=strategy_id, revision=1, edges=edges),
        descriptor,
    )


async def sprint13_verified_strategies(
    root: Path = Path("strategies"),
) -> tuple[
    InMemoryStrategyRepository,
    StrategyRegistry,
    ProblemClassRegistry,
    TargetResolverRegistry,
    FixtureArtifactStore,
]:
    _, skill_registry, artifacts = await sprint12_verified_skills()
    skills = {item.identity.canonical_name: revision for item, revision in skill_registry.query()}
    repository = InMemoryStrategyRepository()
    service = StrategyService(repository, clock=lambda: FIXTURE_TIME)
    problem_classes = ProblemClassRegistry()
    target_resolvers = TargetResolverRegistry()
    for path in sorted(root.glob("*/strategy.yaml")):
        item, draft, edge_set, descriptor = load_strategy_definition(path, skills)
        problem_classes.register(descriptor)
        for edge in edge_set.edges:
            target_resolvers.register(edge.target)
        await service.create(item, draft, edge_set)
        staged = await service.transition(
            draft.strategy_id,
            StrategyStatus.STAGED,
            expected_revision=1,
            actor=_ACTOR,
            reason="Credential-free regressions passed",
        )
        verification = build_strategy_verification_snapshot(
            staged,
            await repository.read_edge_set(staged.strategy_id, staged.revision),
            target_resolvers,
            skill_registry,
        )
        verifier_bundle = await artifacts.put_bytes(
            verification.model_dump_json().encode(), media_type="application/json"
        )
        regression = await artifacts.put_bytes(
            staged.regression_profile.encode(), media_type="application/json"
        )
        promotion = StrategyPromotionDecision(
            decision_id=uuid5(NAMESPACE_URL, f"strategy-promotion:{staged.content_hash}"),
            strategy_id=staged.strategy_id,
            revision=staged.revision,
            outcome=StrategyPromotionOutcome.VERIFY,
            verifier_bundle=verifier_bundle,
            regression_summary=regression,
            decided_by=_ACTOR,
            reason_codes=("all_required_verifiers_passed",),
            decided_at=FIXTURE_TIME,
        )
        await service.transition(
            staged.strategy_id,
            StrategyStatus.VERIFIED,
            expected_revision=staged.revision,
            actor=_ACTOR,
            reason="Verified fixture promotion",
            verification=verification,
            promotion=promotion,
        )
    problem_classes.freeze()
    target_resolvers.freeze()
    registry = StrategyRegistry()
    for item, revision in await repository.query_candidates():
        registry.register(
            item,
            revision,
            await repository.read_edge_set(revision.strategy_id, revision.revision),
        )
    registry.freeze()
    return repository, registry, problem_classes, target_resolvers, artifacts
