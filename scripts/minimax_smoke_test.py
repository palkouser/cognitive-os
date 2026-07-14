"""Explicitly opted-in bounded MiniMax completion smoke test."""

from __future__ import annotations

import argparse
import asyncio
import os
from pathlib import Path
from uuid import uuid4

from cognitive_os.config.provider_config import (
    MiniMaxProviderConfig,
    load_provider_configuration,
)
from cognitive_os.domain.model_requests import (
    ModelProviderRequest,
    ProviderMessage,
    ProviderMessageRole,
)
from cognitive_os.domain.provider import ResponseFormat
from cognitive_os.providers.minimax.client import MiniMaxProvider


async def run(path: Path) -> None:
    if os.environ.get("COGOS_RUN_MINIMAX_LIVE") != "1":
        raise RuntimeError("set COGOS_RUN_MINIMAX_LIVE=1 to enable the live MiniMax test")
    configuration = load_provider_configuration(path)
    config = configuration.providers.get("minimax")
    if not isinstance(config, MiniMaxProviderConfig):
        raise RuntimeError("MiniMax is not configured")
    provider = MiniMaxProvider(config)
    request = ModelProviderRequest(
        model_call_id=uuid4(),
        task_run_id=uuid4(),
        correlation_id=uuid4(),
        requested_model=config.model,
        messages=(
            ProviderMessage(
                role=ProviderMessageRole.USER,
                content='Return the exact JSON object {"status":"ok"}.',
            ),
        ),
        response_format=ResponseFormat.JSON_OBJECT,
        max_output_tokens=32,
        context_budget=1024,
        timeout_seconds=min(config.timeout_seconds, 120),
    )
    try:
        response = await provider.complete(request)
    finally:
        await provider.close()
    if response.structured_output != {"status": "ok"}:
        raise RuntimeError("MiniMax smoke response did not match the bounded request")
    print("MiniMax live smoke test passed.")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    arguments = parser.parse_args()
    asyncio.run(run(arguments.config))


if __name__ == "__main__":
    main()
