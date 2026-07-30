"""The `coding.hidden_pytest` criterion.

Pure, like the other structured-value coding verifiers: it reads normalized hidden-run
evidence produced by `cognitive_os.coding.hidden_verification` and decides. It does not run
pytest and it has no path to the control bundle, so the registry-backed decision stays on the
same side of the boundary as `coding.workspace_integrity` while the mount stays on the other.

The one judgement it makes that the visible verifiers do not: `unverifiable` is not `failed`.
A missing or tampered bundle means the candidate was never measured, and a required criterion
that is unverifiable blocks acceptance through `AcceptancePolicyService` without asserting
anything false about the patch.
"""

from typing import Any, cast

from cognitive_os.domain.common import ErrorInfo
from cognitive_os.domain.enums import VerifierStatus
from cognitive_os.domain.verification import VerifierResult
from cognitive_os.domain.verifiers import VerificationRequest

from ..base import BaseVerifier
from .common import coding_descriptor

_STATUS_MAP = {
    "passed": VerifierStatus.PASSED,
    "failed": VerifierStatus.FAILED,
    "timed_out": VerifierStatus.FAILED,
    "unverifiable": VerifierStatus.UNVERIFIABLE,
}


class HiddenPytestVerifier(BaseVerifier):
    def __init__(self) -> None:
        super().__init__(coding_descriptor("coding.hidden_pytest", sandbox=False))

    async def verify(self, request: VerificationRequest) -> VerifierResult:
        try:
            value = cast(Any, request.subject.inline_value)
            if not isinstance(value, dict):
                raise ValueError("hidden pytest subject must be an object")
            if value.get("criterion_id") != "coding.hidden_pytest":
                raise ValueError("hidden pytest evidence belongs to a different criterion")
            for field in ("bundle_content_hash", "sandbox_image_digest", "evidence_hash"):
                if not value.get(field):
                    raise ValueError(f"hidden pytest evidence is missing {field}")
            status = _STATUS_MAP.get(cast(str, value.get("status")))
            if status is None:
                raise ValueError(f"unknown hidden verification status: {value.get('status')!r}")
            return self.result(
                request,
                status,
                code="coding.hidden_pytest.failed",
                message="the hidden test suite did not pass for this candidate",
                score=1 if status is VerifierStatus.PASSED else 0,
            )
        except (TypeError, ValueError) as error:
            return self.result(
                request,
                VerifierStatus.ERROR,
                error=ErrorInfo(code="invalid_hidden_pytest_evidence", message=str(error)),
            )
