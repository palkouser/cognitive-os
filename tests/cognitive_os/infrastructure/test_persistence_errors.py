from cognitive_os.domain import new_id
from cognitive_os.infrastructure.errors import WrongExpectedVersionError


def test_wrong_expected_version_exposes_structured_fields() -> None:
    stream_id = new_id()
    error = WrongExpectedVersionError(stream_id, 2, 3)
    assert (error.stream_id, error.expected_version, error.actual_version) == (stream_id, 2, 3)
    assert "expected 2, actual 3" in str(error)
