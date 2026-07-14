from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import BaseModel, ValidationError

from cognitive_os.domain import (
    ExecutionPlan,
    ModelCallResultRecord,
    Task,
    TaskRun,
    ToolCallResultRecord,
    VerifierResult,
)
from cognitive_os.events import EventEnvelope

FIXTURES = Path("tests/fixtures/contracts/v1")

DOMAIN_FIXTURES: tuple[tuple[str, type[BaseModel]], ...] = (
    ("task.json", Task),
    ("task-run.json", TaskRun),
    ("execution-plan.json", ExecutionPlan),
    ("model-call-result.json", ModelCallResultRecord),
    ("tool-call-result.json", ToolCallResultRecord),
    ("verifier-result.json", VerifierResult),
)


@pytest.mark.contract
@pytest.mark.parametrize(("filename", "model"), DOMAIN_FIXTURES)
def test_v1_domain_fixtures_validate_and_round_trip(filename: str, model: type[BaseModel]) -> None:
    instance = model.model_validate_json((FIXTURES / filename).read_bytes())
    assert model.model_validate_json(instance.model_dump_json()) == instance


@pytest.mark.contract
@pytest.mark.parametrize(
    "filename",
    [
        "task-created-envelope.json",
        "model-call-completed-envelope.json",
        "tool-call-denied-envelope.json",
    ],
)
def test_v1_envelope_fixtures_validate(filename: str) -> None:
    envelope = EventEnvelope.model_validate_json((FIXTURES / filename).read_bytes())
    assert EventEnvelope.model_validate_json(envelope.model_dump_json()) == envelope


@pytest.mark.contract
def test_v1_fixtures_reject_unknown_and_missing_fields() -> None:
    value = json.loads((FIXTURES / "task.json").read_text())
    with pytest.raises(ValidationError):
        Task.model_validate({**value, "unknown": True})
    value.pop("title")
    with pytest.raises(ValidationError):
        Task.model_validate(value)
