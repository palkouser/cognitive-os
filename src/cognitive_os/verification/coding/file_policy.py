"""Pure changed-file manifest policy verifier."""

from pathlib import PurePosixPath
from typing import Any, cast

from cognitive_os.domain.common import ErrorInfo
from cognitive_os.domain.enums import VerifierStatus
from cognitive_os.domain.verification import VerifierResult
from cognitive_os.domain.verifiers import VerificationRequest

from ..base import BaseVerifier
from .common import coding_descriptor


class FilePolicyVerifier(BaseVerifier):
    def __init__(self) -> None:
        super().__init__(coding_descriptor("coding.file_policy", sandbox=False))

    async def verify(self, request: VerificationRequest) -> VerifierResult:
        try:
            value = cast(Any, request.subject.inline_value)
            if not isinstance(value, dict) or not isinstance(value.get("files"), list):
                raise ValueError("file policy subject requires a files list")
            files = value["files"]
            configuration = cast(Any, request.configuration)
            maximum_count = int(configuration.get("maximum_file_count", 100))
            maximum_bytes = int(configuration.get("maximum_file_bytes", 5_000_000))
            forbidden = tuple(str(item) for item in configuration.get("forbidden_paths", [".git/"]))
            safe = len(files) <= maximum_count
            for item in files:
                path = PurePosixPath(str(item["path"]))
                safe = safe and not path.is_absolute() and ".." not in path.parts
                safe = safe and not any(str(path).startswith(prefix) for prefix in forbidden)
                safe = safe and int(item.get("size_bytes", 0)) <= maximum_bytes
                safe = (
                    safe
                    and not bool(item.get("symlink", False))
                    and not bool(item.get("binary", False))
                )
            return self.result(
                request,
                VerifierStatus.PASSED if safe else VerifierStatus.FAILED,
                code="coding.file_policy.denied",
                message="changed-file manifest violates repository policy",
                score=1 if safe else 0,
            )
        except (KeyError, TypeError, ValueError) as error:
            return self.result(
                request,
                VerifierStatus.ERROR,
                error=ErrorInfo(code="invalid_file_manifest", message=str(error)),
            )
