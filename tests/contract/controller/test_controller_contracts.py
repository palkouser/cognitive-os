from datetime import UTC, datetime
from uuid import uuid4

import pytest
from pydantic import ValidationError

from cognitive_os.domain.common import ActorRef
from cognitive_os.domain.controller import ControllerActionType
from cognitive_os.domain.enums import ActorType
from cognitive_os.domain.execution import ExecutionPlan, PlanStepDefinition
from cognitive_os.domain.planning import ControllerExecutionPlan, ControllerStepAction
from cognitive_os.schemas.registry import build_schema_registry


def test_controller_schemas_are_registered() -> None:
    paths = {entry.path for entry in build_schema_registry()}
    assert "v1/domain/problem-representation.schema.json" in paths
    assert "v1/domain/controller-state-snapshot.schema.json" in paths
    assert "v1/domain/controller-execution-plan.schema.json" in paths


def test_plan_action_mapping_is_complete_and_sequential() -> None:
    now = datetime.now(UTC)
    actor = ActorRef(actor_type=ActorType.SYSTEM, actor_id="test")
    task_run_id, step_id = uuid4(), uuid4()
    plan = ExecutionPlan(
        plan_id=uuid4(),
        task_run_id=task_run_id,
        version=1,
        created_at=now,
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
    action = ControllerStepAction(
        step_id=step_id,
        action_type=ControllerActionType.PROVIDER,
        provider_instructions="Return a bounded response.",
    )
    assert ControllerExecutionPlan(
        plan=plan, actions=(action,), created_at=now, created_by=actor
    ).sequential_only
    with pytest.raises(ValidationError):
        ControllerExecutionPlan(
            plan=plan,
            actions=(action,),
            created_at=now,
            created_by=actor,
            sequential_only=False,
        )
