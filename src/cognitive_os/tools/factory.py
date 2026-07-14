"""Explicit built-in Tool Registry construction."""

from cognitive_os.config.tool_config import ToolPlaneConfiguration

from .host import FilesystemTool, GitReadOnlyTool, SystemInfoTool
from .registry import ToolRegistry


def build_builtin_registry(config: ToolPlaneConfiguration, *, freeze: bool = True) -> ToolRegistry:
    registry = ToolRegistry()
    candidates = (
        FilesystemTool("list", config.workspace_roots),
        FilesystemTool("read", config.workspace_roots),
        FilesystemTool("stat", config.workspace_roots),
        GitReadOnlyTool("status", config.workspace_roots),
        GitReadOnlyTool("diff", config.workspace_roots),
        GitReadOnlyTool("log", config.workspace_roots),
        SystemInfoTool(),
    )
    registry.register_many(
        tuple(item for item in candidates if config.tools.get(item.descriptor.tool_id, False))
    )
    if freeze:
        registry.freeze()
    return registry
