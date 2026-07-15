"""Validated Git repository operations for Coding Agent workspaces."""

from __future__ import annotations

from hashlib import sha256
from pathlib import Path

from cognitive_os.domain.coding import RepositoryReference

from .errors import RepositoryPolicyError
from .git_commands import GitCommandRunner


class GitRepositoryService:
    def __init__(self, allowed_roots: tuple[Path, ...], runner: GitCommandRunner | None = None):
        self.allowed_roots = tuple(root.resolve() for root in allowed_roots)
        self.runner = runner or GitCommandRunner()

    def resolve_allowed(self, path: Path) -> Path:
        resolved = path.resolve(strict=True)
        if not any(
            resolved == root or resolved.is_relative_to(root) for root in self.allowed_roots
        ):
            raise RepositoryPolicyError("repository is outside an allowed host root")
        return resolved

    async def validate(self, path: Path, base_commit: str) -> RepositoryReference:
        repository = self.resolve_allowed(path)
        git_dir = await self.runner.run(repository, "rev-parse", ("--git-dir",))
        if not git_dir.stdout.strip():
            raise RepositoryPolicyError("repository has no readable Git object store")
        if any((repository / ".git" / marker).exists() for marker in ("MERGE_HEAD", "BISECT_LOG")):
            raise RepositoryPolicyError("repository has an active merge or bisect")
        if (repository / ".git" / "rebase-apply").exists() or (
            repository / ".git" / "rebase-merge"
        ).exists():
            raise RepositoryPolicyError("repository has an active rebase")
        resolved = await self.runner.run(
            repository, "rev-parse", ("--verify", f"{base_commit}^{{commit}}")
        )
        commit = resolved.stdout.strip()
        if len(commit) != 40 or commit != base_commit:
            raise RepositoryPolicyError("base commit must be an exact local 40-character commit")
        identity = sha256(f"{repository}:{git_dir.stdout.strip()}".encode()).hexdigest()
        return RepositoryReference(
            repository_path=repository,
            base_commit=commit,
            repository_identity=identity,
        )

    async def head(self, path: Path) -> str:
        return (await self.runner.run(path, "rev-parse", ("HEAD",))).stdout.strip()

    async def status(self, path: Path) -> str:
        return (
            await self.runner.run(path, "status", ("--porcelain=v1", "--untracked-files=all"))
        ).stdout

    async def diff(self, path: Path, base_commit: str) -> str:
        return (
            await self.runner.run(
                path,
                "diff",
                ("--no-color", "--no-ext-diff", "--binary", base_commit, "--"),
            )
        ).stdout

    async def add_worktree(self, repository: Path, destination: Path, commit: str) -> None:
        await self.runner.run(
            repository,
            "worktree",
            ("add", "--detach", str(destination), commit),
        )

    async def remove_worktree(self, repository: Path, destination: Path) -> None:
        await self.runner.run(repository, "worktree", ("remove", "--force", str(destination)))

    async def prune_worktrees(self, repository: Path, *, dry_run: bool = True) -> str:
        arguments = ("prune", "--dry-run") if dry_run else ("prune",)
        return (await self.runner.run(repository, "worktree", arguments)).stdout
