"""Bounded execution of strategy plans through the host-controlled phase port."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from datetime import datetime
from uuid import UUID

from cognitive_os.application.ports.strategy_executor import StrategyExecutorPort
from cognitive_os.config.strategy_config import StrategyConfiguration
from cognitive_os.domain.common import utc_now
from cognitive_os.domain.strategies import (
    StrategyExecutionRequest,
    StrategyExecutionResult,
    StrategyExecutionStatus,
    StrategyOutcome,
    StrategyPhaseExecution,
    StrategyPlanInstantiation,
    StrategyRevision,
    StrategyStatus,
    StrategyTargetType,
)
from cognitive_os.strategies.engine import StrategyRegistry
from cognitive_os.strategies.errors import StrategyPolicyError


def resolve_strategy_fallback(
    revision: StrategyRevision,
    registry: StrategyRegistry,
    *,
    depth: int,
    configuration: StrategyConfiguration,
) -> StrategyRevision | None:
    if depth >= configuration.maximum_strategy_fallback_depth:
        raise StrategyPolicyError("strategy fallback depth exhausted")
    if not revision.fallback_strategy_refs:
        return None
    target = revision.fallback_strategy_refs[0]
    if target.target_type is not StrategyTargetType.STRATEGY_REVISION:
        raise StrategyPolicyError("strategy fallback target must be an exact strategy revision")
    try:
        fallback = registry.resolve(UUID(target.target_id), int(target.target_revision))
    except (TypeError, ValueError) as error:
        raise StrategyPolicyError("strategy fallback target is invalid") from error
    if fallback.status is not StrategyStatus.VERIFIED:
        raise StrategyPolicyError("strategy fallback is not verified")
    return fallback


class StrategyExecutionService:
    def __init__(
        self,
        executor: StrategyExecutorPort,
        configuration: StrategyConfiguration,
        *,
        clock: Callable[[], datetime] = utc_now,
    ) -> None:
        self._executor = executor
        self._configuration = configuration
        self._clock = clock

    async def execute(
        self,
        request: StrategyExecutionRequest,
        plan: StrategyPlanInstantiation,
        revision: StrategyRevision,
        *,
        outcome: StrategyOutcome | None = None,
        completed: tuple[StrategyPhaseExecution, ...] = (),
        cancellation: asyncio.Event | None = None,
    ) -> StrategyExecutionResult:
        if (
            request.selection.selected_strategy_id != revision.strategy_id
            or request.selection.selected_revision != revision.revision
            or plan.strategy_id != revision.strategy_id
            or plan.strategy_revision != revision.revision
        ):
            raise StrategyPolicyError("execution requires one exact selected strategy revision")
        started = self._clock()
        results = list(completed)
        phases = sorted(revision.phases, key=lambda item: (item.sequence, item.phase_id))
        index = len(completed)
        visits = len(completed)
        maximum_visits = len(phases) * (revision.repair_policy.maximum_repairs + 1)
        by_id = {phase.phase_id: position for position, phase in enumerate(phases)}
        terminal: StrategyExecutionStatus | None = None
        while index < len(phases):
            if cancellation is not None and cancellation.is_set():
                terminal = StrategyExecutionStatus.CANCELLED
                break
            visits += 1
            if visits > maximum_visits or visits > self._configuration.maximum_plan_steps:
                terminal = StrategyExecutionStatus.FAILED
                break
            phase = phases[index]
            result = await self._executor.execute_phase(request, plan, phase)
            if result.phase_id != phase.phase_id:
                raise StrategyPolicyError("phase executor returned another strategy phase")
            results.append(result)
            if result.status in {
                StrategyExecutionStatus.FAILED,
                StrategyExecutionStatus.POLICY_DENIED,
                StrategyExecutionStatus.CANCELLED,
                StrategyExecutionStatus.REJECTED,
                StrategyExecutionStatus.UNVERIFIABLE,
            }:
                terminal = result.status
                break
            if result.branch_decision is not None:
                branch = next(
                    (
                        value
                        for value in revision.branches
                        if value.branch_id == result.branch_decision.branch_id
                        and value.source_phase_id == phase.phase_id
                        and value.target_phase_id == result.branch_decision.target_phase_id
                    ),
                    None,
                )
                if branch is None:
                    raise StrategyPolicyError("phase executor returned an invalid branch")
                index = by_id[branch.target_phase_id]
            else:
                index += 1
        if terminal is None:
            terminal = (
                StrategyExecutionStatus.ACCEPTED
                if outcome is not None
                else StrategyExecutionStatus.UNVERIFIABLE
            )
        if terminal is StrategyExecutionStatus.ACCEPTED and (
            outcome is None
            or outcome.execution_id != request.execution_id
            or outcome.plan_instantiation_id != plan.instantiation_id
        ):
            raise StrategyPolicyError(
                "accepted execution requires matching host acceptance evidence"
            )
        finished = self._clock()
        return StrategyExecutionResult(
            execution_id=request.execution_id,
            strategy_id=revision.strategy_id,
            strategy_revision=revision.revision,
            task_run_id=request.task_run_id,
            status=terminal,
            plan_instantiation=plan,
            phase_executions=tuple(results),
            outcome=outcome if terminal is StrategyExecutionStatus.ACCEPTED else None,
            failure=(
                "strategy_execution_not_accepted"
                if terminal
                not in {StrategyExecutionStatus.ACCEPTED, StrategyExecutionStatus.CANCELLED}
                else None
            ),
            started_at=started,
            finished_at=finished,
        )
