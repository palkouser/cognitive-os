"""Print credential-safe normalized health for configured providers."""

from __future__ import annotations

import argparse
import asyncio
from pathlib import Path

from cognitive_os.config.provider_config import (
    ClaudeCodeProviderConfig,
    MiniMaxProviderConfig,
    load_provider_configuration,
)
from cognitive_os.domain.common import utc_now
from cognitive_os.domain.provider import ProviderHealth, ProviderStatus
from cognitive_os.providers.claude_code.advisory import ClaudeCodeAdvisoryProvider
from cognitive_os.providers.minimax.client import MiniMaxProvider


async def check_configured_provider(
    config: MiniMaxProviderConfig | ClaudeCodeProviderConfig,
) -> ProviderHealth:
    if not config.enabled:
        return ProviderHealth(
            provider_id=config.provider_id,
            status=ProviderStatus.UNAVAILABLE,
            checked_at=utc_now(),
            configured_model=getattr(config, "model", None),
            message="provider is disabled",
        )
    if isinstance(config, MiniMaxProviderConfig):
        provider = MiniMaxProvider(config)
        try:
            return await provider.health_check()
        finally:
            await provider.close()
    return await ClaudeCodeAdvisoryProvider(config).health_check()


async def run(config_path: Path) -> None:
    configuration = load_provider_configuration(config_path)
    for provider_id in sorted(configuration.providers):
        config = configuration.providers[provider_id]
        health = await check_configured_provider(config)
        latency = "-" if health.latency_ms is None else f"{health.latency_ms:.1f}ms"
        configured = health.configured_model or "-"
        resolved = health.resolved_model or "-"
        print(
            "\t".join(
                (
                    health.provider_id,
                    config.kind.value,
                    health.status.value,
                    latency,
                    configured,
                    resolved,
                    health.message,
                )
            )
        )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    arguments = parser.parse_args()
    asyncio.run(run(arguments.config))


if __name__ == "__main__":
    main()
