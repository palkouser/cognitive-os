"""Offline dependency-change policy verifier."""

from typing import Any, cast

from cognitive_os.domain.common import ErrorInfo
from cognitive_os.domain.enums import VerifierStatus
from cognitive_os.domain.verification import VerifierResult
from cognitive_os.domain.verifiers import VerificationRequest

from ..base import BaseVerifier
from .common import coding_descriptor


class DependencyPolicyVerifier(BaseVerifier):
    def __init__(self) -> None:
        super().__init__(coding_descriptor("coding.dependency_policy", sandbox=False))

    async def verify(self, request: VerificationRequest) -> VerifierResult:
        try:
            value = cast(Any, request.subject.inline_value)
            configuration = cast(Any, request.configuration)
            if not isinstance(value, dict):
                raise ValueError("dependency policy subject must be an object")
            before = set(value.get("before_direct", []))
            after = set(value.get("after_direct", []))
            approved = set(configuration.get("approved_additions", []))
            added = after - before
            optional_to_core = set(value.get("optional_to_core", []))
            widened = set(value.get("widened_requirements", []))
            passed = added <= approved and not optional_to_core and not widened
            return self.result(
                request,
                VerifierStatus.PASSED if passed else VerifierStatus.FAILED,
                code="coding.dependency_policy.denied",
                message="dependency change is not approved",
                score=1 if passed else 0,
            )
        except (TypeError, ValueError) as error:
            return self.result(
                request,
                VerifierStatus.ERROR,
                error=ErrorInfo(code="invalid_dependency_manifest", message=str(error)),
            )
