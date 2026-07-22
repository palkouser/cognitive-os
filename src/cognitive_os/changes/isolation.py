"""Controlled-change adapters over existing workspace and artifact boundaries."""

from __future__ import annotations

import json
from hashlib import sha256
from pathlib import Path
from uuid import UUID

from cognitive_os.coding.workspace import WorkspaceManager
from cognitive_os.domain.coding import (
    WorkspaceDescriptor,
    WorkspaceDisposition,
    WorkspaceRequest,
)
from cognitive_os.infrastructure.artifacts.filesystem import ContentAddressedFilesystem
from cognitive_os.infrastructure.repository.errors import RepositoryPolicyError
from cognitive_os.infrastructure.repository.git_repository import GitRepositoryService


class ChangeWorktreeIsolation:
    """A thin Sprint 19 policy layer over the Sprint 8 WorkspaceManager."""

    def __init__(
        self,
        workspace_root: Path,
        archive_root: Path,
        repository: Path,
        repository_service: GitRepositoryService,
    ) -> None:
        self.workspace_root = workspace_root.resolve()
        self.archive_root = archive_root.resolve()
        self.repository = repository.resolve()
        if self.workspace_root.is_relative_to(self.repository) or self.repository.is_relative_to(
            self.workspace_root
        ):
            raise RepositoryPolicyError("change worktrees must be outside the active checkout")
        self.repository_service = repository_service
        self._managers: dict[UUID, WorkspaceManager] = {}

    async def prepare(self, experiment_id: UUID, baseline_commit: str) -> WorkspaceDescriptor:
        root = self.workspace_root / str(experiment_id)
        if experiment_id in self._managers or root.exists():
            raise RepositoryPolicyError("experiment already owns a change worktree")
        reference = await self.repository_service.validate(self.repository, baseline_commit)
        manager = WorkspaceManager(
            root,
            self.archive_root / str(experiment_id),
            self.repository_service,
        )
        descriptor = await manager.prepare(
            WorkspaceRequest(
                task_run_id=experiment_id,
                repository=reference,
                idempotency_key=sha256(
                    f"change-worktree:{experiment_id}:{baseline_commit}".encode()
                ).hexdigest(),
                destination_name="worktree",
            )
        )
        path = manager.path_for(descriptor)
        await self.repository_service.lock_worktree(
            self.repository, path, f"controlled-change:{experiment_id}"
        )
        self._managers[experiment_id] = manager
        return descriptor

    async def capture(
        self, experiment_id: UUID, descriptor: WorkspaceDescriptor, allowed_paths: tuple[str, ...]
    ) -> tuple[str, tuple[str, ...]]:
        manager = self._manager(experiment_id)
        path = manager.path_for(descriptor)
        active_before = await self.repository_service.status(self.repository)
        status = await self.repository_service.status(path)
        changed = tuple(
            sorted(line[3:].strip().strip('"') for line in status.splitlines() if len(line) > 3)
        )
        if not set(changed).issubset(allowed_paths):
            raise RepositoryPolicyError("change worktree modified a forbidden path")
        diff = await self.repository_service.diff(path, descriptor.base_commit)
        if await self.repository_service.status(self.repository) != active_before:
            raise RepositoryPolicyError("active checkout changed during candidate capture")
        return sha256(diff.encode()).hexdigest(), changed

    async def cleanup(
        self,
        experiment_id: UUID,
        descriptor: WorkspaceDescriptor,
        *,
        archive: bool = True,
    ) -> None:
        manager = self._manager(experiment_id)
        path = manager.path_for(descriptor)
        await self.repository_service.unlock_worktree(self.repository, path)
        await manager.cleanup(
            descriptor,
            disposition=(WorkspaceDisposition.ARCHIVE if archive else WorkspaceDisposition.REMOVE),
        )
        self._managers.pop(experiment_id)

    async def repair(self, experiment_id: UUID, descriptor: WorkspaceDescriptor) -> None:
        manager = self._manager(experiment_id)
        await self.repository_service.repair_worktrees(
            self.repository, manager.path_for(descriptor)
        )

    def _manager(self, experiment_id: UUID) -> WorkspaceManager:
        try:
            return self._managers[experiment_id]
        except KeyError as error:
            raise RepositoryPolicyError("unknown controlled-change worktree") from error


class ChangeArtifactNamespace:
    def __init__(self, root: Path, experiment_id: UUID) -> None:
        if root.is_symlink():
            raise RepositoryPolicyError("artifact namespace root cannot be a symlink")
        root = root.resolve()
        self.path = root / str(experiment_id)
        if self.path.exists():
            raise RepositoryPolicyError("artifact namespace already exists")
        self.store = ContentAddressedFilesystem(self.path)

    def put(self, data: bytes) -> str:
        return self.store.put_bytes(data).content_hash


def isolate_configuration(
    baseline: dict[str, object], updates: dict[str, object], allowed_keys: tuple[str, ...]
) -> tuple[bytes, bytes]:
    if not set(updates).issubset(allowed_keys):
        raise RepositoryPolicyError("configuration update exceeds approved keys")
    if any(word in key.casefold() for key in baseline for word in ("secret", "token", "password")):
        raise RepositoryPolicyError("secret-bearing configuration cannot enter an experiment")
    candidate = {**baseline, **updates}

    def encode(value: dict[str, object]) -> bytes:
        return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()

    return encode(baseline), encode(candidate)


def validate_database_clone(active_reference: str, clone_reference: str) -> str:
    if not active_reference or active_reference == clone_reference:
        raise RepositoryPolicyError("database clone cannot reuse the active database identity")
    if any(marker in clone_reference.casefold() for marker in ("password", "@", "://")):
        raise RepositoryPolicyError("database clone manifest cannot contain a connection URL")
    return sha256(f"{active_reference}:{clone_reference}".encode()).hexdigest()
