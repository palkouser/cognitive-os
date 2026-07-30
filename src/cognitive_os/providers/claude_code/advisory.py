"""Claude Code as a bounded, read-only, non-interactive advisory teacher.

Every Sprint 21C1 gap this adapter had is closed structurally rather than by convention:

* the prompt goes to stdin through the shared runner, never into `argv`;
* mutation is detected by content-and-mode snapshot, not by `git status` equality;
* stdout and stderr have hard caps, and exceeding one kills the process tree;
* `plan` permission mode, safe mode, an explicit read-only tool allowlist, an explicit
  mutating-tool denylist, a strictly empty MCP configuration and no session persistence;
* health reports installed, logged in, version and a coarse authentication method — and
  discards the account, organisation, email and subscription fields entirely.

The safety flags are built from validated configuration and every one of them is
parse-probed against the installed binary before execution, because a flag that was renamed
upstream must make the adapter unhealthy rather than silently vanish from the command line.
See ADR 0087.
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator

from cognitive_os.config.provider_config import ClaudeCodeProviderConfig
from cognitive_os.domain.common import JsonValue, NonEmptyStr, TokenUsage, utc_now
from cognitive_os.domain.model_requests import (
    ModelProviderRequest,
    ModelProviderResponse,
)
from cognitive_os.domain.provider import (
    ModelCapabilities,
    ModelFinishReason,
    ProviderHealth,
    ProviderIdentity,
    ProviderKind,
    ProviderStatus,
    ProviderStreamEvent,
)
from cognitive_os.providers.advisory_schema import (
    AdvisoryResult,
    advisory_schema_json,
    requested_schema_json,
)
from cognitive_os.providers.cli_process import BoundedCliRunner
from cognitive_os.providers.errors import (
    ProviderInvalidResponseError,
    ProviderUnsupportedCapabilityError,
)

#: Prepended to every advisory prompt. Not a security control — a model instruction is not a
#: boundary — but it makes the intent explicit to the model whose sandbox already refuses.
ADVISORY_POLICY = """Analyse only. Do not edit, create or delete any file.
Do not run commands. Return the requested structured advisory result and nothing else.
"""

#: An MCP configuration with no servers. Passed with `--strict-mcp-config`, so a user-level
#: or project-level MCP file cannot add a server this adapter did not ask for.
EMPTY_MCP_CONFIG = '{"mcpServers":{}}'


#: The only envelope keys a failure may report. Metadata about the run, never `result` and
#: never any message body: a failing advisory run can still hold partial model prose, and a
#: diagnostic that copied it would retain exactly the content this boundary refuses to keep.
FAILURE_DIAGNOSTIC_KEYS: tuple[str, ...] = (
    "subtype",
    "stop_reason",
    "num_turns",
    "duration_api_ms",
    "is_error",
)


def failure_details(stdout: str) -> dict[str, JsonValue]:
    """Explain a non-zero exit from the envelope Claude Code writes to stdout.

    Claude Code reports why it stopped on *stdout*, not stderr, so without this the operator
    saw only "non-zero status" — which is what the Sprint 21C2 live smoke hit when the run
    exhausted its turn budget. Unparsable output yields no keys rather than a guess.
    """
    try:
        document = json.loads(stdout)
    except (json.JSONDecodeError, ValueError):
        return {}
    if not isinstance(document, dict):
        return {}
    details: dict[str, JsonValue] = {
        f"envelope_{key}": document[key]
        for key in FAILURE_DIAGNOSTIC_KEYS
        if isinstance(document.get(key), str | int | float | bool)
    }
    if document.get("stop_reason") == "tool_use" or document.get("subtype") == "error_max_turns":
        details["likely_cause"] = "the run reached its configured maximum turns"
    return details


class ClaudeCodeAdvisoryProvider:
    def __init__(
        self,
        config: ClaudeCodeProviderConfig,
        *,
        runner: BoundedCliRunner | None = None,
    ) -> None:
        self.config = config
        self._runner = runner or BoundedCliRunner(
            provider_id=config.provider_id,
            executable=config.executable,
            working_directory=config.working_directory,
            limits=config.limits,
            environment_allowlist=config.environment_allowlist,
            diagnose_failure=failure_details,
        )
        self._identity = ProviderIdentity(
            provider_id=config.provider_id,
            display_name="Claude Code advisory provider",
            provider_kind=ProviderKind.CLI_AGENT,
            adapter_version="2",
        )

    @property
    def provider_id(self) -> str:
        return self.config.provider_id

    @property
    def identity(self) -> ProviderIdentity:
        return self._identity

    @property
    def enabled(self) -> bool:
        return self.config.enabled

    # -------------------------------------------------------------------- arguments

    def safety_arguments(
        self, *, maximum_turns: int | None = None, schema_json: str | None = None
    ) -> tuple[str, ...]:
        """The exact command line, built from validated configuration only.

        No prompt, no path outside the fixture, no credential. `test_claude_argv` asserts
        this list element by element, because "the flags are correct" is the claim that a
        code review cannot check for a CLI it does not run.

        `schema_json` is the shape the *caller* asked for. It used to be hardcoded to the
        advisory schema, so a request carrying its own `response_schema` was answered in a
        shape nobody had asked for — the reply validated against the wrong contract and the
        caller saw a malformed answer rather than a wrong schema. Defaulting to the advisory
        schema keeps every C2 caller unchanged.
        """
        arguments: list[str] = [
            "--print",
            "--output-format",
            self.config.output_format.value,
            "--json-schema",
            schema_json or advisory_schema_json(),
            "--permission-mode",
            self.config.permission_mode,
            "--allowed-tools",
            ",".join(self.config.allowed_tools),
            "--disallowed-tools",
            ",".join(self.config.disallowed_tools),
            # Strictly empty MCP: no server, and no inherited server either.
            "--mcp-config",
            EMPTY_MCP_CONFIG,
            "--strict-mcp-config",
            # No user, project or local settings: CLAUDE.md, hooks, plugins and custom
            # agents are all customization this boundary does not grant.
            "--setting-sources",
            "",
            "--max-turns",
            str(maximum_turns if maximum_turns is not None else self.config.maximum_turns),
        ]
        if self.config.safe_mode:
            arguments.append("--safe-mode")
        if self.config.model is not None:
            arguments.extend(("--model", self.config.model))
        if self.config.maximum_budget_usd is not None:
            arguments.extend(("--max-budget-usd", str(self.config.maximum_budget_usd)))
        return tuple(arguments)

    def build_prompt(self, request: ModelProviderRequest) -> str:
        parts = [ADVISORY_POLICY]
        if request.system_instructions:
            parts.append(request.system_instructions)
        parts.extend(message.content for message in request.messages)
        return "\n\n".join(parts)

    # ---------------------------------------------------------------------- execute

    async def complete(self, request: ModelProviderRequest) -> ModelProviderResponse:
        outcome, _snapshot = await self._runner.run(
            arguments=self.safety_arguments(
                schema_json=requested_schema_json(request.response_schema)
            ),
            stdin_payload=self.build_prompt(request),
        )
        return map_advisory_response(
            outcome.stdout,
            request,
            provider_id=self.provider_id,
            duration_ms=outcome.duration_ms,
        )

    async def stream(self, request: ModelProviderRequest) -> AsyncIterator[ProviderStreamEvent]:
        del request
        raise ProviderUnsupportedCapabilityError(
            provider_id=self.provider_id,
            message="Claude Code advisory streaming is unsupported",
        )
        yield  # pragma: no cover - unreachable, present so this is an async generator

    # ----------------------------------------------------------------------- health

    async def health_check(self) -> ProviderHealth:
        """Installed, version, coarse authentication method. No account identity, ever."""
        installed, version_excerpt = await self._runner.probe(("--version",))
        if not installed:
            return ProviderHealth(
                provider_id=self.provider_id,
                status=ProviderStatus.UNAVAILABLE,
                checked_at=utc_now(),
                configured_model="claude-code",
                message=f"Claude Code is not usable: {version_excerpt}",
            )
        supported = await self._runner.supports_arguments(self.safety_arguments(maximum_turns=1))
        if not supported:
            return ProviderHealth(
                provider_id=self.provider_id,
                status=ProviderStatus.MISCONFIGURED,
                checked_at=utc_now(),
                configured_model="claude-code",
                message=(
                    "the installed Claude Code version does not accept every required "
                    "safety flag; update the compatibility manifest before executing"
                ),
            )
        return ProviderHealth(
            provider_id=self.provider_id,
            status=ProviderStatus.AVAILABLE,
            checked_at=utc_now(),
            configured_model="claude-code",
            resolved_model=coarse_version(version_excerpt),
            message=f"Claude Code {coarse_version(version_excerpt)} accepts the safety profile",
        )

    async def get_model_capabilities(self, model_id: str) -> ModelCapabilities:
        return ModelCapabilities(
            model_id=model_id,
            provider_id=self.provider_id,
            supports_streaming=False,
            supports_tool_calls=False,
            supports_parallel_tool_calls=False,
            supports_structured_output=True,
            supports_system_messages=True,
            supports_seed=False,
        )


def coarse_version(excerpt: str) -> str:
    """A version number and nothing else.

    `claude --version` prints a version plus a product string today and could print more
    tomorrow. Extracting the number rather than storing the line means a future addition —
    an account hint, a workspace name — cannot arrive in health output by default.
    """
    import re

    match = re.search(r"\d+\.\d+\.\d+", excerpt)
    return match.group(0) if match else "unknown"


def map_advisory_response(
    raw_stdout: str,
    request: ModelProviderRequest,
    *,
    provider_id: str,
    duration_ms: float,
) -> ModelProviderResponse:
    """Normalize Claude Code's structured print output.

    Claude wraps the result in an envelope whose `result` field holds the schema-validated
    payload — as an object or as a JSON string, depending on version — so both are accepted.
    Anything else fails closed rather than being coerced.
    """
    try:
        document = json.loads(raw_stdout)
    except json.JSONDecodeError as error:
        raise ProviderInvalidResponseError(
            provider_id=provider_id,
            message="Claude Code returned output that is not JSON",
        ) from error
    if not isinstance(document, dict):
        raise ProviderInvalidResponseError(
            provider_id=provider_id,
            message="Claude Code returned a JSON value that is not an object",
        )
    if document.get("is_error") is True or document.get("subtype") == "error":
        raise ProviderInvalidResponseError(
            provider_id=provider_id,
            message="Claude Code reported an error result",
        )

    structured: object = document.get("structured_output", document.get("result", document))
    if isinstance(structured, str):
        try:
            structured = json.loads(structured)
        except json.JSONDecodeError as error:
            raise ProviderInvalidResponseError(
                provider_id=provider_id,
                message="Claude Code returned a result string that is not JSON",
            ) from error
    # A caller that supplied its own `response_schema` asked for its own contract, and the
    # CLI was told to produce it. Re-validating that reply against `AdvisoryResult` would
    # reject a correct answer for being the wrong shape — the shape the caller chose — so
    # the payload is handed back unread and the caller validates what it asked for.
    advisory: AdvisoryResult | None = None
    if request.response_schema:
        content = json.dumps(structured, sort_keys=True, separators=(",", ":"))
        structured_output = structured if isinstance(structured, dict | list) else None
    else:
        try:
            advisory = AdvisoryResult.model_validate(structured)
        except ValueError as error:
            raise ProviderInvalidResponseError(
                provider_id=provider_id,
                message="Claude Code output does not match the advisory schema",
            ) from error
        content = advisory.summary
        structured_output = advisory.model_dump(mode="json")

    model = document.get("model")
    resolved: NonEmptyStr = model if isinstance(model, str) and model else "claude-code"
    warnings: list[str] = []
    if "total_cost_usd" in document:
        warnings.append("cost metadata was reported by Claude Code")
    if document.get("num_turns", 1) and int(document.get("num_turns", 1) or 1) > 1:
        warnings.append("the advisory call used more than one turn")
    return ModelProviderResponse(
        model_call_id=request.model_call_id,
        provider_id=provider_id,
        requested_model=request.requested_model,
        resolved_model=resolved,
        content=content,
        structured_output=structured_output,
        finish_reason=ModelFinishReason.COMPLETED,
        usage=_map_usage(document.get("usage")),
        latency_ms=duration_ms,
        warnings=tuple(warnings),
    )


def _map_usage(value: object) -> TokenUsage | None:
    if not isinstance(value, dict):
        return None
    input_tokens = value.get("input_tokens")
    output_tokens = value.get("output_tokens")
    return TokenUsage(
        input_tokens=input_tokens if isinstance(input_tokens, int) else None,
        output_tokens=output_tokens if isinstance(output_tokens, int) else None,
    )
