"""Pure verifier for detached-worktree and main-tree integrity evidence."""

from typing import Any, cast

from cognitive_os.domain.common import ErrorInfo
from cognitive_os.domain.enums import VerifierStatus
from cognitive_os.domain.verification import VerifierResult
from cognitive_os.domain.verifiers import VerificationRequest

from ..base import BaseVerifier
from .common import coding_descriptor


class WorkspaceIntegrityVerifier(BaseVerifier):
    def __init__(self) -> None:
        super().__init__(coding_descriptor("coding.workspace_integrity", sandbox=False))

    async def verify(self, request: VerificationRequest) -> VerifierResult:
        try:
            value = cast(Any, request.subject.inline_value)
            if not isinstance(value, dict):
                raise ValueError("workspace integrity subject must be an object")
            passed = (
                value.get("workspace_head") == value.get("base_commit")
                and bool(value.get("main_head_unchanged"))
                and bool(value.get("main_status_unchanged"))
                and bool(value.get("git_admin_unchanged"))
            )
            return self.result(
                request,
                VerifierStatus.PASSED if passed else VerifierStatus.FAILED,
                code="coding.workspace_integrity.denied",
                message="workspace or main repository integrity invariant failed",
                score=1 if passed else 0,
            )
        except (TypeError, ValueError) as error:
            return self.result(
                request,
                VerifierStatus.ERROR,
                error=ErrorInfo(code="invalid_workspace_integrity", message=str(error)),
            )
