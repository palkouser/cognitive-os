"""Restricted rootless Docker sandbox lifecycle."""

from __future__ import annotations

import json
import os
from pathlib import Path

from cognitive_os.domain.sandbox import SandboxRequest, SandboxResult
from cognitive_os.providers.workspace_snapshot import snapshot_workspace
from cognitive_os.tools.errors import SandboxExecutionError

from .docker_cli import docker


class DockerSandbox:
    def __init__(self, image: str) -> None:
        self._image = image

    async def run(self, request: SandboxRequest) -> SandboxResult:
        workspace = Path(request.workspace).resolve()
        if not workspace.is_dir():
            raise SandboxExecutionError("sandbox workspace is unavailable")
        limits = request.limits
        verification_mount = self._verification_mount(request)
        arguments = (
            "run",
            "--name",
            request.sandbox_id,
            "--label",
            "cogos.managed=true",
            "--label",
            f"cogos.tool_call_id={request.tool_call_id}",
            "--label",
            f"cogos.task_run_id={request.task_run_id}",
            "--read-only",
            "--network",
            "none",
            "--cap-drop",
            "ALL",
            "--security-opt",
            "no-new-privileges",
            "--pids-limit",
            str(limits.pid_limit),
            "--memory",
            str(limits.memory_bytes),
            "--cpus",
            str(limits.cpu_count),
            "--tmpfs",
            "/tmp:rw,noexec,nosuid,nodev,size=64m",  # nosec B108
            "--user",
            f"{os.getuid()}:{os.getgid()}",
            "--mount",
            f"type=bind,src={workspace},dst=/workspace",
            *verification_mount,
            "--workdir",
            "/workspace",
            self._image,
            request.executable,
            *request.arguments,
        )
        code, stdout, stderr = await docker(*arguments, timeout=limits.timeout_seconds)
        return SandboxResult(
            sandbox_id=request.sandbox_id,
            exit_code=code,
            stdout=stdout[: limits.maximum_stdout_bytes],
            stderr=stderr[: limits.maximum_stderr_bytes],
        )

    @staticmethod
    def _verification_mount(request: SandboxRequest) -> tuple[str, ...]:
        """Resolve, verify and describe the one read-only control mount, or nothing.

        The hash is checked here, immediately before `docker run`, rather than when the
        request was built. A bundle verified at build time and swapped before launch would
        pass a check that happened at the wrong moment, and the whole point of the control
        material is that the container runs against the bundle we think it does.
        """
        verification = request.verification_input
        if verification is None:
            return ()
        source = Path(verification.host_path).resolve()
        if not source.is_dir():
            raise SandboxExecutionError("sandbox verification input is unavailable")
        if source == Path(request.workspace).resolve():
            raise SandboxExecutionError("verification input cannot be the workspace itself")
        digest = snapshot_workspace(source).digest
        if digest != verification.content_hash:
            raise SandboxExecutionError(
                "sandbox verification input does not match its declared content hash"
            )
        return ("--mount", f"type=bind,src={source},dst={verification.container_path},readonly")

    async def cancel(self, sandbox_id: str) -> None:
        await docker("kill", sandbox_id)

    async def inspect(self, sandbox_id: str) -> dict[str, object]:
        code, stdout, _ = await docker("inspect", sandbox_id)
        if code:
            raise SandboxExecutionError("sandbox inspection failed")
        values = json.loads(stdout)
        return values[0] if isinstance(values, list) and values else {}

    async def cleanup(self, sandbox_id: str) -> None:
        await docker("rm", "--force", sandbox_id)

    async def list_stale(self) -> tuple[str, ...]:
        _, stdout, _ = await docker(
            "ps", "--all", "--filter", "label=cogos.managed=true", "--format", "{{.Names}}"
        )
        return tuple(item for item in stdout.decode(errors="replace").splitlines() if item)
