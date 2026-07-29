"""One explicit construction boundary from validated configuration to a registered provider.

A `match` over the adapter discriminator, and nothing else. Deliberately not a plugin
registry, an entry-point scan or an import-string constructor: every one of those turns a
configuration file into a mechanism for loading arbitrary code, which is exactly the
authority widening the rest of this sprint spends its effort preventing.

An unknown adapter fails closed. Because the configuration union is discriminated, an
unrecognised value is normally refused at load; this `match` is the second refusal, for the
case where a caller constructed a config object directly. See ADR 0087.
"""

from __future__ import annotations

from cognitive_os.application.ports.model_provider import ModelProviderPort
from cognitive_os.config.provider_config import (
    ClaudeCodeProviderConfig,
    CodexCliProviderConfig,
    MiniMaxProviderConfig,
    OpenRouterProviderConfig,
    ProviderAdapterConfig,
    ProviderConfiguration,
)
from cognitive_os.providers.claude_code import ClaudeCodeAdvisoryProvider
from cognitive_os.providers.codex_cli import CodexCliAdvisoryProvider
from cognitive_os.providers.errors import ProviderConfigurationError
from cognitive_os.providers.minimax.client import MiniMaxProvider
from cognitive_os.providers.openrouter import OpenRouterProvider
from cognitive_os.providers.registry import ProviderRegistry


def build_provider(config: ProviderAdapterConfig) -> ModelProviderPort:
    """Construct exactly one adapter from exactly one validated configuration."""
    match config:
        case MiniMaxProviderConfig():
            return MiniMaxProvider(config)
        case OpenRouterProviderConfig():
            return OpenRouterProvider(config)
        case ClaudeCodeProviderConfig():
            return ClaudeCodeAdvisoryProvider(config)
        case CodexCliProviderConfig():
            return CodexCliAdvisoryProvider(config)
        case _:
            raise ProviderConfigurationError(
                provider_id=getattr(config, "provider_id", "unknown"),
                error_code="unknown_adapter",
                message="no adapter is registered for this provider configuration",
            )


def build_registry(configuration: ProviderConfiguration) -> ProviderRegistry:
    """Register every *enabled* provider, in a stable order.

    Disabled entries are skipped rather than registered-and-ignored: the registry refuses a
    disabled provider by design, and a configuration file that lists four adapters with three
    turned off should produce a registry with one, not an error.
    """
    registry = ProviderRegistry()
    for provider_id in sorted(configuration.providers):
        config = configuration.providers[provider_id]
        if not config.enabled:
            continue
        registry.register(build_provider(config))
    return registry
