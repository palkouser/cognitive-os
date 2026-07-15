from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from cognitive_os.coding.indexing import RepositoryIndexer
from cognitive_os.coding.repository_profile import detect_repository_profile
from cognitive_os.domain.coding import (
    CodingLimits,
    CodingProblemExtension,
    RepositoryProfileStatus,
    RepositorySearchRequest,
)


def pyproject() -> str:
    return """[project]
name = "fixture"
version = "0.1.0"
requires-python = ">=3.12,<3.13"
dependencies = ["pytest>=9", "ruff>=0.12", "mypy>=1.16"]

[tool.pytest.ini_options]
testpaths = ["tests"]

[tool.ruff]
line-length = 100

[tool.mypy]
strict = true
"""


def test_coding_contracts_are_immutable_bounded_and_path_safe(tmp_path: Path) -> None:
    problem = CodingProblemExtension(
        repository_path=tmp_path,
        base_commit="a" * 40,
        issue_description="Fix the boundary condition.",
        expected_behavior="The boundary returns the expected value.",
        allowed_paths=("src", "tests"),
    )
    assert problem.canonical_hash() == problem.canonical_hash()
    with pytest.raises(ValidationError):
        problem.issue_description = "changed"  # type: ignore[misc]
    with pytest.raises(ValidationError):
        CodingLimits(maximum_diff_lines=1001)
    with pytest.raises(ValidationError):
        problem.model_copy(update={"allowed_paths": ("../escape",)}, deep=True).__class__(
            **(problem.model_dump() | {"allowed_paths": ("../escape",)})
        )


def test_profile_detector_is_execution_free_and_reports_each_mismatch(tmp_path: Path) -> None:
    profile = detect_repository_profile(tmp_path, rootless_docker=False)
    assert profile.status is RepositoryProfileStatus.PROFILE_MISMATCH
    assert {item.reason_code for item in profile.mismatches} == {
        "not_git",
        "missing_pyproject",
        "rootless_docker_unavailable",
    }
    (tmp_path / ".git").mkdir()
    (tmp_path / "pyproject.toml").write_text(pyproject(), encoding="utf-8")
    supported = detect_repository_profile(tmp_path, rootless_docker=True)
    assert supported.status is RepositoryProfileStatus.SUPPORTED


def test_profile_detector_rejects_malformed_toml(tmp_path: Path) -> None:
    (tmp_path / ".git").mkdir()
    (tmp_path / "pyproject.toml").write_text("[project", encoding="utf-8")
    profile = detect_repository_profile(tmp_path, rootless_docker=True)
    assert "invalid_pyproject" in {item.reason_code for item in profile.mismatches}


def test_profile_detector_does_not_follow_pyproject_symlink(tmp_path: Path) -> None:
    (tmp_path / ".git").mkdir()
    external = tmp_path.parent / f"external-{tmp_path.name}.toml"
    external.write_text(pyproject(), encoding="utf-8")
    (tmp_path / "pyproject.toml").symlink_to(external)
    profile = detect_repository_profile(tmp_path, rootless_docker=True)
    assert "missing_pyproject" in {item.reason_code for item in profile.mismatches}


def test_repository_index_is_bounded_deterministic_and_adversarial_safe(tmp_path: Path) -> None:
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "good.py").write_text(
        '"""Module."""\nimport os\n\ndef value(x: int) -> int:\n    return x + 1\n',
        encoding="utf-8",
    )
    (tmp_path / "src" / "bad.py").write_text("def broken(:\n", encoding="utf-8")
    (tmp_path / "src" / "binary.py").write_bytes(b"\x00binary")
    (tmp_path / "outside").symlink_to(Path("/tmp"), target_is_directory=True)
    indexer = RepositoryIndexer(CodingLimits())
    first = indexer.build(tmp_path, "b" * 40, 0)
    second = indexer.build(tmp_path, "b" * 40, 0)
    assert first.canonical_hash() == second.canonical_hash()
    assert [item.path for item in first.files] == sorted(item.path for item in first.files)
    assert next(item for item in first.modules if item.path == "src/bad.py").parse_error
    assert next(item for item in first.files if item.path == "src/binary.py").binary
    assert next(item for item in first.files if item.path == "outside").symlink
    results = indexer.search(tmp_path, RepositorySearchRequest(query="return", maximum_results=2))
    assert [(item.path, item.line) for item in results] == [("src/good.py", 5)]
