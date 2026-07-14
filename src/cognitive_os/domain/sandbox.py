"""Sandbox execution contracts."""

from pydantic import Field

from .base import ImmutableContractModel


class SandboxLimits(ImmutableContractModel):
    timeout_seconds: float = Field(gt=0, le=3600)
    memory_bytes: int = Field(ge=134_217_728, le=68_719_476_736)
    cpu_count: float = Field(gt=0, le=32)
    pid_limit: int = Field(ge=16, le=4096)
    maximum_stdout_bytes: int = Field(gt=0, le=16_777_216)
    maximum_stderr_bytes: int = Field(gt=0, le=16_777_216)
    maximum_artifact_bytes: int = Field(gt=0, le=1_073_741_824)
    network_enabled: bool = False


class SandboxRequest(ImmutableContractModel):
    sandbox_id: str
    tool_call_id: str
    task_run_id: str
    workspace: str
    executable: str
    arguments: tuple[str, ...] = ()
    limits: SandboxLimits


class SandboxResult(ImmutableContractModel):
    sandbox_id: str
    exit_code: int
    stdout: bytes
    stderr: bytes
    timed_out: bool = False
