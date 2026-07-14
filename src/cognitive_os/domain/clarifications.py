"""Clarification and continuation contracts."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from pydantic import model_validator

from .base import ImmutableContractModel
from .common import NonEmptyStr, Sha256Hex, UtcDatetime
from .identifiers import TaskRunId
from .problems import ClarificationQuestion


class ClarificationRequest(ImmutableContractModel):
    clarification_id: UUID
    task_run_id: TaskRunId
    problem_id: UUID
    problem_revision: int
    questions: tuple[ClarificationQuestion, ...]
    requested_at: UtcDatetime
    expires_at: UtcDatetime


class ClarificationAnswer(ImmutableContractModel):
    question_id: UUID
    answer: Any


class ClarificationResponse(ImmutableContractModel):
    clarification_id: UUID
    task_run_id: TaskRunId
    answers: tuple[ClarificationAnswer, ...]
    provided_at: UtcDatetime
    provided_by: NonEmptyStr

    @model_validator(mode="after")
    def answers_are_unique(self) -> ClarificationResponse:
        ids = [item.question_id for item in self.answers]
        if len(ids) != len(set(ids)):
            raise ValueError("clarification answers must be unique")
        return self


class ContinuationTokenRecord(ImmutableContractModel):
    continuation_id: UUID
    task_run_id: TaskRunId
    checkpoint_id: UUID
    token_hash: Sha256Hex
    event_stream_version: int
    created_at: UtcDatetime
    expires_at: UtcDatetime
    consumed_at: UtcDatetime | None = None
