from datetime import UTC, datetime
from uuid import uuid4

import pytest
from pydantic import ValidationError

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


def make_problem(**updates) -> ProblemRepresentation:
    goal = ProblemGoal(goal_id=uuid4(), description="Produce a result", priority=1)
    values = dict(
        problem_id=uuid4(),
        task_id=uuid4(),
        task_run_id=uuid4(),
        domain=ProblemDomain.GENERIC,
        title="Task",
        summary="A bounded task",
        goals=(goal,),
        constraints=(),
        assumptions=(),
        inputs=(),
        output_requirements=(
            ProblemOutputRequirement(
                requirement_id=uuid4(), output_type="json", description="Result"
            ),
        ),
        acceptance_criteria=(
            AcceptanceCriterion(
                criterion_id=uuid4(),
                description="Step completes",
                criterion_type=CriterionType.STEP_COMPLETED,
                required=True,
                weight=1,
            ),
        ),
        clarification_questions=(),
        risk_level=RiskLevel.LOW,
        confidence=0.9,
        created_at=datetime.now(UTC),
        revision=1,
        source_request_hash="a" * 64,
    )
    values.update(updates)
    return ProblemRepresentation(**values)


def test_problem_is_executable_and_round_trips() -> None:
    problem = make_problem()
    assert problem.is_executable()
    assert ProblemRepresentation.model_validate_json(problem.model_dump_json()) == problem


def test_required_clarification_blocks_execution() -> None:
    base = make_problem()
    question = ClarificationQuestion(
        question_id=uuid4(),
        question="Which format?",
        reason="Output is ambiguous",
        answer_schema={"type": "string"},
        related_goal_ids=(base.goals[0].goal_id,),
    )
    problem = make_problem(goals=base.goals, clarification_questions=(question,))
    assert problem.requires_clarification()
    assert not problem.is_executable()


@pytest.mark.parametrize(
    "field,value", [("goals", ()), ("output_requirements", ()), ("acceptance_criteria", ())]
)
def test_required_problem_collections(field: str, value: tuple) -> None:
    with pytest.raises(ValidationError):
        make_problem(**{field: value})


def test_unknown_fields_are_rejected() -> None:
    with pytest.raises(ValidationError):
        ProblemGoal(goal_id=uuid4(), description="Goal", priority=1, injected=True)
