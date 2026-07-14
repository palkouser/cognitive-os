from cognitive_os.verification.minimal import validate_schema


def test_schema_check_passes_and_fails_deterministically() -> None:
    schema = {
        "type": "object",
        "required": ["answer"],
        "properties": {"answer": {"type": "integer"}},
        "additionalProperties": False,
    }
    assert validate_schema({"answer": 42}, schema)[0]
    assert not validate_schema({"answer": "42"}, schema)[0]
