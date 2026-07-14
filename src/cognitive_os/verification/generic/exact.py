"""Exact-value verifier with explicit normalization only."""

import json
from typing import Any

from cognitive_os.domain.enums import VerifierStatus
from cognitive_os.domain.problems import CriterionType
from cognitive_os.domain.verification import VerifierResult
from cognitive_os.domain.verifiers import VerificationRequest, VerificationSubjectType

from ..base import BaseVerifier
from .common import generic_descriptor


def _normalize(value: Any, configuration: dict[str, Any]) -> Any:
    if isinstance(value, str):
        if configuration.get("strip_whitespace"):
            value = value.strip()
        if configuration.get("case_sensitive") is False:
            value = value.casefold()
    return value


class ExactValueVerifier(BaseVerifier):
    def __init__(self) -> None:
        super().__init__(
            generic_descriptor(
                "generic.exact",
                VerificationSubjectType.STRUCTURED_VALUE,
                CriterionType.EXACT_MATCH,
            )
        )

    async def verify(self, request: VerificationRequest) -> VerifierResult:
        configuration = request.configuration
        actual = _normalize(request.subject.inline_value, configuration)
        expected = _normalize(configuration.get("expected"), configuration)
        passed = json.dumps(actual, sort_keys=True) == json.dumps(expected, sort_keys=True)
        return self.result(
            request,
            VerifierStatus.PASSED if passed else VerifierStatus.FAILED,
            code="generic.exact.mismatch",
            message="actual value does not exactly match the expected value",
            score=1.0 if passed else 0.0,
        )
