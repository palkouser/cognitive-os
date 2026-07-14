"""Integrity-bound controller checkpoint and continuation primitives."""

from __future__ import annotations

import hashlib
import secrets
from collections.abc import Callable
from datetime import timedelta
from uuid import UUID

from pydantic import Field, model_validator

from cognitive_os.domain.base import ImmutableContractModel
from cognitive_os.domain.clarifications import ContinuationTokenRecord
from cognitive_os.domain.common import Sha256Hex, UtcDatetime, utc_now
from cognitive_os.domain.controller import ControllerStateSnapshot, ControllerUsage
from cognitive_os.domain.identifiers import TaskRunId, new_id
from cognitive_os.domain.planning import ControllerExecutionPlan
from cognitive_os.domain.problems import ProblemRepresentation
from cognitive_os.events.serialization import canonical_json_bytes

from .errors import CheckpointValidationError, ContinuationRejected


class ControllerCheckpoint(ImmutableContractModel):
    checkpoint_id: UUID
    task_run_id: TaskRunId
    controller_state: ControllerStateSnapshot
    problem_representation: ProblemRepresentation | None = None
    controller_plan: ControllerExecutionPlan | None = None
    usage: ControllerUsage
    event_stream_version: int = Field(ge=0)
    created_at: UtcDatetime
    content_hash: Sha256Hex

    @model_validator(mode="after")
    def scope_matches(self) -> ControllerCheckpoint:
        if self.controller_state.task_run_id != self.task_run_id:
            raise ValueError("checkpoint state belongs to another task run")
        return self


class CheckpointCodec:
    @classmethod
    def create(
        cls,
        *,
        checkpoint_id: UUID,
        task_run_id: TaskRunId,
        controller_state: ControllerStateSnapshot,
        problem_representation: ProblemRepresentation | None,
        controller_plan: ControllerExecutionPlan | None,
        usage: ControllerUsage,
        event_stream_version: int,
        created_at: UtcDatetime | None = None,
    ) -> ControllerCheckpoint:
        draft = ControllerCheckpoint(
            checkpoint_id=checkpoint_id,
            task_run_id=task_run_id,
            controller_state=controller_state,
            problem_representation=problem_representation,
            controller_plan=controller_plan,
            usage=usage,
            event_stream_version=event_stream_version,
            created_at=created_at or utc_now(),
            content_hash="0" * 64,
        )
        return draft.model_copy(update={"content_hash": cls.calculate_hash(draft)})

    @staticmethod
    def content_bytes(checkpoint: ControllerCheckpoint) -> bytes:
        return canonical_json_bytes(checkpoint.model_dump(mode="json", exclude={"content_hash"}))

    @classmethod
    def calculate_hash(cls, checkpoint: ControllerCheckpoint) -> str:
        return hashlib.sha256(cls.content_bytes(checkpoint)).hexdigest()

    @classmethod
    def verify(cls, checkpoint: ControllerCheckpoint) -> None:
        if not secrets.compare_digest(cls.calculate_hash(checkpoint), checkpoint.content_hash):
            raise CheckpointValidationError("checkpoint content hash mismatch")
        if checkpoint.event_stream_version > checkpoint.controller_state.last_stream_version:
            raise CheckpointValidationError("checkpoint is from a future stream version")

    @classmethod
    def serialize(cls, checkpoint: ControllerCheckpoint) -> bytes:
        cls.verify(checkpoint)
        return canonical_json_bytes(checkpoint.model_dump(mode="json"))

    @classmethod
    def deserialize(cls, data: bytes) -> ControllerCheckpoint:
        checkpoint = ControllerCheckpoint.model_validate_json(data)
        cls.verify(checkpoint)
        return checkpoint


class ContinuationTokenService:
    def __init__(self, token_factory: Callable[[], str] | None = None) -> None:
        self._token_factory = token_factory or (lambda: secrets.token_urlsafe(32))

    @staticmethod
    def hash_token(token: str) -> str:
        return hashlib.sha256(token.encode("utf-8")).hexdigest()

    def issue(
        self,
        *,
        task_run_id: UUID,
        checkpoint_id: UUID,
        event_stream_version: int,
        ttl_seconds: int,
        now: UtcDatetime | None = None,
    ) -> tuple[str, ContinuationTokenRecord]:
        issued_at = now or utc_now()
        plaintext = self._token_factory()
        return plaintext, ContinuationTokenRecord(
            continuation_id=new_id(),
            task_run_id=task_run_id,
            checkpoint_id=checkpoint_id,
            token_hash=self.hash_token(plaintext),
            event_stream_version=event_stream_version,
            created_at=issued_at,
            expires_at=issued_at + timedelta(seconds=ttl_seconds),
            consumed_at=None,
        )

    def consume(
        self,
        *,
        record: ContinuationTokenRecord,
        token: str,
        task_run_id: UUID,
        checkpoint_id: UUID,
        event_stream_version: int,
        terminal: bool = False,
        now: UtcDatetime | None = None,
    ) -> ContinuationTokenRecord:
        checked_at = now or utc_now()
        invalid = (
            terminal
            or record.consumed_at is not None
            or checked_at >= record.expires_at
            or record.task_run_id != task_run_id
            or record.checkpoint_id != checkpoint_id
            or record.event_stream_version != event_stream_version
            or not secrets.compare_digest(record.token_hash, self.hash_token(token))
        )
        if invalid:
            raise ContinuationRejected("continuation token is invalid, expired, consumed, or stale")
        return record.model_copy(update={"consumed_at": checked_at})
