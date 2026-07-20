"""Application service coordinating compiler persistence."""

from uuid import NAMESPACE_URL, uuid5

from cognitive_os.application.ports.experience_repository import ExperienceRepositoryPort
from cognitive_os.domain.experience import (
    ExperienceAccessRecord,
    ExperienceAccessType,
    ExperienceCompilationRequest,
)
from cognitive_os.events.experience_event_service import ExperienceEventService
from cognitive_os.events.experience_events import (
    ExperienceCandidateCreated,
    ExperienceCompilationCompleted,
    ExperienceCompilationRequested,
    ExperienceSnapshotCreated,
)
from cognitive_os.experience.compiler import ExperienceCompilationResult, ExperienceCompiler


class ExperienceCompilerService:
    def __init__(
        self,
        compiler: ExperienceCompiler,
        repository: ExperienceRepositoryPort,
        events: ExperienceEventService | None = None,
    ) -> None:
        self._compiler = compiler
        self._repository = repository
        self._events = events

    async def compile(self, request: ExperienceCompilationRequest) -> ExperienceCompilationResult:
        existing = await self._repository.get_manifest(request.compilation_id)
        result = self._compiler.compile(request)
        if existing is not None:
            if existing != result.manifest:
                raise ValueError("persisted manifest differs from deterministic recompilation")
            return result
        await self._repository.create_compilation(request)
        if self._events:
            await self._events.append(
                request.compilation_id,
                ExperienceCompilationRequested(
                    compilation_id=request.compilation_id,
                    task_run_id=request.task_run_id,
                    profile_hash=request.compiler_profile_hash,
                    request_hash=request.content_hash,
                    occurred_at=request.created_at,
                ),
                correlation_id=request.task_run_id,
            )
        await self._repository.record_snapshot(request.compilation_id, result.snapshot)
        if self._events:
            await self._events.append(
                request.compilation_id,
                ExperienceSnapshotCreated(
                    compilation_id=request.compilation_id,
                    snapshot_hash=result.snapshot.content_hash,
                    source_count=len(result.snapshot.source_refs),
                    occurred_at=request.created_at,
                ),
                correlation_id=request.task_run_id,
            )
        await self._repository.record_step_assessments(request.compilation_id, result.assessments)
        await self._repository.record_candidates(request.compilation_id, result.candidates)
        if self._events:
            for candidate in result.candidates:
                await self._events.append(
                    request.compilation_id,
                    ExperienceCandidateCreated(
                        compilation_id=request.compilation_id,
                        candidate_id=candidate.candidate_id,
                        candidate_type=candidate.candidate_type,
                        status=candidate.status,
                        candidate_hash=candidate.content_hash,
                        occurred_at=request.created_at,
                    ),
                    correlation_id=request.task_run_id,
                )
        await self._repository.record_decision(result.decision)
        await self._repository.record_manifest(result.manifest)
        accesses = (
            *(
                ExperienceAccessRecord(
                    access_id=uuid5(
                        NAMESPACE_URL,
                        f"experience-access:{request.compilation_id}:source:{index}",
                    ),
                    compilation_id=request.compilation_id,
                    access_type=ExperienceAccessType.SOURCE_RESOLUTION,
                    source_type=source.source_type,
                    source_id=source.source_id,
                    actor_id="experience-compiler",
                    accessed_at=request.created_at,
                )
                for index, source in enumerate(result.snapshot.source_refs)
            ),
            ExperienceAccessRecord(
                access_id=uuid5(
                    NAMESPACE_URL,
                    f"experience-access:{request.compilation_id}:snapshot",
                ),
                compilation_id=request.compilation_id,
                access_type=ExperienceAccessType.SNAPSHOT_READ,
                actor_id="experience-compiler",
                accessed_at=request.created_at,
            ),
            ExperienceAccessRecord(
                access_id=uuid5(
                    NAMESPACE_URL,
                    f"experience-access:{request.compilation_id}:reconstruction",
                ),
                compilation_id=request.compilation_id,
                access_type=ExperienceAccessType.RECONSTRUCTION_READ,
                actor_id="experience-compiler",
                accessed_at=request.created_at,
            ),
        )
        await self._repository.record_access(accesses)
        if self._events:
            await self._events.append(
                request.compilation_id,
                ExperienceCompilationCompleted(
                    compilation_id=request.compilation_id,
                    manifest_hash=result.manifest.content_hash,
                    decision=result.decision.decision,
                    occurred_at=request.created_at,
                ),
                correlation_id=request.task_run_id,
            )
        return result
