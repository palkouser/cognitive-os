from pathlib import Path

import pytest

from cognitive_os.domain.verifiers import VerifierDescriptor


@pytest.mark.contract
def test_verifier_schema_snapshots_are_exported() -> None:
    required = (
        "verifier-capability.schema.json",
        "verifier-descriptor.schema.json",
        "verification-request.schema.json",
        "verification-execution.schema.json",
        "verification-bundle.schema.json",
    )
    root = Path("schemas/v1/domain")
    assert all((root / name).is_file() for name in required)
    assert VerifierDescriptor.model_json_schema()["additionalProperties"] is False
