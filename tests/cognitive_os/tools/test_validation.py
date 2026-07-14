import pytest

from cognitive_os.tools.errors import ToolValidationError
from cognitive_os.tools.validation import validate_schema, validate_value


def test_validation_rejects_invalid_arguments_and_remote_refs() -> None:
    schema = {
        "type": "object",
        "properties": {"value": {"type": "string"}},
        "required": ["value"],
        "additionalProperties": False,
    }
    assert validate_value({"value": "ok"}, schema) == {"value": "ok"}
    with pytest.raises(ToolValidationError):
        validate_value({"value": 1}, schema)
    with pytest.raises(ToolValidationError):
        validate_schema({"type": "object", "$ref": "https://example.test/schema"})
