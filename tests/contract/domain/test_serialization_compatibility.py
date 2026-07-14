import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from cognitive_os.events import EventEnvelope, deserialize_envelope, serialize_envelope
from cognitive_os.events.hashing import sha256_digest

FIXTURE = Path("tests/fixtures/contracts/v1/task-created-envelope.json")


@pytest.mark.contract
def test_v1_envelope_has_stable_canonical_representation() -> None:
    envelope = EventEnvelope.model_validate_json(FIXTURE.read_bytes())
    restored = deserialize_envelope(serialize_envelope(envelope))
    assert restored == envelope
    assert sha256_digest(restored.payload) == restored.payload_hash


@pytest.mark.contract
def test_fixture_tampering_is_detected() -> None:
    value = json.loads(FIXTURE.read_text())
    value["payload"]["task"]["title"] = "Tampered title"
    with pytest.raises(ValidationError, match="hash mismatch"):
        EventEnvelope.model_validate(value)
