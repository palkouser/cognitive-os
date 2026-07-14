"""Explicit MCP v1 STDIO client lifecycle."""

from __future__ import annotations

import os
from contextlib import AsyncExitStack
from typing import Any

from cognitive_os.tools.errors import McpClientError

from .config import McpServerConfiguration


class McpStdioClient:
    def __init__(self, config: McpServerConfiguration) -> None:
        self._config = config
        self._stack: AsyncExitStack | None = None
        self._session: Any | None = None

    async def start(self) -> None:
        try:
            from mcp.client.stdio import stdio_client

            from mcp import ClientSession, StdioServerParameters
        except ImportError as error:
            raise McpClientError("MCP optional dependency is unavailable") from error
        environment = {
            name: os.environ[name]
            for name in self._config.environment_allowlist
            if name in os.environ
        }
        parameters = StdioServerParameters(
            command=str(self._config.command),
            args=list(self._config.arguments),
            env=environment,
            cwd=str(self._config.working_directory),
        )
        stack = AsyncExitStack()
        read, write = await stack.enter_async_context(stdio_client(parameters))
        session = await stack.enter_async_context(ClientSession(read, write))
        await session.initialize()
        self._stack, self._session = stack, session

    async def list_tools(self) -> object:
        if self._session is None:
            raise McpClientError("MCP session is not started")
        return await self._session.list_tools()

    async def call_tool(self, name: str, arguments: dict[str, object]) -> object:
        if self._session is None:
            raise McpClientError("MCP session is not started")
        return await self._session.call_tool(name, arguments)

    async def close(self) -> None:
        if self._stack is not None:
            await self._stack.aclose()
        self._stack, self._session = None, None
