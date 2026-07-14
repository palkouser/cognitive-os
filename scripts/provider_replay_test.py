"""Run a deterministic provider replay without network or credentials."""

from pathlib import Path
from uuid import UUID

from cognitive_os.domain.model_requests import (
    ModelProviderRequest,
    ProviderMessage,
    ProviderMessageRole,
)
from cognitive_os.providers.replay import ReplayProvider


async def run() -> None:
    provider = ReplayProvider.from_directory(Path("tests/fixtures/providers/replay"))
    request = ModelProviderRequest(
        model_call_id=UUID(int=1),
        task_run_id=UUID(int=2),
        correlation_id=UUID(int=3),
        requested_model="replay-model",
        messages=(
            ProviderMessage(
                role=ProviderMessageRole.USER,
                content="Return the exact word ready.",
            ),
        ),
    )
    response = await provider.complete(request)
    if response.content != "ready":
        raise RuntimeError("replay response did not match the reviewed fixture")
    print("Provider replay verification passed.")


if __name__ == "__main__":
    import asyncio

    asyncio.run(run())
