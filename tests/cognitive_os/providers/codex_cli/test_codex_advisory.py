"""The Codex advisory adapter: exact safe flags, bounded JSONL, no bypass, no identity.

The flag assertions are the point of the file. `codex exec` has a `--dangerously-bypass-…`
flag, a writable sandbox mode and a `resume` subcommand, and none of them may be reachable
from configuration or from construction. Each is tested as a refusal rather than as an
absence, because "we never pass it" is a property of today's code and "it cannot be passed"
is a property of the boundary.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from uuid import uuid4

import pytest
from pydantic import ValidationError

from cognitive_os.config.provider_config import CliProcessLimits, CodexCliProviderConfig
from cognitive_os.domain.model_requests import (
    ModelProviderRequest,
    ProviderMessage,
    ProviderMessageRole,
)
from cognitive_os.domain.provider import ProviderStatus
from cognitive_os.providers.cli_process import BoundedCliRunner
from cognitive_os.providers.codex_cli import CodexCliAdvisoryProvider
from cognitive_os.providers.codex_cli.advisory import ADVISORY_POLICY
from cognitive_os.providers.errors import (
    ProviderInvalidResponseError,
    ProviderMutationDetectedError,
    ProviderOutputLimitExceededError,
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


def jsonl(*events: dict[str, object]) -> str:
    return "".join(json.dumps(event) + "\n" for event in events)


SUCCESS_JSONL = jsonl(
    {"type": "thread.started", "thread_id": "t-1"},
    {"type": "turn.started"},
    {"type": "item.completed", "item": {"type": "reasoning", "text": "thinking"}},
    {
        "type": "item.completed",
        "item": {"type": "agent_message", "text": json.dumps(ADVISORY_JSON)},
    },
    {"type": "turn.completed", "usage": {"input_tokens": 800, "output_tokens": 90}},
)

SECRET_PROMPT = "review the fixture; my passphrase is hunter2-correct-horse"


def build(
    tmp_path: Path,
    *,
    behaviour: str = "success",
    payload: str = SUCCESS_JSONL,
    limits: CliProcessLimits | None = None,
    **config_overrides: object,
) -> tuple[CodexCliAdvisoryProvider, Path, Path]:
    workspace = build_fixture_workspace(tmp_path / "fixture")
    executable, record = write_fake_executable(
        tmp_path / "bin", behaviour=behaviour, payload=payload, workspace=workspace
    )
    config = CodexCliProviderConfig(
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
            "OPENAI_API_KEY": "sk-" + "b" * 32,  # pragma: allowlist secret
        },
    )
    return CodexCliAdvisoryProvider(config, runner=runner), workspace, record


def a_request() -> ModelProviderRequest:
    return ModelProviderRequest(
        model_call_id=uuid4(),
        task_run_id=uuid4(),
        correlation_id=uuid4(),
        requested_model="codex",
        messages=(ProviderMessage(role=ProviderMessageRole.USER, content=SECRET_PROMPT),),
    )


class TestTheCommandLineIsExact:
    def test_the_safe_exec_profile_is_asserted_element_by_element(self, tmp_path: Path) -> None:
        provider, workspace, _ = build(tmp_path)
        schema = tmp_path / "schema.json"
        assert provider.safety_arguments(schema_path=schema) == (
            "exec",
            "-c",
            'approval_policy="never"',
            "-c",
            "mcp_servers={}",
            "-c",
            "tools.web_search=false",
            "--ephemeral",
            "--ignore-user-config",
            "--json",
            "--sandbox",
            "read-only",
            "--cd",
            str(workspace),
            "--output-schema",
            str(schema),
            "--ignore-rules",
            "--skip-git-repo-check",
            "-",
        )

    def test_approval_policy_travels_by_config_because_exec_has_no_flag(
        self, tmp_path: Path
    ) -> None:
        """codex exec 0.144.6 rejects `--ask-for-approval`; the override is the same policy."""
        provider, _, _ = build(tmp_path)
        arguments = provider.safety_arguments(schema_path=tmp_path / "s.json")
        assert "--ask-for-approval" not in arguments
        assert 'approval_policy="never"' in arguments

    @pytest.mark.asyncio
    async def test_the_prompt_arrives_on_stdin_behind_a_positional_dash(
        self, tmp_path: Path
    ) -> None:
        provider, _, record = build(tmp_path)
        await provider.complete(a_request())
        invocation = read_invocation(record)
        assert invocation["argv"][-1] == "-"
        assert SECRET_PROMPT in str(invocation["stdin"])
        assert not any("hunter2" in argument for argument in invocation["argv"])

    @pytest.mark.asyncio
    async def test_no_bypass_flag_ever_appears(self, tmp_path: Path) -> None:
        provider, _, record = build(tmp_path)
        await provider.complete(a_request())
        rendered = " ".join(read_invocation(record)["argv"])
        for forbidden in (
            "--dangerously-bypass-approvals-and-sandbox",
            "--dangerously-bypass-hook-trust",
            "--yolo",
            "--add-dir",
            "resume",
            "--last",
        ):
            assert forbidden not in rendered

    @pytest.mark.asyncio
    async def test_the_working_directory_is_explicit_and_isolated(self, tmp_path: Path) -> None:
        provider, workspace, record = build(tmp_path)
        await provider.complete(a_request())
        invocation = read_invocation(record)
        assert invocation["cwd"] == str(workspace.resolve())
        assert str(workspace) in invocation["argv"]

    @pytest.mark.asyncio
    async def test_no_credential_reaches_the_child(self, tmp_path: Path) -> None:
        provider, _, record = build(tmp_path)
        await provider.complete(a_request())
        environment = read_invocation(record)["environment"]
        assert "OPENAI_API_KEY" not in environment


class TestConstructionCannotSelectUnsafeFlags:
    @pytest.mark.parametrize("sandbox", ["workspace-write", "danger-full-access"])
    def test_a_writable_sandbox_is_refused_at_construction(
        self, tmp_path: Path, sandbox: str
    ) -> None:
        with pytest.raises(ValidationError):
            CodexCliProviderConfig(working_directory=tmp_path, sandbox_mode=sandbox)

    def test_approval_cannot_be_widened(self, tmp_path: Path) -> None:
        with pytest.raises(ValidationError):
            CodexCliProviderConfig(working_directory=tmp_path, approval_policy="on-request")

    def test_user_configuration_inheritance_cannot_be_re_enabled(self, tmp_path: Path) -> None:
        with pytest.raises(ValidationError):
            CodexCliProviderConfig(working_directory=tmp_path, ignore_user_config=False)

    def test_session_persistence_cannot_be_re_enabled(self, tmp_path: Path) -> None:
        with pytest.raises(ValidationError):
            CodexCliProviderConfig(working_directory=tmp_path, ephemeral=False)


class TestJsonlParsing:
    @pytest.mark.asyncio
    async def test_the_final_agent_message_becomes_the_normalized_response(
        self, tmp_path: Path
    ) -> None:
        provider, _, _ = build(tmp_path)
        response = await provider.complete(a_request())
        assert response.content == "the helper subtracts where it should add"
        assert response.structured_output is not None

    @pytest.mark.asyncio
    async def test_malformed_jsonl_fails_closed(self, tmp_path: Path) -> None:
        provider, _, _ = build(tmp_path, payload='{"type": "item.completed"\n')
        with pytest.raises(ProviderInvalidResponseError, match="malformed or truncated"):
            await provider.complete(a_request())

    @pytest.mark.asyncio
    async def test_a_missing_final_message_fails_closed(self, tmp_path: Path) -> None:
        provider, _, _ = build(
            tmp_path, payload=jsonl({"type": "thread.started"}, {"type": "turn.completed"})
        )
        with pytest.raises(ProviderInvalidResponseError, match="no final agent message"):
            await provider.complete(a_request())

    @pytest.mark.asyncio
    async def test_an_unrecognised_authority_bearing_event_fails_closed(
        self, tmp_path: Path
    ) -> None:
        """A future event this adapter has not reasoned about may carry the real answer."""
        payload = jsonl(
            {"type": "item.completed", "item": {"type": "agent_message", "text": "{}"}},
            {"type": "tool.result", "item": {"type": "agent_message", "text": "?"}},
        )
        provider, _, _ = build(tmp_path, payload=payload)
        with pytest.raises(ProviderInvalidResponseError, match="unrecognised event type"):
            await provider.complete(a_request())

    @pytest.mark.asyncio
    async def test_documented_narration_events_are_ignored_not_refused(
        self, tmp_path: Path
    ) -> None:
        payload = jsonl(
            {"type": "turn.delta", "text": "partial"},
            {"type": "item.delta", "text": "more"},
            {
                "type": "item.completed",
                "item": {"type": "agent_message", "text": json.dumps(ADVISORY_JSON)},
            },
        )
        provider, _, _ = build(tmp_path, payload=payload)
        assert (await provider.complete(a_request())).content

    @pytest.mark.asyncio
    async def test_a_failed_turn_is_refused_even_with_a_zero_exit_code(
        self, tmp_path: Path
    ) -> None:
        provider, _, _ = build(tmp_path, payload=jsonl({"type": "turn.failed"}))
        with pytest.raises(ProviderInvalidResponseError, match="failed turn"):
            await provider.complete(a_request())

    @pytest.mark.asyncio
    async def test_a_final_message_that_misses_the_schema_fails_closed(
        self, tmp_path: Path
    ) -> None:
        payload = jsonl(
            {
                "type": "item.completed",
                "item": {"type": "agent_message", "text": '{"notes": "no summary"}'},
            }
        )
        provider, _, _ = build(tmp_path, payload=payload)
        with pytest.raises(ProviderInvalidResponseError, match="advisory schema"):
            await provider.complete(a_request())

    @pytest.mark.asyncio
    async def test_a_fenced_final_message_is_still_accepted(self, tmp_path: Path) -> None:
        payload = jsonl(
            {
                "type": "item.completed",
                "item": {
                    "type": "agent_message",
                    "text": "```json\n" + json.dumps(ADVISORY_JSON) + "\n```",
                },
            }
        )
        provider, _, _ = build(tmp_path, payload=payload)
        assert (await provider.complete(a_request())).content

    @pytest.mark.asyncio
    async def test_oversized_jsonl_is_capped_rather_than_parsed(self, tmp_path: Path) -> None:
        """Parser memory is bounded by the runner's cap, not by the model's verbosity."""
        provider, _, _ = build(
            tmp_path,
            behaviour="flood_stdout",
            limits=CliProcessLimits(
                timeout_seconds=10, maximum_stdout_bytes=4096, maximum_stderr_bytes=1024
            ),
        )
        with pytest.raises(ProviderOutputLimitExceededError):
            await provider.complete(a_request())


class TestProcessAndMutationSafety:
    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "behaviour", ["write_file", "modify_dirty", "delete_file", "rename_file", "symlink_swap"]
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
        assert (await provider.complete(a_request())).content

    @pytest.mark.asyncio
    async def test_a_timeout_is_typed(self, tmp_path: Path) -> None:
        provider, _, _ = build(
            tmp_path,
            behaviour="hang",
            limits=CliProcessLimits(timeout_seconds=1, termination_grace_seconds=1),
        )
        with pytest.raises(ProviderTimeoutError):
            await provider.complete(a_request())

    @pytest.mark.asyncio
    async def test_the_temporary_schema_file_is_removed_on_every_path(self, tmp_path: Path) -> None:
        provider, _, record = build(tmp_path, behaviour="malformed")
        with pytest.raises(ProviderInvalidResponseError):
            await provider.complete(a_request())
        schema_path = Path(
            next(
                argument
                for index, argument in enumerate(read_invocation(record)["argv"])
                if index > 0 and read_invocation(record)["argv"][index - 1] == "--output-schema"
            )
        )
        assert not schema_path.exists()
        assert not schema_path.parent.exists()


class TestHealthDisclosesNoIdentity:
    @pytest.mark.asyncio
    async def test_health_reports_a_version_and_no_account(self, tmp_path: Path) -> None:
        provider, _, _ = build(tmp_path, payload="codex-cli 0.144.6")
        health = await provider.health_check()
        assert health.status is ProviderStatus.AVAILABLE
        assert health.resolved_model == "0.144.6"

    @pytest.mark.asyncio
    async def test_an_uninstalled_cli_is_unavailable(self, tmp_path: Path) -> None:
        provider, _, _ = build(tmp_path)
        provider._runner.executable = str(tmp_path / "absent")
        health = await provider.health_check()
        assert health.status is ProviderStatus.UNAVAILABLE

    @pytest.mark.asyncio
    async def test_health_never_reports_a_chatgpt_account(self, tmp_path: Path) -> None:
        provider, _, _ = build(
            tmp_path, payload="codex-cli 0.144.6 signed in as operator@example.test"
        )
        rendered = (await provider.health_check()).model_dump_json()
        assert "operator@example.test" not in rendered


class TestCapabilities:
    @pytest.mark.asyncio
    async def test_streaming_is_refused(self, tmp_path: Path) -> None:
        provider, _, _ = build(tmp_path)
        with pytest.raises(ProviderUnsupportedCapabilityError):
            async for _ in provider.stream(a_request()):
                pass


class TestTheAdvisoryPolicyMatchesCodexCapabilities:
    """Codex has no native file-reading tool: it reads by running commands in its sandbox.

    The adapter first reused the Claude Code policy text, which forbids running commands, and
    Codex correctly answered that it could not inspect the file at all. The prompt had made
    the task impossible. The boundary is `--sandbox read-only`, which the CLI enforces; the
    prompt now states the same intent instead of contradicting it.
    """

    def test_it_does_not_forbid_the_only_capability_codex_has(self) -> None:
        assert "run any command" not in ADVISORY_POLICY.lower()
        assert "do not run commands" not in ADVISORY_POLICY.lower()

    def test_it_still_forbids_every_mutation(self) -> None:
        lowered = ADVISORY_POLICY.lower()
        assert "analyse only" in lowered
        assert "do not edit, create or delete any file" in lowered

    def test_it_is_not_the_claude_code_text(self) -> None:
        from cognitive_os.providers.claude_code.advisory import (
            ADVISORY_POLICY as CLAUDE_POLICY,
        )

        assert ADVISORY_POLICY != CLAUDE_POLICY
        assert "do not run commands" in CLAUDE_POLICY.lower()

    def test_the_prompt_leads_with_the_policy(self, tmp_path: Path) -> None:
        provider, _workspace, _record = build(tmp_path)
        assert provider.build_prompt(a_request()).startswith(ADVISORY_POLICY)
