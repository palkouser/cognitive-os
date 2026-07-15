from __future__ import annotations

import os
import subprocess  # nosec B404 - test fixture construction only
from hashlib import sha256
from pathlib import Path
from uuid import uuid4

import pytest

from cognitive_os.coding.workspace import WorkspaceManager
from cognitive_os.domain.coding import WorkspaceDisposition, WorkspaceRequest
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
    result = subprocess.run(  # nosec B603
        ("git", "-c", "commit.gpgsign=false", "-C", str(repository), *arguments),
        check=True,
        capture_output=True,
        stdin=subprocess.DEVNULL,
        text=True,
        env=environment,
    )
    return result.stdout.strip()


@pytest.mark.asyncio
async def test_detached_worktree_preserves_main_and_cleans_up(tmp_path: Path) -> None:
    repository = tmp_path / "repository"
    worktrees = tmp_path / "worktrees"
    archives = tmp_path / "archives"
    repository.mkdir()
    git(repository, "init", "-q")
    (repository / "value.py").write_text("VALUE = 1\n", encoding="utf-8")
    git(repository, "add", "value.py")
    git(repository, "commit", "-q", "-m", "fixture")
    commit = git(repository, "rev-parse", "HEAD")
    service = GitRepositoryService((tmp_path,), GitCommandRunner())
    reference = await service.validate(repository, commit)
    manager = WorkspaceManager(worktrees, archives, service)
    task_run_id = uuid4()
    descriptor = await manager.prepare(
        WorkspaceRequest(
            task_run_id=task_run_id,
            repository=reference,
            idempotency_key=sha256(str(task_run_id).encode()).hexdigest(),
        )
    )
    assert descriptor.mount_descriptor_hash is not None
    workspace = manager.path_for(descriptor)
    assert git(workspace, "rev-parse", "--abbrev-ref", "HEAD") == "HEAD"
    assert git(workspace, "rev-parse", "HEAD") == commit
    restarted_manager = WorkspaceManager(worktrees, archives, service)
    with pytest.raises(RepositoryPolicyError, match="one active coding workspace"):
        await restarted_manager.prepare(
            WorkspaceRequest(
                task_run_id=uuid4(),
                repository=reference,
                idempotency_key="e" * 64,
            )
        )
    (workspace / "value.py").write_text("VALUE = 2\n", encoding="utf-8")
    assert (repository / "value.py").read_text(encoding="utf-8") == "VALUE = 1\n"
    integrity = await manager.integrity(descriptor)
    assert integrity.git_head == commit
    result = await manager.cleanup(descriptor, disposition=WorkspaceDisposition.ARCHIVE)
    assert result.completed
    assert not workspace.exists()
    assert (archives / str(descriptor.workspace_id) / "unified-diff.patch").exists()
    assert git(repository, "status", "--porcelain") == ""
