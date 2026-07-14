"""Canonical benchmark hashing."""

import json
from hashlib import sha256
from typing import Any


def canonical_hash(value: Any) -> str:
    if hasattr(value, "model_dump"):
        value = value.model_dump(mode="json")
    return sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
