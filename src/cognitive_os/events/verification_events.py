"""Verifier lifecycle payloads."""

from cognitive_os.domain.common import ErrorInfo, Sha256Hex, UtcDatetime
from cognitive_os.domain.identifiers import VerifierResultId
from cognitive_os.domain.verification import VerificationSubjectRef, VerifierResult

from .base import EventPayload


class VerifierStarted(EventPayload):
    event_type = "verifier.started"
    verifier_result_id: VerifierResultId
    verifier_id: str
    verifier_version: str = "1"
    subject: VerificationSubjectRef
    started_at: UtcDatetime
    configuration_hash: Sha256Hex | None = None


class VerifierCompleted(EventPayload):
    event_type = "verifier.completed"
    result: VerifierResult


class VerifierFailed(EventPayload):
    event_type = "verifier.failed"
    verifier_result_id: VerifierResultId
    finished_at: UtcDatetime
    error: ErrorInfo
