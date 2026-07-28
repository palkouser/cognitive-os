"""Construction from configuration, and the shared provider contract all three adapters pass.

Two things are asserted here that no adapter test can assert on its own: that every adapter
is reachable through *one* explicit match rather than through four call sites, and that all
three new adapters satisfy the same `ModelProviderPort` shape as the ones that came before.
An adapter that satisfied its own tests but not the port would fail at the registry.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from cognitive_os.config.provider_config import (
    ClaudeCodeProviderConfig,
    CodexCliProviderConfig,
    MiniMaxKeyType,
    MiniMaxProviderConfig,
    OpenRouterProviderConfig,
    ProviderConfiguration,
    load_provider_configuration,
)
from cognitive_os.domain.provider import ProviderKind
from cognitive_os.domain.provider_output import ProviderAdapterKind
from cognitive_os.providers.claude_code import ClaudeCodeAdvisoryProvider
from cognitive_os.providers.codex_cli import CodexCliAdvisoryProvider
from cognitive_os.providers.errors import ProviderConfigurationError
from cognitive_os.providers.factory import build_provider, build_registry
from cognitive_os.providers.minimax.client import MiniMaxProvider
from cognitive_os.providers.openrouter import OpenRouterProvider


def all_configs(tmp_path: Path) -> dict[ProviderAdapterKind, Any]:
    return {
        ProviderAdapterKind.MINIMAX: MiniMaxProviderConfig(
            key_type=MiniMaxKeyType.SUBSCRIPTION, enabled=True
        ),
        ProviderAdapterKind.OPENROUTER: OpenRouterProviderConfig(enabled=True),
        ProviderAdapterKind.CLAUDE_CODE: ClaudeCodeProviderConfig(
            working_directory=tmp_path, enabled=True
        ),
        ProviderAdapterKind.CODEX_CLI: CodexCliProviderConfig(
            working_directory=tmp_path, enabled=True
        ),
    }


class TestOneExplicitMatch:
    def test_every_adapter_constructs_through_the_factory(self, tmp_path: Path) -> None:
        expected = {
            ProviderAdapterKind.MINIMAX: MiniMaxProvider,
            ProviderAdapterKind.OPENROUTER: OpenRouterProvider,
            ProviderAdapterKind.CLAUDE_CODE: ClaudeCodeAdvisoryProvider,
            ProviderAdapterKind.CODEX_CLI: CodexCliAdvisoryProvider,
        }
        for kind, config in all_configs(tmp_path).items():
            assert isinstance(build_provider(config), expected[kind]), kind

    def test_the_factory_covers_every_adapter_kind_a_configuration_can_name(
        self, tmp_path: Path
    ) -> None:
        """A new adapter kind without a factory arm would fail at runtime, not at import."""
        configurable = set(all_configs(tmp_path))
        never_configured = {ProviderAdapterKind.REPLAY, ProviderAdapterKind.MOCK}
        assert configurable | never_configured == set(ProviderAdapterKind)

    def test_an_unrecognised_configuration_fails_closed(self) -> None:
        class NotAProviderConfig:
            provider_id = "invented"
            enabled = True

        with pytest.raises(ProviderConfigurationError, match="no adapter is registered"):
            build_provider(NotAProviderConfig())  # type: ignore[arg-type]

    def test_construction_is_a_match_not_a_dynamic_import(self) -> None:
        """An import-string constructor would make a configuration file a code loader."""
        source = Path("src/cognitive_os/providers/factory.py").read_text(encoding="utf-8")
        for mechanism in ("importlib", "__import__", "eval(", "exec(", "entry_points"):
            assert mechanism not in source


class TestRegistryConstruction:
    def test_only_enabled_providers_are_registered(self, tmp_path: Path) -> None:
        configuration = ProviderConfiguration(
            default_provider_id="minimax",
            providers={
                "minimax": MiniMaxProviderConfig(
                    key_type=MiniMaxKeyType.SUBSCRIPTION, enabled=True
                ),
                "openrouter": OpenRouterProviderConfig(enabled=False),
                "codex-cli": CodexCliProviderConfig(working_directory=tmp_path, enabled=False),
            },
        )
        registry = build_registry(configuration)
        assert registry.list_provider_ids() == ("minimax",)

    def test_the_example_configuration_builds_the_one_enabled_provider(self) -> None:
        configuration = load_provider_configuration(Path("config/providers.example.yaml"))
        registry = build_registry(configuration)
        assert registry.list_provider_ids() == ("minimax",)

    def test_every_example_provider_can_be_constructed_when_enabled(self) -> None:
        """Disabled by default is a policy, not an excuse for a config that cannot build."""
        configuration = load_provider_configuration(Path("config/providers.example.yaml"))
        for config in configuration.providers.values():
            assert build_provider(config.model_copy(update={"enabled": True})) is not None


class TestTheSharedProviderContract:
    @pytest.mark.parametrize(
        "kind",
        [
            ProviderAdapterKind.OPENROUTER,
            ProviderAdapterKind.CLAUDE_CODE,
            ProviderAdapterKind.CODEX_CLI,
        ],
    )
    def test_each_new_adapter_satisfies_the_port(
        self, tmp_path: Path, kind: ProviderAdapterKind
    ) -> None:
        # Structural rather than `isinstance`: `ModelProviderPort` is a plain `Protocol`,
        # and making it runtime-checkable to satisfy a test would weaken a shared contract
        # for the convenience of one assertion.
        provider = build_provider(all_configs(tmp_path)[kind])
        for member in (
            "provider_id",
            "identity",
            "enabled",
            "complete",
            "stream",
            "health_check",
            "get_model_capabilities",
        ):
            assert hasattr(provider, member), member
        assert provider.identity.provider_id == provider.provider_id
        assert provider.enabled is True

    @pytest.mark.parametrize(
        ("kind", "expected"),
        [
            (ProviderAdapterKind.OPENROUTER, ProviderKind.NETWORK_API),
            (ProviderAdapterKind.CLAUDE_CODE, ProviderKind.CLI_AGENT),
            (ProviderAdapterKind.CODEX_CLI, ProviderKind.CLI_AGENT),
        ],
    )
    def test_the_provider_kind_is_reported_correctly(
        self, tmp_path: Path, kind: ProviderAdapterKind, expected: ProviderKind
    ) -> None:
        provider = build_provider(all_configs(tmp_path)[kind])
        assert provider.identity.provider_kind is expected

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "kind",
        [
            ProviderAdapterKind.OPENROUTER,
            ProviderAdapterKind.CLAUDE_CODE,
            ProviderAdapterKind.CODEX_CLI,
        ],
    )
    async def test_every_adapter_reports_structured_output_capability(
        self, tmp_path: Path, kind: ProviderAdapterKind
    ) -> None:
        """One shared advisory schema is the whole point; an adapter that cannot return
        structured output cannot be compared with the other two."""
        provider = build_provider(all_configs(tmp_path)[kind])
        capabilities = await provider.get_model_capabilities("any-model")
        assert capabilities.supports_structured_output is True
        assert capabilities.supports_streaming is False
