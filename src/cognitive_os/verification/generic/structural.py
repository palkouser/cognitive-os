"""Pure structural state verifiers replacing Sprint 6 temporary checks."""

from typing import cast

from cognitive_os.domain.common import ErrorInfo, JsonValue
from cognitive_os.domain.enums import VerifierStatus
from cognitive_os.domain.problems import CriterionType
from cognitive_os.domain.verification import VerifierResult
from cognitive_os.domain.verifiers import VerificationRequest, VerificationSubjectType

from ..base import BaseVerifier
from .common import generic_descriptor


class _PresenceVerifier(BaseVerifier):
    key: str

    async def verify(self, request: VerificationRequest) -> VerifierResult:
        value = request.subject.inline_value
        passed = isinstance(value, dict) and bool(value.get(self.key))
        return self.result(
            request,
            VerifierStatus.PASSED if passed else VerifierStatus.FAILED,
            code=f"{self.descriptor.verifier_id}.missing",
            message=f"required {self.key.replace('_', ' ')} evidence is missing",
            score=1 if passed else 0,
        )


class StepCompletedVerifier(_PresenceVerifier):
    key = "completed"

    def __init__(self) -> None:
        super().__init__(
            generic_descriptor(
                "generic.step_completed",
                VerificationSubjectType.EXECUTION_STEP,
                CriterionType.STEP_COMPLETED,
            )
        )


class ToolSucceededVerifier(_PresenceVerifier):
    key = "succeeded"

    def __init__(self) -> None:
        super().__init__(
            generic_descriptor(
                "generic.tool_succeeded",
                VerificationSubjectType.TOOL_RESULT,
                CriterionType.TOOL_SUCCEEDED,
            )
        )


class PlanConsistencyVerifier(BaseVerifier):
    def __init__(self) -> None:
        super().__init__(
            generic_descriptor(
                "generic.plan_consistency",
                VerificationSubjectType.EXECUTION_PLAN,
                CriterionType.STEP_COMPLETED,
            )
        )

    async def verify(self, request: VerificationRequest) -> VerifierResult:
        value = request.subject.inline_value
        if not isinstance(value, dict):
            consistent = False
        else:
            required_raw = value.get("required_steps", [])
            completed_raw = value.get("completed_steps", [])
            failed_raw = value.get("failed_steps", [])
            running_raw = value.get("running_steps", [])
            if not all(
                isinstance(item, list)
                for item in (required_raw, completed_raw, failed_raw, running_raw)
            ):
                return self.result(
                    request,
                    VerifierStatus.ERROR,
                    error=ErrorInfo(
                        code="invalid_plan_evidence",
                        message="plan state collections must be lists",
                    ),
                )
            required = set(str(item) for item in cast(list[JsonValue], required_raw))
            completed = [str(item) for item in cast(list[JsonValue], completed_raw)]
            failed = set(str(item) for item in cast(list[JsonValue], failed_raw))
            running = [str(item) for item in cast(list[JsonValue], running_raw)]
            consistent = (
                not running
                and len(completed) == len(set(completed))
                and required <= set(completed)
                and not (set(completed) & failed)
            )
        return self.result(
            request,
            VerifierStatus.PASSED if consistent else VerifierStatus.FAILED,
            code="generic.plan_consistency.failed",
            message="execution plan has incomplete or contradictory terminal state",
            score=1 if consistent else 0,
        )
