"""Canonical worktree path, dependency, and secret policy."""

from __future__ import annotations

import fnmatch
import os
import re
from pathlib import Path, PurePosixPath

from cognitive_os.domain.coding import DependencyChangePolicy, PathPolicy

from .diff import DiffPolicyError

SECRET_PATTERNS = (
    re.compile(rb"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    re.compile(rb"(?i)(?:api[_-]?key|password|authorization)\s*[:=]\s*[^\s]{8,}"),
    re.compile(rb"(?i)(?:postgres(?:ql)?|mysql)://[^\s]+"),
)


class WorkspacePathPolicy:
    def __init__(
        self,
        root: Path,
        path_policy: PathPolicy,
        dependency_policy: DependencyChangePolicy,
    ):
        self.root = root.resolve(strict=True)
        self.paths = path_policy
        self.dependencies = dependency_policy

    def validate(self, relative: str) -> Path:
        path = PurePosixPath(relative)
        if path.is_absolute() or not path.parts or ".." in path.parts or path.as_posix() == ".":
            raise DiffPolicyError("invalid_path", "path must be canonical and relative")
        if path.parts[0].casefold() == ".git":
            raise DiffPolicyError("git_path_forbidden", "Git administrative paths are forbidden")
        if self.paths.allowed_paths and not any(
            relative == prefix or relative.startswith(f"{prefix}/")
            for prefix in self.paths.allowed_paths
        ):
            raise DiffPolicyError("path_not_allowed", "path is outside allowed scope")
        if any(
            relative == prefix or relative.startswith(f"{prefix}/")
            for prefix in self.paths.forbidden_paths
        ):
            raise DiffPolicyError("path_forbidden", "path is explicitly forbidden")
        candidate = self.root.joinpath(*path.parts)
        current = self.root
        for part in path.parts[:-1]:
            current = current / part
            if current.is_symlink():
                raise DiffPolicyError("symlink_escape", "parent path is a symlink")
        if candidate.is_symlink():
            raise DiffPolicyError("symlink_target", "symlink targets cannot be mutated")
        resolved_parent = candidate.parent.resolve(strict=False)
        if not (resolved_parent == self.root or resolved_parent.is_relative_to(self.root)):
            raise DiffPolicyError("path_escape", "resolved path leaves workspace")
        return candidate

    def validate_dependency(self, relative: str) -> None:
        name = PurePosixPath(relative).name
        changed = any(
            fnmatch.fnmatch(relative, pattern) or fnmatch.fnmatch(name, pattern)
            for pattern in self.dependencies.protected_patterns
        )
        if changed and not self.dependencies.allow_dependency_changes:
            raise DiffPolicyError(
                "dependency_change_forbidden", "dependency metadata changes require permission"
            )

    @staticmethod
    def scan_secret(content: bytes) -> None:
        if any(pattern.search(content) for pattern in SECRET_PATTERNS):
            raise DiffPolicyError("secret_detected", "content matches a protected secret pattern")

    @staticmethod
    def ensure_not_hardlinked(path: Path) -> None:
        if (
            path.exists()
            and not path.is_symlink()
            and os.stat(path, follow_symlinks=False).st_nlink > 1
        ):
            raise DiffPolicyError("hardlink_forbidden", "hardlinked files cannot be mutated")
