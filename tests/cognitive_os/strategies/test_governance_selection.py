from uuid import NAMESPACE_URL, uuid5

import pytest
from pydantic import ValidationError

from cognitive_os.application.services.strategy_service import StrategyService
from cognitive_os.config.strategy_config import StrategyConfiguration
from cognitive_os.domain.context import ContextPurpose, ContextSourceType
from cognitive_os.domain.memory import MemorySensitivity
from cognitive_os.domain.skills import SkillProblemSignature
from cognitive_os.domain.strategies import (
    StrategyActor,
    StrategyApplicabilityInput,
    StrategyCreatorType,
    StrategyScope,
    StrategyScopeType,
    StrategySelectionRequest,
    StrategySelectionStatus,
    StrategyStatisticsSnapshot,
    StrategyStatus,
)
from cognitive_os.skills.fixtures import sprint12_verified_skills
from cognitive_os.strategies.engine import (
    StrategyGraphService,
    empty_registry_snapshot,
    instantiate_controller_plan,
    resolve_skill_bindings,
    select_strategy,
)
from cognitive_os.strategies.errors import StrategyError
from cognitive_os.strategies.fixtures import FIXTURE_TIME, sprint13_verified_strategies


@pytest.mark.asyncio
async def test_initial_strategies_are_verified_and_exactly_skill_bound() -> None:
    repository, registry, problem_classes, targets, _ = await sprint13_verified_strategies()

    assert len(repository.items) == 7
    assert len(registry.query()) == 7
    assert len({item.identity.problem_class_id for item, _ in registry.query()}) == 7
    assert all(revision.status is StrategyStatus.VERIFIED for _, revision in registry.query())
    assert all(
        binding.skill_id is not None and binding.revision is not None
        for _, revision in registry.query()
        for binding in revision.skill_bindings
    )
    assert len(problem_classes.snapshot_hash()) == 64
    assert len(targets.snapshot_hash()) == 64
    with pytest.raises(StrategyError, match="frozen"):
        registry.register(*registry.query()[0])


@pytest.mark.asyncio
async def test_cold_start_requires_approval_then_instantiates_existing_plan() -> None:
    _, registry, problem_classes, targets, _ = await sprint13_verified_strategies()
    _, skill_registry, _ = await sprint12_verified_skills()
    item, revision = next(
        row for row in registry.query() if row[0].identity.canonical_name == "clarification-first"
    )
    snapshot = empty_registry_snapshot(
        registry.snapshot_hash(), problem_classes.snapshot_hash(), targets.snapshot_hash()
    )
    applicability = StrategyApplicabilityInput(
        problem_class_id=item.identity.problem_class_id,
        problem_signature=SkillProblemSignature(
            problem_domain="generic", task_type="clarification"
        ),
        scope=item.identity.scope,
        sensitivity_limit=MemorySensitivity.INTERNAL,
    )
    request = StrategySelectionRequest(
        selection_id=uuid5(NAMESPACE_URL, "strategy-selection-test"),
        task_run_id=uuid5(NAMESPACE_URL, "strategy-task-test"),
        problem_reference=uuid5(NAMESPACE_URL, "strategy-problem-test"),
        applicability_input=applicability,
        registry_snapshot=snapshot,
        controller_budget=revision.budget_profile,
        created_at=FIXTURE_TIME,
    )
    statistics = StrategyStatisticsSnapshot(statistics=())
    decision = select_strategy(request, registry, statistics, StrategyConfiguration())
    assert decision.status is StrategySelectionStatus.REQUIRES_APPROVAL
    assert decision.selected_strategy_id is None

    approved_request = request.model_copy(update={"approval_granted": True})
    approved = select_strategy(approved_request, registry, statistics, StrategyConfiguration())
    assert approved.status is StrategySelectionStatus.SELECTED
    assert approved.selected_strategy_id == revision.strategy_id
    skills = resolve_skill_bindings(revision, skill_registry)
    plan = instantiate_controller_plan(approved_request, approved, revision, skills)
    assert plan.plan.task_run_id == request.task_run_id
    assert len(plan.plan.steps) == len(revision.phases)
    assert {value.phase_id for value in plan.step_bindings} == {
        value.phase_id for value in revision.phases
    }


@pytest.mark.asyncio
async def test_graph_snapshot_is_bounded_and_deterministic() -> None:
    _, registry, _, targets, _ = await sprint13_verified_strategies()
    item, revision = registry.query()[0]
    snapshot = empty_registry_snapshot(registry.snapshot_hash(), "0" * 64, targets.snapshot_hash())
    graph = StrategyGraphService(registry, targets, StrategyConfiguration())

    left = graph.snapshot(item.identity.strategy_id, revision.revision, snapshot)
    right = graph.snapshot(item.identity.strategy_id, revision.revision, snapshot)

    assert left.snapshot_hash == right.snapshot_hash
    assert left.nodes
    assert all(edge.source_revision == revision.revision for edge in left.edges)


@pytest.mark.asyncio
async def test_operator_revision_is_append_only_and_returns_to_draft() -> None:
    repository, registry, _, _, _ = await sprint13_verified_strategies()
    _, current = registry.query()[0]
    actor = StrategyActor(
        creator_type=StrategyCreatorType.OPERATOR,
        creator_id="strategy-test-operator",
    )

    revised = await StrategyService(repository, clock=lambda: FIXTURE_TIME).revise(
        current.strategy_id,
        current,
        await repository.read_edge_set(current.strategy_id, current.revision),
        expected_revision=current.revision,
        actor=actor,
        reason="Reviewable content revision",
    )

    assert revised.revision == current.revision + 1
    assert revised.status is StrategyStatus.DRAFT
    assert revised.created_by == actor
    assert len(await repository.list_revisions(current.strategy_id)) == 4


def test_strategy_configuration_seals_deferred_authority() -> None:
    with pytest.raises(ValidationError, match="forbidden"):
        StrategyConfiguration(allow_provider_strategy_selection=True)
    with pytest.raises(ValidationError, match="global"):
        StrategyScope(scope_type=StrategyScopeType.GLOBAL, scope_id="project")
    assert ContextPurpose.STRATEGY_EXECUTION.value == "strategy_execution"
    assert ContextSourceType.STRATEGY.value == "strategy"
    assert StrategyCreatorType.PROVIDER.value == "provider"
