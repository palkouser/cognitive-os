"""Dependency-light append-only Experience Compiler repository."""

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

from .errors import ExperienceConflictError


class InMemoryExperienceRepository:
    """Deterministic repository used by credential-free tests and benchmarks."""

    def __init__(self) -> None:
        self.requests: dict[UUID, ExperienceCompilationRequest] = {}
        self.idempotency: dict[str, UUID] = {}
        self.snapshots: dict[UUID, TrajectorySnapshot] = {}
        self.assessments: dict[UUID, tuple[StepAssessment, ...]] = {}
        self.candidates: dict[UUID, tuple[ExperienceCandidate, ...]] = {}
        self.candidate_revisions: dict[UUID, tuple[CandidateRevision, ...]] = {}
        self.decisions: dict[UUID, CompilationDecision] = {}
        self.manifests: dict[UUID, CompilationManifest] = {}
        self.accesses: list[ExperienceAccessRecord] = []

    async def create_compilation(self, request: ExperienceCompilationRequest) -> None:
        existing = self.idempotency.get(request.idempotency_key)
        if existing is not None and existing != request.compilation_id:
            raise ExperienceConflictError("idempotency key belongs to another compilation")
        current = self.requests.get(request.compilation_id)
        if current is not None and current != request:
            raise ExperienceConflictError("compilation identity changed")
        self.requests[request.compilation_id] = request
        self.idempotency[request.idempotency_key] = request.compilation_id

    async def record_snapshot(self, compilation_id: UUID, snapshot: TrajectorySnapshot) -> None:
        existing = self.snapshots.get(compilation_id)
        if existing is not None and existing != snapshot:
            raise ExperienceConflictError("immutable trajectory snapshot changed")
        self.snapshots[compilation_id] = snapshot

    async def record_step_assessments(
        self, compilation_id: UUID, assessments: tuple[StepAssessment, ...]
    ) -> None:
        if compilation_id in self.assessments:
            raise ExperienceConflictError("step assessments are append-only")
        self.assessments[compilation_id] = assessments

    async def record_candidates(
        self, compilation_id: UUID, candidates: tuple[ExperienceCandidate, ...]
    ) -> None:
        if compilation_id in self.candidates:
            raise ExperienceConflictError("candidate revisions are append-only")
        self.candidates[compilation_id] = candidates

    async def append_candidate_revision(
        self, revision: CandidateRevision, *, expected_revision: int
    ) -> None:
        history = self.candidate_revisions.get(revision.candidate_id, ())
        current = history[-1].revision if history else 1
        if current != expected_revision or revision.revision != expected_revision + 1:
            raise ExperienceConflictError("stale candidate status revision")
        self.candidate_revisions[revision.candidate_id] = (*history, revision)

    async def record_decision(self, decision: CompilationDecision) -> None:
        if decision.compilation_id in self.decisions:
            raise ExperienceConflictError("compilation decision is immutable")
        self.decisions[decision.compilation_id] = decision

    async def record_manifest(self, manifest: CompilationManifest) -> None:
        existing = self.manifests.get(manifest.compilation_id)
        if existing is not None and existing != manifest:
            raise ExperienceConflictError("compilation manifest is immutable")
        self.manifests[manifest.compilation_id] = manifest

    async def get_manifest(self, compilation_id: UUID) -> CompilationManifest | None:
        return self.manifests.get(compilation_id)

    async def list_candidates(
        self, compilation_id: UUID, *, limit: int = 256
    ) -> tuple[ExperienceCandidate, ...]:
        return self.candidates.get(compilation_id, ())[:limit]

    async def record_access(self, records: tuple[ExperienceAccessRecord, ...]) -> None:
        known = {item.access_id for item in self.accesses}
        if any(item.access_id in known for item in records):
            raise ExperienceConflictError("duplicate append-only access record")
        self.accesses.extend(records)
