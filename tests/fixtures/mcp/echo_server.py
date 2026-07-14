"""Tracked local MCP fixture server; no network or installation required."""

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("cognitive-os-test")


@mcp.tool()
def echo(value: str) -> str:
    """Return a bounded test value."""
    return value[:100]


if __name__ == "__main__":
    mcp.run(transport="stdio")
