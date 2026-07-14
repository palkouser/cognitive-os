from uuid import UUID

from cognitive_os.domain.identifiers import new_id


def test_new_ids_are_distinct_uuid4_values() -> None:
    first = new_id()
    second = new_id()
    assert isinstance(first, UUID)
    assert first.version == 4
    assert first != second
