"""Opt-in live MiniMax tool-call and structured-output capability test."""

import argparse
import asyncio
import os
from pathlib import Path
from uuid import uuid4

from cognitive_os.config.provider_config import MiniMaxProviderConfig, load_provider_configuration
from cognitive_os.domain.model_requests import (
    ModelProviderRequest,
    ProviderMessage,
    ProviderMessageRole,
    ProviderToolDefinition,
)
from cognitive_os.domain.provider import ResponseFormat, ToolChoiceMode
from cognitive_os.providers.minimax.client import MiniMaxProvider


async def run(path: Path) -> None:
    if os.environ.get("COGOS_RUN_MINIMAX_LIVE") != "1":
        raise RuntimeError("set COGOS_RUN_MINIMAX_LIVE=1 to enable the live test")
    config = load_provider_configuration(path).providers.get("minimax")
    if not isinstance(config, MiniMaxProviderConfig):
        raise RuntimeError("MiniMax is not configured")
    provider = MiniMaxProvider(config)
    common = {
        "task_run_id": uuid4(),
        "correlation_id": uuid4(),
        "requested_model": config.model,
        "context_budget": 4096,
        "timeout_seconds": min(config.timeout_seconds, 120),
    }
    tool_request = ModelProviderRequest(
        model_call_id=uuid4(),
        messages=(
            ProviderMessage(
                role=ProviderMessageRole.USER,
                content=(
                    "Use the math.add tool to add 17 and 25. "
                    "Do not calculate without calling the tool."
                ),
            ),
        ),
        tools=(
            ProviderToolDefinition(
                name="math.add",
                description="Add two integers.",
                input_schema={
                    "type": "object",
                    "properties": {"a": {"type": "integer"}, "b": {"type": "integer"}},
                    "required": ["a", "b"],
                    "additionalProperties": False,
                },
            ),
        ),
        tool_choice=ToolChoiceMode.REQUIRED,
        max_output_tokens=1024,
        **common,
    )
    structured_request = ModelProviderRequest(
        model_call_id=uuid4(),
        messages=(
            ProviderMessage(
                role=ProviderMessageRole.USER, content='Return JSON with status equal to "ok".'
            ),
        ),
        response_format=ResponseFormat.JSON_SCHEMA,
        response_schema={
            "type": "object",
            "properties": {"status": {"const": "ok"}},
            "required": ["status"],
            "additionalProperties": False,
        },
        max_output_tokens=1024,
        **common,
    )
    try:
        tool_response = await provider.complete(tool_request)
        structured_response = await provider.complete(structured_request)
    finally:
        await provider.close()
    calls = [
        call
        for call in tool_response.tool_calls
        if call.name == "math.add" and call.arguments == {"a": 17, "b": 25}
    ]
    if not calls:
        raise RuntimeError("MiniMax did not return the required normalized tool call")
    if structured_response.structured_output != {"status": "ok"}:
        raise RuntimeError("MiniMax structured output did not validate")
    print("MiniMax tool-call and structured-output smoke test passed.")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    asyncio.run(run(parser.parse_args().config))


if __name__ == "__main__":
    main()
