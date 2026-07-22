from __future__ import annotations

import os
import subprocess  # nosec B404 - deterministic Git fixture construction only
from pathlib import Path
from uuid import uuid4

import pytest

from cognitive_os.changes.isolation import (
    ChangeArtifactNamespace,
    ChangeWorktreeIsolation,
    isolate_configuration,
    validate_database_clone,
)
from cognitive_os.infrastructure.repository import GitCommandRunner, GitRepositoryService
from cognitive_os.infrastructure.repository.errors import RepositoryPolicyError


def git(repository: Path, *arguments: str) -> str:
    environment = os.environ | {
        "GIT_AUTHOR_NAME": "Cognitive OS",
        "GIT_AUTHOR_EMAIL": "fixture@example.invalid",
        "GIT_COMMITTER_NAME": "Cognitive OS",
        "GIT_COMMITTER_EMAIL": "fixture@example.invalid",
        "GIT_AUTHOR_DATE": "2024-01-01T00:00:00Z",
        "GIT_COMMITTER_DATE": "2024-01-01T00:00:00Z",
    }
    return subprocess.run(  # nosec B603
        ("git", "-c", "commit.gpgsign=false", "-C", str(repository), *arguments),
        check=True,
        capture_output=True,
        stdin=subprocess.DEVNULL,
        text=True,
        env=environment,
    ).stdout.strip()


@pytest.mark.asyncio
async def test_change_worktree_is_detached_locked_scoped_and_repairable(
    tmp_path: Path,
) -> None:
    repository = tmp_path / "repository"
    repository.mkdir()
    git(repository, "init", "-q")
    (repository / "value.py").write_text("VALUE = 1\n", encoding="utf-8")
    git(repository, "add", "value.py")
    git(repository, "commit", "-q", "-m", "fixture")
    commit = git(repository, "rev-parse", "HEAD")
    git_service = GitRepositoryService((tmp_path,), GitCommandRunner())
    isolation = ChangeWorktreeIsolation(
        tmp_path / "change-workspaces",
        tmp_path / "change-archives",
        repository,
        git_service,
    )
    experiment_id = uuid4()
    descriptor = await isolation.prepare(experiment_id, commit)
    workspace = tmp_path / "change-workspaces" / str(experiment_id) / "worktree"
    assert git(workspace, "rev-parse", "--abbrev-ref", "HEAD") == "HEAD"
    assert "locked controlled-change" in await git_service.list_worktrees(repository)
    (workspace / "value.py").write_text("VALUE = 2\n", encoding="utf-8")
    patch_hash, changed = await isolation.capture(experiment_id, descriptor, ("value.py",))
    assert len(patch_hash) == 64 and changed == ("value.py",)
    assert (repository / "value.py").read_text(encoding="utf-8") == "VALUE = 1\n"
    await isolation.repair(experiment_id, descriptor)
    await isolation.cleanup(experiment_id, descriptor)
    assert not workspace.exists()
    assert git(repository, "status", "--porcelain") == ""


@pytest.mark.asyncio
async def test_change_worktree_blocks_scope_escape(tmp_path: Path) -> None:
    repository = tmp_path / "repository"
    repository.mkdir()
    git(repository, "init", "-q")
    (repository / "allowed.txt").write_text("ok\n", encoding="utf-8")
    git(repository, "add", "allowed.txt")
    git(repository, "commit", "-q", "-m", "fixture")
    commit = git(repository, "rev-parse", "HEAD")
    git_service = GitRepositoryService((tmp_path,), GitCommandRunner())
    isolation = ChangeWorktreeIsolation(
        tmp_path / "workspaces", tmp_path / "archives", repository, git_service
    )
    experiment_id = uuid4()
    descriptor = await isolation.prepare(experiment_id, commit)
    workspace = tmp_path / "workspaces" / str(experiment_id) / "worktree"
    (workspace / "escape.txt").write_text("forbidden\n", encoding="utf-8")
    with pytest.raises(RepositoryPolicyError, match="forbidden path"):
        await isolation.capture(experiment_id, descriptor, ("allowed.txt",))
    await isolation.cleanup(experiment_id, descriptor, archive=False)


def test_configuration_database_and_artifact_namespaces_fail_closed(tmp_path: Path) -> None:
    baseline, candidate = isolate_configuration(
        {"retrieval.limit": 5}, {"retrieval.limit": 8}, ("retrieval.limit",)
    )
    assert baseline != candidate
    with pytest.raises(RepositoryPolicyError, match="approved keys"):
        isolate_configuration({"safe": 1}, {"unsafe": 2}, ("safe",))
    with pytest.raises(RepositoryPolicyError, match="secret-bearing"):
        isolate_configuration({"provider_token": "redacted"}, {}, ())
    with pytest.raises(RepositoryPolicyError, match="active database"):
        validate_database_clone("active", "active")
    assert len(validate_database_clone("active", "change_fixture")) == 64
    namespace = ChangeArtifactNamespace(tmp_path / "artifacts", uuid4())
    assert namespace.put(b"immutable evidence") == namespace.put(b"immutable evidence")
    link = tmp_path / "artifact-link"
    link.symlink_to(tmp_path / "artifacts", target_is_directory=True)
    with pytest.raises(RepositoryPolicyError, match="symlink"):
        ChangeArtifactNamespace(link, uuid4())
