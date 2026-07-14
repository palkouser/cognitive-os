"""Reusable primitives for deterministic verifier implementations."""

from __future__ import annotations

from abc import ABC, abstractmethod
from uuid import uuid4

from cognitive_os.application.ports.verifier import VerifierPort
from cognitive_os.domain.common import ErrorInfo, utc_now
from cognitive_os.domain.enums import FindingSeverity, VerifierStatus
from cognitive_os.domain.verification import VerificationSubjectRef, VerifierFinding, VerifierResult
from cognitive_os.domain.verifiers import (
    VerificationRequest,
    VerifierDescriptor,
    VerifierHealth,
    VerifierHealthStatus,
)


class BaseVerifier(VerifierPort, ABC):
    def __init__(self, descriptor: VerifierDescriptor) -> None:
        self._descriptor = descriptor

    @property
    def descriptor(self) -> VerifierDescriptor:
        return self._descriptor

    async def health_check(self) -> VerifierHealth:
        return VerifierHealth(status=VerifierHealthStatus.AVAILABLE)

    @abstractmethod
    async def verify(self, request: VerificationRequest) -> VerifierResult: ...

    def result(
        self,
        request: VerificationRequest,
        status: VerifierStatus,
        *,
        code: str = "verification.result",
        message: str = "verification completed",
        score: float | None = None,
        error: ErrorInfo | None = None,
    ) -> VerifierResult:
        now = utc_now()
        findings: tuple[VerifierFinding, ...] = ()
        if status in {VerifierStatus.FAILED, VerifierStatus.PARTIAL}:
            findings = (
                VerifierFinding(code=code, severity=FindingSeverity.ERROR, message=message),
            )
        return VerifierResult(
            verifier_result_id=uuid4(),
            verifier_id=self.descriptor.verifier_id,
            verifier_version=self.descriptor.version,
            subject=VerificationSubjectRef(
                subject_type=request.subject.subject_type.value,
                subject_id=str(request.verification_id),
            ),
            status=status,
            score=score,
            findings=findings,
            started_at=now,
            finished_at=now,
            error=error,
        )
