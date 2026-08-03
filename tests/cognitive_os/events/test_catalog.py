import pytest

from cognitive_os.events.catalog import (
    UnknownEventTypeError,
    UnsupportedSchemaVersionError,
    build_default_event_catalog,
)
from cognitive_os.events.task_events import TaskCreated


def test_default_catalog_is_explicit_and_complete() -> None:
    catalog = build_default_event_catalog()
    # 207 before Sprint 21C1, plus the five learned events it adds: observation intake,
    # artifact-lineage linking, activation approval, rollback and read audit. Sprint 21D2's
    # campaign sequence receipt is the 214th: it existed from W2 but was declared below
    # `CODING_EVENT_MODELS`, so the catalog never registered it and the Event Store refused it
    # as an unsupported contract (W4-F1). This count is what would have caught that in W2.
    assert len(catalog.list_event_types()) == 214
    assert catalog.get_payload_model("task.created", 1) is TaskCreated


def test_unknown_type_version_and_duplicate_registration_fail() -> None:
    catalog = build_default_event_catalog()
    with pytest.raises(UnknownEventTypeError):
        catalog.get_payload_model("unknown.created", 1)
    with pytest.raises(UnsupportedSchemaVersionError):
        catalog.get_payload_model("task.created", 2)
    with pytest.raises(ValueError):
        catalog.register(TaskCreated)
