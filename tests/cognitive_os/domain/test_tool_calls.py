from datetime import timedelta

import pytest
from pydantic import ValidationError

from cognitive_os.domain import CallStatus, ToolCallRequestRecord, ToolCallResultRecord


def test_tool_records_round_trip(tool_request, tool_result) -> None:
    assert ToolCallRequestRecord.model_validate_json(tool_request.model_dump_json()) == tool_request
    assert ToolCallResultRecord.model_validate_json(tool_result.model_dump_json()) == tool_result


def test_failed_process_tool_may_use_nonzero_exit_code(tool_request, now) -> None:
    result = ToolCallResultRecord(
        tool_call_id=tool_request.tool_call_id,
        status=CallStatus.FAILED,
        started_at=now,
        finished_at=now + timedelta(seconds=1),
        exit_code=2,
    )
    assert result.exit_code == 2


def test_failed_non_process_tool_requires_error(tool_request, now) -> None:
    with pytest.raises(ValidationError):
        ToolCallResultRecord(
            tool_call_id=tool_request.tool_call_id,
            status=CallStatus.FAILED,
            started_at=now,
            finished_at=now + timedelta(seconds=1),
        )
