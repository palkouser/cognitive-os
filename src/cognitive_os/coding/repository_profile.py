"""Execution-free Python 3.12 repository profile detection."""

from __future__ import annotations

import tomllib
from pathlib import Path
from typing import Any

from cognitive_os.domain.coding import (
    RepositoryProfile,
    RepositoryProfileMismatch,
    RepositoryProfileStatus,
)


def _tool_present(root: Path, project: dict[str, Any], name: str) -> bool:
    tool = project.get("tool")
    if isinstance(tool, dict) and name in tool:
        return True
    dependencies = project.get("project", {}).get("dependencies", [])
    optional = project.get("project", {}).get("optional-dependencies", {})
    flattened = [*dependencies]
    if isinstance(optional, dict):
        flattened.extend(item for values in optional.values() for item in values)
    dependency_declared = any(
        str(item).lower().split("[")[0].startswith(name) for item in flattened
    )
    configuration_files = {
        "pytest": ("pytest.ini",),
        "ruff": ("ruff.toml", ".ruff.toml", "ruff.cognitive-os.toml"),
        "mypy": ("mypy.ini", ".mypy.ini"),
    }
    return dependency_declared or any(
        (root / relative).is_file() for relative in configuration_files[name]
    )


def detect_repository_profile(root: Path, *, rootless_docker: bool) -> RepositoryProfile:
    reasons: list[RepositoryProfileMismatch] = []
    git = (root / ".git").exists()
    pyproject_path = root / "pyproject.toml"
    has_pyproject = pyproject_path.is_file() and not pyproject_path.is_symlink()
    data: dict[str, Any] = {}
    if not git:
        reasons.append(
            RepositoryProfileMismatch(reason_code="not_git", message="Not a Git repository")
        )
    if not has_pyproject:
        reasons.append(
            RepositoryProfileMismatch(
                reason_code="missing_pyproject", message="pyproject.toml is required"
            )
        )
    else:
        try:
            parsed = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))
            if isinstance(parsed, dict):
                data = parsed
        except (OSError, UnicodeError, tomllib.TOMLDecodeError):
            reasons.append(
                RepositoryProfileMismatch(
                    reason_code="invalid_pyproject", message="pyproject.toml is malformed"
                )
            )
    requires_python = data.get("project", {}).get("requires-python")
    python_ok = isinstance(requires_python, str) and "3.12" in requires_python
    if data and not python_ok:
        reasons.append(
            RepositoryProfileMismatch(
                reason_code="python_version_mismatch",
                message="The repository must explicitly support Python 3.12",
            )
        )
    tools = {name: _tool_present(root, data, name) for name in ("pytest", "ruff", "mypy")}
    for name, present in tools.items():
        if data and not present:
            reasons.append(
                RepositoryProfileMismatch(
                    reason_code=f"missing_{name}", message=f"{name} configuration is required"
                )
            )
    if not rootless_docker:
        reasons.append(
            RepositoryProfileMismatch(
                reason_code="rootless_docker_unavailable",
                message="Rootless Docker is required",
            )
        )
    layout = "src" if (root / "src").is_dir() else "flat"
    return RepositoryProfile(
        status=(
            RepositoryProfileStatus.PROFILE_MISMATCH
            if reasons
            else RepositoryProfileStatus.SUPPORTED
        ),
        git_repository=git,
        has_pyproject=has_pyproject,
        python_version=str(requires_python) if requires_python else None,
        has_pytest=tools["pytest"],
        has_ruff=tools["ruff"],
        has_mypy=tools["mypy"],
        package_layout=layout,
        rootless_docker=rootless_docker,
        mismatches=tuple(reasons),
    )
