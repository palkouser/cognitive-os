import pytest

from cognitive_os.config.provider_config import MiniMaxKeyType, MiniMaxProviderConfig
from cognitive_os.providers.errors import ProviderConfigurationError
from cognitive_os.providers.minimax.client import MiniMaxProvider
from cognitive_os.providers.mock import MockProvider
from cognitive_os.providers.registry import ProviderRegistry, select_provider


def test_registry_selection_is_static_and_duplicate_safe() -> None:
    provider = MockProvider()
    registry = ProviderRegistry((provider,))
    assert select_provider(registry, None, "mock") is provider
    with pytest.raises(ProviderConfigurationError, match="already registered"):
        registry.register(provider)
    with pytest.raises(ProviderConfigurationError, match="not registered"):
        registry.require("unknown")


def test_disabled_provider_cannot_be_registered() -> None:
    provider = MiniMaxProvider(
        MiniMaxProviderConfig(
            key_type=MiniMaxKeyType.SUBSCRIPTION,
            enabled=False,
        )
    )
    with pytest.raises(ProviderConfigurationError, match="disabled"):
        ProviderRegistry((provider,))
