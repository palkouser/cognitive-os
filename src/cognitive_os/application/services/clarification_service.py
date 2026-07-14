"""Schema-validated clarification and scoped continuation handling."""

from datetime import timedelta
from uuid import UUID

import jsonschema

from cognitive_os.config.controller_config import ControllerConfiguration
from cognitive_os.controller.checkpoint import ContinuationTokenService
from cognitive_os.domain.clarifications import (
    ClarificationRequest,
    ClarificationResponse,
    ContinuationTokenRecord,
)
from cognitive_os.domain.common import utc_now
from cognitive_os.domain.identifiers import new_id
from cognitive_os.domain.problems import ProblemRepresentation


class ClarificationService:
    def __init__(
        self,
        configuration: ControllerConfiguration,
        token_service: ContinuationTokenService | None = None,
    ) -> None:
        self._configuration = configuration
        self._tokens = token_service or ContinuationTokenService()

    def create_request(self, representation: ProblemRepresentation) -> ClarificationRequest:
        now = utc_now()
        return ClarificationRequest(
            clarification_id=new_id(),
            task_run_id=representation.task_run_id,
            problem_id=representation.problem_id,
            problem_revision=representation.revision,
            questions=representation.clarification_questions,
            requested_at=now,
            expires_at=now
            + timedelta(seconds=self._configuration.checkpoint.continuation_ttl_seconds),
        )

    def validate_response(
        self, request: ClarificationRequest, response: ClarificationResponse
    ) -> None:
        if request.clarification_id != response.clarification_id:
            raise ValueError("clarification response has the wrong request ID")
        if request.task_run_id != response.task_run_id:
            raise ValueError("clarification response has the wrong task-run ID")
        questions = {question.question_id: question for question in request.questions}
        answers = {answer.question_id: answer.answer for answer in response.answers}
        if set(answers) - set(questions):
            raise ValueError("clarification response references an unknown question")
        missing = {item.question_id for item in request.questions if item.required} - set(answers)
        if missing:
            raise ValueError("clarification response omits a required answer")
        for question_id, answer in answers.items():
            jsonschema.validate(answer, questions[question_id].answer_schema)

    def issue_continuation(
        self,
        *,
        task_run_id: UUID,
        checkpoint_id: UUID,
        event_stream_version: int,
    ) -> tuple[str, ContinuationTokenRecord]:
        return self._tokens.issue(
            task_run_id=task_run_id,
            checkpoint_id=checkpoint_id,
            event_stream_version=event_stream_version,
            ttl_seconds=self._configuration.checkpoint.continuation_ttl_seconds,
        )

    def consume_continuation(
        self,
        *,
        record: ContinuationTokenRecord,
        plaintext: str,
        task_run_id: UUID,
        checkpoint_id: UUID,
        event_stream_version: int,
        terminal: bool = False,
    ) -> ContinuationTokenRecord:
        return self._tokens.consume(
            record=record,
            token=plaintext,
            task_run_id=task_run_id,
            checkpoint_id=checkpoint_id,
            event_stream_version=event_stream_version,
            terminal=terminal,
        )
