from datetime import UTC, datetime
from uuid import UUID

import pytest

from cognitive_os.application.services.memory_service import MemoryService
from cognitive_os.domain.acceptance import AcceptanceDecision, AcceptanceDecisionType
from cognitive_os.domain.coding import (
    CodingProblemExtension,
    CodingTrajectoryPackage,
    RepositoryProfile,
    RepositoryProfileStatus,
    UnifiedDiffArtifact,
)
from cognitive_os.domain.common import ArtifactRef
from cognitive_os.domain.memory import (
    MemoryScopeType,
    MemorySensitivity,
    MemoryType,
    MemoryWritePolicy,
)
from cognitive_os.memory.errors import MemoryIntegrityError
from cognitive_os.memory.ingestion import (
    CodingTrajectoryIngestionService,
    project_accepted_trajectory,
)
from cognitive_os.memory.repository import InMemoryMemoryRepository

NOW = datetime(2026, 7, 15, tzinfo=UTC)
TASK_RUN_ID = UUID("00000000-0000-0000-0000-000000000921")


def trajectory(*, accepted: bool = True) -> CodingTrajectoryPackage:
    decision = AcceptanceDecision(
        decision_id=UUID("00000000-0000-0000-0000-000000000922"),
        task_run_id=TASK_RUN_ID,
        policy_id=UUID("00000000-0000-0000-0000-000000000923"),
        policy_version="1",
        decision=(AcceptanceDecisionType.ACCEPTED if accepted else AcceptanceDecisionType.REJECTED),
        criterion_evaluations=(),
        required_passed=accepted,
        optional_score=1.0 if accepted else 0.0,
        reason="Authoritative verifier outcome.",
        created_at=NOW,
    )
    artifact = ArtifactRef(
        artifact_id=UUID("00000000-0000-0000-0000-000000000924"),
        media_type="text/x-diff",
        content_hash="d" * 64,
        size_bytes=128,
        storage_key="coding/final.diff",
        created_at=NOW,
    )
    return CodingTrajectoryPackage(
        problem=CodingProblemExtension(
            repository_path="/prepared/repository",
            base_commit="b" * 40,
            issue_description="Repair deterministic parsing.",
            expected_behavior="All parser cases pass.",
        ),
        repository_profile=RepositoryProfile(
            status=RepositoryProfileStatus.SUPPORTED,
            git_repository=True,
            has_pyproject=True,
            python_version="3.12",
            has_pytest=True,
            has_ruff=True,
            has_mypy=True,
        ),
        context_hash="c" * 64,
        final_diff=UnifiedDiffArtifact(
            base_commit="b" * 40,
            diff_hash="d" * 64,
            artifact=artifact,
        ),
        acceptance_decision=decision,
        provenance={"fixture": "sprint-9"},
    )


def policy() -> MemoryWritePolicy:
    return MemoryWritePolicy(
        allowed_types=frozenset(MemoryType),
        allowed_scopes=frozenset(MemoryScopeType),
        maximum_sensitivity=MemorySensitivity.INTERNAL,
    )


def test_projection_is_deterministic_and_produces_only_allowed_types() -> None:
    package = trajectory()
    expected_hash = package.canonical_hash()
    first = project_accepted_trajectory(package, expected_hash)
    second = project_accepted_trajectory(package, expected_hash)
    assert [content.canonical_hash() for content in first] == [
        content.canonical_hash() for content in second
    ]
    assert {content.memory_type for content in first} == {
        MemoryType.EPISODE,
        MemoryType.TASK_SUMMARY,
        MemoryType.VERIFICATION_SUMMARY,
        MemoryType.CODE_CONTEXT,
    }


@pytest.mark.asyncio
async def test_ingestion_creates_four_idempotent_provenance_backed_memories() -> None:
    package = trajectory()
    repository = InMemoryMemoryRepository()
    service = CodingTrajectoryIngestionService(MemoryService(repository, policy()))
    first = await service.ingest(package, package.canonical_hash())
    second = await service.ingest(package, package.canonical_hash())
    assert first == second
    assert len(first.memory_ids) == len(repository.records) == 4
    assert all(repository.sources[(memory_id, 1)] for memory_id in first.memory_ids)


@pytest.mark.asyncio
async def test_rejected_or_corrupt_trajectory_cannot_enter_memory() -> None:
    repository = InMemoryMemoryRepository()
    service = CodingTrajectoryIngestionService(MemoryService(repository, policy()))
    rejected = trajectory(accepted=False)
    with pytest.raises(MemoryIntegrityError, match="not authoritatively accepted"):
        await service.ingest(rejected, rejected.canonical_hash())
    accepted = trajectory()
    with pytest.raises(MemoryIntegrityError, match="hash mismatch"):
        await service.ingest(accepted, "f" * 64)
    assert not repository.records
