import pytest
from pydantic import ValidationError

from cognitive_os.domain import ArtifactRef, TokenUsage, new_id


def test_artifact_validation(now) -> None:
    with pytest.raises(ValidationError):
        ArtifactRef(
            artifact_id=new_id(),
            media_type="text/plain",
            content_hash="INVALID",
            size_bytes=-1,
            storage_key="/etc/passwd",
            created_at=now,
        )


def test_token_total_covers_input_and_output() -> None:
    with pytest.raises(ValidationError):
        TokenUsage(input_tokens=5, output_tokens=5, total_tokens=9)
    assert TokenUsage(input_tokens=5, output_tokens=5, total_tokens=10).total_tokens == 10
