"""Sandbox execution contracts."""

from __future__ import annotations

from typing import Literal

from pydantic import Field, field_validator

from .base import ImmutableContractModel
from .common import Sha256Hex


class SandboxVerificationInput(ImmutableContractModel):
    """The one read-only control mount a hidden verifier may receive, Sprint 21C3.

    Deliberately not a general mount list. A verifier needs exactly one trusted input at
    exactly one destination, and `container_path` is a `Literal` so that widening it is a
    contract change someone has to make on purpose rather than a config value someone can
    set. There is no writable variant: the hidden tests are the answer key, and a container
    that could write to them could rewrite the answer.

    `content_hash` is a `snapshot_workspace` tree digest, checked immediately before the
    container starts. A changed bundle fails closed rather than running against unknown
    tests.
    """

    host_path: str
    container_path: Literal["/verification"] = "/verification"
    content_hash: Sha256Hex

    @field_validator("host_path")
    @classmethod
    def host_path_is_absolute(cls, value: str) -> str:
        if not value.startswith("/") or ".." in value.split("/"):
            raise ValueError("verification input host path must be absolute and non-traversing")
        return value


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
    #: Absent for every pre-C3 caller, so the existing visible-verification path is unchanged.
    verification_input: SandboxVerificationInput | None = None


class SandboxResult(ImmutableContractModel):
    sandbox_id: str
    exit_code: int
    stdout: bytes
    stderr: bytes
    timed_out: bool = False
