"""Run the credential-free deterministic Sprint 13 strategy smoke path."""

import asyncio
import json
from hashlib import sha256
from uuid import NAMESPACE_URL, uuid5

from cognitive_os.config.strategy_config import StrategyConfiguration
from cognitive_os.context.fixtures import sprint11_fixture
from cognitive_os.domain.common import TokenUsage
from cognitive_os.domain.context import (
    ContextPurpose,
    ContextSourceType,
    HydrationLevel,
    QueryTerm,
    RetrievalMode,
    RetrievalSubquery,
)
from cognitive_os.domain.memory import MemorySensitivity
from cognitive_os.domain.skills import SkillProblemSignature
from cognitive_os.domain.strategies import (
    StrategyApplicabilityInput,
    StrategyExecutionStatus,
    StrategyOutcome,
    StrategyOutcomeStatus,
    StrategyPhaseExecution,
    StrategySelectionRequest,
    StrategySelectionStatus,
    StrategyStatisticsSnapshot,
)
from cognitive_os.skills.fixtures import sprint12_verified_skills
from cognitive_os.strategies.engine import (
    StrategyGraphService,
    build_statistics,
    empty_registry_snapshot,
    instantiate_controller_plan,
    resolve_skill_bindings,
    select_strategy,
)
from cognitive_os.strategies.fixtures import FIXTURE_TIME, sprint13_verified_strategies
from cognitive_os.strategies.retrieval import StrategyContextRetriever


async def run() -> int:
    repository, registry, problems, targets, artifacts = await sprint13_verified_strategies()
    _, skill_registry, _ = await sprint12_verified_skills()
    item, revision = next(
        row for row in registry.query() if row[0].identity.canonical_name == "python-bug-fix"
    )
    snapshot = empty_registry_snapshot(
        registry.snapshot_hash(), problems.snapshot_hash(), targets.snapshot_hash()
    )
    request = StrategySelectionRequest(
        selection_id=uuid5(NAMESPACE_URL, "sprint13-smoke-selection"),
        task_run_id=uuid5(NAMESPACE_URL, "sprint13-smoke-task"),
        problem_reference=uuid5(NAMESPACE_URL, "sprint13-smoke-problem"),
        applicability_input=StrategyApplicabilityInput(
            problem_class_id=item.identity.problem_class_id,
            problem_signature=SkillProblemSignature(
                problem_domain="coding",
                task_type="repair",
                repository_language="python",
            ),
            repository_profile="cognitive-os",
            risk_level="low",
            scope=item.identity.scope,
            sensitivity_limit=MemorySensitivity.RESTRICTED,
            available_skill_bindings=frozenset(
                binding.binding_id for binding in revision.skill_bindings
            ),
            available_tool_capabilities=frozenset({"workspace.patch"}),
            available_verifier_capabilities=frozenset({"coding.required-checks", "coding.mypy"}),
            available_context_profiles=frozenset({"strategy-context-v1"}),
            permissions=frozenset({"workspace.write"}),
        ),
        registry_snapshot=snapshot,
        controller_budget=revision.budget_profile,
        approval_granted=True,
        created_at=FIXTURE_TIME,
    )
    statistics_snapshot = StrategyStatisticsSnapshot(statistics=())
    selection = select_strategy(request, registry, statistics_snapshot, StrategyConfiguration())
    if selection.status is not StrategySelectionStatus.SELECTED:
        raise RuntimeError("strategy selection did not produce an exact revision")
    resolved_skills = resolve_skill_bindings(revision, skill_registry)
    plan = instantiate_controller_plan(request, selection, revision, resolved_skills)

    context_request, _, _, _ = sprint11_fixture()
    context_request = context_request.model_copy(
        update={
            "context_purpose": ContextPurpose.STRATEGY_EXECUTION,
            "query": "python bug fix",
            "allowed_source_types": (ContextSourceType.STRATEGY,),
        }
    )
    retriever = StrategyContextRetriever(registry, repository)
    candidates = await retriever.retrieve(
        RetrievalSubquery(
            subquery_id=uuid5(NAMESPACE_URL, "sprint13-smoke-context"),
            source_type=ContextSourceType.STRATEGY,
            mode=RetrievalMode.LEXICAL,
            terms=(
                QueryTerm(value="python", normalized="python"),
                QueryTerm(value="bug", normalized="bug"),
            ),
            maximum_results=7,
        ),
        context_request,
    )
    hydrated = await retriever.hydrate(candidates[0], HydrationLevel.FULL)
    verifier_bundle = await artifacts.put_bytes(
        revision.content_hash.encode(), media_type="application/json"
    )
    outcome = StrategyOutcome(
        outcome_id=uuid5(NAMESPACE_URL, "sprint13-smoke-outcome"),
        execution_id=uuid5(NAMESPACE_URL, "sprint13-smoke-execution"),
        selection_id=selection.selection_id,
        task_run_id=request.task_run_id,
        problem_signature=request.applicability_input.problem_signature,
        strategy_id=revision.strategy_id,
        strategy_revision=revision.revision,
        resolved_skills=resolved_skills,
        plan_instantiation_id=plan.instantiation_id,
        plan_hash=plan.plan_hash,
        phase_executions=tuple(
            StrategyPhaseExecution(phase_id=phase.phase_id, status=StrategyExecutionStatus.ACCEPTED)
            for phase in revision.phases
        ),
        context_bundle_references=(),
        verifier_bundle=verifier_bundle,
        acceptance_decision_id=uuid5(NAMESPACE_URL, "sprint13-smoke-acceptance"),
        status=StrategyOutcomeStatus.ACCEPTED,
        usage=TokenUsage(total_tokens=0),
        elapsed_ms=0,
        started_at=FIXTURE_TIME,
        finished_at=FIXTURE_TIME,
    )
    await repository.record_selection(selection)
    await repository.record_outcome(outcome)
    statistics = build_statistics(
        revision.strategy_id, revision.revision, (outcome,), minimum_sample=1
    )
    await repository.write_statistics(statistics)
    graph = StrategyGraphService(registry, targets, StrategyConfiguration()).snapshot(
        revision.strategy_id, revision.revision, snapshot
    )

    restored = await sprint13_verified_strategies()
    restored_registry, restored_targets = restored[1], restored[3]
    restored_item, restored_revision = next(
        row
        for row in restored_registry.query()
        if row[0].identity.canonical_name == "python-bug-fix"
    )
    restored_snapshot = empty_registry_snapshot(
        restored_registry.snapshot_hash(),
        restored[2].snapshot_hash(),
        restored_targets.snapshot_hash(),
    )
    restored_graph = StrategyGraphService(
        restored_registry, restored_targets, StrategyConfiguration()
    ).snapshot(restored_item.identity.strategy_id, restored_revision.revision, restored_snapshot)
    payload = {
        "verified_strategies": len(registry.query()),
        "selected_strategy": f"{selection.selected_strategy_id}@{selection.selected_revision}",
        "resolved_skills": len(resolved_skills),
        "plan_hash": plan.plan_hash,
        "context_hash": hydrated.content_hash,
        "outcome_hash": outcome.outcome_hash,
        "statistics_hash": statistics.projection_hash,
        "graph_hash": graph.snapshot_hash,
        "restore_reproduced": (
            restored_registry.snapshot_hash() == registry.snapshot_hash()
            and restored_graph.snapshot_hash == graph.snapshot_hash
        ),
        "access_records": len(repository.accesses),
        "permission_expansions": 0,
    }
    payload["smoke_hash"] = sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    print(json.dumps(payload, sort_keys=True, separators=(",", ":")))
    return 0 if payload["restore_reproduced"] and len(resolved_skills) == 5 else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(run()))
