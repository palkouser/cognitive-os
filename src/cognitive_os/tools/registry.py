"""Explicit, deterministic Tool Registry."""

from __future__ import annotations

import json
from hashlib import sha256

from cognitive_os.application.ports.tool import ToolPort
from cognitive_os.domain.tools import ToolDescriptor

from .errors import ToolNotFoundError, ToolRegistrationError


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[tuple[str, str], ToolPort] = {}
        self._frozen = False

    def register(self, tool: ToolPort) -> None:
        if self._frozen:
            raise ToolRegistrationError("tool registry is frozen")
        descriptor = tool.descriptor
        key = (descriptor.tool_id, descriptor.version)
        if key in self._tools:
            raise ToolRegistrationError(f"duplicate tool registration: {descriptor.tool_id}")
        if descriptor.descriptor_hash != descriptor.computed_hash():
            raise ToolRegistrationError("tool descriptor hash is invalid")
        self._tools[key] = tool

    def register_many(self, tools: tuple[ToolPort, ...]) -> None:
        for tool in tools:
            self.register(tool)

    def get(self, tool_id: str, version: str) -> ToolPort | None:
        return self._tools.get((tool_id, version))

    def require(self, tool_id: str, version: str) -> ToolPort:
        tool = self.get(tool_id, version)
        if tool is None:
            raise ToolNotFoundError(f"tool is unavailable: {tool_id}@{version}")
        return tool

    def list_all(self) -> tuple[ToolDescriptor, ...]:
        return tuple(tool.descriptor for _, tool in sorted(self._tools.items()))

    def list_provider_visible(self) -> tuple[ToolDescriptor, ...]:
        return tuple(item for item in self.list_all() if item.provider_visible)

    def list_by_risk(self, risk: str) -> tuple[ToolDescriptor, ...]:
        return tuple(item for item in self.list_all() if item.risk_level.value == risk)

    def freeze(self) -> None:
        self._frozen = True

    def snapshot(self) -> str:
        records = [item.model_dump(mode="json") for item in self.list_all()]
        return sha256(
            json.dumps(records, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
