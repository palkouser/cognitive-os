from __future__ import annotations

from importlib.metadata import requires

import pytest

pytestmark = pytest.mark.contract


def test_core_metadata_excludes_optional_integrations() -> None:
    declared = requires("cognitive-os") or []
    core = {item.split(";", 1)[0].strip().lower() for item in declared if "extra ==" not in item}

    assert not any(item.startswith("mem0ai") for item in core)
    assert not any(item.startswith("boto3") for item in core)
    assert not any(item.startswith("langfuse") for item in core)
