"""Bounded development tools executed only inside the sandbox."""

from datetime import UTC, datetime
from pathlib import PurePosixPath
from typing import ClassVar, cast
from uuid import uuid4

from cognitive_os.domain.sandbox import SandboxLimits, SandboxRequest
from cognitive_os.domain.tools import (
    ToolDescriptor,
    ToolExecutionContext,
    ToolExecutionMode,
    ToolExecutionResult,
    ToolExecutionStatus,
    ToolInvocation,
    ToolRiskLevel,
    ToolSideEffect,
    ToolSource,
)

from .lifecycle import DockerSandbox


class SandboxDevelopmentTool:
    _EXECUTABLES: ClassVar[dict[str, str]] = {
        "python": "python",
        "pytest": "pytest",
        "ruff": "ruff",
        "mypy": "mypy",
    }

    def __init__(self, name: str, sandbox: DockerSandbox, limits: SandboxLimits) -> None:
        if name not in self._EXECUTABLES:
            raise ValueError("sandbox executable is not allowlisted")
        self._name, self._sandbox, self._limits = name, sandbox, limits
        self._descriptor = ToolDescriptor(
            tool_id=f"sandbox.{name}",
            version="1",
            display_name=f"Sandbox {name}",
            description=f"Run bounded {name} inside the rootless sandbox.",
            source=ToolSource.BUILT_IN,
            input_schema={
                "type": "object",
                "properties": {
                    "arguments": {"type": "array", "items": {"type": "string"}, "maxItems": 32}
                },
                "required": ["arguments"],
                "additionalProperties": False,
            },
            output_schema={"type": "object"},
            risk_level=ToolRiskLevel.R1,
            side_effects=(ToolSideEffect.LOCAL_WRITE,),
            execution_mode=ToolExecutionMode.SANDBOX,
            provider_visible=True,
            default_timeout_seconds=limits.timeout_seconds,
        )

    @property
    def descriptor(self) -> ToolDescriptor:
        return self._descriptor

    async def execute(
        self, invocation: ToolInvocation, context: ToolExecutionContext
    ) -> ToolExecutionResult:
        raw = invocation.arguments.get("arguments")
        if not isinstance(raw, list) or not all(isinstance(item, str) for item in raw):
            raise ValueError("sandbox arguments must be strings")
        arguments = tuple(cast(str, item) for item in raw)
        self._validate_arguments(arguments)
        started = datetime.now(UTC)
        sandbox_id = f"cogos-{uuid4().hex[:20]}"
        result = await self._sandbox.run(
            SandboxRequest(
                sandbox_id=sandbox_id,
                tool_call_id=str(invocation.tool_call_id),
                task_run_id=str(invocation.task_run_id),
                workspace=context.workspace,
                executable=self._EXECUTABLES[self._name],
                arguments=arguments,
                limits=self._limits,
            )
        )
        await self._sandbox.cleanup(sandbox_id)
        return ToolExecutionResult(
            tool_call_id=invocation.tool_call_id,
            tool_id=invocation.tool_id,
            tool_version=invocation.tool_version,
            status=ToolExecutionStatus.COMPLETED
            if result.exit_code == 0
            else ToolExecutionStatus.FAILED,
            started_at=started,
            finished_at=datetime.now(UTC),
            exit_code=result.exit_code,
            result={
                "stdout": result.stdout.decode(errors="replace"),
                "stderr": result.stderr.decode(errors="replace"),
            },
            sandbox_id=sandbox_id,
        )

    def _validate_arguments(self, arguments: tuple[str, ...]) -> None:
        forbidden = {"-c", "-m", "--install", "install"}
        if any(item in forbidden or "\n" in item or "\x00" in item for item in arguments):
            raise ValueError("sandbox argument is forbidden")
        for item in arguments:
            if item.startswith("-"):
                continue
            path = PurePosixPath(item)
            if path.is_absolute() or ".." in path.parts:
                raise ValueError("sandbox path must be workspace-relative")
