"""Codex `exec` as an ephemeral, read-only, never-approving advisory teacher.

The argument profile is built from validated configuration and nothing else. One verified
deviation from the Sprint 21C2 backlog's expectation, recorded in ADR 0087 and the
compatibility manifest: `codex exec` 0.144.6 has no `--ask-for-approval` flag — it is a
top-level flag that `exec` rejects — so the adapter emits `-c approval_policy="never"`, the
same policy through the documented configuration path. That is not a weaker setting: `exec`
is non-interactive by construction and the sandbox stays `read-only` regardless.

Every emitted flag is parse-probed against the installed binary before execution. A required
flag that was renamed upstream makes the adapter unhealthy; it is never silently dropped.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from pathlib import Path

from cognitive_os.config.provider_config import CodexCliProviderConfig
from cognitive_os.domain.common import utc_now
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
from cognitive_os.providers.advisory_schema import advisory_schema_json
from cognitive_os.providers.claude_code.advisory import coarse_version
from cognitive_os.providers.cli_process import BoundedCliRunner
from cognitive_os.providers.errors import ProviderUnsupportedCapabilityError

from .mapping import parse_advisory_result

#: Codex's own advisory policy, deliberately not the Claude Code text.
#:
#: Claude Code reads files with native Read/Glob/Grep tools, so telling it "do not run
#: commands" costs it nothing. Codex has no such tool: it reads files *by* running commands
#: inside its read-only sandbox. Reusing the Claude wording forbade the only capability
#: Codex has, and it correctly answered that it could not inspect the file at all — a
#: prompt that made the task impossible, discovered by the Sprint 21C2 live smoke.
#:
#: The boundary is `--sandbox read-only`, which the CLI enforces. This text states the same
#: intent instead of contradicting it, because a model instruction is not a boundary and a
#: model instruction that fights the boundary is worse than none.
ADVISORY_POLICY = """Analyse only. Do not edit, create or delete any file, and make no
change of any kind. Read-only inspection of the given directory is expected.
Return the requested structured advisory result and nothing else.
"""

#: Configuration overrides emitted with every call. Each is a policy the flag surface either
#: cannot express (`approval_policy`) or expresses less completely (empty MCP, no tools).
SAFE_CONFIG_OVERRIDES: tuple[str, ...] = (
    'approval_policy="never"',
    "mcp_servers={}",
    "tools.web_search=false",
)


class CodexCliAdvisoryProvider:
    def __init__(
        self,
        config: CodexCliProviderConfig,
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
        )
        self._identity = ProviderIdentity(
            provider_id=config.provider_id,
            display_name="Codex CLI advisory provider",
            provider_kind=ProviderKind.CLI_AGENT,
            adapter_version="1",
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

    def safety_arguments(self, *, schema_path: Path) -> tuple[str, ...]:
        """The exact `codex exec` command line. No prompt, no credential, no bypass flag.

        `-` as the positional argument is what makes Codex read the prompt from stdin; the
        prompt itself never appears here. `test_codex_argv` asserts the list element by
        element.
        """
        arguments: list[str] = ["exec"]
        for override in SAFE_CONFIG_OVERRIDES:
            arguments.extend(("-c", override))
        arguments.extend(
            (
                "--ephemeral",
                "--ignore-user-config",
                "--json",
                "--sandbox",
                self.config.sandbox_mode,
                "--cd",
                str(self.config.working_directory),
                "--output-schema",
                str(schema_path),
            )
        )
        if self.config.ignore_rules:
            arguments.append("--ignore-rules")
        if self.config.skip_git_repo_check:
            arguments.append("--skip-git-repo-check")
        if self.config.model is not None:
            arguments.extend(("--model", self.config.model))
        # Prompt from stdin. Positional `-` rather than the prompt itself: in `argv` the
        # prompt is readable by every process on the host.
        arguments.append("-")
        return tuple(arguments)

    def build_prompt(self, request: ModelProviderRequest) -> str:
        parts = [ADVISORY_POLICY]
        if request.system_instructions:
            parts.append(request.system_instructions)
        parts.extend(message.content for message in request.messages)
        return "\n\n".join(parts)

    # ---------------------------------------------------------------------- execute

    async def complete(self, request: ModelProviderRequest) -> ModelProviderResponse:
        async with self._runner.temporary_directory() as scratch:
            schema_path = scratch / "advisory-schema.json"
            schema_path.write_text(advisory_schema_json(), encoding="utf-8")
            outcome, _snapshot = await self._runner.run(
                arguments=self.safety_arguments(schema_path=schema_path),
                stdin_payload=self.build_prompt(request),
            )
        advisory = parse_advisory_result(outcome.stdout, provider_id=self.provider_id)
        return ModelProviderResponse(
            model_call_id=request.model_call_id,
            provider_id=self.provider_id,
            requested_model=request.requested_model,
            resolved_model=self.config.model or "codex",
            content=advisory.summary,
            structured_output=advisory.model_dump(mode="json"),
            finish_reason=ModelFinishReason.COMPLETED,
            latency_ms=outcome.duration_ms,
            warnings=("stdout was truncated at the configured cap",)
            if outcome.stdout_truncated
            else (),
        )

    async def stream(self, request: ModelProviderRequest) -> AsyncIterator[ProviderStreamEvent]:
        del request
        raise ProviderUnsupportedCapabilityError(
            provider_id=self.provider_id,
            message="Codex advisory streaming is unsupported",
        )
        yield  # pragma: no cover - unreachable, present so this is an async generator

    # ----------------------------------------------------------------------- health

    async def health_check(self) -> ProviderHealth:
        """Installed, version, and whether the safety profile parses. No account identity."""
        installed, version_excerpt = await self._runner.probe(("--version",))
        if not installed:
            return ProviderHealth(
                provider_id=self.provider_id,
                status=ProviderStatus.UNAVAILABLE,
                checked_at=utc_now(),
                configured_model="codex",
                message=f"Codex is not usable: {version_excerpt}",
            )
        async with self._runner.temporary_directory() as scratch:
            schema_path = scratch / "advisory-schema.json"
            schema_path.write_text(advisory_schema_json(), encoding="utf-8")
            supported = await self._runner.supports_arguments(
                self.safety_arguments(schema_path=schema_path)[:-1]
            )
        if not supported:
            return ProviderHealth(
                provider_id=self.provider_id,
                status=ProviderStatus.MISCONFIGURED,
                checked_at=utc_now(),
                configured_model="codex",
                message=(
                    "the installed Codex version does not accept every required safety "
                    "flag; update the compatibility manifest before executing"
                ),
            )
        return ProviderHealth(
            provider_id=self.provider_id,
            status=ProviderStatus.AVAILABLE,
            checked_at=utc_now(),
            configured_model="codex",
            resolved_model=coarse_version(version_excerpt),
            message=f"Codex {coarse_version(version_excerpt)} accepts the safety profile",
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
