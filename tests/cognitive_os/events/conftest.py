from datetime import UTC, datetime, timedelta

import pytest

from cognitive_os.domain import (
    ActorRef,
    ActorType,
    ArtifactRef,
    CallStatus,
    ExecutionPlan,
    ModelCallResultRecord,
    PlanStepDefinition,
    Task,
    TaskRun,
    TaskRunStatus,
    ToolCallResultRecord,
    VerificationSubjectRef,
    VerifierResult,
    VerifierStatus,
    new_id,
)


@pytest.fixture
def now() -> datetime:
    return datetime(2026, 7, 14, 9, 0, tzinfo=UTC)


@pytest.fixture
def actor() -> ActorRef:
    return ActorRef(actor_type=ActorType.USER, actor_id="user-1")


@pytest.fixture
def artifact(now) -> ArtifactRef:
    return ArtifactRef(
        artifact_id=new_id(),
        media_type="text/plain",
        content_hash="c" * 64,
        size_bytes=2,
        storage_key="results/output.txt",
        created_at=now,
    )


@pytest.fixture
def task(now, actor) -> Task:
    return Task(
        task_id=new_id(),
        title="Test task",
        raw_request="Run the offline contract test.",
        created_at=now,
        updated_at=now,
        requested_by=actor,
    )


@pytest.fixture
def task_run(task, now) -> TaskRun:
    return TaskRun(
        task_run_id=new_id(),
        task_id=task.task_id,
        session_id=new_id(),
        correlation_id=new_id(),
        status=TaskRunStatus.RUNNING,
        started_at=now,
    )


@pytest.fixture
def plan(task_run, now, actor) -> ExecutionPlan:
    step = PlanStepDefinition(
        step_id=new_id(),
        sequence=1,
        step_type="analysis",
        title="Analyze",
    )
    return ExecutionPlan(
        plan_id=new_id(),
        task_run_id=task_run.task_run_id,
        version=1,
        created_at=now,
        created_by=actor,
        steps=(step,),
    )


@pytest.fixture
def model_result(now, artifact) -> ModelCallResultRecord:
    return ModelCallResultRecord(
        model_call_id=new_id(),
        resolved_model="offline-model",
        status=CallStatus.COMPLETED,
        started_at=now,
        finished_at=now + timedelta(milliseconds=1),
        content_artifact=artifact,
    )


@pytest.fixture
def tool_result(now, artifact) -> ToolCallResultRecord:
    return ToolCallResultRecord(
        tool_call_id=new_id(),
        status=CallStatus.COMPLETED,
        started_at=now,
        finished_at=now + timedelta(milliseconds=1),
        result_artifacts=(artifact,),
    )


@pytest.fixture
def verifier_result(now, artifact) -> VerifierResult:
    return VerifierResult(
        verifier_result_id=new_id(),
        verifier_id="offline-verifier",
        verifier_version="1",
        subject=VerificationSubjectRef(subject_type="artifact", artifact_id=artifact.artifact_id),
        status=VerifierStatus.PASSED,
        started_at=now,
        finished_at=now + timedelta(milliseconds=1),
    )
