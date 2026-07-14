"""Execute one enabled R0 host tool after validation and policy evaluation."""

import argparse
import asyncio
import json
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from cognitive_os.config.tool_config import load_tool_configuration
from cognitive_os.domain.approvals import PolicyAction
from cognitive_os.domain.tools import ToolExecutionContext, ToolInvocation, ToolRiskLevel
from cognitive_os.tools.factory import build_builtin_registry
from cognitive_os.tools.policy import ToolPolicyEngine
from cognitive_os.tools.validation import validate_value


async def run(config_path: Path, tool_id: str, arguments_path: Path) -> None:
    config = load_tool_configuration(config_path)
    registry = build_builtin_registry(config)
    descriptor = next((item for item in registry.list_all() if item.tool_id == tool_id), None)
    if descriptor is None or descriptor.risk_level is not ToolRiskLevel.R0:
        raise RuntimeError("operational execution supports enabled R0 tools only")
    arguments = json.loads(arguments_path.read_text(encoding="utf-8"))
    validate_value(arguments, descriptor.input_schema)
    invocation = ToolInvocation(
        tool_call_id=uuid4(),
        task_run_id=uuid4(),
        correlation_id=uuid4(),
        tool_id=tool_id,
        tool_version=descriptor.version,
        arguments=arguments,
        requested_at=datetime.now(UTC),
        requested_by="operator",
    )
    enabled = frozenset(name for name, value in config.tools.items() if value)
    decision = await ToolPolicyEngine(config.workspace_roots, enabled).evaluate(
        invocation, descriptor
    )
    if decision.action is not PolicyAction.ALLOW:
        raise RuntimeError(f"tool execution denied by {decision.rule_id}")
    context = ToolExecutionContext(
        workspace=str(config.workspace_roots[0]),
        timeout_seconds=descriptor.default_timeout_seconds,
        maximum_stdout_bytes=config.sandbox.limits.maximum_stdout_bytes,
        maximum_stderr_bytes=config.sandbox.limits.maximum_stderr_bytes,
        maximum_artifact_bytes=config.sandbox.limits.maximum_artifact_bytes,
    )
    result = await registry.require(tool_id, descriptor.version).execute(invocation, context)
    validate_value(result.result, descriptor.output_schema)
    print(f"{result.status.value}\t{result.tool_id}\t{result.tool_call_id}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--tool", required=True)
    parser.add_argument("--arguments-file", type=Path, required=True)
    args = parser.parse_args()
    asyncio.run(run(args.config, args.tool, args.arguments_file))


if __name__ == "__main__":
    main()
