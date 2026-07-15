from pathlib import Path

import pytest

from cognitive_os.coding.sandbox import (
    CodingSandboxMountDescriptor,
    build_sandbox_mount_descriptor,
)
from cognitive_os.domain.coding import CodingLimits
from cognitive_os.infrastructure.repository.errors import RepositoryPolicyError
from cognitive_os.infrastructure.repository.git_commands import GitCommandRunner


def test_sandbox_descriptor_hides_host_path_and_seals_limits(tmp_path: Path) -> None:
    descriptor = build_sandbox_mount_descriptor("workspace-1", tmp_path, CodingLimits())

    assert descriptor.container_workspace == "/workspace"
    assert descriptor.network_mode == "none"
    assert descriptor.cpu_limit == 4
    assert descriptor.memory_mb == 8192
    assert str(tmp_path) not in descriptor.canonical_json()


def test_sandbox_descriptor_cannot_weaken_boundary(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="cannot be weakened"):
        CodingSandboxMountDescriptor(
            workspace_id="workspace-1",
            host_workspace=tmp_path,
            user="1000:1000",
            cpu_limit=4,
            memory_mb=8192,
            network_mode="bridge",
        )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "argument",
    ("-c", "--config-env=credential.helper=TOKEN", "--exec-path=/tmp/tool", "bad\nargument"),
)
async def test_git_runner_rejects_global_option_and_control_injection(
    tmp_path: Path, argument: str
) -> None:
    with pytest.raises(RepositoryPolicyError, match="invalid repository"):
        await GitCommandRunner().run(tmp_path, "status", (argument,))
