"""Bounded JSON-Schema validation for tool inputs and outputs."""

from __future__ import annotations

import json
from copy import deepcopy
from typing import cast

from jsonschema import Draft202012Validator, ValidationError

from cognitive_os.domain.common import JsonValue

from .errors import ToolValidationError

MAX_SCHEMA_BYTES = 65_536
MAX_SCHEMA_DEPTH = 24


def validate_schema(schema: dict[str, JsonValue]) -> None:
    if len(json.dumps(schema, separators=(",", ":")).encode()) > MAX_SCHEMA_BYTES:
        raise ToolValidationError("tool schema exceeds the size limit")
    if _depth(schema) > MAX_SCHEMA_DEPTH:
        raise ToolValidationError("tool schema exceeds the depth limit")
    if schema.get("type") != "object":
        raise ToolValidationError("tool schema must describe a JSON object")
    if _contains_remote_reference(schema):
        raise ToolValidationError("remote schema references are forbidden")
    try:
        Draft202012Validator.check_schema(schema)
    except Exception as error:
        raise ToolValidationError("tool schema is invalid") from error


def validate_value(value: JsonValue, schema: dict[str, JsonValue]) -> JsonValue:
    validate_schema(schema)
    copied = deepcopy(value)
    try:
        Draft202012Validator(cast(dict[str, object], schema)).validate(copied)
    except ValidationError as error:
        raise ToolValidationError(f"tool value failed validation at {list(error.path)}") from error
    return copied


def _depth(value: JsonValue, current: int = 0) -> int:
    if isinstance(value, dict):
        return max((_depth(item, current + 1) for item in value.values()), default=current)
    if isinstance(value, list):
        return max((_depth(item, current + 1) for item in value), default=current)
    return current


def _contains_remote_reference(value: JsonValue) -> bool:
    if isinstance(value, dict):
        for key, item in value.items():
            if key == "$ref" and isinstance(item, str) and not item.startswith("#"):
                return True
            if _contains_remote_reference(item):
                return True
    if isinstance(value, list):
        return any(_contains_remote_reference(item) for item in value)
    return False
