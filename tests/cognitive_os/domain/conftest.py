from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from cognitive_os.domain import (
    ActorRef,
    ActorType,
    ArtifactRef,
    CallStatus,
    ErrorInfo,
    ExecutionPlan,
    FindingSeverity,
    ModelCallResultRecord,
    PermissionDecision,
    PlanStepDefinition,
    RiskLevel,
    Task,
    TaskRun,
    TaskRunStatus,
    TaskStatus,
    ToolCallRequestRecord,
    ToolCallResultRecord,
    VerificationSubjectRef,
    VerifierFinding,
    VerifierResult,
    VerifierStatus,
    new_id,
)


@pytest.fixture
def now() -> datetime:
    return datetime(2026, 7, 14, 8, 0, tzinfo=UTC)


@pytest.fixture
def actor() -> ActorRef:
    return ActorRef(actor_type=ActorType.USER, actor_id="user-1", display_name="Owner")


@pytest.fixture
def artifact(now: datetime) -> ArtifactRef:
    return ArtifactRef(
        artifact_id=new_id(),
        media_type="application/json",
        content_hash="a" * 64,
        size_bytes=42,
        storage_key="tasks/result.json",
        created_at=now,
    )


@pytest.fixture
def error() -> ErrorInfo:
    return ErrorInfo(code="execution_failed", message="Execution failed")


@pytest.fixture
def task(now: datetime, actor: ActorRef) -> Task:
    return Task(
        task_id=new_id(),
        title="Create report",
        raw_request="Create an English report.",
        created_at=now,
        updated_at=now,
        requested_by=actor,
        status=TaskStatus.READY,
        tags=("report",),
    )


@pytest.fixture
def task_run(task: Task, now: datetime) -> TaskRun:
    return TaskRun(
        task_run_id=new_id(),
        task_id=task.task_id,
        session_id=new_id(),
        correlation_id=new_id(),
        status=TaskRunStatus.RUNNING,
        started_at=now,
    )


@pytest.fixture
def plan(task_run: TaskRun, now: datetime, actor: ActorRef) -> ExecutionPlan:
    first = PlanStepDefinition(step_id=new_id(), sequence=1, step_type="analysis", title="Analyze")
    second = PlanStepDefinition(
        step_id=new_id(),
        sequence=2,
        step_type="write",
        title="Write",
        depends_on=(first.step_id,),
    )
    return ExecutionPlan(
        plan_id=new_id(),
        task_run_id=task_run.task_run_id,
        version=1,
        created_at=now,
        created_by=actor,
        steps=(first, second),
    )


@pytest.fixture
def model_result(now: datetime, artifact: ArtifactRef) -> ModelCallResultRecord:
    return ModelCallResultRecord(
        model_call_id=new_id(),
        resolved_model="offline-model",
        status=CallStatus.COMPLETED,
        started_at=now,
        finished_at=now + timedelta(milliseconds=5),
        content_artifact=artifact,
        latency_ms=5,
    )


@pytest.fixture
def tool_request(task_run: TaskRun, now: datetime) -> ToolCallRequestRecord:
    return ToolCallRequestRecord(
        tool_call_id=new_id(),
        task_run_id=task_run.task_run_id,
        tool_id="calculator",
        tool_version="1",
        arguments={"expression": "20 + 22"},
        requested_at=now,
        risk_level=RiskLevel.LOW,
        permission_decision=PermissionDecision.NOT_REQUIRED,
    )


@pytest.fixture
def tool_result(
    tool_request: ToolCallRequestRecord, now: datetime, artifact: ArtifactRef
) -> ToolCallResultRecord:
    return ToolCallResultRecord(
        tool_call_id=tool_request.tool_call_id,
        status=CallStatus.COMPLETED,
        started_at=now,
        finished_at=now + timedelta(milliseconds=2),
        result_artifacts=(artifact,),
        duration_ms=2,
    )


@pytest.fixture
def verifier_result(now: datetime, artifact: ArtifactRef) -> VerifierResult:
    return VerifierResult(
        verifier_result_id=new_id(),
        verifier_id="logic-check",
        verifier_version="1",
        subject=VerificationSubjectRef(subject_type="artifact", artifact_id=artifact.artifact_id),
        status=VerifierStatus.PASSED,
        score=1,
        confidence=0.9,
        findings=(
            VerifierFinding(
                code="valid",
                severity=FindingSeverity.INFO,
                message="The result is valid.",
            ),
        ),
        started_at=now,
        finished_at=now + timedelta(milliseconds=1),
    )
