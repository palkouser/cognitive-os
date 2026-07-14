import os
from uuid import uuid4

import pytest

from cognitive_os.config.provider_config import MiniMaxKeyType, MiniMaxProviderConfig
from cognitive_os.domain.model_requests import (
    ModelProviderRequest,
    ProviderMessage,
    ProviderMessageRole,
)
from cognitive_os.providers.minimax.client import MiniMaxProvider


@pytest.mark.minimax_live
@pytest.mark.asyncio
async def test_live_minimax_health_and_bounded_completion() -> None:
    if os.environ.get("COGOS_RUN_MINIMAX_LIVE") != "1":
        pytest.skip("live MiniMax execution is not enabled")
    if not os.environ.get("COGOS_MINIMAX_API_KEY"):
        pytest.skip("MiniMax API key is not configured")
    provider = MiniMaxProvider(MiniMaxProviderConfig(key_type=MiniMaxKeyType.SUBSCRIPTION))
    request = ModelProviderRequest(
        model_call_id=uuid4(),
        task_run_id=uuid4(),
        correlation_id=uuid4(),
        requested_model=provider.config.model,
        messages=(
            ProviderMessage(
                role=ProviderMessageRole.USER,
                content="Return only the word ready.",
            ),
        ),
        max_output_tokens=8,
        context_budget=1024,
    )
    try:
        health = await provider.health_check()
        response = await provider.complete(request)
    finally:
        await provider.close()
    assert health.resolved_model == provider.config.model
    assert response.content
