"""Provider configuration: unambiguous adapters, conservative defaults, unsafe values refused.

The point of the `adapter` discriminator is that Claude Code and Codex are both `cli_agent`.
These tests exist so that a future entry cannot silently resolve to the wrong CLI, and so
that a configuration file cannot be the thing that widens a provider's authority.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from cognitive_os.config.provider_config import (
    MAXIMUM_CLI_STDERR_BYTES,
    MAXIMUM_CLI_STDOUT_BYTES,
    MAXIMUM_CLI_TIMEOUT_SECONDS,
    PROVIDER_CONFIGURATION_VERSION,
    ClaudeCodeProviderConfig,
    CliProcessLimits,
    CodexCliProviderConfig,
    OpenRouterProviderConfig,
    ProviderRetentionDefaults,
    load_provider_configuration,
)
from cognitive_os.domain.memory import MemorySensitivity
from cognitive_os.domain.provider_output import (
    ProviderAdapterKind,
    ProviderOutputRetentionMode,
)


def _write(tmp_path: Path, document: dict[str, object]) -> Path:
    path = tmp_path / "providers.yaml"
    path.write_text(yaml.safe_dump(document), encoding="utf-8")
    return path


class TestEveryAdapterParsesUnambiguously:
    def test_the_example_configuration_resolves_all_four_adapters(self) -> None:
        configuration = load_provider_configuration(Path("config/providers.example.yaml"))
        assert configuration.configuration_version == PROVIDER_CONFIGURATION_VERSION
        assert {key: value.adapter for key, value in configuration.providers.items()} == {
            "minimax": ProviderAdapterKind.MINIMAX,
            "openrouter": ProviderAdapterKind.OPENROUTER,
            "claude-code": ProviderAdapterKind.CLAUDE_CODE,
            "codex-cli": ProviderAdapterKind.CODEX_CLI,
        }

    def test_two_cli_adapters_are_distinguished_by_adapter_not_by_kind(self) -> None:
        configuration = load_provider_configuration(Path("config/providers.example.yaml"))
        claude = configuration.providers["claude-code"]
        codex = configuration.providers["codex-cli"]
        assert claude.kind == codex.kind
        assert claude.adapter is not codex.adapter
        assert isinstance(claude, ClaudeCodeProviderConfig)
        assert isinstance(codex, CodexCliProviderConfig)

    def test_an_unknown_adapter_fails_closed(self, tmp_path: Path) -> None:
        path = _write(
            tmp_path,
            {
                "default_provider_id": "x",
                "providers": {"x": {"adapter": "some_new_provider", "kind": "network_api"}},
            },
        )
        with pytest.raises(ValidationError):
            load_provider_configuration(path)

    def test_a_cli_entry_without_an_adapter_written_today_must_be_explicit(
        self, tmp_path: Path
    ) -> None:
        """`cli_agent` meant Claude Code once and means nothing definite now."""
        path = _write(
            tmp_path,
            {
                "default_provider_id": "mystery",
                "providers": {
                    "mystery": {"kind": "mock", "working_directory": str(tmp_path)},
                },
            },
        )
        with pytest.raises(ValueError, match="does not name an adapter"):
            load_provider_configuration(path)


class TestLegacyConfigurationStillLoads:
    def test_a_pre_discriminator_file_is_migrated_rather_than_rejected(
        self, tmp_path: Path
    ) -> None:
        path = _write(
            tmp_path,
            {
                "default_provider_id": "minimax",
                "providers": {
                    "minimax": {"kind": "network_api", "key_type": "subscription"},
                    "claude-code": {
                        "kind": "cli_agent",
                        "working_directory": str(tmp_path),
                        "timeout_seconds": 300,
                    },
                },
            },
        )
        configuration = load_provider_configuration(path)
        assert configuration.providers["minimax"].adapter is ProviderAdapterKind.MINIMAX
        claude = configuration.providers["claude-code"]
        assert claude.adapter is ProviderAdapterKind.CLAUDE_CODE
        # The old top-level timeout meant exactly the new nested one.
        assert claude.limits.timeout_seconds == 300

    def test_a_future_configuration_version_is_refused(self, tmp_path: Path) -> None:
        path = _write(
            tmp_path,
            {
                "configuration_version": PROVIDER_CONFIGURATION_VERSION + 1,
                "default_provider_id": "minimax",
                "providers": {"minimax": {"adapter": "minimax", "key_type": "subscription"}},
            },
        )
        with pytest.raises(ValidationError, match="newer than this build"):
            load_provider_configuration(path)


class TestDefaultsAreTheRefusingOnes:
    def test_every_adapter_defaults_to_transient_retention_and_no_live_smoke(
        self, tmp_path: Path
    ) -> None:
        configuration = load_provider_configuration(Path("config/providers.example.yaml"))
        for provider in configuration.providers.values():
            assert provider.retention.retention_mode is ProviderOutputRetentionMode.NONE
            assert provider.live_smoke_enabled is False

    def test_normalized_content_cannot_be_a_configured_default(self) -> None:
        with pytest.raises(ValidationError, match="cannot be a configured default"):
            ProviderRetentionDefaults(retention_mode=ProviderOutputRetentionMode.NORMALIZED_CONTENT)

    def test_an_unrecognised_sensitivity_default_is_refused(self) -> None:
        with pytest.raises(ValidationError):
            ProviderRetentionDefaults(sensitivity=MemorySensitivity.CONFIDENTIAL)

    def test_openrouter_defaults_to_zero_spend_and_the_strict_data_policy(self) -> None:
        config = OpenRouterProviderConfig()
        assert config.maximum_spend_usd == 0.0
        assert config.require_free_model is True
        assert config.require_zero_data_retention is True
        assert config.allow_data_collection is False
        assert config.maximum_attempts == 1
        assert config.default_route == "openrouter/free"
        assert config.pinned_free_model is None

    def test_the_cli_process_limits_default_below_the_hard_maxima(self) -> None:
        limits = CliProcessLimits()
        assert limits.timeout_seconds < MAXIMUM_CLI_TIMEOUT_SECONDS
        assert limits.maximum_stdout_bytes < MAXIMUM_CLI_STDOUT_BYTES
        assert limits.maximum_stderr_bytes < MAXIMUM_CLI_STDERR_BYTES


class TestUnsafeValuesFailAtLoad:
    @pytest.mark.parametrize(
        "overrides",
        [
            {"timeout_seconds": MAXIMUM_CLI_TIMEOUT_SECONDS + 1},
            {"maximum_stdout_bytes": MAXIMUM_CLI_STDOUT_BYTES + 1},
            {"maximum_stderr_bytes": MAXIMUM_CLI_STDERR_BYTES + 1},
        ],
    )
    def test_a_limit_above_a_hard_maximum_is_refused(self, overrides: dict[str, float]) -> None:
        with pytest.raises(ValidationError, match="exceeds"):
            CliProcessLimits(**overrides)

    @pytest.mark.parametrize("mode", ["acceptEdits", "auto", "bypassPermissions", "dontAsk"])
    def test_a_mutating_claude_permission_mode_is_refused(self, mode: str, tmp_path: Path) -> None:
        with pytest.raises(ValidationError, match="permits mutation"):
            ClaudeCodeProviderConfig(working_directory=tmp_path, permission_mode=mode)

    @pytest.mark.parametrize("tool", ["Bash", "Edit", "Write", "WebFetch", "Task"])
    def test_a_mutating_claude_tool_cannot_be_allowed(self, tool: str, tmp_path: Path) -> None:
        with pytest.raises(ValidationError, match="must not allow mutating tools"):
            ClaudeCodeProviderConfig(working_directory=tmp_path, allowed_tools=("Read", tool))

    def test_an_empty_claude_tool_allowlist_is_refused(self, tmp_path: Path) -> None:
        with pytest.raises(ValidationError, match="at least one read-only tool"):
            ClaudeCodeProviderConfig(working_directory=tmp_path, allowed_tools=())

    @pytest.mark.parametrize("sandbox", ["workspace-write", "danger-full-access"])
    def test_a_writable_codex_sandbox_is_refused(self, sandbox: str, tmp_path: Path) -> None:
        with pytest.raises(ValidationError, match="permits writes"):
            CodexCliProviderConfig(working_directory=tmp_path, sandbox_mode=sandbox)

    def test_codex_cannot_be_configured_to_ask_for_approval(self, tmp_path: Path) -> None:
        """An unattended advisory call has nobody to answer the prompt."""
        with pytest.raises(ValidationError, match="must be 'never'"):
            CodexCliProviderConfig(working_directory=tmp_path, approval_policy="on-request")

    def test_codex_cannot_be_configured_to_persist_or_inherit_user_config(
        self, tmp_path: Path
    ) -> None:
        for field in ("ephemeral", "ignore_user_config"):
            with pytest.raises(ValidationError):
                CodexCliProviderConfig(working_directory=tmp_path, **{field: False})

    def test_a_secret_like_environment_name_cannot_be_allowlisted(self, tmp_path: Path) -> None:
        with pytest.raises(ValidationError, match="secret-like names"):
            ClaudeCodeProviderConfig(
                working_directory=tmp_path,
                environment_allowlist=("PATH", "OPENROUTER_API_KEY"),
            )

    def test_an_executable_cannot_be_a_shell_fragment(self, tmp_path: Path) -> None:
        with pytest.raises(ValidationError, match="never a shell fragment"):
            CodexCliProviderConfig(working_directory=tmp_path, executable="codex; rm -rf /")

    def test_openrouter_requires_https_and_refuses_embedded_credentials(self) -> None:
        with pytest.raises(ValidationError, match="HTTPS URL"):
            OpenRouterProviderConfig(base_url="http://openrouter.ai/api/v1")
        with pytest.raises(ValidationError, match="credentials"):
            OpenRouterProviderConfig(
                base_url="https://user:pass@openrouter.ai/api/v1"  # pragma: allowlist secret
            )

    def test_the_openrouter_key_may_only_come_from_its_own_variable(self) -> None:
        with pytest.raises(ValidationError, match="OPENROUTER_API_KEY"):
            OpenRouterProviderConfig(
                api_key_environment_variable="COGOS_MINIMAX_API_KEY"  # pragma: allowlist secret
            )

    def test_a_free_only_policy_cannot_also_authorise_spend(self) -> None:
        with pytest.raises(ValidationError, match="cannot also authorise spend"):
            OpenRouterProviderConfig(require_free_model=True, maximum_spend_usd=5.0)

    def test_a_pinned_model_under_a_free_policy_must_be_a_free_variant(self) -> None:
        with pytest.raises(ValidationError, match="must be a free variant"):
            OpenRouterProviderConfig(pinned_free_model="vendor/expensive-model")

    def test_an_unknown_key_is_refused_rather_than_ignored(self, tmp_path: Path) -> None:
        with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
            CodexCliProviderConfig(working_directory=tmp_path, dangerously_bypass=True)
