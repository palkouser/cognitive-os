"""Bounded read-only filesystem tools."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from cognitive_os.domain.common import JsonValue
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


class FilesystemTool:
    def __init__(self, operation: str, roots: tuple[Path, ...], maximum_bytes: int = 1_048_576):
        self._operation = operation
        self._roots = tuple(root.resolve() for root in roots)
        self._maximum_bytes = maximum_bytes
        self._descriptor = _descriptor(operation)

    @property
    def descriptor(self) -> ToolDescriptor:
        return self._descriptor

    async def execute(
        self, invocation: ToolInvocation, context: ToolExecutionContext
    ) -> ToolExecutionResult:
        started = datetime.now(UTC)
        raw_path = invocation.arguments.get("path")
        if not isinstance(raw_path, str):
            raise ToolPolicyError("filesystem path is required")
        path = Path(raw_path).resolve()
        if not any(path == root or path.is_relative_to(root) for root in self._roots):
            raise ToolPolicyError("filesystem path is outside configured roots")
        if any(part in {".git", ".config"} for part in path.parts) or path.name.endswith(".env"):
            raise ToolPolicyError("sensitive filesystem path is forbidden")
        result: JsonValue
        if self._operation == "stat":
            value = path.stat()
            result = {
                "path": str(path),
                "size": value.st_size,
                "is_file": path.is_file(),
                "is_dir": path.is_dir(),
                "is_symlink": path.is_symlink(),
            }
        elif self._operation == "list":
            raw_limit = invocation.arguments.get("limit", 100)
            maximum = min(raw_limit if isinstance(raw_limit, int) else 100, 1000)
            result = {
                "entries": [
                    {"name": item.name, "is_dir": item.is_dir(), "is_symlink": item.is_symlink()}
                    for item in sorted(path.iterdir())[:maximum]
                ]
            }
        else:
            data = path.read_bytes()[: self._maximum_bytes + 1]
            if b"\x00" in data:
                raise ToolPolicyError("binary files cannot be read")
            truncated = len(data) > self._maximum_bytes
            result = {
                "content": data[: self._maximum_bytes].decode("utf-8", errors="replace"),
                "truncated": truncated,
            }
        return completed(invocation, started, result)


def _descriptor(operation: str) -> ToolDescriptor:
    properties: dict[str, JsonValue] = {"path": {"type": "string"}}
    if operation == "list":
        properties["limit"] = {"type": "integer", "minimum": 1, "maximum": 1000}
    return ToolDescriptor(
        tool_id=f"filesystem.{operation}",
        version="1",
        display_name=f"Filesystem {operation}",
        description=f"Bounded read-only filesystem {operation} operation.",
        source=ToolSource.BUILT_IN,
        input_schema={
            "type": "object",
            "properties": properties,
            "required": ["path"],
            "additionalProperties": False,
        },
        output_schema={"type": "object"},
        risk_level=ToolRiskLevel.R0,
        side_effects=(ToolSideEffect.LOCAL_READ,),
        execution_mode=ToolExecutionMode.HOST_READ_ONLY,
        provider_visible=True,
        idempotent=True,
        deterministic=True,
        default_timeout_seconds=10,
    )
