"""Opt-in live CLI advisory tests, driven through the one governed live path.

These call a real, locally authenticated CLI. They are skipped unless the operator sets the
opt-in variable, and they are excluded from every credential-free lane.

They deliberately drive `scripts/provider.py`'s own live-smoke path rather than constructing
an adapter directly. A second live route that built its own configuration would be a route
without the isolation check, the mutation guard or the independent verifier — and it was
exactly that shape, pointed at `Path.cwd()`, that this file used to hold.
"""

from __future__ import annotations

import json
import os
from argparse import Namespace
from pathlib import Path
from shutil import copytree

import pytest

from cognitive_os.config.provider_config import (
    ClaudeCodeProviderConfig,
    CliProcessLimits,
    CodexCliProviderConfig,
)
from cognitive_os.providers.advisory_fixture import DEFAULT_FIXTURE_PATH, load_advisory_fixture
from scripts import provider as cli

LIVE_TIMEOUT_SECONDS = 300


def _isolated_fixture(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """A verified copy of the public fixture, outside the repository working tree.

    `tmp_path_factory` roots outside the repository, which is what `_resolve_isolation_root`
    requires — a live agent must never run where the source it is describing lives.
    """
    root = tmp_path_factory.mktemp("advisory-live") / "advisory"
    copytree(DEFAULT_FIXTURE_PATH, root)
    load_advisory_fixture(root)  # refuses a drifted, incomplete or unlisted-file copy
    return root


def _arguments(root: Path, provider_id: str) -> Namespace:
    return Namespace(
        provider=provider_id,
        isolation_root=root,
        i_understand_this_calls_a_live_provider=True,
    )


async def _assert_governed_live_run(
    config: object, root: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    status = await cli._run_live_smoke(config, _arguments(root, config.provider_id))  # type: ignore[attr-defined]
    receipt = json.loads(capsys.readouterr().out)

    assert receipt["workspace_unchanged"] is True, receipt["workspace_changes"]
    assert receipt["answer_correct"] is True, receipt["missing_concepts"]
    assert receipt["verifier_verdict"] == "correct"
    # Retention stays at the default: a live smoke proves the boundary, it does not record
    # a governance revision.
    assert receipt["retention_mode"] == "none"
    assert receipt["governance_recorded"] is False
    assert status == 0


@pytest.mark.claude_code_live
@pytest.mark.asyncio
async def test_live_claude_code_read_only_advisory(
    tmp_path_factory: pytest.TempPathFactory, capsys: pytest.CaptureFixture[str]
) -> None:
    if os.environ.get("COGOS_RUN_CLAUDE_CODE_LIVE") != "1":
        pytest.skip("live Claude Code execution is not enabled")
    root = _isolated_fixture(tmp_path_factory)
    config = ClaudeCodeProviderConfig(
        working_directory=root / "workspace",
        enabled=True,
        live_smoke_enabled=True,
        limits=CliProcessLimits(timeout_seconds=LIVE_TIMEOUT_SECONDS),
        maximum_turns=3,
    )
    await _assert_governed_live_run(config, root, capsys)


@pytest.mark.codex_cli_live
@pytest.mark.asyncio
async def test_live_codex_read_only_advisory(
    tmp_path_factory: pytest.TempPathFactory, capsys: pytest.CaptureFixture[str]
) -> None:
    if os.environ.get("COGOS_RUN_CODEX_LIVE") != "1":
        pytest.skip("live Codex execution is not enabled")
    root = _isolated_fixture(tmp_path_factory)
    config = CodexCliProviderConfig(
        working_directory=root / "workspace",
        enabled=True,
        live_smoke_enabled=True,
        limits=CliProcessLimits(timeout_seconds=LIVE_TIMEOUT_SECONDS),
    )
    await _assert_governed_live_run(config, root, capsys)
