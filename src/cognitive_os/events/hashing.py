"""Deterministic SHA-256 hashing for JSON-compatible values."""

from hashlib import sha256

from cognitive_os.domain.common import JsonValue

from .serialization import canonical_json_bytes


def sha256_digest(value: JsonValue) -> str:
    return sha256(canonical_json_bytes(value)).hexdigest()
