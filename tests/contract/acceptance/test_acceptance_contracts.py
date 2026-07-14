from pathlib import Path

import pytest


@pytest.mark.contract
def test_acceptance_policy_and_decision_schemas_exist() -> None:
    root = Path("schemas/v1/domain")
    assert (root / "acceptance-policy.schema.json").is_file()
    assert (root / "acceptance-decision.schema.json").is_file()
    assert (root / "criterion-evaluation.schema.json").is_file()
