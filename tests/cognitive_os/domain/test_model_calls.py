from datetime import timedelta

import pytest
from pydantic import ValidationError

from cognitive_os.domain import CallStatus, ErrorInfo, ModelCallResultRecord, new_id


def test_model_result_round_trip(model_result: ModelCallResultRecord) -> None:
    assert ModelCallResultRecord.model_validate_json(model_result.model_dump_json()) == model_result


def test_failed_model_result_requires_error(now) -> None:
    with pytest.raises(ValidationError):
        ModelCallResultRecord(
            model_call_id=new_id(),
            status=CallStatus.FAILED,
            started_at=now,
            finished_at=now + timedelta(seconds=1),
        )
    valid = ModelCallResultRecord(
        model_call_id=new_id(),
        status=CallStatus.FAILED,
        started_at=now,
        finished_at=now + timedelta(seconds=1),
        error=ErrorInfo(code="provider_error", message="Provider failed"),
    )
    assert valid.error is not None
