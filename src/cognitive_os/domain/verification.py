"""Verifier-neutral result contracts."""

from __future__ import annotations

from pydantic import Field, model_validator

from .base import ImmutableContractModel
from .common import ArtifactRef, ErrorInfo, NonEmptyStr, UtcDatetime
from .enums import FindingSeverity, VerifierStatus
from .identifiers import ArtifactId, VerifierResultId


class VerificationSubjectRef(ImmutableContractModel):
    subject_type: NonEmptyStr
    subject_id: NonEmptyStr | None = None
    artifact_id: ArtifactId | None = None

    @model_validator(mode="after")
    def require_reference(self) -> VerificationSubjectRef:
        if self.subject_id is None and self.artifact_id is None:
            raise ValueError("at least one stable subject reference is required")
        return self


class VerifierFinding(ImmutableContractModel):
    code: NonEmptyStr
    severity: FindingSeverity
    message: NonEmptyStr
    location: str | None = None
    evidence_artifacts: tuple[ArtifactRef, ...] = ()


class VerifierResult(ImmutableContractModel):
    verifier_result_id: VerifierResultId
    verifier_id: NonEmptyStr
    verifier_version: NonEmptyStr
    subject: VerificationSubjectRef
    status: VerifierStatus
    score: float | None = Field(default=None, ge=0, le=1)
    confidence: float | None = Field(default=None, ge=0, le=1)
    findings: tuple[VerifierFinding, ...] = ()
    evidence_artifacts: tuple[ArtifactRef, ...] = ()
    started_at: UtcDatetime
    finished_at: UtcDatetime
    error: ErrorInfo | None = None

    @model_validator(mode="after")
    def validate_result(self) -> VerifierResult:
        if self.finished_at < self.started_at:
            raise ValueError("finished_at cannot be earlier than started_at")
        if self.status is VerifierStatus.FAILED and not self.findings:
            raise ValueError("failed verifier results require at least one finding")
        if self.status is VerifierStatus.ERROR and self.error is None:
            raise ValueError("error verifier results require ErrorInfo")
        if self.status is VerifierStatus.PASSED and self.error is not None:
            raise ValueError("passed verifier results cannot contain an error")
        artifacts = self.evidence_artifacts + tuple(
            artifact for finding in self.findings for artifact in finding.evidence_artifacts
        )
        ids = tuple(item.artifact_id for item in artifacts)
        if len(set(ids)) != len(ids):
            raise ValueError("verifier evidence references must be unique")
        return self
