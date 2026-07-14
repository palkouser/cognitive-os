from datetime import UTC, datetime
from uuid import uuid4

import pytest

from cognitive_os.application.services.acceptance_service import AcceptancePolicyService
from cognitive_os.domain.acceptance import (
    AcceptanceDecisionType,
    AcceptancePolicy,
    VerifierRequirement,
)
from cognitive_os.domain.enums import FindingSeverity, VerifierStatus
from cognitive_os.domain.verification import VerificationSubjectRef, VerifierFinding, VerifierResult
from cognitive_os.domain.verifiers import (
    VerificationRequest,
    VerificationSubject,
    VerificationSubjectType,
)
from cognitive_os.verification.coding import (
    DependencyPolicyVerifier,
    DiffPolicyVerifier,
    FilePolicyVerifier,
)


def policy(
    *, required: bool = True, minimum_optional_score: float = 0
) -> tuple[AcceptancePolicy, VerifierRequirement]:
    requirement = VerifierRequirement(
        requirement_id=uuid4(),
        verifier_id="generic.exact",
        minimum_version="1",
        criterion_ids=(uuid4(),),
        required=required,
        weight=1,
        allowed_outcomes=(VerifierStatus.PASSED,),
    )
    return (
        AcceptancePolicy(
            policy_id=uuid4(),
            version="1",
            name="test",
            description="test acceptance policy",
            requirements=(requirement,),
            minimum_optional_score=minimum_optional_score,
            created_at=datetime.now(UTC),
        ),
        requirement,
    )


def result(
    status: VerifierStatus, *, score: float | None = None, finding_code: str = "failed"
) -> VerifierResult:
    now = datetime.now(UTC)
    findings = (
        ()
        if status is not VerifierStatus.FAILED
        else (VerifierFinding(code=finding_code, severity=FindingSeverity.ERROR, message="failed"),)
    )
    error = None
    if status is VerifierStatus.ERROR:
        from cognitive_os.domain.common import ErrorInfo

        error = ErrorInfo(code="infrastructure", message="verifier unavailable")
    return VerifierResult(
        verifier_result_id=uuid4(),
        verifier_id="generic.exact",
        verifier_version="1",
        subject=VerificationSubjectRef(subject_type="structured_value", subject_id="subject"),
        status=status,
        score=score,
        findings=findings,
        started_at=now,
        finished_at=now,
        error=error,
    )


def test_acceptance_required_pass_error_unavailable_and_repair() -> None:
    active, _ = policy()
    service = AcceptancePolicyService(repairable_finding_codes=frozenset({"repairable"}))
    task_run_id = uuid4()
    assert (
        service.evaluate(active, task_run_id, (result(VerifierStatus.PASSED, score=1),)).decision
        is AcceptanceDecisionType.ACCEPTED
    )
    assert (
        service.evaluate(active, task_run_id, (result(VerifierStatus.ERROR),)).decision
        is AcceptanceDecisionType.VERIFICATION_ERROR
    )
    assert service.evaluate(active, task_run_id, ()).decision is AcceptanceDecisionType.UNVERIFIABLE
    assert (
        service.evaluate(
            active,
            task_run_id,
            (result(VerifierStatus.FAILED, finding_code="repairable"),),
            repair_budget_remaining=True,
        ).decision
        is AcceptanceDecisionType.NEEDS_REPAIR
    )


def test_acceptance_optional_score_and_duplicate_result_protection() -> None:
    active, _ = policy(required=False, minimum_optional_score=0.8)
    candidate = result(VerifierStatus.PASSED, score=0.5)
    assert (
        AcceptancePolicyService().evaluate(active, uuid4(), (candidate,)).decision
        is AcceptanceDecisionType.REJECTED
    )
    assert (
        AcceptancePolicyService().evaluate(active, uuid4(), (candidate, candidate)).decision
        is AcceptanceDecisionType.VERIFICATION_ERROR
    )


def request(verifier_id: str, value, configuration=None) -> VerificationRequest:
    return VerificationRequest(
        verification_id=uuid4(),
        task_run_id=uuid4(),
        criterion_id=uuid4(),
        verifier_id=verifier_id,
        verifier_version="1",
        subject=VerificationSubject(
            subject_type=VerificationSubjectType.STRUCTURED_VALUE, inline_value=value
        ),
        configuration=configuration or {},
        requested_at=datetime.now(UTC),
        correlation_id=uuid4(),
    )


@pytest.mark.asyncio
async def test_file_policy_rejects_traversal_git_binary_and_symlink() -> None:
    verifier = FilePolicyVerifier()
    for path, extra in [
        ("../escape", {}),
        (".git/config", {}),
        ("image.bin", {"binary": True}),
        ("link", {"symlink": True}),
    ]:
        checked = await verifier.verify(
            request("coding.file_policy", {"files": [{"path": path, "size_bytes": 1, **extra}]})
        )
        assert checked.status is VerifierStatus.FAILED


@pytest.mark.asyncio
async def test_diff_and_dependency_policies_are_offline_and_bounded() -> None:
    diff = await DiffPolicyVerifier().verify(
        request("coding.diff_policy", {"paths": [".git/config"], "line_count": 1})
    )
    dependency = await DependencyPolicyVerifier().verify(
        request(
            "coding.dependency_policy",
            {"before_direct": ["pydantic"], "after_direct": ["pydantic", "unknown-package"]},
        )
    )
    approved = await DependencyPolicyVerifier().verify(
        request(
            "coding.dependency_policy",
            {"before_direct": ["pydantic"], "after_direct": ["pydantic", "sympy"]},
            {"approved_additions": ["sympy"]},
        )
    )
    assert diff.status is VerifierStatus.FAILED
    assert dependency.status is VerifierStatus.FAILED
    assert approved.status is VerifierStatus.PASSED
