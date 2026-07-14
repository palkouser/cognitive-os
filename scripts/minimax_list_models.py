"""Safely list MiniMax model identifiers without account metadata."""

import argparse
import asyncio
from pathlib import Path

from cognitive_os.config.provider_config import MiniMaxProviderConfig, load_provider_configuration
from cognitive_os.providers.minimax.client import MiniMaxProvider
from cognitive_os.providers.minimax.health import model_ids


async def run(path: Path) -> None:
    config = load_provider_configuration(path).providers.get("minimax")
    if not isinstance(config, MiniMaxProviderConfig):
        raise RuntimeError("MiniMax is not configured")
    provider = MiniMaxProvider(config)
    try:
        response = await provider._get_client().models.list()
        for model in model_ids(response):
            print(model)
    finally:
        await provider.close()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    asyncio.run(run(parser.parse_args().config))


if __name__ == "__main__":
    main()
