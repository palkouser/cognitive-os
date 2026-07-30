"""The hidden verifier boundary: §4.8.

A visible test suite tells a candidate what it has to satisfy. That makes it a specification,
and a specification is exactly what an overfitted patch satisfies without repairing anything.
The hidden suite is the part of the answer nobody being measured gets to read.

Three structural decisions keep it that way, and none of them is a policy check that a caller
could forget:

* the control bundle reaches the container through `SandboxRequest.verification_input`, whose
  destination is a `Literal["/verification"]` and whose mount is `readonly`. There is no
  writable variant to pass by mistake;
* the hidden run does **not** go through the tool plane. `SandboxDevelopmentTool` descriptors
  are `provider_visible=True`, so routing the control mount through them would put a
  provider-visible tool one argument away from the answer key. This module talks to
  the sandbox port directly and exposes no descriptor at all;
* the pytest command is a module constant. Nothing a candidate, a provider or a caller
  supplies reaches the argument vector, so there is no "run only the tests that pass" input.

What the sandbox produces here is *evidence*, not a verdict. `coding.hidden_pytest` in
`cognitive_os.verification.coding.hidden_pytest` reads that evidence and decides, which keeps
the decision on the same registry-backed path as every other criterion.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from hashlib import sha256
from pathlib import Path
from time import perf_counter
from uuid import UUID, uuid4

from pydantic import Field, field_validator

from cognitive_os.application.ports.sandbox import SandboxPort
from cognitive_os.domain.common import JsonValue, NonEmptyStr, Sha256Hex, UtcDatetime, utc_now
from cognitive_os.domain.experience import HashedExperienceContract
from cognitive_os.domain.sandbox import SandboxLimits, SandboxRequest, SandboxVerificationInput
from cognitive_os.providers.workspace_snapshot import snapshot_workspace
from cognitive_os.tools.errors import SandboxExecutionError

#: The criterion identity every C3 run is measured against.
HIDDEN_PYTEST_VERIFIER_ID = "coding.hidden_pytest"

#: Host-selected and fixed. `-p no:cacheprovider` keeps pytest from trying to write a cache
#: directory into a read-only mount; `--rootdir` stops it walking up out of the bundle looking
#: for configuration the task could have planted.
HIDDEN_PYTEST_ARGUMENTS: tuple[str, ...] = (
    "-q",
    "--no-header",
    "-p",
    "no:cacheprovider",
    "--rootdir",
    "/verification",
    "/verification",
)

#: Bounded so a failing test that prints in a loop cannot fill the evidence artifact.
_MAXIMUM_CAPTURED_BYTES = 262_144


class HiddenVerificationStatus(StrEnum):
    """What the hidden suite established. `UNVERIFIABLE` is not `FAILED`.

    A missing bundle, a tampered bundle or a sandbox that never started tells us nothing
    about the candidate. Recording that as a failure would put an infrastructure problem into
    the corpus as evidence about a patch, which is the mislabelling §9 requires us to avoid.
    """

    PASSED = "passed"
    FAILED = "failed"
    TIMED_OUT = "timed_out"
    UNVERIFIABLE = "unverifiable"


class HiddenVerificationBundle(HashedExperienceContract):
    """One task's control material: where it lives, what it hashes to, where it is archived."""

    task_id: UUID
    host_path: str = Field(exclude=True)
    bundle_content_hash: Sha256Hex
    artifact_id: UUID
    artifact_hash: Sha256Hex

    @field_validator("host_path")
    @classmethod
    def host_path_is_absolute(cls, value: str) -> str:
        if not Path(value).is_absolute():
            raise ValueError("hidden verification bundle path must be absolute host configuration")
        return value


class HiddenVerificationEvidence(HashedExperienceContract):
    """The normalized result of one hidden run.

    Carries hashes of the captured output, never the output itself. A hidden test's assertion
    message names the edge case it checks, so quoting it into an event, a manifest or a report
    would leak the answer through the evidence trail rather than through the mount.
    """

    task_id: UUID
    task_run_id: UUID
    criterion_id: NonEmptyStr = HIDDEN_PYTEST_VERIFIER_ID
    status: HiddenVerificationStatus
    exit_code: int | None = None
    bundle_content_hash: Sha256Hex
    sandbox_image_digest: NonEmptyStr
    stdout_hash: Sha256Hex
    stderr_hash: Sha256Hex
    captured_bytes: int = Field(ge=0)
    truncated: bool = False
    duration_seconds: float = Field(ge=0)
    reason: NonEmptyStr | None = None
    recorded_at: UtcDatetime

    @property
    def passed(self) -> bool:
        return self.status is HiddenVerificationStatus.PASSED

    def as_verifier_subject(self) -> dict[str, JsonValue]:
        """The structured value `coding.hidden_pytest` decides on."""
        return {
            "criterion_id": self.criterion_id,
            "status": self.status.value,
            "exit_code": self.exit_code,
            "bundle_content_hash": self.bundle_content_hash,
            "sandbox_image_digest": self.sandbox_image_digest,
            "evidence_hash": self.content_hash,
        }


@dataclass(frozen=True, slots=True)
class HiddenVerificationRunner:
    """Runs the fixed hidden pytest command against one workspace and one control bundle."""

    sandbox: SandboxPort
    limits: SandboxLimits
    image_digest: str

    async def run(
        self,
        *,
        task_id: UUID,
        task_run_id: UUID,
        workspace: Path,
        bundle: HiddenVerificationBundle,
    ) -> HiddenVerificationEvidence:
        """Execute and normalize. Never raises for a candidate's failure; raises for ours.

        An infrastructure problem becomes `UNVERIFIABLE` evidence rather than an exception,
        because the campaign has to record *something* for a run it attempted — a run that
        vanished is a gap in the denominator nobody can audit afterwards.
        """
        started = perf_counter()
        source = Path(bundle.host_path)
        if not source.is_dir():
            return self._unverifiable(
                task_id, task_run_id, bundle, started, "control bundle is missing"
            )
        if snapshot_workspace(source).digest != bundle.bundle_content_hash:
            return self._unverifiable(
                task_id, task_run_id, bundle, started, "control bundle content hash changed"
            )

        sandbox_id = f"cogos-hidden-{uuid4().hex[:16]}"
        try:
            result = await self.sandbox.run(
                SandboxRequest(
                    sandbox_id=sandbox_id,
                    tool_call_id=str(uuid4()),
                    task_run_id=str(task_run_id),
                    workspace=str(workspace),
                    executable="pytest",
                    arguments=HIDDEN_PYTEST_ARGUMENTS,
                    limits=self.limits,
                    verification_input=SandboxVerificationInput(
                        host_path=str(source.resolve()),
                        content_hash=bundle.bundle_content_hash,
                    ),
                )
            )
        except SandboxExecutionError as error:
            return self._unverifiable(task_id, task_run_id, bundle, started, str(error))
        finally:
            # Success, failure, timeout and cancellation all land here: a container left
            # behind holds a bind mount to the answer key.
            await self.sandbox.cleanup(sandbox_id)

        stdout = result.stdout[:_MAXIMUM_CAPTURED_BYTES]
        stderr = result.stderr[:_MAXIMUM_CAPTURED_BYTES]
        if result.timed_out:
            status = HiddenVerificationStatus.TIMED_OUT
        elif result.exit_code == 0:
            status = HiddenVerificationStatus.PASSED
        else:
            status = HiddenVerificationStatus.FAILED
        return HiddenVerificationEvidence(
            task_id=task_id,
            task_run_id=task_run_id,
            status=status,
            exit_code=result.exit_code,
            bundle_content_hash=bundle.bundle_content_hash,
            sandbox_image_digest=self.image_digest,
            stdout_hash=sha256(stdout).hexdigest(),
            stderr_hash=sha256(stderr).hexdigest(),
            captured_bytes=len(stdout) + len(stderr),
            truncated=len(result.stdout) > len(stdout) or len(result.stderr) > len(stderr),
            duration_seconds=perf_counter() - started,
            recorded_at=utc_now(),
        )

    def _unverifiable(
        self,
        task_id: UUID,
        task_run_id: UUID,
        bundle: HiddenVerificationBundle,
        started: float,
        reason: str,
    ) -> HiddenVerificationEvidence:
        empty = sha256(b"").hexdigest()
        return HiddenVerificationEvidence(
            task_id=task_id,
            task_run_id=task_run_id,
            status=HiddenVerificationStatus.UNVERIFIABLE,
            bundle_content_hash=bundle.bundle_content_hash,
            sandbox_image_digest=self.image_digest,
            stdout_hash=empty,
            stderr_hash=empty,
            captured_bytes=0,
            duration_seconds=perf_counter() - started,
            reason=reason,
            recorded_at=utc_now(),
        )


def load_bundle(
    *, task_id: UUID, host_path: Path, artifact_id: UUID, artifact_hash: str
) -> HiddenVerificationBundle:
    """Describe a control bundle on disk, hashing it as it is now."""
    resolved = host_path.resolve()
    if not resolved.is_dir():
        raise ValueError(f"hidden verification bundle is not a directory: {host_path}")
    return HiddenVerificationBundle(
        task_id=task_id,
        host_path=str(resolved),
        bundle_content_hash=snapshot_workspace(resolved).digest,
        artifact_id=artifact_id,
        artifact_hash=artifact_hash,
    )
