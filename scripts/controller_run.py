"""Run a bounded credential-free replay-provider controller task."""

import argparse
import asyncio
import json
from pathlib import Path
from uuid import uuid4

from controller_common import build_event_store

from cognitive_os.application.ports.controller import StartControllerRequest
from cognitive_os.application.services.cognitive_controller import (
    ActionOutcome,
    BoundedCognitiveController,
)
from cognitive_os.application.services.controller_recovery import ControllerRecoveryService
from cognitive_os.application.services.minimal_acceptance import MinimalAcceptanceService
from cognitive_os.application.services.model_execution import ModelExecutionService
from cognitive_os.config.controller_config import load_controller_configuration
from cognitive_os.domain.common import ActorRef, utc_now
from cognitive_os.domain.controller import ControllerActionType
from cognitive_os.domain.enums import ActorType, RiskLevel
from cognitive_os.domain.execution import ExecutionPlan, PlanStepDefinition
from cognitive_os.domain.identifiers import new_id
from cognitive_os.domain.model_requests import (
    ModelProviderRequest,
    ProviderMessage,
    ProviderMessageRole,
)
from cognitive_os.domain.planning import ControllerExecutionPlan, ControllerStepAction
from cognitive_os.domain.problems import (
    AcceptanceCriterion,
    CriterionType,
    ProblemDomain,
    ProblemGoal,
    ProblemOutputRequirement,
    ProblemRepresentation,
)
from cognitive_os.events.controller_event_service import ControllerEventService
from cognitive_os.events.provider_event_service import ProviderEventService
from cognitive_os.providers.registry import ProviderRegistry
from cognitive_os.providers.replay import ReplayProvider


class ReplayProblemEngine:
    def __init__(self, step_id) -> None:
        self._step_id = step_id

    async def represent(self, seed):
        return ProblemRepresentation(
            problem_id=new_id(),
            task_id=seed.task_id,
            task_run_id=seed.task_run_id,
            domain=seed.domain_hint or ProblemDomain.GENERIC,
            title=seed.title,
            summary=seed.normalized_request,
            goals=(ProblemGoal(goal_id=new_id(), description=seed.normalized_request, priority=1),),
            output_requirements=(
                ProblemOutputRequirement(
                    requirement_id=new_id(),
                    output_type="text",
                    description="Replay response",
                ),
            ),
            acceptance_criteria=(
                AcceptanceCriterion(
                    criterion_id=new_id(),
                    description="Replay step completed",
                    criterion_type=CriterionType.STEP_COMPLETED,
                    weight=1,
                    configuration={"step_id": str(self._step_id)},
                ),
            ),
            risk_level=RiskLevel.LOW,
            confidence=1,
            created_at=utc_now(),
            revision=1,
            source_request_hash=seed.request_hash,
        )

    async def revise(self, current, clarification):
        raise RuntimeError("offline replay task does not request clarification")


class ReplayPlanner:
    def __init__(self, task_run_id, step_id) -> None:
        actor = ActorRef(actor_type=ActorType.SYSTEM, actor_id="controller-replay-cli")
        structural = ExecutionPlan(
            plan_id=new_id(),
            task_run_id=task_run_id,
            version=1,
            created_at=utc_now(),
            created_by=actor,
            steps=(
                PlanStepDefinition(
                    step_id=step_id,
                    sequence=1,
                    step_type="provider",
                    title="Replay response",
                ),
            ),
        )
        self._plan = ControllerExecutionPlan(
            plan=structural,
            actions=(
                ControllerStepAction(
                    step_id=step_id,
                    action_type=ControllerActionType.PROVIDER,
                    provider_id="replay",
                    requested_model="replay-model",
                    provider_instructions="Return the exact word ready.",
                ),
            ),
            created_at=utc_now(),
            created_by=actor,
        )

    async def create_plan(self, problem, budget):
        return self._plan

    async def revise_plan(self, current, reason, budget):
        raise RuntimeError("reviewed replay task has no repair fixture")


class ReplayActionExecutor:
    def __init__(self, models: ModelExecutionService) -> None:
        self._models = models

    async def execute(self, action, request):
        model_call_id = new_id()
        response = await self._models.execute(
            ModelProviderRequest(
                model_call_id=model_call_id,
                task_run_id=request.task_run_id,
                step_id=action.step_id,
                correlation_id=request.correlation_id,
                requested_model=action.requested_model or "replay-model",
                messages=(
                    ProviderMessage(
                        role=ProviderMessageRole.USER,
                        content=action.provider_instructions or "Return the exact word ready.",
                    ),
                ),
            ),
            provider_id=action.provider_id,
        )
        return ActionOutcome(succeeded=response.content == "ready", output=response.content)


async def run(args) -> None:
    configuration = load_controller_configuration(args.controller_config)
    task_id, task_run_id, step_id = uuid4(), uuid4(), uuid4()
    engine, store = build_event_store()
    try:
        replay = ReplayProvider.from_directory(Path("tests/fixtures/providers/replay"))
        models = ModelExecutionService(
            ProviderRegistry((replay,)),
            default_provider_id="replay",
            event_service=ProviderEventService(store),
        )
        controller = BoundedCognitiveController(
            problem_engine=ReplayProblemEngine(step_id),
            planning=ReplayPlanner(task_run_id, step_id),
            action_executor=ReplayActionExecutor(models),
            acceptance=MinimalAcceptanceService(),
            events=ControllerEventService(store),
            recovery=ControllerRecoveryService(store),
            configuration=configuration,
            provider_ids=("replay",),
        )
        result = await controller.start(
            StartControllerRequest(
                task_id=task_id,
                task_run_id=task_run_id,
                correlation_id=uuid4(),
                title=args.request_file.stem,
                raw_request=args.request_file.read_text(encoding="utf-8"),
            )
        )
        output = result.model_dump(mode="json", exclude_none=True)
        print(
            json.dumps(output, sort_keys=True)
            if args.json
            else f"{task_run_id}\t{result.state.value}"
        )
    finally:
        await engine.dispose()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--request-file", type=Path, required=True)
    parser.add_argument("--provider", choices=("replay",), default="replay")
    parser.add_argument("--controller-config", type=Path, required=True)
    parser.add_argument("--provider-config", type=Path)
    parser.add_argument("--tool-config", type=Path)
    parser.add_argument("--json", action="store_true")
    asyncio.run(run(parser.parse_args()))


if __name__ == "__main__":
    main()
