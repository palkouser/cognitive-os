from __future__ import annotations

from importlib.util import find_spec

import pytest

import cognitive_os
from cognitive_os.runtime import OptionalDependencyError, require_legacy_memory

pytestmark = pytest.mark.contract


def test_default_environment_imports_without_mem0() -> None:
    assert cognitive_os.__version__ == "0.1.0.dev1"
    assert find_spec("mem0") is None


def test_missing_legacy_memory_extra_has_clear_error() -> None:
    with pytest.raises(OptionalDependencyError, match="lightagent-legacy-memory"):
        require_legacy_memory()
