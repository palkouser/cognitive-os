"""Locale-independent semantic canonicalization."""

import json
import re
import unicodedata
from decimal import Decimal, InvalidOperation
from hashlib import sha256

from cognitive_os.domain.semantic_memory import SemanticLiteral, SemanticLiteralKind, SemanticValue

_IDENTIFIER = re.compile(r"^[a-z0-9][a-z0-9._:/@+-]*$")
_VERSION = re.compile(r"^[0-9]+(?:\.[0-9]+)*(?:[-+][0-9A-Za-z.-]+)?$")


def canonical_identifier(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value).strip().casefold()
    if not normalized.isascii() or not _IDENTIFIER.fullmatch(normalized):
        raise ValueError("semantic identifier must be unambiguous ASCII")
    return normalized


def canonical_text(value: str) -> str:
    return " ".join(unicodedata.normalize("NFC", value).split())


def canonical_decimal(value: str | Decimal) -> Decimal:
    try:
        result = Decimal(value)
    except InvalidOperation as error:
        raise ValueError("invalid decimal value") from error
    if not result.is_finite():
        raise ValueError("decimal value must be finite")
    return result.normalize()


def canonical_value(value: SemanticValue) -> str:
    if isinstance(value, SemanticLiteral):
        raw = value.value
        if value.literal_kind is SemanticLiteralKind.DECIMAL:
            raw = format(canonical_decimal(str(raw)), "f")
        elif isinstance(raw, str):
            raw = canonical_text(raw)
        payload = {"kind": value.literal_kind.value, "unit": value.unit, "value": raw}
    else:
        payload = value.model_dump(mode="json", exclude={"display_label"})
    return json.dumps(payload, default=str, sort_keys=True, separators=(",", ":"))


def deterministic_claim_key(
    scope_key: str, subject_key: str, predicate_id: str, value: SemanticValue
) -> str:
    payload = "|".join(
        (
            canonical_identifier(scope_key),
            canonical_identifier(subject_key),
            canonical_identifier(predicate_id),
            canonical_value(value),
        )
    )
    return sha256(payload.encode()).hexdigest()
