"""Validated provider configuration without credential values.

Every adapter is selected by an explicit `adapter` discriminator rather than by
`ProviderKind`. That distinction is load-bearing from Sprint 21C2 onwards: Claude Code and
Codex are both `cli_agent`, so a `kind`-discriminated union could not tell them apart and
would have to guess — and a configuration loader that guesses which CLI to launch, with
which safety flags, is a configuration loader that can widen authority.

Configuration written before the discriminator existed still loads. `load_provider_configuration`
infers `adapter` from `kind` for the two Sprint 21 adapters and refuses to infer anything
else, so an old file keeps working and a new one has to be explicit. See ADR 0087.
"""

from __future__ import annotations

from enum import StrEnum
from pathlib import Path
from typing import Annotated, Any, Literal
from urllib.parse import urlparse

import yaml
from pydantic import Field, field_validator, model_validator

from cognitive_os.domain.base import ImmutableContractModel
from cognitive_os.domain.common import NonEmptyStr
from cognitive_os.domain.memory import MemorySensitivity
from cognitive_os.domain.provider import ProviderKind
from cognitive_os.domain.provider_output import (
    GOVERNED_SENSITIVITIES,
    ProviderAdapterKind,
    ProviderOutputIntendedUse,
    ProviderOutputRetentionMode,
)

#: The configuration schema version. Bumped when an existing key changes meaning, never
#: when a key is added.
PROVIDER_CONFIGURATION_VERSION = 2

#: Process limits the shared CLI runner will never exceed, whatever configuration asks for.
#: Raising one requires an ADR revision and new resource-exhaustion evidence, because a
#: truncated response is recoverable and an exhausted host is not.
MAXIMUM_CLI_TIMEOUT_SECONDS = 600.0
MAXIMUM_CLI_STDOUT_BYTES = 1024 * 1024
MAXIMUM_CLI_STDERR_BYTES = 256 * 1024

DEFAULT_CLI_TIMEOUT_SECONDS = 120.0
DEFAULT_CLI_STDOUT_BYTES = 256 * 1024
DEFAULT_CLI_STDERR_BYTES = 64 * 1024

#: Environment names a CLI adapter may pass through. Anything else — and in particular
#: anything secret-shaped — is dropped before the child process exists.
DEFAULT_ENVIRONMENT_ALLOWLIST: tuple[str, ...] = (
    "HOME",
    "LANG",
    "LC_ALL",
    "PATH",
    "TERM",
    "TZ",
)

#: Sandbox and permission values that would give an advisory provider more than read
#: access. Refused at load, so an unsafe adapter cannot be constructed at all.
_FORBIDDEN_CODEX_SANDBOXES = frozenset({"workspace-write", "danger-full-access"})
_FORBIDDEN_CLAUDE_PERMISSION_MODES = frozenset(
    {"acceptEdits", "auto", "bypassPermissions", "dontAsk"}
)
_MUTATING_CLAUDE_TOOLS = frozenset(
    {
        "Bash",
        "Edit",
        "MultiEdit",
        "NotebookEdit",
        "Write",
        "WebFetch",
        "WebSearch",
        "Task",
        "Agent",
    }
)
#: Arguments no adapter may ever emit, whatever a configuration file says.
FORBIDDEN_CLI_ARGUMENTS = frozenset(
    {
        "--dangerously-bypass-approvals-and-sandbox",
        "--dangerously-bypass-hook-trust",
        "--dangerously-skip-permissions",
        "--allow-dangerously-skip-permissions",
        "--yolo",
        "--add-dir",
        "--ignore-instructions",
        "resume",
        "--last",
    }
)


class MiniMaxKeyType(StrEnum):
    PAY_AS_YOU_GO = "pay_as_you_go"
    SUBSCRIPTION = "subscription"


class ClaudeOutputFormat(StrEnum):
    JSON = "json"
    STREAM_JSON = "stream-json"


def _validate_https_base_url(value: str, *, require_https: bool) -> str:
    parsed = urlparse(value)
    allowed = {"https"} if require_https else {"https", "http"}
    if parsed.scheme not in allowed or not parsed.netloc:
        raise ValueError(f"base_url must be an absolute {'/'.join(sorted(allowed)).upper()} URL")
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ValueError("base_url must not contain credentials, query, or fragment")
    return value.rstrip("/")


class ProviderRetentionDefaults(ImmutableContractModel):
    """What a provider retains when a caller does not say otherwise.

    All three defaults are the refusing ones. A caller who wants bytes kept has to ask for
    it explicitly and answer the rights question at the same time.
    """

    retention_mode: ProviderOutputRetentionMode = ProviderOutputRetentionMode.NONE
    intended_use: ProviderOutputIntendedUse = ProviderOutputIntendedUse.TRANSIENT_ADVICE
    sensitivity: MemorySensitivity = MemorySensitivity.INTERNAL

    @model_validator(mode="after")
    def defaults_are_conservative(self) -> ProviderRetentionDefaults:
        if self.sensitivity not in GOVERNED_SENSITIVITIES:
            raise ValueError(
                f"sensitivity {self.sensitivity.value!r} is not a label learned intake "
                "recognises; governed output must be public, internal or restricted"
            )
        if self.retention_mode is ProviderOutputRetentionMode.NORMALIZED_CONTENT:
            raise ValueError(
                "normalized content retention cannot be a configured default: it requires "
                "a per-call rights, scan and sensitivity decision"
            )
        return self


class CliProcessLimits(ImmutableContractModel):
    """Bounds the shared runner enforces. Configuration may lower them, never raise them."""

    timeout_seconds: float = Field(default=DEFAULT_CLI_TIMEOUT_SECONDS, gt=0)
    maximum_stdout_bytes: int = Field(default=DEFAULT_CLI_STDOUT_BYTES, gt=0)
    maximum_stderr_bytes: int = Field(default=DEFAULT_CLI_STDERR_BYTES, gt=0)
    termination_grace_seconds: float = Field(default=2.0, gt=0, le=30)

    @model_validator(mode="after")
    def limits_are_within_hard_maxima(self) -> CliProcessLimits:
        if self.timeout_seconds > MAXIMUM_CLI_TIMEOUT_SECONDS:
            raise ValueError(f"timeout_seconds exceeds {MAXIMUM_CLI_TIMEOUT_SECONDS:.0f} seconds")
        if self.maximum_stdout_bytes > MAXIMUM_CLI_STDOUT_BYTES:
            raise ValueError(f"maximum_stdout_bytes exceeds {MAXIMUM_CLI_STDOUT_BYTES} bytes")
        if self.maximum_stderr_bytes > MAXIMUM_CLI_STDERR_BYTES:
            raise ValueError(f"maximum_stderr_bytes exceeds {MAXIMUM_CLI_STDERR_BYTES} bytes")
        return self


class _BaseProviderConfig(ImmutableContractModel):
    provider_id: NonEmptyStr
    enabled: bool = False
    retention: ProviderRetentionDefaults = ProviderRetentionDefaults()
    #: Live execution against a real credential or a real CLI is off unless an operator
    #: turns it on in configuration *and* passes an explicit runtime flag.
    live_smoke_enabled: bool = False


class _BaseCliProviderConfig(_BaseProviderConfig):
    kind: Literal[ProviderKind.CLI_AGENT] = ProviderKind.CLI_AGENT
    executable: NonEmptyStr
    working_directory: Path
    limits: CliProcessLimits = CliProcessLimits()
    environment_allowlist: tuple[NonEmptyStr, ...] = DEFAULT_ENVIRONMENT_ALLOWLIST

    @field_validator("environment_allowlist")
    @classmethod
    def allowlist_excludes_secrets(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        from cognitive_os.providers.redaction import is_secret_like_name

        offending = sorted(name for name in value if is_secret_like_name(name))
        if offending:
            raise ValueError(f"environment allowlist must not carry secret-like names: {offending}")
        return tuple(sorted(set(value)))

    @field_validator("executable")
    @classmethod
    def executable_is_a_name_or_path(cls, value: str) -> str:
        if any(character in value for character in " \t\n;|&$`"):
            raise ValueError("executable must be a bare name or path, never a shell fragment")
        return value

    @property
    def timeout_seconds(self) -> float:
        return self.limits.timeout_seconds


class MiniMaxProviderConfig(_BaseProviderConfig):
    adapter: Literal[ProviderAdapterKind.MINIMAX] = ProviderAdapterKind.MINIMAX
    kind: Literal[ProviderKind.NETWORK_API] = ProviderKind.NETWORK_API
    provider_id: NonEmptyStr = "minimax"
    base_url: str = "https://api.minimax.io/v1"
    model: NonEmptyStr = "MiniMax-M3"
    api_key_environment_variable: NonEmptyStr = "COGOS_MINIMAX_API_KEY"
    key_type: MiniMaxKeyType
    timeout_seconds: float = Field(default=120, gt=0)
    maximum_attempts: int = Field(default=3, ge=1, le=10)
    maximum_context_tokens: int = Field(default=131072, ge=1, le=131072)
    default_max_output_tokens: int = Field(default=8192, ge=1)
    supports_tool_calls: bool = False
    supports_structured_output: bool = False
    enabled: bool = True

    @field_validator("base_url")
    @classmethod
    def validate_base_url(cls, value: str) -> str:
        return _validate_https_base_url(value, require_https=False)

    @model_validator(mode="after")
    def output_fits_context(self) -> MiniMaxProviderConfig:
        if self.default_max_output_tokens > self.maximum_context_tokens:
            raise ValueError("default output tokens cannot exceed the context limit")
        return self


class OpenRouterProviderConfig(_BaseProviderConfig):
    """OpenRouter through the installed OpenAI client. Zero spend unless raised on purpose."""

    adapter: Literal[ProviderAdapterKind.OPENROUTER] = ProviderAdapterKind.OPENROUTER
    kind: Literal[ProviderKind.NETWORK_API] = ProviderKind.NETWORK_API
    provider_id: NonEmptyStr = "openrouter"
    base_url: str = "https://openrouter.ai/api/v1"
    api_key_environment_variable: NonEmptyStr = "OPENROUTER_API_KEY"
    #: The router, not a model. A specific free slug may be pinned, and is validated
    #: against the live catalog before use, because a free model can disappear.
    default_route: NonEmptyStr = "openrouter/free"
    pinned_free_model: NonEmptyStr | None = None
    require_free_model: bool = True
    maximum_spend_usd: float = Field(default=0.0, ge=0)
    timeout_seconds: float = Field(default=120, gt=0)
    maximum_attempts: int = Field(default=1, ge=1, le=5)
    maximum_output_tokens: int = Field(default=1024, ge=1, le=32768)
    maximum_context_tokens: int = Field(default=32768, ge=1, le=131072)
    catalog_cache_seconds: float = Field(default=300, ge=0, le=3600)
    #: Provider-side data policy, defaulted for this project's material rather than for a
    #: hypothetical one. ADR 0088 classifies open-development data as `public`: task text,
    #: public source and generated diffs. Demanding zero data retention for material that is
    #: already public bought no confidentiality and cost every free route, because free
    #: OpenRouter endpoints do not offer ZDR — so the strict default made the honest
    #: configuration the one an operator had to override.
    #:
    #: The relaxation is about subject matter only. Credentials, keys and authorization
    #: values are excluded from provider requests by the prompt boundary, not by these
    #: flags, and that boundary is unchanged. An operator handling non-public material sets
    #: these back to the strict values.
    require_zero_data_retention: bool = False
    allow_data_collection: bool = True
    application_referer: NonEmptyStr | None = None
    application_title: NonEmptyStr | None = None

    @field_validator("base_url")
    @classmethod
    def validate_base_url(cls, value: str) -> str:
        return _validate_https_base_url(value, require_https=True)

    @field_validator("api_key_environment_variable")
    @classmethod
    def key_comes_from_openrouter_only(cls, value: str) -> str:
        if value != "OPENROUTER_API_KEY":
            raise ValueError("the OpenRouter key must come from OPENROUTER_API_KEY")
        return value

    @model_validator(mode="after")
    def free_routing_is_consistent(self) -> OpenRouterProviderConfig:
        if self.require_free_model and self.maximum_spend_usd > 0:
            raise ValueError(
                "a free-only configuration cannot also authorise spend; set "
                "require_free_model to false to permit paid routing"
            )
        if (
            self.pinned_free_model is not None
            and self.require_free_model
            and ":free" not in self.pinned_free_model
            and not self.pinned_free_model.endswith("/free")
        ):
            raise ValueError(
                "a pinned model under a free-only policy must be a free variant; "
                "availability is still validated against the runtime catalog"
            )
        if self.maximum_output_tokens > self.maximum_context_tokens:
            raise ValueError("output tokens cannot exceed the context limit")
        return self


class ClaudeCodeProviderConfig(_BaseCliProviderConfig):
    """Claude Code as a bounded, read-only, non-interactive advisory teacher."""

    adapter: Literal[ProviderAdapterKind.CLAUDE_CODE] = ProviderAdapterKind.CLAUDE_CODE
    provider_id: NonEmptyStr = "claude-code"
    executable: NonEmptyStr = "claude"
    output_format: ClaudeOutputFormat = ClaudeOutputFormat.JSON
    permission_mode: NonEmptyStr = "plan"
    safe_mode: bool = True
    allowed_tools: tuple[NonEmptyStr, ...] = ("Read", "Glob", "Grep")
    disallowed_tools: tuple[NonEmptyStr, ...] = ("Bash", "Edit", "Write", "WebFetch", "WebSearch")
    #: A cost and latency bound, not a safety boundary — the sandbox flags, the timeout
    #: and the output caps are what contain the run. Three was too low for a read-then-
    #: answer task: the Sprint 21C2 live smoke exhausted it on a two-function file and
    #: exited non-zero, which reads as a failure rather than as the budget it is.
    maximum_turns: int = Field(default=6, ge=1, le=20)
    maximum_budget_usd: float | None = Field(default=None, gt=0)
    model: NonEmptyStr | None = None

    @model_validator(mode="after")
    def tools_and_mode_are_read_only(self) -> ClaudeCodeProviderConfig:
        if self.permission_mode in _FORBIDDEN_CLAUDE_PERMISSION_MODES:
            raise ValueError(
                f"permission mode {self.permission_mode!r} permits mutation; advisory "
                "execution requires 'plan'"
            )
        mutating = sorted(set(self.allowed_tools) & _MUTATING_CLAUDE_TOOLS)
        if mutating:
            raise ValueError(f"advisory configuration must not allow mutating tools: {mutating}")
        overlap = sorted(set(self.allowed_tools) & set(self.disallowed_tools))
        if overlap:
            raise ValueError(f"tools cannot be both allowed and disallowed: {overlap}")
        if not self.allowed_tools:
            raise ValueError("an advisory adapter needs at least one read-only tool")
        return self


class CodexCliProviderConfig(_BaseCliProviderConfig):
    """Codex `exec` as an ephemeral, read-only, never-approving advisory teacher."""

    adapter: Literal[ProviderAdapterKind.CODEX_CLI] = ProviderAdapterKind.CODEX_CLI
    provider_id: NonEmptyStr = "codex-cli"
    executable: NonEmptyStr = "codex"
    sandbox_mode: NonEmptyStr = "read-only"
    approval_policy: NonEmptyStr = "never"
    ephemeral: Literal[True] = True
    ignore_user_config: Literal[True] = True
    ignore_rules: bool = True
    skip_git_repo_check: bool = True
    model: NonEmptyStr | None = None

    @model_validator(mode="after")
    def sandbox_and_approval_are_safe(self) -> CodexCliProviderConfig:
        if self.sandbox_mode in _FORBIDDEN_CODEX_SANDBOXES:
            raise ValueError(
                f"sandbox {self.sandbox_mode!r} permits writes; advisory execution requires "
                "'read-only'"
            )
        if self.sandbox_mode != "read-only":
            raise ValueError("Codex advisory execution supports only the read-only sandbox")
        if self.approval_policy != "never":
            raise ValueError(
                "an unattended advisory call cannot answer an approval prompt; the policy "
                "must be 'never'"
            )
        return self


ProviderAdapterConfig = Annotated[
    MiniMaxProviderConfig
    | OpenRouterProviderConfig
    | ClaudeCodeProviderConfig
    | CodexCliProviderConfig,
    Field(discriminator="adapter"),
]

#: How a pre-discriminator configuration file is read. Only the two Sprint 21 adapters are
#: inferable; a `cli_agent` entry written after Codex existed has to say which CLI it means.
_LEGACY_KIND_TO_ADAPTER = {
    ProviderKind.NETWORK_API.value: ProviderAdapterKind.MINIMAX.value,
    ProviderKind.CLI_AGENT.value: ProviderAdapterKind.CLAUDE_CODE.value,
}

_CLI_ADAPTERS = frozenset(
    {ProviderAdapterKind.CLAUDE_CODE.value, ProviderAdapterKind.CODEX_CLI.value}
)


class ProviderConfiguration(ImmutableContractModel):
    configuration_version: int = PROVIDER_CONFIGURATION_VERSION
    default_provider_id: NonEmptyStr
    providers: dict[str, ProviderAdapterConfig]

    @model_validator(mode="after")
    def validate_provider_ids(self) -> ProviderConfiguration:
        if not self.providers:
            raise ValueError("at least one provider configuration is required")
        for key, provider in self.providers.items():
            if key != provider.provider_id:
                raise ValueError("provider mapping key must equal provider_id")
        if self.default_provider_id not in self.providers:
            raise ValueError("default provider is not configured")
        if self.configuration_version > PROVIDER_CONFIGURATION_VERSION:
            raise ValueError(
                f"configuration version {self.configuration_version} is newer than this "
                f"build understands ({PROVIDER_CONFIGURATION_VERSION})"
            )
        return self


def _migrate_provider_document(document: dict[str, Any]) -> dict[str, Any]:
    """Add the `adapter` discriminator to a pre-Sprint-21C2 document.

    Inference is deliberately narrow. `cli_agent` meant Claude Code when it was written and
    means nothing definite now, so exactly one legacy mapping is honoured and everything
    else must be explicit.
    """
    providers = document.get("providers")
    if not isinstance(providers, dict):
        return document
    migrated: dict[str, Any] = {}
    for key, value in providers.items():
        if not isinstance(value, dict):
            migrated[key] = value
            continue
        entry = {"provider_id": key, **value}
        if "adapter" not in entry:
            kind = entry.get("kind")
            inferred = _LEGACY_KIND_TO_ADAPTER.get(str(kind))
            if inferred is None:
                raise ValueError(
                    f"provider {key!r} does not name an adapter and its kind {kind!r} "
                    "cannot be inferred; add an explicit 'adapter' key"
                )
            entry["adapter"] = inferred
        # A CLI adapter's timeout moved into `limits` when stdout and stderr caps joined
        # it. Folding rather than rejecting: the old key meant exactly the new one, and a
        # file that still says `timeout_seconds: 300` should keep working.
        if entry["adapter"] in _CLI_ADAPTERS and "timeout_seconds" in entry:
            legacy_timeout = entry.pop("timeout_seconds")
            limits = dict(entry.get("limits") or {})
            limits.setdefault("timeout_seconds", legacy_timeout)
            entry["limits"] = limits
        migrated[key] = entry
    return {**document, "providers": migrated}


def load_provider_configuration(path: Path) -> ProviderConfiguration:
    with path.open(encoding="utf-8") as stream:
        document = yaml.safe_load(stream)
    if not isinstance(document, dict):
        raise ValueError("provider configuration must be a YAML mapping")
    return ProviderConfiguration.model_validate(_migrate_provider_document(document))
