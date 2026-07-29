"""One bounded, read-only subprocess boundary, shared by both CLI adapters.

Claude Code and Codex need identical guarantees, and two copies of process-group cleanup is
two places for an orphan process to survive. This is that one copy — not a general process
framework, and it grows only if a third adapter needs the same thing.

What it enforces, and why each one is here rather than in the adapters:

* **the prompt goes on stdin.** In `argv` it is visible to every process on the host through
  `/proc`, and it lands in any shell history, audit log or crash dump that records command
  lines. Sprint 21C1's Claude adapter passed it positionally;
* **no shell.** `create_subprocess_exec`, never `_shell`: there is no interpolation step for
  a fixture path or a model name to escape from;
* **a minimal environment allowlist.** Secret-shaped names are refused at configuration
  load, and everything not on the list is simply absent from the child;
* **a new process group.** Termination signals the group, so a child that spawned its own
  children takes them with it;
* **hard byte caps on stdout and stderr.** Exceeding one terminates the process tree instead
  of growing a buffer. Truncated output is a recoverable failure; an exhausted host is not;
* **one termination path.** Timeout, cancellation, cap overflow and a caller's parser
  refusal all end in the same graceful-then-forced process-tree kill, so there is no path
  that returns first and cleans up later;
* **a content-and-mode snapshot before and after.** See `workspace_snapshot`;
* **runner-owned temporary files outside the working directory,** removed on every path. A
  schema file inside the fixture would have to be excluded from the snapshot, and an
  excluded path is a path a provider can change unobserved.

See ADR 0087.
"""

from __future__ import annotations

import asyncio
import os
import shutil
import signal
import tempfile
import time
from collections.abc import AsyncIterator, Callable, Mapping, Sequence
from contextlib import asynccontextmanager, suppress
from pathlib import Path

from pydantic import Field

from cognitive_os.config.provider_config import FORBIDDEN_CLI_ARGUMENTS, CliProcessLimits
from cognitive_os.domain.base import ImmutableContractModel
from cognitive_os.domain.common import JsonValue, NonEmptyStr
from cognitive_os.providers.errors import (
    ProviderCancelledError,
    ProviderConfigurationError,
    ProviderMutationDetectedError,
    ProviderOutputLimitExceededError,
    ProviderProcessError,
    ProviderTimeoutError,
    ProviderUnavailableError,
)
from cognitive_os.providers.redaction import redact_for_diagnostics
from cognitive_os.providers.workspace_snapshot import (
    WorkspaceChange,
    WorkspaceSnapshot,
    snapshot_workspace,
)

#: Pipe read size. Large enough that a chatty provider is not read byte-by-byte, small
#: enough that the overshoot past a cap before truncation stays bounded.
_READ_CHUNK = 64 * 1024

#: How long a `--version` style probe may take. Fixed rather than configurable: a health
#: probe that could be given a five-minute budget is a health check that can hang a CLI.
_PROBE_TIMEOUT_SECONDS = 10.0


class CliProcessOutcome(ImmutableContractModel):
    """What a bounded run produced. Sanitized excerpts only."""

    stdout: str
    stderr: str
    return_code: int
    duration_ms: float = Field(ge=0)
    stdout_truncated: bool = False
    stderr_truncated: bool = False


class BoundedCliRunner:
    """Runs one CLI, once, inside every bound the configuration declares."""

    def __init__(
        self,
        *,
        provider_id: str,
        executable: str,
        working_directory: Path,
        limits: CliProcessLimits,
        environment_allowlist: Sequence[str],
        environment: Mapping[str, str] | None = None,
        diagnose_failure: Callable[[str], Mapping[str, JsonValue]] | None = None,
    ) -> None:
        self.provider_id = provider_id
        self.executable = executable
        self.working_directory = Path(working_directory)
        self.limits = limits
        self.environment_allowlist = tuple(environment_allowlist)
        self._environment = os.environ if environment is None else environment
        # Adapters know their own CLI's failure envelope; this runner does not, and must
        # not learn. `stdout` on a failing advisory run can hold partial model prose, which
        # is content this boundary deliberately never retains — so the raw text never leaves
        # here. The adapter's diagnoser is handed the text and returns only the allowlisted
        # scalar metadata that explains *why* it failed.
        self._diagnose_failure = diagnose_failure or (lambda _stdout: {})

    # ------------------------------------------------------------------ environment

    def safe_environment(self) -> dict[str, str]:
        """Exactly the allowlisted names, and nothing else.

        Built by selection rather than by deletion: a denylist has to anticipate every
        secret-carrying variable name, and the one it misses is the one that leaks.
        """
        return {
            name: value
            for name, value in self._environment.items()
            if name in self.environment_allowlist
        }

    # ------------------------------------------------------------------- temporaries

    @asynccontextmanager
    async def temporary_directory(self) -> AsyncIterator[Path]:
        """A runner-owned scratch directory, outside the working directory, always removed.

        Outside on purpose: a schema or configuration file written into the fixture would
        have to be excluded from the mutation snapshot, and an excluded path is a path a
        provider could change without the guard noticing.
        """
        directory = Path(tempfile.mkdtemp(prefix=f"cogos-{self.provider_id}-"))
        try:
            yield directory
        finally:
            shutil.rmtree(directory, ignore_errors=True)

    # ------------------------------------------------------------------- availability

    async def probe(self, arguments: Sequence[str]) -> tuple[bool, str]:
        """Run a bounded, read-only probe such as `--version` or a flag-acceptance check.

        Returns success and a redacted, truncated excerpt. Never raises for an unavailable
        binary: a health check that raises cannot report "not installed".
        """
        if shutil.which(self.executable) is None:
            return False, "executable is not installed"
        try:
            process = await asyncio.create_subprocess_exec(
                self.executable,
                *arguments,
                cwd=self.working_directory if self.working_directory.is_dir() else None,
                env=self.safe_environment(),
                stdin=asyncio.subprocess.DEVNULL,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                start_new_session=True,
            )
        except OSError:
            return False, "executable could not be started"
        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(), timeout=_PROBE_TIMEOUT_SECONDS
            )
        except TimeoutError:
            await self._terminate_tree(process)
            return False, "probe timed out"
        combined = (stdout + stderr).decode(errors="replace")
        return process.returncode == 0, redact_for_diagnostics(combined, limit=200)

    async def supports_arguments(self, arguments: Sequence[str]) -> bool:
        """Whether the installed binary accepts these flags.

        Parse acceptance, not help-text scraping: Claude Code 2.1.219 accepts `--max-turns`
        without listing it in `--help`, and `codex exec` 0.144.6 lists `--sandbox` while
        rejecting `--ask-for-approval`. Only what the binary itself accepts may be emitted.
        """
        accepted, _ = await self.probe((*arguments, "--help"))
        return accepted

    # --------------------------------------------------------------------------- run

    async def run(
        self,
        *,
        arguments: Sequence[str],
        stdin_payload: str,
        expect_unchanged_workspace: bool = True,
    ) -> tuple[CliProcessOutcome, WorkspaceSnapshot | None]:
        """Execute once under every bound, and return the outcome and the after-snapshot.

        Raises a typed provider error for every failure class; a non-zero exit is a
        `ProviderProcessError` rather than an outcome, because a caller that had to check a
        return code would eventually forget to.
        """
        self._validate_arguments(arguments)
        if shutil.which(self.executable) is None:
            raise ProviderUnavailableError(
                provider_id=self.provider_id,
                error_code="cli_executable_missing",
                message="the configured CLI executable is not installed",
            )
        if not self.working_directory.is_dir():
            raise ProviderConfigurationError(
                provider_id=self.provider_id,
                error_code="cli_working_directory_missing",
                message="the configured working directory does not exist",
            )

        before = snapshot_workspace(self.working_directory) if expect_unchanged_workspace else None
        started = time.monotonic()
        try:
            process = await asyncio.create_subprocess_exec(
                self.executable,
                *arguments,
                cwd=self.working_directory,
                env=self.safe_environment(),
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                # A new session, so `killpg` reaches children the provider spawned.
                start_new_session=True,
            )
        except OSError as error:
            raise ProviderUnavailableError(
                provider_id=self.provider_id,
                error_code="cli_start_failed",
                message="the CLI executable could not be started",
            ) from error

        try:
            return await self._finish(
                process,
                stdin_payload=stdin_payload,
                before=before,
                started=started,
                expect_unchanged_workspace=expect_unchanged_workspace,
            )
        finally:
            # Every path, including every raise above: an unclosed subprocess transport is
            # a leaked pipe pair, and the interpreter only complains about it much later,
            # in whatever unrelated code happens to be running when it is collected.
            self._release(process)

    async def _finish(
        self,
        process: asyncio.subprocess.Process,
        *,
        stdin_payload: str,
        before: WorkspaceSnapshot | None,
        started: float,
        expect_unchanged_workspace: bool,
    ) -> tuple[CliProcessOutcome, WorkspaceSnapshot | None]:
        try:
            stdout, stderr, truncated_out, truncated_err = await self._communicate(
                process, stdin_payload
            )
        except TimeoutError as error:
            await self._terminate_tree(process)
            raise ProviderTimeoutError(
                provider_id=self.provider_id,
                message="advisory CLI execution exceeded its timeout",
                details={"timeout_seconds": self.limits.timeout_seconds},
            ) from error
        except asyncio.CancelledError:
            # Cleanup before re-raising as a typed error: a cancelled call that left the
            # provider running would keep spending the operator's subscription unobserved.
            await self._terminate_tree(process)
            raise ProviderCancelledError(
                provider_id=self.provider_id,
                message="advisory CLI execution was cancelled",
            ) from None

        duration_ms = (time.monotonic() - started) * 1000
        after = snapshot_workspace(self.working_directory) if expect_unchanged_workspace else None

        if truncated_out or truncated_err:
            # The tree was already terminated by `_communicate`; a mutation it managed to
            # perform before being stopped is still the more serious failure to report.
            self._raise_for_mutation(before, after)
            raise ProviderOutputLimitExceededError(
                provider_id=self.provider_id,
                message="advisory CLI output exceeded its configured cap",
                details={
                    "stdout_truncated": truncated_out,
                    "stderr_truncated": truncated_err,
                    "maximum_stdout_bytes": self.limits.maximum_stdout_bytes,
                    "maximum_stderr_bytes": self.limits.maximum_stderr_bytes,
                },
            )

        # Mutation is checked before the exit code. A provider that wrote to the fixture
        # *and* failed has still written to the fixture, and that is the more serious of
        # the two facts.
        self._raise_for_mutation(before, after)

        decoded_stderr = redact_for_diagnostics(
            stderr.decode(errors="replace"), limit=self.limits.maximum_stderr_bytes
        )
        if process.returncode != 0:
            raise ProviderProcessError(
                provider_id=self.provider_id,
                error_code="cli_nonzero_exit",
                message="advisory CLI process returned a non-zero status",
                details={
                    "return_code": process.returncode,
                    "stderr_excerpt": redact_for_diagnostics(
                        stderr.decode(errors="replace"), limit=400
                    ),
                    **self._diagnose_failure(stdout.decode(errors="replace")),
                },
            )
        return (
            CliProcessOutcome(
                stdout=stdout.decode(errors="replace"),
                stderr=decoded_stderr,
                return_code=process.returncode,
                duration_ms=duration_ms,
                stdout_truncated=truncated_out,
                stderr_truncated=truncated_err,
            ),
            after,
        )

    # --------------------------------------------------------------------- internals

    @staticmethod
    def _release(process: asyncio.subprocess.Process) -> None:
        """Close the subprocess transport and its pipes. Safe to call more than once."""
        transport = getattr(process, "_transport", None)
        if transport is not None:
            with suppress(Exception):
                transport.close()

    def _validate_arguments(self, arguments: Sequence[str]) -> None:
        """Refuse an authority-widening flag however it got into the argument list."""
        forbidden = sorted(set(arguments) & FORBIDDEN_CLI_ARGUMENTS)
        if forbidden:
            raise ProviderConfigurationError(
                provider_id=self.provider_id,
                error_code="cli_forbidden_argument",
                message="advisory execution refuses an authority-widening argument",
                details={"arguments": list(forbidden)},
            )

    def _raise_for_mutation(
        self, before: WorkspaceSnapshot | None, after: WorkspaceSnapshot | None
    ) -> None:
        if before is None or after is None:
            return
        changes: tuple[WorkspaceChange, ...] = before.difference(after)
        if not changes:
            return
        raise ProviderMutationDetectedError(
            provider_id=self.provider_id,
            message="the advisory provider changed its working directory",
            details={
                "change_count": len(changes),
                # Paths and hashes. Bounded, because a provider that rewrote a thousand
                # files should not be able to write a thousand entries into an event.
                "changes": [change.model_dump(mode="json") for change in changes[:32]],
                "before_digest": before.digest,
                "after_digest": after.digest,
            },
        )

    async def _communicate(
        self, process: asyncio.subprocess.Process, stdin_payload: str
    ) -> tuple[bytes, bytes, bool, bool]:
        """Feed stdin, read both streams under their caps, and stop the moment one is hit.

        Waiting for both readers to finish would deadlock on the case that matters: a
        provider flooding stdout fills the pipe as soon as this side stops reading, so it
        never exits, so the stderr reader never sees EOF — and a cap overflow would surface
        as a timeout several minutes later instead of as itself.
        """
        # A real check rather than `assert`: under `python -O` an assertion disappears, and
        # what would be left is an unguarded `None.write(...)` on the path that delivers the
        # prompt.
        stdin, out_stream, err_stream = process.stdin, process.stdout, process.stderr
        if stdin is None or out_stream is None or err_stream is None:
            raise ProviderProcessError(
                provider_id=self.provider_id,
                error_code="cli_pipes_unavailable",
                message="the advisory CLI process was started without the required pipes",
            )

        async def feed() -> None:
            try:
                stdin.write(stdin_payload.encode())
                await stdin.drain()
            except (BrokenPipeError, ConnectionResetError):
                # The provider exited before reading the prompt. That is its failure to
                # report through the exit code, not the runner's to raise here.
                pass
            finally:
                with suppress(BrokenPipeError, ConnectionResetError):
                    stdin.close()

        feed_task = asyncio.create_task(feed())
        out_task = asyncio.create_task(_read_capped(out_stream, self.limits.maximum_stdout_bytes))
        err_task = asyncio.create_task(_read_capped(err_stream, self.limits.maximum_stderr_bytes))
        try:
            async with asyncio.timeout(self.limits.timeout_seconds):
                pending: set[asyncio.Task[tuple[bytes, bool]]] = {out_task, err_task}
                truncated = False
                while pending and not truncated:
                    done, pending = await asyncio.wait(pending, return_when=asyncio.FIRST_COMPLETED)
                    truncated = any(task.result()[1] for task in done)
                if truncated:
                    # Terminate first, then drain: with the tree gone the remaining reader
                    # reaches EOF immediately instead of waiting on a live pipe.
                    await self._terminate_tree(process)
                    for task in pending:
                        with suppress(TimeoutError, asyncio.CancelledError):
                            await asyncio.wait_for(task, timeout=1)
                        task.cancel()
                else:
                    await process.wait()
                await asyncio.gather(feed_task, return_exceptions=True)
        except (TimeoutError, asyncio.CancelledError):
            feed_task.cancel()
            out_task.cancel()
            err_task.cancel()
            raise
        stdout, truncated_out = _task_result(out_task)
        stderr, truncated_err = _task_result(err_task)
        return stdout, stderr, truncated_out, truncated_err

    async def _terminate_tree(self, process: asyncio.subprocess.Process) -> None:
        """Signal the whole process group, then force it. Returns only when it is gone.

        `killpg` rather than `process.terminate()`: the provider may have spawned children,
        and terminating only the parent would leave them holding the operator's credentials
        and spending its budget.
        """
        try:
            group = os.getpgid(process.pid)
        except ProcessLookupError:
            with suppress(ProcessLookupError):
                await process.wait()
            return
        with suppress(ProcessLookupError, PermissionError):
            os.killpg(group, signal.SIGTERM)
        try:
            await asyncio.wait_for(process.wait(), timeout=self.limits.termination_grace_seconds)
        except TimeoutError:
            with suppress(ProcessLookupError, PermissionError):
                os.killpg(group, signal.SIGKILL)
            await process.wait()


def _task_result(task: asyncio.Task[tuple[bytes, bool]]) -> tuple[bytes, bool]:
    """A cancelled reader contributes nothing rather than propagating its cancellation."""
    if task.cancelled() or not task.done():
        return b"", False
    if task.exception() is not None:
        return b"", False
    return task.result()


async def _read_capped(stream: asyncio.StreamReader, cap: int) -> tuple[bytes, bool]:
    """Read until EOF or until `cap` bytes have been kept.

    On overflow it stops reading and returns. The pipe then fills and the provider blocks,
    which is fine and brief: the caller terminates the process tree immediately.
    """
    chunks: list[bytes] = []
    kept = 0
    while True:
        chunk = await stream.read(_READ_CHUNK)
        if not chunk:
            return b"".join(chunks), False
        remaining = cap - kept
        if len(chunk) >= remaining:
            chunks.append(chunk[:remaining])
            return b"".join(chunks), True
        chunks.append(chunk)
        kept += len(chunk)


def quote_free_argument(value: str) -> NonEmptyStr:
    """Refuse an argument that only makes sense to a shell.

    Nothing here is passed to a shell, so a value containing shell metacharacters is either
    a mistake or an attempt, and both should stop before the process starts.
    """
    if any(character in value for character in "\n\r\0"):
        raise ValueError("CLI arguments must not contain control characters")
    return value
