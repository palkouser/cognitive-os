"""Credential-free fixtures for the Sprint 21C3 reality-input tests.

No Docker, no PostgreSQL, no network. The sandbox is the one thing these fixtures refuse to
fake into evidence: `StubSandbox` records the `SandboxRequest` it was given and returns a
canned result, so a test can assert what *would* be mounted, never that a mount worked. The
opt-in Docker slice in `tests/integration/coding/` is what proves the mount itself.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from uuid import NAMESPACE_URL, UUID, uuid4, uuid5

from cognitive_os.coding.hidden_verification import (
    HiddenVerificationBundle,
    HiddenVerificationEvidence,
    HiddenVerificationStatus,
)
from cognitive_os.domain.acceptance import AcceptanceDecision, AcceptanceDecisionType
from cognitive_os.domain.coding import (
    CodingOutcome,
    CodingOutcomeStatus,
    RepositoryProfile,
    RepositoryProfileStatus,
    WorkspaceDisposition,
)
from cognitive_os.domain.common import ArtifactRef
from cognitive_os.domain.memory import MemorySensitivity
from cognitive_os.domain.reality import (
    RealityCandidateManifest,
    RealityCandidateSource,
    RealityCandidateStrategy,
    RealityContentEntry,
    RealitySourceRights,
    RealityTaskDifficulty,
    RealityTaskFamily,
    RealityTaskManifest,
    RealityTaskProjection,
)
from cognitive_os.domain.sandbox import SandboxLimits, SandboxRequest, SandboxResult

FIXTURE_TIME = datetime(2026, 7, 29, 12, 0, tzinfo=UTC)
BASE_COMMIT = "0" * 40

SANDBOX_LIMITS = SandboxLimits(
    timeout_seconds=60,
    memory_bytes=536_870_912,
    cpu_count=1,
    pid_limit=128,
    maximum_stdout_bytes=100_000,
    maximum_stderr_bytes=100_000,
    maximum_artifact_bytes=100_000,
)


def digest(text: str) -> str:
    return sha256(text.encode()).hexdigest()


class InMemoryArtifactStore:
    """Content-addressed, in-process, and able to lose bytes on purpose.

    `corrupt` and `forget` exist because the failures worth testing are the ones the
    inconsistent development pair actually exhibits: a metadata row whose file is gone, and a
    row whose hash no longer describes the file.
    """

    def __init__(self) -> None:
        self._data: dict[UUID, bytes] = {}
        self._refs: dict[UUID, ArtifactRef] = {}

    async def put_bytes(
        self, data: bytes, *, media_type: str, source_event_id: UUID | None = None
    ) -> ArtifactRef:
        del source_event_id
        artifact_id = uuid4()
        content_hash = sha256(data).hexdigest()
        reference = ArtifactRef(
            artifact_id=artifact_id,
            media_type=media_type,
            content_hash=content_hash,
            size_bytes=len(data),
            storage_key=f"sha256/{content_hash[:2]}/{content_hash}",
            created_at=FIXTURE_TIME,
        )
        self._data[artifact_id] = data
        self._refs[artifact_id] = reference
        return reference

    async def put_file(
        self, path: Path, *, media_type: str, source_event_id: UUID | None = None
    ) -> ArtifactRef:
        return await self.put_bytes(
            path.read_bytes(), media_type=media_type, source_event_id=source_event_id
        )

    async def get_bytes(self, artifact_id: UUID) -> bytes:
        return self._data[artifact_id]

    async def open_read(self, artifact_id: UUID) -> object:  # pragma: no cover - unused
        raise NotImplementedError

    async def verify(self, artifact_id: UUID) -> bool:
        data = self._data.get(artifact_id)
        reference = self._refs.get(artifact_id)
        return (
            data is not None
            and reference is not None
            and sha256(data).hexdigest() == reference.content_hash
        )

    async def describe(self, artifact_id: UUID) -> ArtifactRef | None:
        return self._refs.get(artifact_id)

    async def exists(self, artifact_id: UUID) -> bool:
        return artifact_id in self._data

    async def find_orphan_blobs(self) -> tuple[str, ...]:
        return ()

    def corrupt(self, artifact_id: UUID) -> None:
        """Change the bytes behind a metadata row without changing the row."""
        self._data[artifact_id] = b"corrupted"

    def forget(self, artifact_id: UUID) -> None:
        """Delete the file and keep the metadata row: the C1 mismatch, reproduced."""
        self._data.pop(artifact_id, None)


@dataclass
class StubSandbox:
    """Records requests, returns a canned result. Never launches anything."""

    exit_code: int = 0
    stdout: bytes = b""
    stderr: bytes = b""
    timed_out: bool = False
    requests: list[SandboxRequest] = field(default_factory=list)
    cleaned: list[str] = field(default_factory=list)

    async def run(self, request: SandboxRequest) -> SandboxResult:
        self.requests.append(request)
        return SandboxResult(
            sandbox_id=request.sandbox_id,
            exit_code=self.exit_code,
            stdout=self.stdout,
            stderr=self.stderr,
            timed_out=self.timed_out,
        )

    async def cancel(self, sandbox_id: str) -> None:  # pragma: no cover - unused
        self.cleaned.append(sandbox_id)

    async def inspect(self, sandbox_id: str) -> dict[str, object]:  # pragma: no cover
        return {}

    async def cleanup(self, sandbox_id: str) -> None:
        self.cleaned.append(sandbox_id)

    async def list_stale(self) -> tuple[str, ...]:  # pragma: no cover - unused
        return ()


def task_manifest(
    *,
    task_id: UUID | None = None,
    seed: int = 1,
    family: RealityTaskFamily = RealityTaskFamily.NUMERIC_LOGIC,
) -> RealityTaskManifest:
    identity = task_id or uuid4()
    projection = RealityTaskProjection(
        task_id=identity,
        task_family=family,
        difficulty=RealityTaskDifficulty.SINGLE_EDIT,
        issue_description="mean() returns 0.0 for an empty sequence instead of raising.",
        expected_behavior="mean() raises ValueError for an empty sequence.",
        visible_test_command=("pytest", "-q", "tests"),
        allowed_paths=("src",),
        forbidden_paths=("tests",),
        files=(
            RealityContentEntry(
                path="src/stats.py", size_bytes=120, file_hash=digest("visible source")
            ),
        ),
    )
    return RealityTaskManifest(
        task_id=identity,
        task_family=family,
        repository_group="numeric-logic-statistics",
        difficulty=RealityTaskDifficulty.SINGLE_EDIT,
        generator_profile_id="reality.tasks",
        generator_profile_version=1,
        generation_seed=seed,
        projection=projection,
        base_repository_manifest_hash=digest("base repository"),
        hidden_verifier_bundle_artifact_id=uuid4(),
        hidden_verifier_bundle_hash=digest("hidden bundle"),
        control_material_manifest_hash=digest("control material"),
        baseline_failure_reason="mean([]) returns 0.0 instead of raising ValueError",
        required_verifier_ids=("coding.hidden_pytest", "coding.pytest"),
        rights=RealitySourceRights(
            source_identity="cognitive-os:generated:numeric_logic.empty_mean",
            licence_identifier="Apache-2.0",
            rights_verified=True,
            rights_evidence_hash=digest("project-owned"),
            attribution="Cognitive OS project",
            sensitivity=MemorySensitivity.PUBLIC,
        ),
        created_at=FIXTURE_TIME,
    )


def candidate_manifest(
    task: RealityTaskManifest,
    strategy: RealityCandidateStrategy = RealityCandidateStrategy.CORRECT_NARROW,
    *,
    source: RealityCandidateSource = RealityCandidateSource.CURATED,
    provider_id: str | None = None,
    provider_output_id: UUID | None = None,
) -> RealityCandidateManifest:
    return RealityCandidateManifest(
        candidate_id=uuid4(),
        task_id=task.task_id,
        task_manifest_hash=task.content_hash,
        strategy=strategy,
        source=source,
        patch_artifact_id=uuid4(),
        patch_hash=digest(f"patch:{strategy.value}"),
        generator_profile_id="reality.tasks",
        generator_profile_version=1,
        provider_id=provider_id,
        provider_output_id=provider_output_id,
        created_at=FIXTURE_TIME,
    )


def accepted_decision(task_run_id: UUID) -> AcceptanceDecision:
    """The minimum an `ACCEPTED` outcome must carry: the contract refuses one without it.

    `decision_id` is derived from the run rather than random, so `coding_outcome` stays a pure
    function of its arguments. A `uuid4` here would give the same run two canonical hashes and
    make the recorder's replay detection untestable — it would look broken when the fixture was.
    """
    return AcceptanceDecision(
        decision_id=uuid5(NAMESPACE_URL, f"cognitive-os:test:acceptance:{task_run_id}"),
        task_run_id=task_run_id,
        policy_id=uuid5(NAMESPACE_URL, "cognitive-os:sprint21c3:python-coding-hidden-acceptance"),
        policy_version="1",
        decision=AcceptanceDecisionType.ACCEPTED,
        criterion_evaluations=(),
        required_passed=True,
        optional_score=1.0,
        reason="every required criterion passed, including hidden verification",
        created_at=FIXTURE_TIME,
    )


def coding_outcome(
    *,
    task_run_id: UUID,
    status: CodingOutcomeStatus = CodingOutcomeStatus.FAILED,
    marker: str = "run",
) -> CodingOutcome:
    """A minimal but complete outcome. `marker` makes two outcomes differ by content."""
    return CodingOutcome(
        task_run_id=task_run_id,
        status=status,
        repository_profile=RepositoryProfile(
            status=RepositoryProfileStatus.SUPPORTED,
            git_repository=True,
            has_pyproject=True,
            has_pytest=True,
        ),
        base_commit=BASE_COMMIT,
        acceptance_decision=accepted_decision(task_run_id)
        if status is CodingOutcomeStatus.ACCEPTED
        else None,
        workspace_disposition=WorkspaceDisposition.REMOVE,
        policy_denials=(marker,),
        completed_at=FIXTURE_TIME,
    )


def hidden_bundle(task: RealityTaskManifest, host_path: Path) -> HiddenVerificationBundle:
    return HiddenVerificationBundle(
        task_id=task.task_id,
        host_path=str(host_path),
        bundle_content_hash=digest("control bundle"),
        artifact_id=uuid4(),
        artifact_hash=digest("control archive"),
    )


def hidden_evidence(
    *,
    task: RealityTaskManifest,
    task_run_id: UUID,
    status: HiddenVerificationStatus = HiddenVerificationStatus.FAILED,
) -> HiddenVerificationEvidence:
    return HiddenVerificationEvidence(
        task_id=task.task_id,
        task_run_id=task_run_id,
        status=status,
        exit_code=0 if status is HiddenVerificationStatus.PASSED else 1,
        bundle_content_hash=digest("control bundle"),
        sandbox_image_digest="sha256:fixture",
        stdout_hash=digest("stdout"),
        stderr_hash=digest(""),
        captured_bytes=12,
        duration_seconds=0.5,
        recorded_at=FIXTURE_TIME,
    )
