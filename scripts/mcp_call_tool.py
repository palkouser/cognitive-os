"""Call one explicit MCP tool for operator diagnostics."""

import argparse
import asyncio
import json
from pathlib import Path

from cognitive_os.tools.mcp.client import McpStdioClient
from cognitive_os.tools.mcp.config import load_mcp_configuration


async def run(path: Path, server_id: str, tool: str, arguments_path: Path) -> None:
    config = load_mcp_configuration(path).servers[server_id]
    arguments = json.loads(arguments_path.read_text(encoding="utf-8"))
    client = McpStdioClient(config)
    try:
        await client.start()
        result = await client.call_tool(tool, arguments)
        print(f"MCP tool completed with {len(result.content)} content item(s).")
    finally:
        await client.close()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--server", required=True)
    parser.add_argument("--tool", required=True)
    parser.add_argument("--arguments-file", type=Path, required=True)
    args = parser.parse_args()
    asyncio.run(run(args.config, args.server, args.tool, args.arguments_file))


if __name__ == "__main__":
    main()
