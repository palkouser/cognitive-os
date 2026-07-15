"""Provider-visible coding tools bound to one host-owned detached worktree."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal, cast

from cognitive_os.coding.diff import DiffPolicyError, parse_unified_diff
from cognitive_os.coding.patching import PatchService
from cognitive_os.coding.workspace import WorkspaceManager
from cognitive_os.domain.coding import PatchProposal, WorkspaceDescriptor
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
from cognitive_os.infrastructure.repository.git_repository import GitRepositoryService
from cognitive_os.tools.base import completed
from cognitive_os.tools.errors import ToolPolicyError


class WorkspaceTool:
    def __init__(
        self,
        operation: Literal[
            "apply_patch", "write_file", "delete_generated_file", "read_diff", "list_changed_files"
        ],
        descriptor: WorkspaceDescriptor,
        workspaces: WorkspaceManager,
        patches: PatchService,
        repositories: GitRepositoryService,
    ) -> None:
        self._operation = operation
        self._workspace = descriptor
        self._workspace_revision = descriptor.workspace_revision
        self._workspaces = workspaces
        self._patches = patches
        self._repositories = repositories
        self._descriptor = _descriptor(operation)

    @property
    def descriptor(self) -> ToolDescriptor:
        return self._descriptor

    async def execute(
        self, invocation: ToolInvocation, context: ToolExecutionContext
    ) -> ToolExecutionResult:
        if invocation.task_run_id != self._workspace.task_run_id:
            raise ToolPolicyError("workspace tool invocation belongs to another task run")
        started = datetime.now(UTC)
        arguments = invocation.arguments
        result: JsonValue
        try:
            if self._operation == "apply_patch":
                proposal = PatchProposal.model_validate(arguments)
                if proposal.expected_workspace_revision != self._workspace_revision:
                    raise ToolPolicyError("patch proposal references a stale workspace revision")
                active_workspace = self._workspace.model_copy(
                    update={"workspace_revision": self._workspace_revision}
                )
                applied = await self._patches.apply(active_workspace, proposal)
                if applied.applied:
                    self._workspace_revision = applied.workspace_revision
                result = applied.model_dump(mode="json")
            elif self._operation == "write_file":
                path = arguments.get("path")
                content = arguments.get("content")
                expected = arguments.get("expected_before_hash")
                if not isinstance(path, str) or not isinstance(content, str):
                    raise ToolPolicyError("write_file requires path and UTF-8 content")
                changed = await self._patches.write_file(
                    self._workspace,
                    path,
                    content.encode("utf-8"),
                    expected_before_hash=expected if isinstance(expected, str) else None,
                )
                result = changed.model_dump(mode="json")
            elif self._operation == "delete_generated_file":
                path = arguments.get("path")
                if not isinstance(path, str):
                    raise ToolPolicyError("delete_generated_file requires path")
                changed = await self._patches.delete_generated_file(self._workspace, path)
                result = changed.model_dump(mode="json")
            else:
                root = self._workspaces.path_for(self._workspace)
                diff = await self._repositories.diff(root, self._workspace.base_commit)
                if self._operation == "read_diff":
                    maximum = min(context.maximum_stdout_bytes, 1_000_000)
                    result = {"diff": diff[:maximum], "truncated": len(diff) > maximum}
                else:
                    parsed = parse_unified_diff(diff) if diff else ()
                    result = {
                        "files": [
                            {"path": item.path, "change_type": item.change_type.value}
                            for item in sorted(parsed, key=lambda item: item.path)
                        ]
                    }
        except DiffPolicyError as error:
            raise ToolPolicyError(f"{error.reason_code}: {error}") from error
        return completed(invocation, started, result)


def build_workspace_tools(
    descriptor: WorkspaceDescriptor,
    workspaces: WorkspaceManager,
    patches: PatchService,
    repositories: GitRepositoryService,
) -> tuple[WorkspaceTool, ...]:
    operations: tuple[
        Literal[
            "apply_patch",
            "write_file",
            "delete_generated_file",
            "read_diff",
            "list_changed_files",
        ],
        ...,
    ] = (
        "apply_patch",
        "write_file",
        "delete_generated_file",
        "read_diff",
        "list_changed_files",
    )
    return tuple(
        WorkspaceTool(operation, descriptor, workspaces, patches, repositories)
        for operation in operations
    )


def _descriptor(operation: str) -> ToolDescriptor:
    write = operation in {"apply_patch", "write_file", "delete_generated_file"}
    properties: dict[str, JsonValue]
    required: list[str]
    if operation == "apply_patch":
        properties = {
            "expected_workspace_revision": {"type": "integer", "minimum": 0},
            "plan_hash": {"type": "string", "pattern": "^[0-9a-f]{64}$"},
            "unified_diff": {"type": "string", "minLength": 1, "maxLength": 2000000},
            "target_files": {"type": "array", "items": {"type": "string"}},
            "rationale": {"type": "string", "minLength": 1},
        }
        required = list(properties)
    elif operation == "write_file":
        properties = {
            "path": {"type": "string"},
            "content": {"type": "string", "maxLength": 1000000},
            "expected_before_hash": {
                "type": ["string", "null"],
                "pattern": "^[0-9a-f]{64}$",
            },
        }
        required = ["path", "content"]
    elif operation == "delete_generated_file":
        properties, required = {"path": {"type": "string"}}, ["path"]
    else:
        properties, required = {}, []
    input_schema: dict[str, JsonValue] = {
        "type": "object",
        "properties": cast(JsonValue, properties),
        "required": cast(JsonValue, required),
        "additionalProperties": False,
    }
    return ToolDescriptor(
        tool_id=f"workspace.{operation}",
        version="1",
        display_name=f"Workspace {operation.replace('_', ' ')}",
        description="Bounded operation on the active detached coding worktree.",
        source=ToolSource.BUILT_IN,
        input_schema=input_schema,
        output_schema={"type": "object"},
        risk_level=ToolRiskLevel.R2 if write else ToolRiskLevel.R0,
        side_effects=(ToolSideEffect.LOCAL_WRITE if write else ToolSideEffect.LOCAL_READ,),
        execution_mode=ToolExecutionMode.SANDBOX,
        provider_visible=True,
        idempotent=not write,
        deterministic=True,
        default_timeout_seconds=30,
        required_permissions=("coding.workspace.write",) if write else ("coding.workspace.read",),
        tags=("coding", "workspace", "network-none"),
    )
