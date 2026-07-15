import os
from pathlib import Path
from uuid import uuid4

import pytest

from cognitive_os.domain.sandbox import SandboxLimits, SandboxRequest
from cognitive_os.tools.sandbox.lifecycle import DockerSandbox


@pytest.mark.integration
@pytest.mark.skipif(
    os.environ.get("COGOS_RUN_SANDBOX_INTEGRATION") != "1",
    reason="opt-in rootless Docker test",
)
@pytest.mark.asyncio
async def test_coding_sandbox_mount_is_only_writable_workspace(tmp_path: Path) -> None:
    workspace = tmp_path / "detached-worktree"
    workspace.mkdir()
    workspace.chmod(0o777)
    sandbox_id = f"cogos-coding-test-{uuid4().hex[:12]}"
    sandbox = DockerSandbox("cognitive-os-sandbox:sprint-5")
    request = SandboxRequest(
        sandbox_id=sandbox_id,
        tool_call_id=str(uuid4()),
        task_run_id=str(uuid4()),
        workspace=str(workspace),
        executable="python",
        arguments=(
            "-c",
            "from pathlib import Path; Path('/workspace/result.txt').write_text('bounded'); "
            "assert not Path('/main').exists()",
        ),
        limits=SandboxLimits(
            timeout_seconds=20,
            memory_bytes=268_435_456,
            cpu_count=1,
            pid_limit=64,
            maximum_stdout_bytes=10_000,
            maximum_stderr_bytes=10_000,
            maximum_artifact_bytes=10_000,
            network_enabled=False,
        ),
    )
    try:
        result = await sandbox.run(request)
        assert result.exit_code == 0, result.stderr.decode(errors="replace")
        inspected = await sandbox.inspect(sandbox_id)
        host = inspected["HostConfig"]
        mounts = inspected["Mounts"]
        assert (workspace / "result.txt").read_text(encoding="utf-8") == "bounded"
        assert host["ReadonlyRootfs"] is True
        assert host["NetworkMode"] == "none"
        assert host["CapDrop"] == ["ALL"]
        assert len(mounts) == 1
        assert mounts[0]["Destination"] == "/workspace"
        assert mounts[0]["RW"] is True
    finally:
        await sandbox.cleanup(sandbox_id)
