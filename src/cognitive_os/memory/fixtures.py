"""Deterministic credential-free Memory Plane fixture factory."""

from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

from cognitive_os.domain.acceptance import AcceptanceDecision, AcceptanceDecisionType
from cognitive_os.domain.coding import (
    CodingProblemExtension,
    CodingTrajectoryPackage,
    RepositoryProfile,
    RepositoryProfileStatus,
    UnifiedDiffArtifact,
)
from cognitive_os.domain.common import ArtifactRef

FIXTURE_TIME = datetime(2026, 1, 1, tzinfo=UTC)


def accepted_coding_trajectory_fixture() -> CodingTrajectoryPackage:
    decision = AcceptanceDecision(
        decision_id=UUID("00000000-0000-0000-0000-000000009002"),
        task_run_id=UUID("00000000-0000-0000-0000-000000009001"),
        policy_id=UUID("00000000-0000-0000-0000-000000009003"),
        policy_version="1",
        decision=AcceptanceDecisionType.ACCEPTED,
        criterion_evaluations=(),
        required_passed=True,
        optional_score=1.0,
        reason="Deterministic authoritative fixture acceptance.",
        created_at=FIXTURE_TIME,
    )
    artifact = ArtifactRef(
        artifact_id=UUID("00000000-0000-0000-0000-000000009004"),
        media_type="text/x-diff",
        content_hash="d" * 64,
        size_bytes=128,
        storage_key="memory-fixtures/final.diff",
        created_at=FIXTURE_TIME,
    )
    return CodingTrajectoryPackage(
        problem=CodingProblemExtension(
            repository_path=Path("/prepared/fixture-repository"),
            base_commit="b" * 40,
            issue_description="Repair deterministic fixture parsing.",
            expected_behavior="All bounded parser cases pass.",
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
        provenance={"fixture": "sprint-9-memory"},
    )
