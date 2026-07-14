from pathlib import Path

import pytest

from cognitive_os.events import EventEnvelope
from cognitive_os.events.catalog import (
    UnknownEventTypeError,
    UnsupportedSchemaVersionError,
    build_default_event_catalog,
)
from cognitive_os.events.task_events import TaskCreated

FIXTURES = Path("tests/fixtures/contracts/v1")


@pytest.mark.contract
def test_catalog_decodes_fixture_to_registered_payload() -> None:
    envelope = EventEnvelope.model_validate_json(
        (FIXTURES / "task-created-envelope.json").read_bytes()
    )
    assert isinstance(build_default_event_catalog().decode_payload(envelope), TaskCreated)


@pytest.mark.contract
def test_catalog_rejects_unknown_type_and_version() -> None:
    catalog = build_default_event_catalog()
    with pytest.raises(UnknownEventTypeError):
        catalog.get_payload_model("missing.created", 1)
    with pytest.raises(UnsupportedSchemaVersionError):
        catalog.get_payload_model("task.created", 99)
