import asyncio
from pathlib import Path

import pytest

from cognitive_os.config.provider_config import ClaudeCodeProviderConfig
from cognitive_os.providers.claude_code.process import ClaudeProcessRunner
from cognitive_os.providers.errors import ProviderProcessError


def test_arguments_are_shell_free_and_exclude_permission_bypass(tmp_path: Path) -> None:
    runner = ClaudeProcessRunner(
        ClaudeCodeProviderConfig(executable="claude", working_directory=tmp_path)
    )
    arguments = runner.build_arguments("analyze; touch forbidden", '{"type":"object"}')
    assert arguments[0] == "claude"
    assert arguments[-1] == "analyze; touch forbidden"
    assert "--dangerously-skip-permissions" not in arguments


@pytest.mark.asyncio
async def test_repository_modification_is_a_policy_violation(tmp_path: Path, monkeypatch) -> None:
    runner = ClaudeProcessRunner(
        ClaudeCodeProviderConfig(executable="claude", working_directory=tmp_path)
    )
    statuses = iter(("", "?? created-by-provider.txt\n"))

    async def fake_git_status() -> str:
        return next(statuses)

    class FakeProcess:
        returncode = 0

        async def communicate(self) -> tuple[bytes, bytes]:
            await asyncio.sleep(0)
            return b'{"summary":"done"}', b""

    async def fake_subprocess(*_arguments, **_keywords) -> FakeProcess:
        return FakeProcess()

    monkeypatch.setattr(runner, "_git_status", fake_git_status)
    monkeypatch.setattr(asyncio, "create_subprocess_exec", fake_subprocess)
    with pytest.raises(ProviderProcessError, match="modified the repository"):
        await runner.run(prompt="analyze", schema='{"type":"object"}')
