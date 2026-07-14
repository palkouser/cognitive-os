from __future__ import annotations

import asyncio

import pytest

from LightAgent import AsyncToolDispatcher, ToolRegistry

pytestmark = pytest.mark.contract


def add_numbers(left: int, right: int) -> int:
    return left + right


add_numbers.tool_info = {
    "tool_name": "add_numbers",
    "tool_description": "Add two integers.",
    "tool_params": [
        {"name": "left", "type": "integer", "required": True},
        {"name": "right", "type": "integer", "required": True},
    ],
}


def test_tool_registration_and_dispatch_contract() -> None:
    registry = ToolRegistry()
    assert registry.register_tool(add_numbers) is True
    assert registry.get_tools()[0]["function"]["name"] == "add_numbers"

    dispatcher = AsyncToolDispatcher(registry.function_mappings, registry.function_info)
    assert asyncio.run(dispatcher.dispatch("add_numbers", {"left": 20, "right": 22})) == "42"


def test_invalid_tool_input_is_reported_predictably() -> None:
    registry = ToolRegistry()
    registry.register_tool(add_numbers)
    dispatcher = AsyncToolDispatcher(registry.function_mappings, registry.function_info)

    result = asyncio.run(dispatcher.dispatch("add_numbers", {"left": "20", "right": 22}))

    assert result.startswith("[LA-TOOL]")
    assert "expected `integer`" in result
