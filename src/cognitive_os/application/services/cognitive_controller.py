"""First bounded, sequential, event-sourced Cognitive Controller loop."""

from __future__ import annotations

from dataclasses import dataclass
from time import monotonic
from typing import Protocol
from uuid import UUID

from cognitive_os.application.ports.artifact_store import ArtifactStorePort
from cognitive_os.application.ports.controller import (
    ContinueControllerRequest,
    ControllerRunResult,
    StartControllerRequest,
)
from cognitive_os.application.ports.planning import PlanningPort
from cognitive_os.application.ports.problem_representation import ProblemRepresentationPort
from cognitive_os.application.services.clarification_service import ClarificationService
from cognitive_os.application.services.controller_recovery import ControllerRecoveryService
from cognitive_os.application.services.controller_verification import ControllerVerificationService
from cognitive_os.application.services.minimal_acceptance import MinimalAcceptanceService
from cognitive_os.config.controller_config import ControllerConfiguration
from cognitive_os.controller.actions import select_next_action
from cognitive_os.controller.budget import BudgetLedger
from cognitive_os.controller.checkpoint import CheckpointCodec
from cognitive_os.controller.machine import ControllerStateMachine, StateTransition
from cognitive_os.domain.common import ErrorInfo, utc_now
from cognitive_os.domain.controller import (
    ControllerDecision,
    ControllerDecisionType,
    ControllerState,
    ControllerStateSnapshot,
    ControllerUsage,
)
from cognitive_os.domain.enums import RiskLevel, StepStatus
from cognitive_os.domain.execution import ExecutionStep
from cognitive_os.domain.identifiers import new_id
from cognitive_os.domain.planning import ControllerExecutionPlan, ControllerStepAction
from cognitive_os.domain.problems import ProblemRepresentation
from cognitive_os.domain.tools import ToolDescriptor
from cognitive_os.events.base import EventPayload
from cognitive_os.events.controller_event_service import ControllerEventService
from cognitive_os.events.controller_events import (
    AcceptanceDecisionRecorded,
    ControllerCancelled,
    ControllerCheckpointCreated,
    ControllerClarificationProvided,
    ControllerClarificationRequested,
    ControllerContinuationConsumed,
    ControllerContinuationIssued,
    ControllerDecisionRecorded,
    ControllerStateChanged,
    ProblemRepresentationCreated,
    ProblemRepresentationRevised,
)
from cognitive_os.events.execution_events import (
    ExecutionStepCompleted,
    ExecutionStepCreated,
    ExecutionStepFailed,
    ExecutionStepStarted,
    PlanCreated,
    PlanRevised,
)
from cognitive_os.problem.normalization import normalize_problem
from cognitive_os.verification.minimal import MinimalAcceptanceDecision


@dataclass(frozen=True)
class ActionOutcome:
    succeeded: bool
    output: object = None
    tool_call_id: UUID | None = None
    warning: str | None = None


class ControllerActionExecutor(Protocol):
    async def execute(
        self, action: ControllerStepAction, request: StartControllerRequest
    ) -> ActionOutcome: ...


class BoundedCognitiveController:
    def __init__(
        self,
        *,
        problem_engine: ProblemRepresentationPort,
        planning: PlanningPort,
        action_executor: ControllerActionExecutor,
        acceptance: MinimalAcceptanceService,
        verification: ControllerVerificationService | None = None,
        events: ControllerEventService,
        recovery: ControllerRecoveryService,
        configuration: ControllerConfiguration,
        clarification: ClarificationService | None = None,
        artifact_store: ArtifactStorePort | None = None,
        provider_ids: tuple[str, ...] = (),
        tool_descriptors: tuple[ToolDescriptor, ...] = (),
    ) -> None:
        self._problem_engine = problem_engine
        self._planning = planning
        self._executor = action_executor
        self._acceptance = acceptance
        self._verification = verification
        self._events = events
        self._recovery = recovery
        self._configuration = configuration
        self._clarification = clarification
        self._artifact_store = artifact_store
        self._provider_ids = provider_ids
        self._tool_descriptors = tool_descriptors
        self._plans: dict[UUID, ControllerExecutionPlan] = {}
        self._problems: dict[UUID, ProblemRepresentation] = {}

    async def start(self, request: StartControllerRequest) -> ControllerRunResult:
        now = utc_now()
        usage = ControllerUsage(started_at=now, last_updated_at=now)
        ledger = BudgetLedger(self._configuration.budgets, usage)
        state = ControllerState.RECEIVED
        version = 0
        started = monotonic()
        warnings: list[str] = []

        async def transition(target: ControllerState, reason: str) -> None:
            nonlocal state, version
            decision_id = new_id()
            change = StateTransition(state, target, reason, decision_id, version)
            ControllerStateMachine.require_transition(change)
            result = await self._events.append(
                task_run_id=request.task_run_id,
                payload=ControllerStateChanged(
                    previous_state=state,
                    current_state=target,
                    reason=reason,
                    decision_id=decision_id,
                    changed_at=utc_now(),
                ),
                expected_version=version,
                correlation_id=request.correlation_id,
            )
            version = result.current_stream_version
            state = target

        async def create_checkpoint(
            problem: ProblemRepresentation,
            plan: ControllerExecutionPlan | None = None,
        ) -> None:
            nonlocal version
            if self._artifact_store is None:
                return
            snapshot = ControllerStateSnapshot(
                task_run_id=request.task_run_id,
                state=state,
                problem_id=problem.problem_id if problem else None,
                problem_revision=problem.revision if problem else None,
                plan_id=plan.plan.plan_id if plan else None,
                plan_version=plan.plan.version if plan else None,
                usage=ledger.usage,
                repair_cycle=ledger.usage.repair_cycles,
                clarification_cycle=ledger.usage.clarification_cycles,
                last_stream_version=version,
                updated_at=utc_now(),
            )
            checkpoint = CheckpointCodec.create(
                checkpoint_id=new_id(),
                task_run_id=request.task_run_id,
                controller_state=snapshot,
                problem_representation=problem,
                controller_plan=plan,
                usage=ledger.usage,
                event_stream_version=version,
            )
            artifact = await self._artifact_store.put_bytes(
                CheckpointCodec.serialize(checkpoint),
                media_type="application/vnd.cognitive-os.controller-checkpoint+json",
            )
            result = await self._events.append(
                task_run_id=request.task_run_id,
                payload=ControllerCheckpointCreated(
                    checkpoint_id=checkpoint.checkpoint_id,
                    checkpoint_artifact=artifact,
                    event_stream_version=version,
                    content_hash=checkpoint.content_hash,
                ),
                expected_version=version,
                correlation_id=request.correlation_id,
            )
            version = result.current_stream_version

        async def execute_repair_actions(
            repair_plan: ControllerExecutionPlan,
            completed: set[UUID],
            failed: set[UUID],
            successful_tools: set[str],
            outputs: dict[str, object],
        ) -> bool:
            nonlocal version
            iterations = 0
            while len((completed | failed) & {s.step_id for s in repair_plan.plan.steps}) < len(
                repair_plan.plan.steps
            ):
                iterations += 1
                if iterations > self._configuration.maximum_controller_iterations:
                    return False
                if not ledger.evaluate(elapsed_seconds=monotonic() - started).allowed:
                    return False
                action = select_next_action(
                    repair_plan,
                    completed=frozenset(completed),
                    failed=frozenset(failed),
                )
                if action is None:
                    return False
                decision_type = (
                    ControllerDecisionType.EXECUTE_TOOL
                    if action.action_type.value == "tool"
                    else ControllerDecisionType.EXECUTE_PROVIDER
                )
                result = await self._events.append(
                    task_run_id=request.task_run_id,
                    payload=ControllerDecisionRecorded(
                        decision=ControllerDecision(
                            decision_id=new_id(),
                            task_run_id=request.task_run_id,
                            current_state=ControllerState.EXECUTING,
                            decision_type=decision_type,
                            reason="repair scheduler selected the next ready step",
                            selected_step_id=action.step_id,
                            selected_provider_id=action.provider_id,
                            selected_tool_id=action.tool_id,
                            created_at=utc_now(),
                        )
                    ),
                    expected_version=version,
                    correlation_id=request.correlation_id,
                )
                version = result.current_stream_version
                result = await self._events.append(
                    task_run_id=request.task_run_id,
                    payload=ExecutionStepStarted(
                        step_id=action.step_id,
                        started_at=utc_now(),
                        attempt=ledger.usage.repair_cycles + 1,
                    ),
                    expected_version=version,
                    correlation_id=request.correlation_id,
                )
                version = result.current_stream_version
                outcome = await self._executor.execute(action, request)
                ledger.record(plan_steps_started=1)
                if action.action_type.value == "tool":
                    ledger.record(tool_calls=1)
                elif action.action_type.value == "provider":
                    ledger.record(provider_calls=1)
                if outcome.succeeded:
                    completed.add(action.step_id)
                    failed.discard(action.step_id)
                    ledger.record(plan_steps_completed=1)
                    outputs[str(action.step_id)] = outcome.output
                    if outcome.tool_call_id:
                        successful_tools.add(str(outcome.tool_call_id))
                    terminal_payload: EventPayload = ExecutionStepCompleted(
                        step_id=action.step_id, finished_at=utc_now()
                    )
                else:
                    failed.add(action.step_id)
                    terminal_payload = ExecutionStepFailed(
                        step_id=action.step_id,
                        finished_at=utc_now(),
                        error=ErrorInfo(
                            code="controller_repair_action_failed",
                            message="planned repair action failed",
                        ),
                    )
                result = await self._events.append(
                    task_run_id=request.task_run_id,
                    payload=terminal_payload,
                    expected_version=version,
                    correlation_id=request.correlation_id,
                )
                version = result.current_stream_version
                await create_checkpoint(problem, repair_plan)
                if outcome.warning:
                    warnings.append(outcome.warning)
            return True

        await transition(ControllerState.REPRESENTING_PROBLEM, "normalize and represent task")
        seed = normalize_problem(
            task_id=request.task_id,
            task_run_id=request.task_run_id,
            title=request.title,
            raw_request=request.raw_request,
            risk_level=RiskLevel.LOW,
            tools=self._tool_descriptors,
            provider_ids=self._provider_ids,
        )
        if not ledger.evaluate(elapsed_seconds=monotonic() - started).allowed:
            await transition(ControllerState.BUDGET_EXHAUSTED, "budget exhausted")
            return self._result(request.task_run_id, state, ledger.usage, version)
        problem = await self._problem_engine.represent(seed)
        ledger.record(provider_calls=1)
        result = await self._events.append(
            task_run_id=request.task_run_id,
            payload=ProblemRepresentationCreated(representation=problem),
            expected_version=version,
            correlation_id=request.correlation_id,
        )
        version = result.current_stream_version
        self._problems[request.task_run_id] = problem
        await create_checkpoint(problem)
        if problem.requires_clarification():
            if self._clarification is None or self._artifact_store is None:
                raise RuntimeError(
                    "clarification waits require clarification and artifact services"
                )
            clarification = self._clarification.create_request(problem)
            result = await self._events.append(
                task_run_id=request.task_run_id,
                payload=ControllerClarificationRequested(request=clarification),
                expected_version=version,
                correlation_id=request.correlation_id,
            )
            version = result.current_stream_version
            await transition(
                ControllerState.WAITING_FOR_CLARIFICATION,
                "problem representation requires clarification",
            )
            snapshot = ControllerStateSnapshot(
                task_run_id=request.task_run_id,
                state=state,
                problem_id=problem.problem_id,
                problem_revision=problem.revision,
                usage=ledger.usage,
                clarification_cycle=1,
                last_stream_version=version,
                updated_at=utc_now(),
            )
            checkpoint = CheckpointCodec.create(
                checkpoint_id=new_id(),
                task_run_id=request.task_run_id,
                controller_state=snapshot,
                problem_representation=problem,
                controller_plan=None,
                usage=ledger.usage,
                event_stream_version=version,
            )
            artifact = await self._artifact_store.put_bytes(
                CheckpointCodec.serialize(checkpoint),
                media_type="application/vnd.cognitive-os.controller-checkpoint+json",
            )
            result = await self._events.append(
                task_run_id=request.task_run_id,
                payload=ControllerCheckpointCreated(
                    checkpoint_id=checkpoint.checkpoint_id,
                    checkpoint_artifact=artifact,
                    event_stream_version=checkpoint.event_stream_version,
                    content_hash=checkpoint.content_hash,
                ),
                expected_version=version,
                correlation_id=request.correlation_id,
            )
            version = result.current_stream_version
            plaintext, record = self._clarification.issue_continuation(
                task_run_id=request.task_run_id,
                checkpoint_id=checkpoint.checkpoint_id,
                event_stream_version=version + 1,
            )
            result = await self._events.append(
                task_run_id=request.task_run_id,
                payload=ControllerContinuationIssued(record=record),
                expected_version=version,
                correlation_id=request.correlation_id,
            )
            version = result.current_stream_version
            return self._result(
                request.task_run_id,
                state,
                ledger.usage,
                version,
                problem=problem,
                continuation_token=plaintext,
            )
        await transition(ControllerState.READY, "problem representation is executable")
        await transition(ControllerState.PLANNING, "create bounded execution plan")
        plan = await self._planning.create_plan(problem, self._configuration.budgets)
        if len(plan.plan.steps) > self._configuration.budgets.maximum_plan_steps:
            await transition(ControllerState.BUDGET_EXHAUSTED, "plan-step budget exhausted")
            return self._result(request.task_run_id, state, ledger.usage, version, problem=problem)
        result = await self._events.append(
            task_run_id=request.task_run_id,
            payload=PlanCreated(plan=plan.plan),
            expected_version=version,
            correlation_id=request.correlation_id,
        )
        version = result.current_stream_version
        for step in plan.plan.steps:
            result = await self._events.append(
                task_run_id=request.task_run_id,
                payload=ExecutionStepCreated(
                    step=ExecutionStep(
                        step_id=step.step_id,
                        task_run_id=request.task_run_id,
                        plan_id=plan.plan.plan_id,
                        status=StepStatus.PENDING,
                    )
                ),
                expected_version=version,
                correlation_id=request.correlation_id,
            )
            version = result.current_stream_version
        await create_checkpoint(problem, plan)
        self._plans[request.task_run_id] = plan
        await transition(ControllerState.EXECUTING, "execute one ready step at a time")
        completed: set[UUID] = set()
        failed: set[UUID] = set()
        successful_tools: set[str] = set()
        outputs: dict[str, object] = {}
        iterations = 0
        while len(completed | failed) < len(plan.plan.steps):
            iterations += 1
            if iterations > self._configuration.maximum_controller_iterations:
                await transition(ControllerState.BUDGET_EXHAUSTED, "controller iteration ceiling")
                return self._result(
                    request.task_run_id,
                    state,
                    ledger.usage,
                    version,
                    problem=problem,
                    plan=plan,
                    warnings=tuple(warnings),
                )
            decision = ledger.evaluate(elapsed_seconds=monotonic() - started)
            if not decision.allowed:
                await transition(ControllerState.BUDGET_EXHAUSTED, decision.reason)
                return self._result(
                    request.task_run_id,
                    state,
                    ledger.usage,
                    version,
                    problem=problem,
                    plan=plan,
                    warnings=tuple(warnings),
                )
            action = select_next_action(
                plan, completed=frozenset(completed), failed=frozenset(failed)
            )
            if action is None:
                await transition(ControllerState.FAILED, "plan made no progress")
                return self._result(
                    request.task_run_id,
                    state,
                    ledger.usage,
                    version,
                    problem=problem,
                    plan=plan,
                    error="plan made no progress",
                )
            decision_type = (
                ControllerDecisionType.EXECUTE_TOOL
                if action.action_type.value == "tool"
                else ControllerDecisionType.EXECUTE_PROVIDER
            )
            recorded = await self._events.append(
                task_run_id=request.task_run_id,
                payload=ControllerDecisionRecorded(
                    decision=ControllerDecision(
                        decision_id=new_id(),
                        task_run_id=request.task_run_id,
                        current_state=state,
                        decision_type=decision_type,
                        reason="deterministic scheduler selected the next ready step",
                        selected_step_id=action.step_id,
                        selected_provider_id=action.provider_id,
                        selected_tool_id=action.tool_id,
                        created_at=utc_now(),
                    )
                ),
                expected_version=version,
                correlation_id=request.correlation_id,
            )
            version = recorded.current_stream_version
            result = await self._events.append(
                task_run_id=request.task_run_id,
                payload=ExecutionStepStarted(
                    step_id=action.step_id, started_at=utc_now(), attempt=1
                ),
                expected_version=version,
                correlation_id=request.correlation_id,
            )
            version = result.current_stream_version
            outcome = await self._executor.execute(action, request)
            ledger.record(plan_steps_started=1)
            if action.action_type.value == "tool":
                ledger.record(tool_calls=1)
            elif action.action_type.value == "provider":
                ledger.record(provider_calls=1)
            if outcome.succeeded:
                completed.add(action.step_id)
                ledger.record(plan_steps_completed=1)
                outputs[str(action.step_id)] = outcome.output
                if outcome.tool_call_id:
                    successful_tools.add(str(outcome.tool_call_id))
                result = await self._events.append(
                    task_run_id=request.task_run_id,
                    payload=ExecutionStepCompleted(step_id=action.step_id, finished_at=utc_now()),
                    expected_version=version,
                    correlation_id=request.correlation_id,
                )
            else:
                failed.add(action.step_id)
                result = await self._events.append(
                    task_run_id=request.task_run_id,
                    payload=ExecutionStepFailed(
                        step_id=action.step_id,
                        finished_at=utc_now(),
                        error=ErrorInfo(
                            code="controller_action_failed",
                            message="planned controller action failed",
                        ),
                    ),
                    expected_version=version,
                    correlation_id=request.correlation_id,
                )
            version = result.current_stream_version
            await create_checkpoint(problem, plan)
            if outcome.warning:
                warnings.append(outcome.warning)
        await transition(ControllerState.VERIFYING, "run deterministic minimal acceptance")
        if self._verification is not None:
            verification_outcome = await self._verification.verify(
                problem,
                completed_step_ids=frozenset(str(item) for item in completed),
                successful_tool_call_ids=frozenset(successful_tools),
                outputs=outputs,
                repair_budget_remaining=ledger.usage.repair_cycles
                < self._configuration.budgets.maximum_repair_cycles,
                maximum_calls=max(
                    0,
                    self._configuration.budgets.maximum_verifier_calls
                    - ledger.usage.verifier_calls,
                ),
            )
            ledger.record(
                verifier_calls=verification_outcome.verifier_calls,
                verification_seconds=verification_outcome.elapsed_seconds,
            )
            result = await self._events.append(
                task_run_id=request.task_run_id,
                payload=AcceptanceDecisionRecorded(decision=verification_outcome.decision),
                expected_version=version,
                correlation_id=request.correlation_id,
            )
            version = result.current_stream_version
            acceptance = verification_outcome.minimal
        else:
            acceptance = self._acceptance.evaluate(
                problem.acceptance_criteria,
                completed_step_ids=frozenset(str(item) for item in completed),
                successful_tool_call_ids=frozenset(successful_tools),
                outputs=outputs,
            )
        if acceptance.accepted:
            await transition(ControllerState.COMPLETED, acceptance.decision_reason)
        else:
            while (
                not acceptance.accepted
                and ledger.usage.repair_cycles < self._configuration.budgets.maximum_repair_cycles
            ):
                decision = ledger.evaluate(elapsed_seconds=monotonic() - started)
                if not decision.allowed:
                    await transition(ControllerState.BUDGET_EXHAUSTED, decision.reason)
                    break
                await transition(ControllerState.REPAIRING, acceptance.decision_reason)
                previous_version = plan.plan.version
                plan = await self._planning.revise_plan(
                    plan, acceptance.decision_reason, self._configuration.budgets
                )
                ledger.record(repair_cycles=1, provider_calls=1)
                result = await self._events.append(
                    task_run_id=request.task_run_id,
                    payload=PlanRevised(plan=plan.plan, previous_version=previous_version),
                    expected_version=version,
                    correlation_id=request.correlation_id,
                )
                version = result.current_stream_version
                completed &= {step.step_id for step in plan.plan.steps}
                failed.clear()
                for step in plan.plan.steps:
                    if step.step_id not in completed:
                        result = await self._events.append(
                            task_run_id=request.task_run_id,
                            payload=ExecutionStepCreated(
                                step=ExecutionStep(
                                    step_id=step.step_id,
                                    task_run_id=request.task_run_id,
                                    plan_id=plan.plan.plan_id,
                                    status=StepStatus.PENDING,
                                    attempt=ledger.usage.repair_cycles + 1,
                                )
                            ),
                            expected_version=version,
                            correlation_id=request.correlation_id,
                        )
                        version = result.current_stream_version
                await transition(ControllerState.EXECUTING, "execute bounded repair plan")
                progressed = await execute_repair_actions(
                    plan, completed, failed, successful_tools, outputs
                )
                if not progressed:
                    await transition(ControllerState.FAILED, "repair plan made no progress")
                    break
                await transition(
                    ControllerState.VERIFYING,
                    "verify repaired structural evidence",
                )
                if self._verification is not None:
                    verification_outcome = await self._verification.verify(
                        problem,
                        completed_step_ids=frozenset(str(item) for item in completed),
                        successful_tool_call_ids=frozenset(successful_tools),
                        outputs=outputs,
                        repair_budget_remaining=ledger.usage.repair_cycles
                        < self._configuration.budgets.maximum_repair_cycles,
                        maximum_calls=max(
                            0,
                            self._configuration.budgets.maximum_verifier_calls
                            - ledger.usage.verifier_calls,
                        ),
                    )
                    ledger.record(
                        verifier_calls=verification_outcome.verifier_calls,
                        verification_seconds=verification_outcome.elapsed_seconds,
                    )
                    result = await self._events.append(
                        task_run_id=request.task_run_id,
                        payload=AcceptanceDecisionRecorded(decision=verification_outcome.decision),
                        expected_version=version,
                        correlation_id=request.correlation_id,
                    )
                    version = result.current_stream_version
                    acceptance = verification_outcome.minimal
                else:
                    acceptance = self._acceptance.evaluate(
                        problem.acceptance_criteria,
                        completed_step_ids=frozenset(str(item) for item in completed),
                        successful_tool_call_ids=frozenset(successful_tools),
                        outputs=outputs,
                    )
                if acceptance.accepted:
                    await transition(ControllerState.COMPLETED, acceptance.decision_reason)
                    break
            if state is ControllerState.VERIFYING:
                await transition(ControllerState.FAILED, "repair budget exhausted")
        return self._result(
            request.task_run_id,
            state,
            ledger.usage,
            version,
            problem=problem,
            plan=plan,
            acceptance=acceptance,
            warnings=tuple(warnings),
        )

    async def inspect(self, task_run_id: UUID) -> ControllerStateSnapshot:
        return await self._recovery.replay(task_run_id)

    async def replay(self, task_run_id: UUID) -> ControllerStateSnapshot:
        return await self._recovery.replay(task_run_id)

    async def continue_run(self, request: ContinueControllerRequest) -> ControllerRunResult:
        if self._clarification is None:
            raise RuntimeError("continuation requires a clarification service")
        context = await self._recovery.continuation_context(request.task_run_id)
        response = context.response_from_answers(request.answers)
        self._clarification.validate_response(context.request, response)
        consumed = self._clarification.consume_continuation(
            record=context.token_record,
            plaintext=request.continuation_token,
            task_run_id=request.task_run_id,
            checkpoint_id=context.token_record.checkpoint_id,
            event_stream_version=context.stream_version,
        )
        result = await self._events.append(
            task_run_id=request.task_run_id,
            payload=ControllerClarificationProvided(response=response),
            expected_version=context.stream_version,
            correlation_id=request.task_run_id,
        )
        version = result.current_stream_version
        result = await self._events.append(
            task_run_id=request.task_run_id,
            payload=ControllerContinuationConsumed(
                continuation_id=consumed.continuation_id,
                consumed_at=consumed.consumed_at or utc_now(),
            ),
            expected_version=version,
            correlation_id=request.task_run_id,
        )
        version = result.current_stream_version
        revised = await self._problem_engine.revise(context.problem, response)
        if revised.revision != context.problem.revision + 1:
            raise ValueError("problem representation revision must increase by one")
        result = await self._events.append(
            task_run_id=request.task_run_id,
            payload=ProblemRepresentationRevised(
                problem_id=revised.problem_id,
                previous_revision=context.problem.revision,
                representation=revised,
            ),
            expected_version=version,
            correlation_id=request.task_run_id,
        )
        version = result.current_stream_version
        decision_id = new_id()
        ControllerStateMachine.require_transition(
            StateTransition(
                ControllerState.WAITING_FOR_CLARIFICATION,
                ControllerState.REPRESENTING_PROBLEM,
                "validated clarification response",
                decision_id,
                version,
            )
        )
        result = await self._events.append(
            task_run_id=request.task_run_id,
            payload=ControllerStateChanged(
                previous_state=ControllerState.WAITING_FOR_CLARIFICATION,
                current_state=ControllerState.REPRESENTING_PROBLEM,
                reason="validated clarification response",
                decision_id=decision_id,
                changed_at=utc_now(),
            ),
            expected_version=version,
            correlation_id=request.task_run_id,
        )
        version = result.current_stream_version
        if revised.requires_clarification():
            raise ValueError("revised representation still requires clarification")
        decision_id = new_id()
        result = await self._events.append(
            task_run_id=request.task_run_id,
            payload=ControllerStateChanged(
                previous_state=ControllerState.REPRESENTING_PROBLEM,
                current_state=ControllerState.READY,
                reason="clarification produced an executable representation",
                decision_id=decision_id,
                changed_at=utc_now(),
            ),
            expected_version=version,
            correlation_id=request.task_run_id,
        )
        usage = context.usage.model_copy(
            update={
                "clarification_cycles": context.usage.clarification_cycles + 1,
                "last_updated_at": utc_now(),
            }
        )
        return self._result(
            request.task_run_id,
            ControllerState.READY,
            usage,
            result.current_stream_version,
            problem=revised,
        )

    async def cancel(self, task_run_id: UUID, reason: str) -> ControllerRunResult:
        snapshot = await self._recovery.replay(task_run_id)
        decision_id = new_id()
        transition = StateTransition(
            snapshot.state,
            ControllerState.CANCELLED,
            reason,
            decision_id,
            snapshot.last_stream_version,
        )
        ControllerStateMachine.require_transition(transition)
        result = await self._events.append(
            task_run_id=task_run_id,
            payload=ControllerStateChanged(
                previous_state=snapshot.state,
                current_state=ControllerState.CANCELLED,
                reason=reason,
                decision_id=decision_id,
                changed_at=utc_now(),
            ),
            expected_version=snapshot.last_stream_version,
            correlation_id=task_run_id,
        )
        result = await self._events.append(
            task_run_id=task_run_id,
            payload=ControllerCancelled(
                task_run_id=task_run_id, reason=reason, cancelled_at=utc_now()
            ),
            expected_version=result.current_stream_version,
            correlation_id=task_run_id,
        )
        return self._result(
            task_run_id,
            ControllerState.CANCELLED,
            snapshot.usage,
            result.current_stream_version,
            error=reason,
        )

    @staticmethod
    def _result(
        task_run_id: UUID,
        state: ControllerState,
        usage: ControllerUsage,
        version: int,
        *,
        problem: ProblemRepresentation | None = None,
        plan: ControllerExecutionPlan | None = None,
        acceptance: MinimalAcceptanceDecision | None = None,
        continuation_token: str | None = None,
        warnings: tuple[str, ...] = (),
        error: str | None = None,
    ) -> ControllerRunResult:
        return ControllerRunResult(
            task_run_id=task_run_id,
            state=state,
            problem_representation=problem,
            plan=plan,
            acceptance_decision=acceptance,
            continuation_token=continuation_token,
            usage=usage,
            warnings=warnings,
            error=error,
            last_stream_version=version,
        )
