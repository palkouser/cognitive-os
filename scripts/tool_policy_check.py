"""Dry-run a Tool Plane policy decision without execution."""

import argparse
import asyncio
import json
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from cognitive_os.config.tool_config import load_tool_configuration
from cognitive_os.domain.tools import ToolInvocation
from cognitive_os.tools.factory import build_builtin_registry
from cognitive_os.tools.policy import ToolPolicyEngine


async def run(config_path: Path, tool_id: str, arguments_path: Path) -> int:
    config = load_tool_configuration(config_path)
    registry = build_builtin_registry(config)
    descriptor = next((item for item in registry.list_all() if item.tool_id == tool_id), None)
    if descriptor is None:
        raise RuntimeError("tool is unavailable")
    arguments = json.loads(arguments_path.read_text(encoding="utf-8"))
    invocation = ToolInvocation(
        tool_call_id=uuid4(),
        task_run_id=uuid4(),
        correlation_id=uuid4(),
        tool_id=tool_id,
        tool_version=descriptor.version,
        arguments=arguments,
        requested_at=datetime.now(UTC),
        requested_by="policy-dry-run",
    )
    enabled = frozenset(name for name, value in config.tools.items() if value)
    decision = await ToolPolicyEngine(config.workspace_roots, enabled).evaluate(
        invocation, descriptor
    )
    print(f"{decision.action.value}\t{decision.rule_id}\t{decision.reason}")
    return 1 if decision.action.value == "deny" else 0


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tool", required=True)
    parser.add_argument("--arguments-file", type=Path, required=True)
    parser.add_argument("--config", type=Path, required=True)
    arguments = parser.parse_args()
    raise SystemExit(asyncio.run(run(arguments.config, arguments.tool, arguments.arguments_file)))


if __name__ == "__main__":
    main()
