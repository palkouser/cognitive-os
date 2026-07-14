from datetime import UTC, datetime
from uuid import uuid4

import pytest

from cognitive_os.application.services.clarification_service import ClarificationService
from cognitive_os.config.controller_config import ControllerConfiguration
from cognitive_os.domain.clarifications import ClarificationAnswer, ClarificationResponse
from cognitive_os.domain.controller import ControllerBudget
from cognitive_os.domain.enums import RiskLevel
from cognitive_os.domain.problems import (
    AcceptanceCriterion,
    ClarificationQuestion,
    CriterionType,
    ProblemDomain,
    ProblemGoal,
    ProblemOutputRequirement,
    ProblemRepresentation,
)


def service() -> ClarificationService:
    return ClarificationService(
        ControllerConfiguration(
            default_provider_id="replay",
            problem_representation_provider_id="replay",
            planning_provider_id="replay",
            budgets=ControllerBudget(
                maximum_provider_calls=1,
                maximum_tool_calls=1,
                maximum_plan_steps=1,
                maximum_repair_cycles=1,
                maximum_clarification_cycles=1,
                maximum_elapsed_seconds=10,
            ),
        )
    )


def problem():
    task_run_id, goal_id = uuid4(), uuid4()
    question = ClarificationQuestion(
        question_id=uuid4(),
        question="How many?",
        reason="Required value is missing",
        answer_schema={"type": "integer", "minimum": 1},
        related_goal_ids=(goal_id,),
    )
    return ProblemRepresentation(
        problem_id=uuid4(),
        task_id=uuid4(),
        task_run_id=task_run_id,
        domain=ProblemDomain.GENERIC,
        title="Task",
        summary="Needs one answer",
        goals=(ProblemGoal(goal_id=goal_id, description="Answer", priority=1),),
        output_requirements=(
            ProblemOutputRequirement(
                requirement_id=uuid4(), output_type="text", description="Answer"
            ),
        ),
        acceptance_criteria=(
            AcceptanceCriterion(
                criterion_id=uuid4(),
                description="Complete",
                criterion_type=CriterionType.STEP_COMPLETED,
                weight=1,
            ),
        ),
        clarification_questions=(question,),
        risk_level=RiskLevel.LOW,
        confidence=0.5,
        created_at=datetime.now(UTC),
        revision=1,
        source_request_hash="b" * 64,
    )


def test_clarification_answers_are_schema_validated() -> None:
    value = problem()
    request = service().create_request(value)
    valid = ClarificationResponse(
        clarification_id=request.clarification_id,
        task_run_id=value.task_run_id,
        answers=(ClarificationAnswer(question_id=request.questions[0].question_id, answer=2),),
        provided_at=datetime.now(UTC),
        provided_by="owner",
    )
    service().validate_response(request, valid)
    with pytest.raises(ValueError):
        service().validate_response(request, valid.model_copy(update={"answers": ()}))
