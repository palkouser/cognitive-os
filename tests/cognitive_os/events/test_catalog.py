import pytest

from cognitive_os.events.catalog import (
    UnknownEventTypeError,
    UnsupportedSchemaVersionError,
    build_default_event_catalog,
)
from cognitive_os.events.task_events import TaskCreated


def test_default_catalog_is_explicit_and_complete() -> None:
    catalog = build_default_event_catalog()
    assert len(catalog.list_event_types()) == 106
    assert catalog.get_payload_model("task.created", 1) is TaskCreated


def test_unknown_type_version_and_duplicate_registration_fail() -> None:
    catalog = build_default_event_catalog()
    with pytest.raises(UnknownEventTypeError):
        catalog.get_payload_model("unknown.created", 1)
    with pytest.raises(UnsupportedSchemaVersionError):
        catalog.get_payload_model("task.created", 2)
    with pytest.raises(ValueError):
        catalog.register(TaskCreated)
