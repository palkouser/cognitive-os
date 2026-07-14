"""Bounded shell-free read-only Git tools."""

import asyncio
from datetime import UTC, datetime
from pathlib import Path

from cognitive_os.domain.tools import (
    ToolDescriptor,
    ToolExecutionContext,
    ToolExecutionMode,
    ToolExecutionResult,
    ToolInvocation,
    ToolRiskLevel,
    ToolSideEffect,
    ToolSource,
)

from ..base import completed
from ..errors import ToolPolicyError


class GitReadOnlyTool:
    def __init__(self, operation: str, roots: tuple[Path, ...]) -> None:
        if operation not in {"status", "diff", "log"}:
            raise ValueError("Git operation is not allowlisted")
        self._operation = operation
        self._roots = tuple(path.resolve() for path in roots)
        self._descriptor = ToolDescriptor(
            tool_id=f"git.{operation}",
            version="1",
            display_name=f"Git {operation}",
            description=f"Bounded read-only Git {operation}.",
            source=ToolSource.BUILT_IN,
            input_schema={
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "limit": {"type": "integer", "minimum": 1, "maximum": 100},
                },
                "required": ["path"],
                "additionalProperties": False,
            },
            output_schema={"type": "object"},
            risk_level=ToolRiskLevel.R0,
            side_effects=(ToolSideEffect.LOCAL_READ,),
            execution_mode=ToolExecutionMode.HOST_READ_ONLY,
            provider_visible=True,
            idempotent=True,
            default_timeout_seconds=10,
        )

    @property
    def descriptor(self) -> ToolDescriptor:
        return self._descriptor

    async def execute(
        self, invocation: ToolInvocation, context: ToolExecutionContext
    ) -> ToolExecutionResult:
        raw = invocation.arguments.get("path")
        if not isinstance(raw, str):
            raise ToolPolicyError("Git repository path is required")
        repository = Path(raw).resolve()
        if not any(repository == root or repository.is_relative_to(root) for root in self._roots):
            raise ToolPolicyError("Git repository is outside configured roots")
        arguments: tuple[str, ...]
        if self._operation == "status":
            arguments = ("status", "--short", "--branch")
        elif self._operation == "diff":
            arguments = ("-c", "core.pager=cat", "diff", "--no-ext-diff", "--no-textconv")
        else:
            raw_limit = invocation.arguments.get("limit", 20)
            limit = min(raw_limit if isinstance(raw_limit, int) else 20, 100)
            arguments = ("-c", "core.pager=cat", "log", f"-{limit}", "--format=%H%x09%s")
        process = await asyncio.create_subprocess_exec(
            "git",
            "-C",
            str(repository),
            *arguments,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env={"PATH": "/usr/bin:/bin", "GIT_CONFIG_NOSYSTEM": "1"},
        )
        async with asyncio.timeout(context.timeout_seconds):
            stdout, stderr = await process.communicate()
        if process.returncode:
            raise ToolPolicyError("Git read-only operation failed")
        return completed(
            invocation,
            datetime.now(UTC),
            {
                "output": stdout[: context.maximum_stdout_bytes].decode(errors="replace"),
                "stderr": stderr[: context.maximum_stderr_bytes].decode(errors="replace"),
            },
        )
