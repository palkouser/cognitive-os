"""Detached worktree lifecycle coordinated by a trusted host repository service."""

from __future__ import annotations

import fcntl
import json
import os
import shutil
from collections.abc import Iterator
from contextlib import contextmanager
from hashlib import sha256
from pathlib import Path
from uuid import UUID, uuid4

from cognitive_os.domain.coding import (
    CodingLimits,
    WorkspaceCleanupResult,
    WorkspaceDescriptor,
    WorkspaceDisposition,
    WorkspaceIntegritySnapshot,
    WorkspaceRecoveryClassification,
    WorkspaceRequest,
    WorkspaceState,
)
from cognitive_os.domain.common import utc_now
from cognitive_os.infrastructure.repository.errors import RepositoryPolicyError
from cognitive_os.infrastructure.repository.git_repository import GitRepositoryService

from .sandbox import build_sandbox_mount_descriptor

TERMINAL_WORKSPACE_STATES = {
    WorkspaceState.ARCHIVED,
    WorkspaceState.REMOVED,
    WorkspaceState.FAILED,
}

WORKSPACE_TRANSITIONS: dict[WorkspaceState, frozenset[WorkspaceState]] = {
    WorkspaceState.REQUESTED: frozenset({WorkspaceState.VALIDATING, WorkspaceState.FAILED}),
    WorkspaceState.VALIDATING: frozenset({WorkspaceState.PREPARED, WorkspaceState.FAILED}),
    WorkspaceState.PREPARED: frozenset(
        {
            WorkspaceState.MOUNTED,
            WorkspaceState.ACTIVE,
            WorkspaceState.ARCHIVED,
            WorkspaceState.REMOVED,
        }
    ),
    WorkspaceState.MOUNTED: frozenset(
        {WorkspaceState.ACTIVE, WorkspaceState.RECOVERY_REQUIRED, WorkspaceState.FAILED}
    ),
    WorkspaceState.ACTIVE: frozenset(
        {WorkspaceState.COLLECTING, WorkspaceState.RECOVERY_REQUIRED, WorkspaceState.FAILED}
    ),
    WorkspaceState.COLLECTING: frozenset(
        {WorkspaceState.ARCHIVED, WorkspaceState.REMOVED, WorkspaceState.RECOVERY_REQUIRED}
    ),
    WorkspaceState.RECOVERY_REQUIRED: frozenset(
        {
            WorkspaceState.ACTIVE,
            WorkspaceState.ARCHIVED,
            WorkspaceState.REMOVED,
            WorkspaceState.FAILED,
        }
    ),
    WorkspaceState.ARCHIVED: frozenset(),
    WorkspaceState.REMOVED: frozenset(),
    WorkspaceState.FAILED: frozenset(),
}


def can_transition_workspace(source: WorkspaceState, target: WorkspaceState) -> bool:
    return target in WORKSPACE_TRANSITIONS[source]


class WorkspaceManager:
    def __init__(
        self,
        worktree_root: Path,
        archive_root: Path,
        repository_service: GitRepositoryService,
        coding_limits: CodingLimits | None = None,
    ):
        self.worktree_root = worktree_root
        self.archive_root = archive_root
        self.repository_service = repository_service
        self._coding_limits = coding_limits or CodingLimits()
        self._paths: dict[UUID, Path] = {}
        self._repositories: dict[UUID, Path] = {}
        self._tasks: dict[UUID, UUID] = {}

    @contextmanager
    def _global_lock(self) -> Iterator[None]:
        self.worktree_root.mkdir(parents=True, exist_ok=True)
        lock_path = self.worktree_root / ".coding-workspace.lock"
        with lock_path.open("a+b") as handle:
            try:
                fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                raise RepositoryPolicyError(
                    "another coding workspace operation is active"
                ) from None
            try:
                yield
            finally:
                fcntl.flock(handle, fcntl.LOCK_UN)

    def path_for(self, descriptor: WorkspaceDescriptor) -> Path:
        path = self._paths.get(descriptor.workspace_id)
        if path is None or self._tasks.get(descriptor.workspace_id) != descriptor.task_run_id:
            raise RepositoryPolicyError("workspace is not owned by this task run")
        return path

    async def prepare(self, request: WorkspaceRequest) -> WorkspaceDescriptor:
        if request.task_run_id in self._tasks.values():
            raise RepositoryPolicyError("task run already owns a workspace")
        with self._global_lock():
            active = [
                path
                for path in self.worktree_root.iterdir()
                if path.is_dir() and not path.is_symlink()
            ]
            if active:
                raise RepositoryPolicyError("Sprint 8 permits one active coding workspace")
            repository = request.repository.repository_path
            await self.repository_service.validate(repository, request.repository.base_commit)
            destination = self.worktree_root / str(request.task_run_id)
            if destination.exists() or destination.is_symlink():
                raise RepositoryPolicyError("workspace destination already exists")
            main_before = await self.repository_service.status(repository)
            try:
                await self.repository_service.add_worktree(
                    repository, destination, request.repository.base_commit
                )
                head = await self.repository_service.head(destination)
                status = await self.repository_service.status(destination)
                main_after = await self.repository_service.status(repository)
                if head != request.repository.base_commit or status or main_before != main_after:
                    raise RepositoryPolicyError(
                        "worktree preparation violated repository integrity"
                    )
            except Exception:
                if destination.exists():
                    shutil.rmtree(destination, ignore_errors=True)
                raise
            workspace_id = uuid4()
            self._paths[workspace_id] = destination
            self._repositories[workspace_id] = repository
            self._tasks[workspace_id] = request.task_run_id
            sandbox_mount = build_sandbox_mount_descriptor(
                str(workspace_id), destination, self._coding_limits
            )
            return WorkspaceDescriptor(
                workspace_id=workspace_id,
                task_run_id=request.task_run_id,
                base_commit=request.repository.base_commit,
                workspace_revision=0,
                state=WorkspaceState.PREPARED,
                logical_name=f"coding-{request.task_run_id}",
                created_at=utc_now(),
                mount_descriptor_hash=sandbox_mount.canonical_hash(),
            )

    async def integrity(self, descriptor: WorkspaceDescriptor) -> WorkspaceIntegritySnapshot:
        path = self.path_for(descriptor)
        head = await self.repository_service.head(path)
        status = await self.repository_service.status(path)
        manifest: list[tuple[str, int, str]] = []
        for root, directories, files in os.walk(path, followlinks=False):
            directories[:] = sorted(item for item in directories if item != ".git")
            for name in sorted(files):
                candidate = Path(root) / name
                relative = candidate.relative_to(path).as_posix()
                if relative == ".git" or candidate.is_symlink():
                    continue
                try:
                    content = candidate.read_bytes()
                except OSError:
                    continue
                manifest.append((relative, len(content), sha256(content).hexdigest()))
        manifest_hash = sha256(json.dumps(manifest, separators=(",", ":")).encode()).hexdigest()
        return WorkspaceIntegritySnapshot(
            workspace_id=descriptor.workspace_id,
            workspace_revision=descriptor.workspace_revision,
            git_head=head,
            status_hash=sha256(status.encode()).hexdigest(),
            file_manifest_hash=manifest_hash,
            captured_at=utc_now(),
        )

    async def classify_recovery(
        self, descriptor: WorkspaceDescriptor
    ) -> WorkspaceRecoveryClassification:
        try:
            path = self.path_for(descriptor)
        except RepositoryPolicyError:
            return WorkspaceRecoveryClassification.NOT_PREPARED
        if not path.exists():
            return WorkspaceRecoveryClassification.ORPHANED
        try:
            head = await self.repository_service.head(path)
            status = await self.repository_service.status(path)
        except Exception:
            return WorkspaceRecoveryClassification.CORRUPT
        if head != descriptor.base_commit:
            return WorkspaceRecoveryClassification.REQUIRES_MANUAL_REVIEW
        if descriptor.state is WorkspaceState.RECOVERY_REQUIRED:
            return (
                WorkspaceRecoveryClassification.SAFE_TO_RESUME
                if not status
                else (WorkspaceRecoveryClassification.PREPARED_WITH_CHANGES)
            )
        return (
            WorkspaceRecoveryClassification.PREPARED_WITH_CHANGES
            if status
            else WorkspaceRecoveryClassification.PREPARED_CLEAN
        )

    async def cleanup(
        self,
        descriptor: WorkspaceDescriptor,
        *,
        dry_run: bool = False,
        disposition: WorkspaceDisposition = WorkspaceDisposition.REMOVE,
    ) -> WorkspaceCleanupResult:
        path = self.path_for(descriptor)
        if dry_run:
            return WorkspaceCleanupResult(
                workspace_id=descriptor.workspace_id,
                disposition=disposition,
                completed=False,
            )
        repository = self._repositories[descriptor.workspace_id]
        with self._global_lock():
            if disposition is WorkspaceDisposition.REMOVE:
                await self.repository_service.remove_worktree(repository, path)
            else:
                self.archive_root.mkdir(parents=True, exist_ok=True)
                archive = self.archive_root / str(descriptor.workspace_id)
                archive.mkdir(mode=0o700)
                diff = await self.repository_service.diff(path, descriptor.base_commit)
                (archive / "unified-diff.patch").write_text(diff, encoding="utf-8")
                await self.repository_service.remove_worktree(repository, path)
            self._paths.pop(descriptor.workspace_id, None)
            self._repositories.pop(descriptor.workspace_id, None)
            self._tasks.pop(descriptor.workspace_id, None)
        return WorkspaceCleanupResult(
            workspace_id=descriptor.workspace_id,
            disposition=disposition,
            completed=True,
        )
