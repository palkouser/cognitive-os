"""Check explicitly configured MCP STDIO servers."""

import argparse
import asyncio
from pathlib import Path

from cognitive_os.tools.mcp.client import McpStdioClient
from cognitive_os.tools.mcp.config import load_mcp_configuration


async def run(path: Path) -> int:
    failures = 0
    for server_id, config in load_mcp_configuration(path).servers.items():
        if not config.enabled:
            print(f"{server_id}\tdisabled")
            continue
        client = McpStdioClient(config)
        try:
            await client.start()
            await client.list_tools()
            print(f"{server_id}\tavailable")
        except Exception as error:
            failures += 1
            print(f"{server_id}\tunavailable\t{type(error).__name__}")
        finally:
            await client.close()
    return failures


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    raise SystemExit(asyncio.run(run(parser.parse_args().config)))


if __name__ == "__main__":
    main()
