"""Pure normalized-diff policy verifier."""

from typing import Any, cast

from cognitive_os.domain.common import ErrorInfo
from cognitive_os.domain.enums import VerifierStatus
from cognitive_os.domain.verification import VerifierResult
from cognitive_os.domain.verifiers import VerificationRequest

from ..base import BaseVerifier
from .common import coding_descriptor


class DiffPolicyVerifier(BaseVerifier):
    def __init__(self) -> None:
        super().__init__(coding_descriptor("coding.diff_policy", sandbox=False))

    async def verify(self, request: VerificationRequest) -> VerifierResult:
        try:
            value = cast(Any, request.subject.inline_value)
            configuration = cast(Any, request.configuration)
            if not isinstance(value, dict):
                raise ValueError("diff policy subject must be an object")
            paths = [str(item) for item in value.get("paths", [])]
            safe = int(value.get("line_count", 0)) <= int(
                configuration.get("maximum_diff_lines", 2000)
            )
            safe = safe and len(paths) <= int(configuration.get("maximum_file_count", 100))
            safe = safe and not any(item == ".git" or item.startswith(".git/") for item in paths)
            safe = safe and not bool(value.get("submodule_change"))
            safe = safe and (
                bool(configuration.get("allow_binary", False))
                or not bool(value.get("binary_patch"))
            )
            safe = safe and (
                bool(configuration.get("allow_mode_change", False))
                or not bool(value.get("mode_change"))
            )
            protected = set(configuration.get("protected_files", []))
            safe = safe and not (protected & set(value.get("deleted_paths", [])))
            return self.result(
                request,
                VerifierStatus.PASSED if safe else VerifierStatus.FAILED,
                code="coding.diff_policy.denied",
                message="diff violates repository policy",
                score=1 if safe else 0,
            )
        except (TypeError, ValueError) as error:
            return self.result(
                request,
                VerifierStatus.ERROR,
                error=ErrorInfo(code="invalid_diff_manifest", message=str(error)),
            )
