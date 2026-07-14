"""Content-addressed artifact integrity verifier."""

from cognitive_os.application.ports.artifact_store import ArtifactStorePort
from cognitive_os.domain.enums import VerifierStatus
from cognitive_os.domain.problems import CriterionType
from cognitive_os.domain.verification import VerifierResult
from cognitive_os.domain.verifiers import VerificationRequest, VerificationSubjectType

from ..base import BaseVerifier
from .common import generic_descriptor


class ArtifactIntegrityVerifier(BaseVerifier):
    def __init__(self, artifacts: ArtifactStorePort) -> None:
        super().__init__(
            generic_descriptor(
                "generic.artifact_integrity",
                VerificationSubjectType.ARTIFACT,
                CriterionType.ARTIFACT_EXISTS,
            )
        )
        self._artifacts = artifacts

    async def verify(self, request: VerificationRequest) -> VerifierResult:
        references = request.subject.artifact_refs
        passed = bool(references)
        expected_media_type = request.configuration.get("media_type")
        for reference in references:
            passed = passed and await self._artifacts.exists(reference.artifact_id)
            passed = passed and await self._artifacts.verify(reference.artifact_id)
            if expected_media_type:
                passed = passed and reference.media_type == expected_media_type
        return self.result(
            request,
            VerifierStatus.PASSED if passed else VerifierStatus.FAILED,
            code="generic.artifact_integrity.failed",
            message="artifact is missing, corrupt, or has an unexpected media type",
            score=1 if passed else 0,
        )
