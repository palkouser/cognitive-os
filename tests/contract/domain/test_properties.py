from __future__ import annotations

from datetime import UTC, datetime

from hypothesis import given, settings
from hypothesis import strategies as st

from cognitive_os.domain import (
    ActorRef,
    ActorType,
    ArtifactRef,
    ExecutionPlan,
    PlanStepDefinition,
    Task,
    TokenUsage,
    new_id,
)
from cognitive_os.events.hashing import sha256_digest
from cognitive_os.events.serialization import canonical_json_bytes


@settings(max_examples=30, deadline=None)
@given(st.uuids(version=4))
def test_uuid_artifact_references_round_trip(identifier) -> None:
    artifact = ArtifactRef(
        artifact_id=identifier,
        media_type="text/plain",
        content_hash="d" * 64,
        size_bytes=0,
        storage_key="fixture.txt",
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
    )
    assert ArtifactRef.model_validate_json(artifact.model_dump_json()) == artifact


@settings(max_examples=30, deadline=None)
@given(
    st.integers(min_value=0, max_value=10000),
    st.integers(min_value=0, max_value=10000),
)
def test_token_usage_totals(input_tokens: int, output_tokens: int) -> None:
    usage = TokenUsage(
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        total_tokens=input_tokens + output_tokens,
    )
    assert usage.total_tokens == input_tokens + output_tokens


@settings(max_examples=25, deadline=None)
@given(
    st.lists(
        st.text(alphabet="abcdefghijklmnopqrstuvwxyz", min_size=1, max_size=12),
        unique=True,
        max_size=8,
    )
)
def test_task_tag_tuples_round_trip(tags: list[str]) -> None:
    task = Task(
        task_id=new_id(),
        title="Property task",
        raw_request="Validate bounded tags.",
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
        updated_at=datetime(2026, 1, 1, tzinfo=UTC),
        tags=tuple(tags),
        requested_by=ActorRef(actor_type=ActorType.USER, actor_id="property-user"),
    )
    assert Task.model_validate_json(task.model_dump_json()).tags == tuple(tags)


@settings(max_examples=30, deadline=None)
@given(st.dictionaries(st.text(min_size=1, max_size=8), st.integers(), max_size=10))
def test_serialization_and_hashing_are_deterministic(value: dict[str, int]) -> None:
    reversed_value = dict(reversed(tuple(value.items())))
    assert canonical_json_bytes(value) == canonical_json_bytes(reversed_value)
    assert sha256_digest(value) == sha256_digest(reversed_value)


def test_generated_execution_plan_is_a_valid_dag() -> None:
    first = PlanStepDefinition(step_id=new_id(), sequence=1, step_type="first", title="First")
    second = PlanStepDefinition(
        step_id=new_id(),
        sequence=2,
        step_type="second",
        title="Second",
        depends_on=(first.step_id,),
    )
    plan = ExecutionPlan(
        plan_id=new_id(),
        task_run_id=new_id(),
        version=1,
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
        created_by=ActorRef(actor_type=ActorType.AGENT, actor_id="planner"),
        steps=(first, second),
    )
    assert len(plan.steps) == 2
