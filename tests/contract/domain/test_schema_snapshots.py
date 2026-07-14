from pathlib import Path

import pytest

from cognitive_os.schemas.export import check_schemas


@pytest.mark.contract
def test_tracked_schema_snapshots_are_current() -> None:
    assert check_schemas(Path("schemas"))
