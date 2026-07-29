"""The hardened Claude Code adapter, against a generated stand-in.

The assertions that matter are about the command line and about what never appears in it.
"The flags are correct" is exactly the claim a code review cannot check for a CLI it does not
run, so `argv` is asserted element by element, and the prompt, the credential and the
repository path are each asserted absent.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from uuid import uuid4

import pytest

from cognitive_os.config.provider_config import ClaudeCodeProviderConfig, CliProcessLimits
from cognitive_os.domain.model_requests import (
    ModelProviderRequest,
    ProviderMessage,
    ProviderMessageRole,
)
from cognitive_os.domain.provider import ProviderStatus
from cognitive_os.providers.advisory_schema import advisory_schema_json
from cognitive_os.providers.claude_code import ClaudeCodeAdvisoryProvider
from cognitive_os.providers.cli_process import BoundedCliRunner
from cognitive_os.providers.errors import (
    ProviderInvalidResponseError,
    ProviderMutationDetectedError,
    ProviderProcessError,
    ProviderTimeoutError,
    ProviderUnsupportedCapabilityError,
)

from ..cli.fake_executable import (
    build_fixture_workspace,
    read_invocation,
    write_fake_executable,
)

ADVISORY_JSON = {
    "summary": "the helper subtracts where it should add",
    "findings": [
        {
            "title": "inverted operator",
            "severity": "high",
            "description": "add returns a - b",
            "evidence": ["nested/module.py:2"],
        }
    ],
}

SUCCESS_ENVELOPE = json.dumps(
    {
        "type": "result",
        "subtype": "success",
        "is_error": False,
        "model": "claude-opus-5",
        "num_turns": 1,
        "usage": {"input_tokens": 900, "output_tokens": 120},
        "result": ADVISORY_JSON,
    }
)

SECRET_PROMPT = "review the fixture; my passphrase is hunter2-correct-horse"


def build(
    tmp_path: Path,
    *,
    behaviour: str = "success",
    payload: str = SUCCESS_ENVELOPE,
    limits: CliProcessLimits | None = None,
    **config_overrides: object,
) -> tuple[ClaudeCodeAdvisoryProvider, Path, Path]:
    workspace = build_fixture_workspace(tmp_path / "fixture")
    executable, record = write_fake_executable(
        tmp_path / "bin", behaviour=behaviour, payload=payload, workspace=workspace
    )
    config = ClaudeCodeProviderConfig(
        enabled=True,
        executable=str(executable),
        working_directory=workspace,
        limits=limits or CliProcessLimits(timeout_seconds=10),
        **config_overrides,  # type: ignore[arg-type]
    )
    runner = BoundedCliRunner(
        provider_id=config.provider_id,
        executable=config.executable,
        working_directory=config.working_directory,
        limits=config.limits,
        environment_allowlist=config.environment_allowlist,
        environment={
            "HOME": os.environ.get("HOME", "/tmp"),
            "PATH": os.environ["PATH"],
            "ANTHROPIC_API_KEY": "sk-ant-" + "a" * 32,  # pragma: allowlist secret
        },
    )
    return ClaudeCodeAdvisoryProvider(config, runner=runner), workspace, record


def a_request() -> ModelProviderRequest:
    return ModelProviderRequest(
        model_call_id=uuid4(),
        task_run_id=uuid4(),
        correlation_id=uuid4(),
        requested_model="claude-code",
        messages=(ProviderMessage(role=ProviderMessageRole.USER, content=SECRET_PROMPT),),
    )


class TestTheCommandLineIsExact:
    def test_the_safety_profile_is_asserted_element_by_element(self, tmp_path: Path) -> None:
        provider, _workspace, _ = build(tmp_path)
        assert provider.safety_arguments() == (
            "--print",
            "--output-format",
            "json",
            "--json-schema",
            advisory_schema_json(),
            "--permission-mode",
            "plan",
            "--allowed-tools",
            "Read,Glob,Grep",
            "--disallowed-tools",
            "Bash,Edit,Write,WebFetch,WebSearch",
            "--mcp-config",
            '{"mcpServers":{}}',
            "--strict-mcp-config",
            "--setting-sources",
            "",
            "--max-turns",
            "6",
            "--safe-mode",
        )

    @pytest.mark.asyncio
    async def test_the_actual_argv_matches_and_carries_no_prompt(self, tmp_path: Path) -> None:
        provider, _, record = build(tmp_path)
        await provider.complete(a_request())
        invocation = read_invocation(record)
        assert invocation["argv"] == list(provider.safety_arguments())
        assert SECRET_PROMPT in str(invocation["stdin"])
        assert not any("hunter2" in argument for argument in invocation["argv"])

    @pytest.mark.asyncio
    async def test_mutating_tools_mcp_and_delegation_are_structurally_absent(
        self, tmp_path: Path
    ) -> None:
        provider, _, record = build(tmp_path)
        await provider.complete(a_request())
        rendered = " ".join(read_invocation(record)["argv"])
        assert "--allowed-tools Read,Glob,Grep" in rendered
        assert "--strict-mcp-config" in rendered
        assert '"mcpServers":{}' in rendered
        for forbidden in ("--dangerously-skip-permissions", "--add-dir", "--agents", "--chrome"):
            assert forbidden not in rendered

    @pytest.mark.asyncio
    async def test_no_credential_reaches_the_child(self, tmp_path: Path) -> None:
        provider, _, record = build(tmp_path)
        await provider.complete(a_request())
        environment = read_invocation(record)["environment"]
        assert "ANTHROPIC_API_KEY" not in environment
        assert not any("sk-ant-" in str(value) for value in environment.values())

    def test_a_lower_turn_limit_can_be_requested_for_a_smoke(self, tmp_path: Path) -> None:
        provider, _, _ = build(tmp_path)
        assert "1" in provider.safety_arguments(maximum_turns=1)


class TestOutputMapping:
    @pytest.mark.asyncio
    async def test_a_schema_valid_result_normalizes(self, tmp_path: Path) -> None:
        provider, _, _ = build(tmp_path)
        response = await provider.complete(a_request())
        assert response.resolved_model == "claude-opus-5"
        assert response.content == "the helper subtracts where it should add"
        assert response.structured_output is not None
        assert response.usage is not None
        assert response.usage.input_tokens == 900

    @pytest.mark.asyncio
    async def test_a_result_delivered_as_a_json_string_is_accepted(self, tmp_path: Path) -> None:
        """Claude versions differ on whether `result` is an object or a JSON string."""
        envelope = json.dumps({"result": json.dumps(ADVISORY_JSON), "model": "claude-opus-5"})
        provider, _, _ = build(tmp_path, payload=envelope)
        response = await provider.complete(a_request())
        assert response.content == "the helper subtracts where it should add"

    @pytest.mark.asyncio
    async def test_malformed_json_fails_closed(self, tmp_path: Path) -> None:
        provider, _, _ = build(tmp_path, behaviour="malformed")
        with pytest.raises(ProviderInvalidResponseError, match="not JSON"):
            await provider.complete(a_request())

    @pytest.mark.asyncio
    async def test_output_that_does_not_match_the_schema_fails_closed(self, tmp_path: Path) -> None:
        """Schema validity is the *minimum*; a shape that misses it is not a partial answer."""
        provider, _, _ = build(tmp_path, payload=json.dumps({"result": {"notes": "no summary"}}))
        with pytest.raises(ProviderInvalidResponseError, match="advisory schema"):
            await provider.complete(a_request())

    @pytest.mark.asyncio
    async def test_an_error_result_is_refused_even_with_a_zero_exit_code(
        self, tmp_path: Path
    ) -> None:
        envelope = json.dumps({"is_error": True, "subtype": "error_during_execution"})
        provider, _, _ = build(tmp_path, payload=envelope)
        with pytest.raises(ProviderInvalidResponseError, match="error result"):
            await provider.complete(a_request())

    @pytest.mark.asyncio
    async def test_cost_and_multi_turn_metadata_become_warnings(self, tmp_path: Path) -> None:
        envelope = json.dumps({"result": ADVISORY_JSON, "total_cost_usd": 0.01, "num_turns": 3})
        provider, _, _ = build(tmp_path, payload=envelope)
        response = await provider.complete(a_request())
        assert any("cost metadata" in warning for warning in response.warnings)
        assert any("more than one turn" in warning for warning in response.warnings)


class TestProcessAndMutationSafety:
    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "behaviour", ["write_file", "modify_dirty", "delete_file", "chmod_file", "symlink_swap"]
    )
    async def test_every_mutation_attempt_fails_closed(
        self, tmp_path: Path, behaviour: str
    ) -> None:
        provider, _, _ = build(tmp_path, behaviour=behaviour)
        with pytest.raises(ProviderMutationDetectedError):
            await provider.complete(a_request())

    @pytest.mark.asyncio
    async def test_an_already_dirty_fixture_still_passes(self, tmp_path: Path) -> None:
        provider, workspace, _ = build(tmp_path)
        (workspace / "dirty.txt").write_text("locally modified again\n", encoding="utf-8")
        response = await provider.complete(a_request())
        assert response.content

    @pytest.mark.asyncio
    async def test_a_timeout_is_typed_and_leaves_no_process(self, tmp_path: Path) -> None:
        provider, _, _ = build(
            tmp_path,
            behaviour="hang",
            limits=CliProcessLimits(timeout_seconds=1, termination_grace_seconds=1),
        )
        with pytest.raises(ProviderTimeoutError):
            await provider.complete(a_request())

    @pytest.mark.asyncio
    async def test_a_non_zero_exit_is_typed_and_its_stderr_is_redacted(
        self, tmp_path: Path
    ) -> None:
        provider, _, _ = build(tmp_path, behaviour="nonzero")
        with pytest.raises(ProviderProcessError) as failure:
            await provider.complete(a_request())
        assert "abcdef0123456789" not in str(failure.value.details)


class TestHealthDisclosesNoIdentity:
    @pytest.mark.asyncio
    async def test_health_reports_a_version_and_no_account(self, tmp_path: Path) -> None:
        provider, _, _ = build(tmp_path, payload="claude 2.1.219 (Claude Code)")
        health = await provider.health_check()
        assert health.status is ProviderStatus.AVAILABLE
        assert health.resolved_model == "2.1.219"
        assert "@" not in health.model_dump_json()

    @pytest.mark.asyncio
    async def test_an_uninstalled_cli_is_unavailable_rather_than_a_crash(
        self, tmp_path: Path
    ) -> None:
        provider, _, _ = build(tmp_path)
        provider._runner.executable = str(tmp_path / "absent")
        health = await provider.health_check()
        assert health.status is ProviderStatus.UNAVAILABLE
        assert "not usable" in health.message

    @pytest.mark.asyncio
    async def test_a_cli_that_rejects_a_required_flag_is_misconfigured_not_degraded(
        self, tmp_path: Path
    ) -> None:
        """Flag drift must stop execution, not silently drop a safety flag."""
        provider, _, _ = build(tmp_path, behaviour="nonzero")
        health = await provider.health_check()
        assert health.status is ProviderStatus.UNAVAILABLE

    @pytest.mark.asyncio
    async def test_health_never_reports_an_email_or_organisation(self, tmp_path: Path) -> None:
        provider, _, _ = build(
            tmp_path, payload="claude 2.1.219 logged in as operator@example.test (Acme Org)"
        )
        rendered = (await provider.health_check()).model_dump_json()
        assert "operator@example.test" not in rendered
        assert "Acme Org" not in rendered


class TestCapabilities:
    @pytest.mark.asyncio
    async def test_streaming_is_refused(self, tmp_path: Path) -> None:
        provider, _, _ = build(tmp_path)
        with pytest.raises(ProviderUnsupportedCapabilityError):
            async for _ in provider.stream(a_request()):
                pass
