from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from cognitive_os.controller.checkpoint import ContinuationTokenService
from cognitive_os.controller.errors import ContinuationRejected


def test_continuation_is_hashed_scoped_and_single_use() -> None:
    now = datetime.now(UTC)
    service = ContinuationTokenService(lambda: "opaque-test-value")
    task_run_id, checkpoint_id = uuid4(), uuid4()
    token, record = service.issue(
        task_run_id=task_run_id,
        checkpoint_id=checkpoint_id,
        event_stream_version=4,
        ttl_seconds=60,
        now=now,
    )
    assert record.token_hash != token
    consumed = service.consume(
        record=record,
        token=token,
        task_run_id=task_run_id,
        checkpoint_id=checkpoint_id,
        event_stream_version=4,
        now=now,
    )
    with pytest.raises(ContinuationRejected):
        service.consume(
            record=consumed,
            token=token,
            task_run_id=task_run_id,
            checkpoint_id=checkpoint_id,
            event_stream_version=4,
            now=now,
        )


def test_expired_continuation_is_rejected() -> None:
    now = datetime.now(UTC)
    service = ContinuationTokenService(lambda: "expired")
    token, record = service.issue(
        task_run_id=uuid4(), checkpoint_id=uuid4(), event_stream_version=1, ttl_seconds=1, now=now
    )
    with pytest.raises(ContinuationRejected):
        service.consume(
            record=record,
            token=token,
            task_run_id=record.task_run_id,
            checkpoint_id=record.checkpoint_id,
            event_stream_version=1,
            now=now + timedelta(seconds=2),
        )
