"""The operator CLI: every command, and the refusals that keep the live one hard to reach.

The refusal tests carry the weight here. `live-smoke` is the only command in the repository
that can spend money and start a real agent, and the property being protected is that no
single mistake — a stray flag, a copied command line, a config left enabled — is enough on
its own.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from shutil import copytree
from typing import Any

import pytest

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
)
from scripts import provider as cli

ADVISORY_ROOT = Path("tests/fixtures/providers/advisory")
EXAMPLE_CONFIG = Path("config/providers.example.yaml")

CORRECT_ANSWER = {
    "summary": "one defect found",
    "findings": [
        {
            "title": "arithmetic_mean divides by zero",
            "severity": "high",
            "description": (
                "statistics_helper.py: arithmetic_mean divides by len(values) with no "
                "guard, so an empty sequence raises ZeroDivisionError."
            ),
            "evidence": [],
        }
    ],
}


def run(capsys: pytest.CaptureFixture[str], *argv: str) -> tuple[int, dict[str, Any]]:
    """Run one command and return its status with the single JSON line it printed."""
    status = cli.main(list(argv))
    captured = capsys.readouterr().out.strip()
    return status, json.loads(captured) if captured else {}


class TestListingConfiguration:
    def test_it_names_every_configured_provider(self, capsys: pytest.CaptureFixture[str]) -> None:
        status, payload = run(capsys, "list", "--config", str(EXAMPLE_CONFIG))
        assert status == 0
        adapters = {entry["adapter"] for entry in payload["providers"]}
        assert adapters == {"minimax", "openrouter", "claude_code", "codex_cli"}

    def test_it_prints_credential_variable_names_and_never_values(
        self, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-v1-not-a-real-key")
        _, payload = run(capsys, "list", "--config", str(EXAMPLE_CONFIG))
        rendered = json.dumps(payload)
        assert "OPENROUTER_API_KEY" in rendered
        assert "sk-or-v1-not-a-real-key" not in rendered


class TestHealthIsOfflineByDefault:
    def test_a_network_provider_is_not_probed_without_the_flag(
        self, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """No credential is read and no socket is opened unless the operator asks."""

        def refuse(_config: Any) -> Any:
            raise AssertionError("offline health must not construct a network adapter")

        monkeypatch.setattr("cognitive_os.providers.factory.build_provider", refuse)
        status, payload = run(
            capsys, "health", "--config", str(EXAMPLE_CONFIG), "--provider", "minimax"
        )
        assert status == 0
        report = payload["providers"][0]
        assert report["status"] == "unavailable"
        assert "--allow-network" in report["message"]

    def test_a_disabled_provider_reports_disabled_rather_than_failing(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        status, payload = run(
            capsys,
            "health",
            "--config",
            str(EXAMPLE_CONFIG),
            "--provider",
            "openrouter",
        )
        assert status == 0
        assert payload["providers"][0]["message"] == "provider is disabled in configuration"

    def test_require_available_turns_an_offline_answer_into_a_failure(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        status, _ = run(
            capsys,
            "health",
            "--config",
            str(EXAMPLE_CONFIG),
            "--provider",
            "minimax",
            "--require-available",
        )
        assert status == 1

    def test_an_unknown_provider_is_not_found(self, capsys: pytest.CaptureFixture[str]) -> None:
        status, payload = run(
            capsys, "health", "--config", str(EXAMPLE_CONFIG), "--provider", "nope"
        )
        assert status == cli.NOT_FOUND
        assert payload == {"provider_id": "nope", "found": False}

    def test_with_the_flag_the_adapter_is_probed(
        self, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(
            "cognitive_os.providers.factory.build_provider",
            lambda config: _StubProvider(config.provider_id, ProviderStatus.AVAILABLE),
        )
        status, payload = run(
            capsys,
            "health",
            "--config",
            str(EXAMPLE_CONFIG),
            "--provider",
            "minimax",
            "--allow-network",
            "--require-available",
        )
        assert status == 0
        assert payload["providers"][0]["status"] == "available"


class TestCredentialFreeChecks:
    def test_replay_matches_the_reviewed_fixture(self, capsys: pytest.CaptureFixture[str]) -> None:
        status, payload = run(capsys, "replay")
        assert status == 0
        assert payload["matched_reviewed_fixture"] is True

    def test_fixture_verifies_the_fixture_and_that_the_verifier_discriminates(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        status, payload = run(capsys, "fixture")
        assert status == 0
        assert payload["verifier_discriminates"] is True
        assert payload["is_real_governed_outcome"] is False
        assert payload["content_hash"]

    def test_a_missing_fixture_root_is_not_found(
        self, capsys: pytest.CaptureFixture[str], tmp_path: Path
    ) -> None:
        status, payload = run(capsys, "fixture", "--fixture-root", str(tmp_path))
        assert status == cli.NOT_FOUND
        assert payload["found"] is False

    def test_governance_verify_without_a_database_is_not_found(
        self, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("COGOS_DATABASE_URL", raising=False)
        status, payload = run(capsys, "governance-verify")
        assert status == cli.NOT_FOUND
        assert payload["found"] is False

    def test_governance_verify_imports_nothing_postgres_when_unconfigured(
        self, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The credential-free lanes install no PostgreSQL extra.

        Importing the health module before checking the URL turned "no database is
        configured" into an unhandled `ModuleNotFoundError` in the `provider-offline` lane.
        Asserting on the module table rather than on the message keeps the fix from being
        undone by a later import moved back to the top of the function.
        """
        module = "cognitive_os.infrastructure.learned.postgres.provider_output_health"
        monkeypatch.delenv("COGOS_DATABASE_URL", raising=False)
        monkeypatch.delitem(sys.modules, module, raising=False)
        run(capsys, "governance-verify")
        assert module not in sys.modules


class TestLiveExecutionCannotHappenByAccident:
    def test_without_the_runtime_flag_nothing_runs(
        self, capsys: pytest.CaptureFixture[str], tmp_path: Path
    ) -> None:
        status, payload = run(
            capsys,
            "live-smoke",
            "--config",
            str(EXAMPLE_CONFIG),
            "--provider",
            "claude-code",
            "--isolation-root",
            str(tmp_path),
        )
        assert status == cli.REFUSED
        assert "--i-understand-this-calls-a-live-provider" in payload["reason"]

    def test_with_the_flag_but_without_the_configuration_nothing_runs(
        self, capsys: pytest.CaptureFixture[str], tmp_path: Path
    ) -> None:
        """The second half of the two-part opt-in. Both are required, in that order."""
        status, payload = run(
            capsys,
            "live-smoke",
            "--config",
            str(EXAMPLE_CONFIG),
            "--provider",
            "claude-code",
            "--isolation-root",
            str(tmp_path),
            "--i-understand-this-calls-a-live-provider",
        )
        assert status == cli.REFUSED
        assert "configuration does not enable live smokes" in payload["reason"]

    def test_an_unknown_provider_is_not_found(
        self, capsys: pytest.CaptureFixture[str], tmp_path: Path
    ) -> None:
        status, payload = run(
            capsys,
            "live-smoke",
            "--config",
            str(EXAMPLE_CONFIG),
            "--provider",
            "nope",
            "--isolation-root",
            str(tmp_path),
            "--i-understand-this-calls-a-live-provider",
        )
        assert status == cli.NOT_FOUND
        assert payload["found"] is False

    def test_the_repository_working_tree_is_never_an_isolation_root(self) -> None:
        with pytest.raises(cli.LiveSmokeRefused, match="outside the repository working tree"):
            cli._resolve_isolation_root(Path.cwd())

    def test_a_directory_inside_the_repository_is_never_an_isolation_root(self) -> None:
        with pytest.raises(cli.LiveSmokeRefused, match="outside the repository working tree"):
            cli._resolve_isolation_root(ADVISORY_ROOT)

    def test_a_missing_isolation_root_is_refused(self, tmp_path: Path) -> None:
        with pytest.raises(cli.LiveSmokeRefused, match="does not exist"):
            cli._resolve_isolation_root(tmp_path / "absent")


class TestTheLiveSmokePath:
    """Everything the live command does apart from the provider call itself.

    The adapter is replaced at the construction boundary, so the workspace snapshot, the
    independent verifier, the retention default and the receipt shape are all exercised for
    real without a process, a credential or a network.
    """

    @pytest.fixture
    def isolated(self, tmp_path_factory: pytest.TempPathFactory) -> Path:
        root = tmp_path_factory.mktemp("isolation") / "advisory"
        copytree(ADVISORY_ROOT, root)
        return root

    def _config(self, isolated: Path, **overrides: Any) -> Any:
        from cognitive_os.config.provider_config import ClaudeCodeProviderConfig

        return ClaudeCodeProviderConfig(
            provider_id="claude-code",
            executable="claude",
            working_directory=isolated / "workspace",
            enabled=True,
            live_smoke_enabled=True,
            **overrides,
        )

    def _arguments(self, isolated: Path) -> Any:
        from argparse import Namespace

        return Namespace(
            provider="claude-code",
            isolation_root=isolated,
            i_understand_this_calls_a_live_provider=True,
        )

    @pytest.mark.asyncio
    async def test_a_correct_answer_and_an_untouched_workspace_pass(
        self,
        capsys: pytest.CaptureFixture[str],
        isolated: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setattr(
            "cognitive_os.providers.factory.build_provider",
            lambda config: _StubProvider(config.provider_id, answer=CORRECT_ANSWER),
        )
        status = await cli._run_live_smoke(self._config(isolated), self._arguments(isolated))
        payload = json.loads(capsys.readouterr().out)
        assert status == 0
        assert payload["answer_correct"] is True
        assert payload["workspace_unchanged"] is True
        assert payload["retention_mode"] == "none"
        assert payload["governance_recorded"] is False

    @pytest.mark.asyncio
    async def test_a_well_formed_but_wrong_answer_fails(
        self,
        capsys: pytest.CaptureFixture[str],
        isolated: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Schema validity is not correctness, and the CLI is where that has to be visible."""
        monkeypatch.setattr(
            "cognitive_os.providers.factory.build_provider",
            lambda config: _StubProvider(
                config.provider_id, answer={"summary": "nothing found", "findings": []}
            ),
        )
        status = await cli._run_live_smoke(self._config(isolated), self._arguments(isolated))
        payload = json.loads(capsys.readouterr().out)
        assert status == 1
        assert payload["answer_correct"] is False
        assert payload["verifier_verdict"] == "no_findings"

    @pytest.mark.asyncio
    async def test_a_mutated_workspace_fails_even_when_the_answer_is_right(
        self,
        capsys: pytest.CaptureFixture[str],
        isolated: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """A correct diagnosis from a provider that edited the fixture is still a failure."""

        def build(config: Any) -> Any:
            return _StubProvider(
                config.provider_id,
                answer=CORRECT_ANSWER,
                side_effect=lambda: (isolated / "workspace" / "touched.txt").write_text("x"),
            )

        monkeypatch.setattr("cognitive_os.providers.factory.build_provider", build)
        status = await cli._run_live_smoke(self._config(isolated), self._arguments(isolated))
        payload = json.loads(capsys.readouterr().out)
        assert status == 1
        assert payload["workspace_unchanged"] is False
        assert payload["workspace_changes"][0]["path"] == "touched.txt"

    @pytest.mark.asyncio
    async def test_a_working_directory_outside_the_verified_fixture_is_refused(
        self, isolated: Path, tmp_path: Path
    ) -> None:
        config = self._config(isolated).model_copy(update={"working_directory": tmp_path})
        with pytest.raises(cli.LiveSmokeRefused, match="working_directory does not match"):
            await cli._run_live_smoke(config, self._arguments(isolated))

    @pytest.mark.asyncio
    async def test_the_receipt_carries_no_prompt_or_response_text(
        self,
        capsys: pytest.CaptureFixture[str],
        isolated: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setattr(
            "cognitive_os.providers.factory.build_provider",
            lambda config: _StubProvider(config.provider_id, answer=CORRECT_ANSWER),
        )
        await cli._run_live_smoke(self._config(isolated), self._arguments(isolated))
        rendered = capsys.readouterr().out
        assert "arithmetic_mean divides by len(values)" not in rendered
        assert "Read-only review task" not in rendered
        # The hashes are what a later run compares against, so they must be there.
        payload = json.loads(rendered)
        assert payload["request_hash"] and payload["normalized_response_hash"]
        assert payload["answer_hash"]


class _StubProvider:
    """A provider-shaped object for the construction boundary, with no process behind it."""

    def __init__(
        self,
        provider_id: str,
        status: ProviderStatus = ProviderStatus.AVAILABLE,
        *,
        answer: dict[str, Any] | None = None,
        side_effect: Any = None,
    ) -> None:
        self.provider_id = provider_id
        self.enabled = True
        self._status = status
        self._answer = answer
        self._side_effect = side_effect
        self.identity = ProviderIdentity(
            provider_id=provider_id,
            display_name="stub",
            provider_kind=ProviderKind.CLI_AGENT,
            adapter_version="test",
        )

    async def health_check(self) -> ProviderHealth:
        return ProviderHealth(
            provider_id=self.provider_id,
            status=self._status,
            checked_at=utc_now(),
            message="stub",
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

    async def complete(self, request: ModelProviderRequest) -> ModelProviderResponse:
        if self._side_effect is not None:
            self._side_effect()
        return ModelProviderResponse(
            model_call_id=request.model_call_id,
            provider_id=self.provider_id,
            requested_model=request.requested_model or "stub-model",
            resolved_model="stub-model-v1",
            content=json.dumps(self._answer or {}),
            structured_output=self._answer,
            finish_reason=ModelFinishReason.COMPLETED,
            latency_ms=1.0,
        )
