"""Narrow shell-free Git command runner for trusted host services."""

from __future__ import annotations

import os
import subprocess  # nosec B404 - trusted fixed executable and shell=False
from dataclasses import dataclass
from pathlib import Path

from .errors import GitCommandError, GitCommandTimeout, RepositoryPolicyError


@dataclass(frozen=True)
class GitCommandResult:
    argv: tuple[str, ...]
    returncode: int
    stdout: str
    stderr: str
    truncated: bool = False


class GitCommandRunner:
    def __init__(self, *, timeout_seconds: float = 30, maximum_output_bytes: int = 1_000_000):
        self.timeout_seconds = timeout_seconds
        self.maximum_output_bytes = maximum_output_bytes

    async def run(
        self,
        repository: Path,
        operation: str,
        arguments: tuple[str, ...] = (),
        *,
        check: bool = True,
    ) -> GitCommandResult:
        allowed = {"rev-parse", "status", "diff", "show", "log", "worktree", "apply"}
        if operation not in allowed:
            raise RepositoryPolicyError(f"Git operation is not allowlisted: {operation}")
        forbidden_global_options = (
            "-c",
            "--config-env",
            "--exec-path",
        )
        if (
            not repository.is_absolute()
            or any("\x00" in item or "\n" in item or "\r" in item for item in arguments)
            or any(
                item == option or item.startswith(f"{option}=")
                for item in arguments
                for option in forbidden_global_options
            )
        ):
            raise RepositoryPolicyError("invalid repository path or Git argument")
        argv = ("git", "-C", str(repository), operation, *arguments)
        env = {
            "HOME": os.environ.get("HOME", "/nonexistent"),
            "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
            "LANG": "C.UTF-8",
            "LC_ALL": "C.UTF-8",
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_TERMINAL_PROMPT": "0",
        }
        try:
            completed = subprocess.run(  # nosec B603
                argv,
                capture_output=True,
                check=False,
                stdin=subprocess.DEVNULL,
                timeout=self.timeout_seconds,
                env=env,
            )
        except subprocess.TimeoutExpired:
            raise GitCommandTimeout(f"Git {operation} timed out") from None
        stdout_bytes, stderr_bytes = completed.stdout, completed.stderr
        truncated = (
            len(stdout_bytes) > self.maximum_output_bytes
            or len(stderr_bytes) > self.maximum_output_bytes
        )
        stdout = stdout_bytes[: self.maximum_output_bytes].decode("utf-8", errors="replace")
        stderr = stderr_bytes[: self.maximum_output_bytes].decode("utf-8", errors="replace")
        result = GitCommandResult(argv, completed.returncode, stdout, stderr, truncated)
        if check and result.returncode:
            raise GitCommandError(f"Git {operation} failed with exit code {result.returncode}")
        return result
