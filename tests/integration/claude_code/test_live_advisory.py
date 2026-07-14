import os
from pathlib import Path
from uuid import uuid4

import pytest

from cognitive_os.config.provider_config import ClaudeCodeProviderConfig
from cognitive_os.domain.model_requests import (
    ModelProviderRequest,
    ProviderMessage,
    ProviderMessageRole,
)
from cognitive_os.providers.claude_code.advisory import ClaudeCodeAdvisoryProvider


@pytest.mark.claude_code_live
@pytest.mark.asyncio
async def test_live_claude_code_read_only_advisory() -> None:
    if os.environ.get("COGOS_RUN_CLAUDE_CODE_LIVE") != "1":
        pytest.skip("live Claude Code execution is not enabled")
    provider = ClaudeCodeAdvisoryProvider(
        ClaudeCodeProviderConfig(
            working_directory=Path.cwd(),
            enabled=True,
            timeout_seconds=180,
            maximum_turns=3,
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
                content="Summarize the architecture without modifying any file.",
            ),
        ),
    )
    response = await provider.complete(request)
    assert response.content
