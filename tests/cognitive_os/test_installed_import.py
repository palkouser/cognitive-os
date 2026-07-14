from __future__ import annotations

from pathlib import Path

import cognitive_os


def test_cognitive_os_imports_from_installed_package() -> None:
    module_path = Path(cognitive_os.__file__).resolve()
    assert "src/cognitive_os" in module_path.as_posix()
