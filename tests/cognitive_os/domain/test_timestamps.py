from datetime import UTC, datetime, timedelta, timezone

import pytest
from pydantic import ValidationError

from cognitive_os.domain.common import ArtifactRef
from cognitive_os.domain.identifiers import new_id


def artifact_at(value: datetime) -> ArtifactRef:
    return ArtifactRef(
        artifact_id=new_id(),
        media_type="text/plain",
        content_hash="b" * 64,
        size_bytes=0,
        storage_key="artifact.txt",
        created_at=value,
    )


def test_naive_timestamp_is_rejected() -> None:
    with pytest.raises(ValidationError):
        artifact_at(datetime(2026, 1, 1))


def test_aware_timestamp_normalizes_to_utc_and_round_trips() -> None:
    source = datetime(2026, 1, 1, 12, 30, 0, 123456, tzinfo=timezone(timedelta(hours=2)))
    artifact = artifact_at(source)
    restored = ArtifactRef.model_validate_json(artifact.model_dump_json())
    assert artifact.created_at.tzinfo is UTC
    assert restored.created_at == source.astimezone(UTC)
    assert restored.created_at.microsecond == 123456
