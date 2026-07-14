from datetime import UTC, datetime
from uuid import uuid4

import pytest

from cognitive_os.controller.checkpoint import CheckpointCodec
from cognitive_os.controller.errors import CheckpointValidationError
from cognitive_os.domain.controller import ControllerState, ControllerStateSnapshot, ControllerUsage


def test_checkpoint_hash_and_round_trip() -> None:
    now = datetime.now(UTC)
    task_run_id = uuid4()
    usage = ControllerUsage(started_at=now, last_updated_at=now)
    snapshot = ControllerStateSnapshot(
        task_run_id=task_run_id,
        state=ControllerState.READY,
        usage=usage,
        last_stream_version=3,
        updated_at=now,
    )
    checkpoint = CheckpointCodec.create(
        checkpoint_id=uuid4(),
        task_run_id=task_run_id,
        controller_state=snapshot,
        problem_representation=None,
        controller_plan=None,
        usage=usage,
        event_stream_version=3,
        created_at=now,
    )
    assert CheckpointCodec.deserialize(CheckpointCodec.serialize(checkpoint)) == checkpoint
    with pytest.raises(CheckpointValidationError):
        CheckpointCodec.verify(checkpoint.model_copy(update={"content_hash": "f" * 64}))
