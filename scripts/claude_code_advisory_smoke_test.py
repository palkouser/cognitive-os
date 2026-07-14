"""Explicitly opted-in read-only Claude Code advisory smoke test."""

from __future__ import annotations

import argparse
import asyncio
import os
from pathlib import Path
from uuid import uuid4

from cognitive_os.config.provider_config import ClaudeCodeProviderConfig
from cognitive_os.domain.model_requests import (
    ModelProviderRequest,
    ProviderMessage,
    ProviderMessageRole,
)
from cognitive_os.providers.claude_code.advisory import ClaudeCodeAdvisoryProvider


async def run(working_directory: Path) -> None:
    if os.environ.get("COGOS_RUN_CLAUDE_CODE_LIVE") != "1":
        raise RuntimeError("set COGOS_RUN_CLAUDE_CODE_LIVE=1 to enable the live Claude Code test")
    provider = ClaudeCodeAdvisoryProvider(
        ClaudeCodeProviderConfig(
            working_directory=working_directory,
            enabled=True,
            maximum_turns=3,
            timeout_seconds=180,
        )
    )
    request = ModelProviderRequest(
        model_call_id=uuid4(),
        task_run_id=uuid4(),
        correlation_id=uuid4(),
        requested_model="claude-code",
        messages=(
            ProviderMessage(
                role=ProviderMessageRole.USER,
                content=(
                    "Read the project instructions and return a short architectural summary. "
                    "Do not modify any file."
                ),
            ),
        ),
        timeout_seconds=180,
    )
    await provider.complete(request)
    print("Claude Code advisory smoke test passed without repository modification.")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--working-directory", type=Path, required=True)
    arguments = parser.parse_args()
    asyncio.run(run(arguments.working_directory))


if __name__ == "__main__":
    main()
