import math

import pytest

from cognitive_os.events.hashing import sha256_digest
from cognitive_os.events.serialization import canonical_json_bytes


def test_canonical_json_ignores_mapping_insertion_order_and_preserves_utf8() -> None:
    first = {"message": "Hello 🌍", "count": 2}
    second = {"count": 2, "message": "Hello 🌍"}
    assert canonical_json_bytes(first) == canonical_json_bytes(second)
    assert canonical_json_bytes(first).decode() == '{"count":2,"message":"Hello 🌍"}'
    assert sha256_digest(first) == sha256_digest(second)
    assert sha256_digest({**first, "count": 3}) != sha256_digest(first)


def test_nan_and_infinity_are_rejected() -> None:
    with pytest.raises(ValueError):
        canonical_json_bytes({"value": math.nan})
    with pytest.raises(ValueError):
        canonical_json_bytes({"value": math.inf})
