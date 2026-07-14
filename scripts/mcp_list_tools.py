"""List tools from one explicit MCP STDIO server."""

import argparse
import asyncio
from pathlib import Path

from cognitive_os.tools.mcp.client import McpStdioClient
from cognitive_os.tools.mcp.config import load_mcp_configuration


async def run(path: Path, server_id: str) -> None:
    config = load_mcp_configuration(path).servers[server_id]
    client = McpStdioClient(config)
    try:
        await client.start()
        response = await client.list_tools()
        for tool in response.tools:
            print(tool.name)
    finally:
        await client.close()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--server", required=True)
    args = parser.parse_args()
    asyncio.run(run(args.config, args.server))


if __name__ == "__main__":
    main()
