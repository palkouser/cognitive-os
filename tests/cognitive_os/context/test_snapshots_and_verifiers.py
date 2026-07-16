from uuid import UUID

from cognitive_os.context.snapshots import source_snapshot_matches, stale_source_codes
from cognitive_os.domain.context import ContextSourceSnapshot, EventStreamSnapshot

from .helpers import NOW


def test_source_snapshot_detects_stale_task_stream() -> None:
    expected = ContextSourceSnapshot(
        event_streams=(EventStreamSnapshot(stream_id=UUID(int=1), upper_version=4),),
        captured_at=NOW,
    )
    current = ContextSourceSnapshot(
        event_streams=(EventStreamSnapshot(stream_id=UUID(int=1), upper_version=5),),
        captured_at=NOW,
    )
    assert not source_snapshot_matches(expected, current)
    assert stale_source_codes(expected, current) == ("event_stream_version_changed",)
