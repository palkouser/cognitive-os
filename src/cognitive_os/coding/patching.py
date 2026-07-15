"""Atomic policy-controlled Patch Service for detached worktrees."""

from __future__ import annotations

import os
import tempfile
from contextlib import suppress
from hashlib import sha256
from pathlib import Path

from cognitive_os.domain.coding import (
    ChangedFile,
    ChangedFileManifest,
    CodingLimits,
    DependencyChangePolicy,
    PatchApplicationResult,
    PatchProposal,
    PathPolicy,
    WorkspaceDescriptor,
)

from .diff import DiffPolicyError, apply_file_patch, parse_unified_diff
from .path_policy import WorkspacePathPolicy
from .workspace import WorkspaceManager


class PatchService:
    def __init__(
        self,
        workspaces: WorkspaceManager,
        limits: CodingLimits,
        path_policy: PathPolicy,
        dependency_policy: DependencyChangePolicy,
    ):
        self.workspaces = workspaces
        self.limits = limits
        self.path_policy = path_policy
        self.dependency_policy = dependency_policy
        self._attempts: dict[object, int] = {}
        self._seen_proposals: dict[object, set[str]] = {}
        self._revisions: dict[object, list[dict[str, bytes | None]]] = {}
        self._cumulative_lines: dict[object, int] = {}
        self._cumulative_paths: dict[object, set[str]] = {}
        self._generated_paths: dict[object, set[str]] = {}

    def _policy(self, root: Path) -> WorkspacePathPolicy:
        return WorkspacePathPolicy(root, self.path_policy, self.dependency_policy)

    @staticmethod
    def _read(path: Path) -> bytes | None:
        return path.read_bytes() if path.exists() else None

    @staticmethod
    def _atomic_write(path: Path, content: bytes) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
        try:
            with os.fdopen(descriptor, "wb") as handle:
                handle.write(content)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, path)
        except Exception:
            with suppress(FileNotFoundError):
                os.unlink(temporary)
            raise

    def _reserve_mutation(self, key: object, relative: str, diff_lines: int) -> None:
        paths = self._cumulative_paths.setdefault(key, set())
        proposed_paths = paths | {relative}
        if len(proposed_paths) > self.limits.maximum_changed_files:
            raise DiffPolicyError("changed_file_limit", "mutation changes too many files")
        proposed_lines = self._cumulative_lines.get(key, 0) + diff_lines
        if proposed_lines > self.limits.maximum_diff_lines:
            raise DiffPolicyError("diff_line_limit", "mutation exceeds cumulative diff line limit")
        self._cumulative_paths[key] = proposed_paths
        self._cumulative_lines[key] = proposed_lines

    async def apply(
        self, workspace: WorkspaceDescriptor, proposal: PatchProposal
    ) -> PatchApplicationResult:
        key = workspace.workspace_id
        attempts = self._attempts.get(key, 0) + 1
        self._attempts[key] = attempts
        if attempts > self.limits.maximum_patch_attempts:
            return PatchApplicationResult(
                applied=False,
                reason_code="patch_attempt_budget_exhausted",
                workspace_revision=workspace.workspace_revision,
            )
        proposal_hash = proposal.canonical_hash()
        seen = self._seen_proposals.setdefault(key, set())
        if proposal_hash in seen:
            return PatchApplicationResult(
                applied=False,
                reason_code="repeated_patch",
                workspace_revision=workspace.workspace_revision,
            )
        seen.add(proposal_hash)
        if proposal.expected_workspace_revision != workspace.workspace_revision:
            return PatchApplicationResult(
                applied=False,
                reason_code="stale_workspace_revision",
                workspace_revision=workspace.workspace_revision,
            )
        try:
            patches = parse_unified_diff(proposal.unified_diff)
            cumulative_paths = self._cumulative_paths.setdefault(key, set())
            proposed_paths = cumulative_paths | {item.path for item in patches}
            if len(proposed_paths) > self.limits.maximum_changed_files:
                raise DiffPolicyError("changed_file_limit", "patch changes too many files")
            if set(item.path for item in patches) != set(proposal.target_files):
                raise DiffPolicyError(
                    "proposal_target_mismatch", "diff and proposal targets differ"
                )
            root = self.workspaces.path_for(workspace)
            policy = self._policy(root)
            snapshots: dict[str, bytes | None] = {}
            replacements: dict[str, bytes | None] = {}
            changed: list[ChangedFile] = []
            total_lines = 0
            for patch in patches:
                target = policy.validate(patch.path)
                policy.validate_dependency(patch.path)
                policy.ensure_not_hardlinked(target)
                before = self._read(target)
                after = apply_file_patch(before, patch)
                if after is not None:
                    if len(after) > self.limits.maximum_indexed_file_bytes:
                        raise DiffPolicyError(
                            "file_size_limit", "resulting file exceeds size limit"
                        )
                    policy.scan_secret(after)
                snapshots[patch.path] = before
                replacements[patch.path] = after
                added = sum(line.startswith("+") for hunk in patch.hunks for line in hunk.lines)
                deleted = sum(line.startswith("-") for hunk in patch.hunks for line in hunk.lines)
                total_lines += added + deleted
                changed.append(
                    ChangedFile(
                        path=patch.path,
                        change_type=patch.change_type,
                        before_hash=sha256(before).hexdigest() if before is not None else None,
                        after_hash=sha256(after).hexdigest() if after is not None else None,
                        added_lines=added,
                        deleted_lines=deleted,
                    )
                )
            cumulative_lines = self._cumulative_lines.get(key, 0) + total_lines
            if cumulative_lines > self.limits.maximum_diff_lines:
                raise DiffPolicyError("diff_line_limit", "patch exceeds cumulative diff line limit")
            applied: list[str] = []
            try:
                for relative, content in replacements.items():
                    target = policy.validate(relative)
                    if content is None:
                        target.unlink()
                    else:
                        self._atomic_write(target, content)
                    applied.append(relative)
            except Exception:
                for relative in reversed(applied):
                    target = policy.validate(relative)
                    original = snapshots[relative]
                    if original is None:
                        target.unlink(missing_ok=True)
                    else:
                        self._atomic_write(target, original)
                raise
            self._revisions.setdefault(key, []).append(snapshots)
            self._cumulative_paths[key] = proposed_paths
            self._cumulative_lines[key] = cumulative_lines
            generated = self._generated_paths.setdefault(key, set())
            generated.update(path for path, before in snapshots.items() if before is None)
            manifest = ChangedFileManifest(
                base_commit=workspace.base_commit,
                workspace_revision=workspace.workspace_revision + 1,
                files=tuple(sorted(changed, key=lambda item: item.path)),
                total_diff_lines=total_lines,
            )
            return PatchApplicationResult(
                applied=True,
                workspace_revision=workspace.workspace_revision + 1,
                manifest=manifest,
                diff_hash=sha256(proposal.unified_diff.encode()).hexdigest(),
            )
        except DiffPolicyError as error:
            return PatchApplicationResult(
                applied=False,
                reason_code=error.reason_code,
                workspace_revision=workspace.workspace_revision,
            )

    async def rollback(self, workspace: WorkspaceDescriptor, revision: int) -> ChangedFileManifest:
        histories = self._revisions.get(workspace.workspace_id, [])
        if revision < 0 or revision >= len(histories):
            raise DiffPolicyError("unknown_revision", "rollback revision is unavailable")
        root = self.workspaces.path_for(workspace)
        policy = self._policy(root)
        snapshot = histories[revision]
        for relative, content in snapshot.items():
            target = policy.validate(relative)
            if content is None:
                target.unlink(missing_ok=True)
            else:
                self._atomic_write(target, content)
        return ChangedFileManifest(
            base_commit=workspace.base_commit,
            workspace_revision=revision,
            files=(),
            total_diff_lines=0,
        )

    async def write_file(
        self,
        workspace: WorkspaceDescriptor,
        relative: str,
        content: bytes,
        *,
        expected_before_hash: str | None = None,
    ) -> ChangedFile:
        root = self.workspaces.path_for(workspace)
        policy = self._policy(root)
        target = policy.validate(relative)
        policy.validate_dependency(relative)
        policy.ensure_not_hardlinked(target)
        policy.scan_secret(content)
        if len(content) > self.limits.maximum_indexed_file_bytes:
            raise DiffPolicyError("file_size_limit", "file exceeds size limit")
        before = self._read(target)
        actual = sha256(before).hexdigest() if before is not None else None
        if before is not None and expected_before_hash is None:
            raise DiffPolicyError(
                "expected_hash_required", "overwriting a file requires its expected content hash"
            )
        if expected_before_hash is not None and expected_before_hash != actual:
            raise DiffPolicyError("concurrent_modification", "expected file hash does not match")
        before_lines = len(before.splitlines()) if before is not None else 0
        self._reserve_mutation(
            workspace.workspace_id, relative, before_lines + len(content.splitlines())
        )
        self._atomic_write(target, content)
        from cognitive_os.domain.coding import ChangeType

        if before is None:
            self._generated_paths.setdefault(workspace.workspace_id, set()).add(relative)
        return ChangedFile(
            path=relative,
            change_type=ChangeType.MODIFIED if before is not None else ChangeType.ADDED,
            before_hash=actual,
            after_hash=sha256(content).hexdigest(),
        )

    async def delete_generated_file(
        self, workspace: WorkspaceDescriptor, relative: str
    ) -> ChangedFile:
        if relative not in self._generated_paths.get(workspace.workspace_id, set()):
            raise DiffPolicyError(
                "baseline_delete_forbidden", "only task-generated files may be deleted"
            )
        root = self.workspaces.path_for(workspace)
        target = self._policy(root).validate(relative)
        if not target.is_file() or target.is_symlink():
            raise DiffPolicyError("invalid_delete_target", "delete target must be a regular file")
        before = target.read_bytes()
        self._reserve_mutation(workspace.workspace_id, relative, len(before.splitlines()))
        target.unlink()
        from cognitive_os.domain.coding import ChangeType

        return ChangedFile(
            path=relative,
            change_type=ChangeType.DELETED,
            before_hash=sha256(before).hexdigest(),
        )
