import hashlib
from uuid import UUID, uuid4

import pytest

from cognitive_os.application.ports.controller import (
    ContinueControllerRequest,
    StartControllerRequest,
)
from cognitive_os.application.services.acceptance_service import AcceptancePolicyService
from cognitive_os.application.services.clarification_service import ClarificationService
from cognitive_os.application.services.cognitive_controller import (
    ActionOutcome,
    BoundedCognitiveController,
)
from cognitive_os.application.services.controller_recovery import ControllerRecoveryService
from cognitive_os.application.services.controller_verification import ControllerVerificationService
from cognitive_os.application.services.minimal_acceptance import MinimalAcceptanceService
from cognitive_os.application.services.verification_service import VerificationService
from cognitive_os.config.controller_config import ControllerConfiguration
from cognitive_os.domain.common import ActorRef, ArtifactRef, utc_now
from cognitive_os.domain.controller import ControllerActionType, ControllerBudget, ControllerState
from cognitive_os.domain.enums import ActorType, RiskLevel
from cognitive_os.domain.execution import ExecutionPlan, PlanStepDefinition
from cognitive_os.domain.planning import ControllerExecutionPlan, ControllerStepAction
from cognitive_os.domain.problems import (
    AcceptanceCriterion,
    ClarificationQuestion,
    CriterionType,
    ProblemDomain,
    ProblemGoal,
    ProblemOutputRequirement,
    ProblemRepresentation,
)
from cognitive_os.events.controller_event_service import ControllerEventService
from cognitive_os.events.storage import AppendResult, StoredEvent
from cognitive_os.events.verifier_event_service import VerifierEventService
from cognitive_os.verification.factory import build_builtin_registry


class MemoryEventStore:
    def __init__(self) -> None:
        self.events: list[StoredEvent] = []

    async def append(self, events, *, expected_version):
        event = events[0]
        current = len([item for item in self.events if item.envelope.stream_id == event.stream_id])
        if current != expected_version:
            raise RuntimeError("expected-version conflict")
        stored = StoredEvent(
            global_position=len(self.events) + 1, stored_at=utc_now(), envelope=event
        )
        self.events.append(stored)
        return AppendResult(
            stream_id=event.stream_id,
            previous_stream_version=current,
            current_stream_version=event.stream_version,
            event_ids=(event.event_id,),
            global_positions=(stored.global_position,),
            stored_at=stored.stored_at,
        )

    async def read_stream(self, stream_id, *, from_version=1, to_version=None, limit=None):
        values = [
            item
            for item in self.events
            if item.envelope.stream_id == stream_id and item.envelope.stream_version >= from_version
        ]
        if to_version is not None:
            values = [item for item in values if item.envelope.stream_version <= to_version]
        return tuple(values[:limit] if limit else values)

    async def get_stream_version(self, stream_id):
        values = [item for item in self.events if item.envelope.stream_id == stream_id]
        return values[-1].envelope.stream_version if values else None


class MemoryArtifactStore:
    async def put_bytes(self, data, *, media_type, source_event_id=None):
        return ArtifactRef(
            artifact_id=uuid4(),
            media_type=media_type,
            content_hash=hashlib.sha256(data).hexdigest(),
            size_bytes=len(data),
            storage_key=f"checkpoint/{uuid4()}",
            created_at=utc_now(),
        )


class ProblemEngine:
    def __init__(self, step_id: UUID) -> None:
        self.step_id = step_id

    async def represent(self, seed):
        return ProblemRepresentation(
            problem_id=uuid4(),
            task_id=seed.task_id,
            task_run_id=seed.task_run_id,
            domain=ProblemDomain.GENERIC,
            title=seed.title,
            summary="Bounded offline task",
            goals=(ProblemGoal(goal_id=uuid4(), description="Complete one step", priority=1),),
            output_requirements=(
                ProblemOutputRequirement(
                    requirement_id=uuid4(), output_type="text", description="Result"
                ),
            ),
            acceptance_criteria=(
                AcceptanceCriterion(
                    criterion_id=uuid4(),
                    description="Required step completes",
                    criterion_type=CriterionType.STEP_COMPLETED,
                    required=True,
                    weight=1,
                    configuration={"step_id": str(self.step_id)},
                ),
            ),
            risk_level=RiskLevel.LOW,
            confidence=1,
            created_at=utc_now(),
            revision=1,
            source_request_hash=seed.request_hash,
        )

    async def revise(self, current, clarification):
        return current.model_copy(
            update={"revision": current.revision + 1, "clarification_questions": ()}
        )


class ClarifyingProblemEngine(ProblemEngine):
    async def represent(self, seed):
        value = await super().represent(seed)
        question = ClarificationQuestion(
            question_id=uuid4(),
            question="How many?",
            reason="A required value is missing",
            answer_schema={"type": "integer", "minimum": 1},
            related_goal_ids=(value.goals[0].goal_id,),
        )
        return value.model_copy(update={"clarification_questions": (question,)})


class Planner:
    def __init__(self, task_run_id, step_id) -> None:
        actor = ActorRef(actor_type=ActorType.SYSTEM, actor_id="test")
        structural = ExecutionPlan(
            plan_id=uuid4(),
            task_run_id=task_run_id,
            version=1,
            created_at=utc_now(),
            created_by=actor,
            steps=(
                PlanStepDefinition(
                    step_id=step_id,
                    sequence=1,
                    step_type="provider",
                    title="Respond",
                ),
            ),
        )
        self.plan = ControllerExecutionPlan(
            plan=structural,
            actions=(
                ControllerStepAction(
                    step_id=step_id,
                    action_type=ControllerActionType.PROVIDER,
                    provider_id="replay",
                    provider_instructions="Return a deterministic response.",
                ),
            ),
            created_at=utc_now(),
            created_by=actor,
        )

    async def create_plan(self, problem, budget):
        return self.plan

    async def revise_plan(self, current, reason, budget):
        return current.model_copy(
            update={"plan": current.plan.model_copy(update={"version": current.plan.version + 1})}
        )


class Executor:
    async def execute(self, action, request):
        return ActionOutcome(succeeded=True, output="done")


class FlakyExecutor:
    def __init__(self) -> None:
        self.calls = 0

    async def execute(self, action, request):
        self.calls += 1
        return ActionOutcome(succeeded=self.calls > 1, output="repaired")


def config() -> ControllerConfiguration:
    return ControllerConfiguration(
        default_provider_id="replay",
        problem_representation_provider_id="replay",
        planning_provider_id="replay",
        budgets=ControllerBudget(
            maximum_provider_calls=4,
            maximum_tool_calls=2,
            maximum_plan_steps=4,
            maximum_repair_cycles=2,
            maximum_clarification_cycles=2,
            maximum_elapsed_seconds=30,
        ),
    )


@pytest.mark.asyncio
async def test_bounded_controller_completes_and_replays() -> None:
    task_id, task_run_id, step_id = uuid4(), uuid4(), uuid4()
    store = MemoryEventStore()
    recovery = ControllerRecoveryService(store)
    controller = BoundedCognitiveController(
        problem_engine=ProblemEngine(step_id),
        planning=Planner(task_run_id, step_id),
        action_executor=Executor(),
        acceptance=MinimalAcceptanceService(),
        events=ControllerEventService(store),
        recovery=recovery,
        configuration=config(),
        provider_ids=("replay",),
    )
    result = await controller.start(
        StartControllerRequest(
            task_id=task_id,
            task_run_id=task_run_id,
            correlation_id=uuid4(),
            title="Offline task",
            raw_request="Complete one deterministic step.",
        )
    )
    assert result.state is ControllerState.COMPLETED


@pytest.mark.asyncio
async def test_controller_uses_registered_verifier_and_persists_acceptance() -> None:
    task_id, task_run_id, step_id = uuid4(), uuid4(), uuid4()
    store = MemoryEventStore()
    registry = build_builtin_registry()
    verification = ControllerVerificationService(
        VerificationService(registry, VerifierEventService(store)),
        AcceptancePolicyService(),
    )
    controller = BoundedCognitiveController(
        problem_engine=ProblemEngine(step_id),
        planning=Planner(task_run_id, step_id),
        action_executor=Executor(),
        acceptance=MinimalAcceptanceService(),
        verification=verification,
        events=ControllerEventService(store),
        recovery=ControllerRecoveryService(store),
        configuration=config(),
        provider_ids=("replay",),
    )
    result = await controller.start(
        StartControllerRequest(
            task_id=task_id,
            task_run_id=task_run_id,
            correlation_id=uuid4(),
            title="Verified offline task",
            raw_request="Complete one deterministic verified step.",
        )
    )
    event_types = [item.envelope.event_type for item in store.events]
    assert result.state is ControllerState.COMPLETED
    assert "verifier.started" in event_types
    assert "verifier.completed" in event_types
    assert "controller.acceptance_decision_recorded" in event_types
    assert result.acceptance_decision and result.acceptance_decision.accepted
    assert (await controller.replay(task_run_id)).state is ControllerState.COMPLETED
    event_types = [item.envelope.event_type for item in store.events]
    assert event_types.count("controller.state_changed") == 6
    decision_index = event_types.index("controller.decision_recorded")
    assert "controller.state_changed" in event_types[decision_index + 1 :]


@pytest.mark.asyncio
async def test_clarification_token_is_single_use_and_resume_revises_problem() -> None:
    task_id, task_run_id, step_id = uuid4(), uuid4(), uuid4()
    store = MemoryEventStore()
    controller = BoundedCognitiveController(
        problem_engine=ClarifyingProblemEngine(step_id),
        planning=Planner(task_run_id, step_id),
        action_executor=Executor(),
        acceptance=MinimalAcceptanceService(),
        events=ControllerEventService(store),
        recovery=ControllerRecoveryService(store),
        configuration=config(),
        clarification=ClarificationService(config()),
        artifact_store=MemoryArtifactStore(),
    )
    waiting = await controller.start(
        StartControllerRequest(
            task_id=task_id,
            task_run_id=task_run_id,
            correlation_id=uuid4(),
            title="Clarify",
            raw_request="Ask for a required number.",
        )
    )
    assert waiting.state is ControllerState.WAITING_FOR_CLARIFICATION
    assert waiting.continuation_token
    question_id = waiting.problem_representation.clarification_questions[0].question_id
    resumed = await controller.continue_run(
        ContinueControllerRequest(
            task_run_id=task_run_id,
            continuation_token=waiting.continuation_token,
            answers={str(question_id): 2},
        )
    )
    assert resumed.state is ControllerState.READY
    assert resumed.problem_representation.revision == 2
    with pytest.raises(ValueError, match="consumed"):
        await controller.continue_run(
            ContinueControllerRequest(
                task_run_id=task_run_id,
                continuation_token=waiting.continuation_token,
                answers={str(question_id): 2},
            )
        )


@pytest.mark.asyncio
async def test_failed_structural_acceptance_runs_one_bounded_repair() -> None:
    task_id, task_run_id, step_id = uuid4(), uuid4(), uuid4()
    store = MemoryEventStore()
    executor = FlakyExecutor()
    controller = BoundedCognitiveController(
        problem_engine=ProblemEngine(step_id),
        planning=Planner(task_run_id, step_id),
        action_executor=executor,
        acceptance=MinimalAcceptanceService(),
        events=ControllerEventService(store),
        recovery=ControllerRecoveryService(store),
        configuration=config(),
    )
    result = await controller.start(
        StartControllerRequest(
            task_id=task_id,
            task_run_id=task_run_id,
            correlation_id=uuid4(),
            title="Repair",
            raw_request="Repair one failed structural result.",
        )
    )
    assert result.state is ControllerState.COMPLETED
    assert result.usage.repair_cycles == 1
    assert executor.calls == 2
    assert any(item.envelope.event_type == "plan.revised" for item in store.events)
