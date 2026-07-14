"""Argument-safe bounded subprocess execution for Claude Code advisory mode."""

from __future__ import annotations

import asyncio
import os
import shutil
import signal
import time
from collections.abc import Mapping
from contextlib import suppress

from pydantic import Field

from cognitive_os.domain.base import ImmutableContractModel
from cognitive_os.providers.errors import (
    ProviderProcessError,
    ProviderTimeoutError,
    ProviderUnavailableError,
)

from .config import ClaudeCodeProviderConfig

_ENVIRONMENT_ALLOWLIST = {"HOME", "LANG", "LC_ALL", "PATH", "SHELL", "TERM", "TZ"}


class ProcessResult(ImmutableContractModel):
    stdout: str
    stderr: str
    return_code: int
    duration_ms: float = Field(ge=0)


class ClaudeProcessRunner:
    def __init__(self, config: ClaudeCodeProviderConfig) -> None:
        self.config = config

    def build_arguments(self, prompt: str, schema: str) -> tuple[str, ...]:
        arguments = [
            self.config.executable,
            "-p",
            "--output-format",
            self.config.output_format.value,
            "--max-turns",
            str(self.config.maximum_turns),
            "--json-schema",
            schema,
        ]
        if self.config.maximum_budget_usd is not None:
            arguments.extend(("--max-budget-usd", str(self.config.maximum_budget_usd)))
        arguments.append(prompt)
        return tuple(arguments)

    async def availability(self) -> tuple[bool, str]:
        if shutil.which(self.config.executable) is None:
            return False, "Claude Code executable is unavailable"
        if not self.config.working_directory.is_dir():
            return False, "configured working directory is unavailable"
        try:
            process = await asyncio.create_subprocess_exec(
                self.config.executable,
                "--version",
                cwd=self.config.working_directory,
                env=self._safe_environment(),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            _stdout, _stderr = await asyncio.wait_for(
                process.communicate(), timeout=min(10, self.config.timeout_seconds)
            )
        except (OSError, TimeoutError):
            return False, "Claude Code version check failed"
        return process.returncode == 0, (
            "Claude Code is available"
            if process.returncode == 0
            else "Claude Code version check failed"
        )

    async def run(self, *, prompt: str, schema: str) -> ProcessResult:
        before = await self._git_status()
        started = time.monotonic()
        try:
            process = await asyncio.create_subprocess_exec(
                *self.build_arguments(prompt, schema),
                cwd=self.config.working_directory,
                env=self._safe_environment(),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                start_new_session=True,
            )
        except OSError as error:
            raise ProviderUnavailableError(
                provider_id=self.config.provider_id,
                message="Claude Code executable could not be started",
            ) from error
        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(), timeout=self.config.timeout_seconds
            )
        except TimeoutError as error:
            await self._terminate_process_group(process)
            raise ProviderTimeoutError(
                provider_id=self.config.provider_id,
                message="Claude Code advisory execution timed out",
            ) from error
        duration_ms = (time.monotonic() - started) * 1000
        after = await self._git_status()
        if before != after:
            raise ProviderProcessError(
                provider_id=self.config.provider_id,
                error_code="repository_modification_detected",
                message="Claude Code modified the repository during advisory execution",
            )
        decoded_stdout = stdout.decode(errors="replace")
        decoded_stderr = stderr.decode(errors="replace")
        if process.returncode != 0:
            raise ProviderProcessError(
                provider_id=self.config.provider_id,
                error_code="claude_code_nonzero_exit",
                message="Claude Code advisory process returned a non-zero status",
                details={"return_code": process.returncode},
            )
        return ProcessResult(
            stdout=decoded_stdout,
            stderr=decoded_stderr,
            return_code=process.returncode,
            duration_ms=duration_ms,
        )

    def _safe_environment(self) -> Mapping[str, str]:
        return {key: value for key, value in os.environ.items() if key in _ENVIRONMENT_ALLOWLIST}

    async def _git_status(self) -> str:
        process = await asyncio.create_subprocess_exec(
            "git",
            "status",
            "--porcelain=v1",
            "--untracked-files=all",
            cwd=self.config.working_directory,
            env=self._safe_environment(),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _stderr = await process.communicate()
        if process.returncode != 0:
            raise ProviderProcessError(
                provider_id=self.config.provider_id,
                message="repository modification guard could not inspect Git status",
            )
        return stdout.decode(errors="replace")

    @staticmethod
    async def _terminate_process_group(process: asyncio.subprocess.Process) -> None:
        try:
            os.killpg(process.pid, signal.SIGTERM)
            await asyncio.wait_for(process.wait(), timeout=2)
        except (ProcessLookupError, TimeoutError):
            with suppress(ProcessLookupError):
                os.killpg(process.pid, signal.SIGKILL)
            await process.wait()
