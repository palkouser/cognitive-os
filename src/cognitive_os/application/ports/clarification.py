"""Clarification lifecycle boundary."""

from typing import Protocol
from uuid import UUID

from cognitive_os.domain.clarifications import (
    ClarificationRequest,
    ClarificationResponse,
    ContinuationTokenRecord,
)
from cognitive_os.domain.problems import ProblemRepresentation


class ClarificationPort(Protocol):
    def create_request(self, representation: ProblemRepresentation) -> ClarificationRequest: ...
    def validate_response(
        self, request: ClarificationRequest, response: ClarificationResponse
    ) -> None: ...
    def issue_continuation(
        self, *, task_run_id: UUID, checkpoint_id: UUID, event_stream_version: int
    ) -> tuple[str, ContinuationTokenRecord]: ...
