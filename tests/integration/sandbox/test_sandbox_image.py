import json
import os
import subprocess

import pytest


@pytest.mark.integration
@pytest.mark.skipif(
    os.environ.get("COGOS_RUN_SANDBOX_INTEGRATION") != "1", reason="opt-in Docker test"
)
def test_sandbox_has_no_network_and_runs_non_root() -> None:
    command = [
        "docker",
        "run",
        "--rm",
        "--read-only",
        "--network",
        "none",
        "--cap-drop",
        "ALL",
        "--security-opt",
        "no-new-privileges",
        "--pids-limit",
        "64",
        "--memory",
        "256m",
        "--cpus",
        "1",
        "--tmpfs",
        "/tmp:rw,noexec,nosuid,nodev,size=16m",
        "cognitive-os-sandbox:sprint-5",
        "id",
        "-u",
    ]
    result = subprocess.run(command, check=True, capture_output=True, text=True)
    assert result.stdout.strip() == "10001"


@pytest.mark.integration
@pytest.mark.skipif(
    os.environ.get("COGOS_RUN_SANDBOX_INTEGRATION") != "1", reason="opt-in Docker test"
)
def test_sandbox_restrictions_are_visible_to_docker_inspection() -> None:
    name = "cogos-inspection-test"
    command = [
        "docker",
        "run",
        "--detach",
        "--name",
        name,
        "--read-only",
        "--network",
        "none",
        "--cap-drop",
        "ALL",
        "--security-opt",
        "no-new-privileges",
        "--pids-limit",
        "64",
        "--memory",
        "256m",
        "--cpus",
        "1",
        "--tmpfs",
        "/tmp:rw,noexec,nosuid,nodev,size=16m",
        "cognitive-os-sandbox:sprint-5",
        "sleep",
        "30",
    ]
    subprocess.run(command, check=True, capture_output=True, text=True)
    try:
        inspected = subprocess.run(
            ["docker", "inspect", name], check=True, capture_output=True, text=True
        )
        value = json.loads(inspected.stdout)[0]
        host = value["HostConfig"]
        assert value["Config"]["User"] == "10001:10001"
        assert host["ReadonlyRootfs"] is True
        assert host["NetworkMode"] == "none"
        assert host["CapDrop"] == ["ALL"]
        assert "no-new-privileges" in host["SecurityOpt"]
        assert host["PidsLimit"] == 64
        assert host["Memory"] == 268435456
        assert host["Privileged"] is False
        assert host["Devices"] == []
    finally:
        subprocess.run(["docker", "rm", "--force", name], check=True)
