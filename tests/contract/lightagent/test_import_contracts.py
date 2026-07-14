from __future__ import annotations

import pytest

pytestmark = pytest.mark.contract


def test_lightagent_import_contract() -> None:
    import LightAgent

    assert LightAgent.LightAgent is not None
    assert LightAgent.__version__ == "0.9.1"


def test_lightflow_import_contract() -> None:
    from LightAgent import LightFlow

    assert LightFlow is not None
