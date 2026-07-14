from __future__ import annotations

from importlib.util import find_spec

import pytest

pytestmark = pytest.mark.contract


@pytest.mark.parametrize("package", ["boto3", "langfuse", "mem0"])
def test_optional_package_is_absent_from_default_environment(package: str) -> None:
    assert find_spec(package) is None


def test_default_lightagent_import_does_not_require_optional_packages() -> None:
    import LightAgent

    assert LightAgent.__version__ == "0.9.1"
