import pytest
from pydantic import ValidationError

from cognitive_os.domain import VerificationSubjectRef, VerifierResult, VerifierStatus, new_id


def test_verifier_result_round_trip(verifier_result: VerifierResult) -> None:
    assert VerifierResult.model_validate_json(verifier_result.model_dump_json()) == verifier_result


def test_subject_requires_stable_reference() -> None:
    with pytest.raises(ValidationError):
        VerificationSubjectRef(subject_type="task")


def test_failed_verifier_requires_finding(verifier_result: VerifierResult) -> None:
    with pytest.raises(ValidationError):
        VerifierResult.model_validate(
            {
                **verifier_result.model_dump(),
                "verifier_result_id": new_id(),
                "status": VerifierStatus.FAILED,
                "findings": [],
            }
        )
