"""Persistence-neutral Experience Compiler repository boundary."""

from typing import Protocol
from uuid import UUID

from cognitive_os.domain.experience import (
    CandidateRevision,
    CompilationDecision,
    CompilationManifest,
    ExperienceAccessRecord,
    ExperienceCandidate,
    ExperienceCompilationRequest,
    StepAssessment,
    TrajectorySnapshot,
)


class ExperienceRepositoryPort(Protocol):
    async def create_compilation(self, request: ExperienceCompilationRequest) -> None: ...
    async def record_snapshot(self, compilation_id: UUID, snapshot: TrajectorySnapshot) -> None: ...
    async def record_step_assessments(
        self, compilation_id: UUID, assessments: tuple[StepAssessment, ...]
    ) -> None: ...
    async def record_candidates(
        self, compilation_id: UUID, candidates: tuple[ExperienceCandidate, ...]
    ) -> None: ...
    async def append_candidate_revision(
        self, revision: CandidateRevision, *, expected_revision: int
    ) -> None: ...
    async def record_decision(self, decision: CompilationDecision) -> None: ...
    async def record_manifest(self, manifest: CompilationManifest) -> None: ...
    async def get_manifest(self, compilation_id: UUID) -> CompilationManifest | None: ...
    async def list_candidates(
        self, compilation_id: UUID, *, limit: int = 256
    ) -> tuple[ExperienceCandidate, ...]: ...
    async def record_access(self, records: tuple[ExperienceAccessRecord, ...]) -> None: ...
