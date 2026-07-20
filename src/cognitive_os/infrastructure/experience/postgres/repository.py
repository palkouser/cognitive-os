"""Transactional PostgreSQL repository for Experience Compiler metadata."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncEngine

from cognitive_os.application.ports.experience_repository import ExperienceRepositoryPort
from cognitive_os.domain.experience import (
    CandidateRevision,
    CompilationDecision,
    CompilationDecisionType,
    CompilationManifest,
    ExperienceAccessRecord,
    ExperienceCandidate,
    ExperienceCompilationRequest,
    StepAssessment,
    TrajectorySnapshot,
)
from cognitive_os.experience.errors import ExperienceConflictError
from cognitive_os.infrastructure.postgres.engine import postgres_transaction

from .tables import (
    experience_accesses,
    experience_candidate_revisions,
    experience_candidate_sources,
    experience_candidates,
    experience_compilations,
    experience_decisions,
    experience_snapshots,
    experience_sources,
    experience_step_assessments,
)


class PostgresExperienceRepository(ExperienceRepositoryPort):
    def __init__(self, engine: AsyncEngine) -> None:
        self._engine = engine

    async def create_compilation(self, request: ExperienceCompilationRequest) -> None:
        values = {
            "compilation_id": request.compilation_id,
            "task_run_id": request.task_run_id,
            "idempotency_key": request.idempotency_key,
            "profile_id": request.compiler_profile_id,
            "profile_version": request.compiler_profile_version,
            "profile_hash": request.compiler_profile_hash,
            "current_status": "requested",
            "request_hash": request.content_hash,
            "request_json": request.model_dump(mode="json"),
            "created_at": request.created_at,
        }
        async with postgres_transaction(self._engine) as connection:
            await connection.execute(
                pg_insert(experience_compilations).values(**values).on_conflict_do_nothing()
            )
        statement = select(
            experience_compilations.c.compilation_id,
            experience_compilations.c.request_hash,
        ).where(experience_compilations.c.idempotency_key == request.idempotency_key)
        async with self._engine.connect() as connection:
            row = (await connection.execute(statement)).one()
        if row.compilation_id != request.compilation_id or row.request_hash != request.content_hash:
            raise ExperienceConflictError("experience compilation idempotency conflict")

    async def record_snapshot(self, compilation_id: UUID, snapshot: TrajectorySnapshot) -> None:
        if snapshot.task_run_id is None:
            raise ExperienceConflictError("snapshot task identity is absent")
        async with postgres_transaction(self._engine) as connection:
            await connection.execute(
                pg_insert(experience_snapshots)
                .values(
                    compilation_id=compilation_id,
                    task_run_id=snapshot.task_run_id,
                    snapshot_hash=snapshot.content_hash,
                    terminal_state=snapshot.terminal_state,
                    completeness=snapshot.completeness.value,
                    payload_json=snapshot.model_dump(mode="json"),
                    created_at=snapshot.snapshot_created_at,
                )
                .on_conflict_do_nothing()
            )
            if snapshot.source_refs:
                await connection.execute(
                    pg_insert(experience_sources)
                    .values(
                        [
                            {
                                "compilation_id": compilation_id,
                                "source_order": index,
                                "source_type": item.source_type.value,
                                "source_id": item.source_id,
                                "source_revision": item.source_revision,
                                "source_hash": item.source_content_hash,
                                "scope": item.scope,
                                "sensitivity": item.sensitivity.value,
                                "required": item.required,
                                "payload_json": item.model_dump(mode="json"),
                            }
                            for index, item in enumerate(snapshot.source_refs)
                        ]
                    )
                    .on_conflict_do_nothing()
                )

    async def record_step_assessments(
        self, compilation_id: UUID, assessments: tuple[StepAssessment, ...]
    ) -> None:
        if not assessments:
            return
        async with postgres_transaction(self._engine) as connection:
            await connection.execute(
                pg_insert(experience_step_assessments)
                .values(
                    [
                        {
                            "compilation_id": compilation_id,
                            "sequence": item.sequence,
                            "step_id": item.step_id,
                            "assessment_hash": item.content_hash,
                            "confidence": item.confidence,
                            "payload_json": item.model_dump(mode="json"),
                        }
                        for item in assessments
                    ]
                )
                .on_conflict_do_nothing()
            )

    async def record_candidates(
        self, compilation_id: UUID, candidates: tuple[ExperienceCandidate, ...]
    ) -> None:
        if not candidates:
            return
        async with postgres_transaction(self._engine) as connection:
            for candidate in candidates:
                await connection.execute(
                    pg_insert(experience_candidates)
                    .values(
                        candidate_id=candidate.candidate_id,
                        compilation_id=compilation_id,
                        candidate_type=candidate.candidate_type.value,
                        current_revision=candidate.candidate_revision,
                        current_status=candidate.status.value,
                        target_subsystem=candidate.target_subsystem,
                        target_schema_version=candidate.target_schema_version,
                        candidate_hash=candidate.content_hash,
                        payload_json=candidate.model_dump(mode="json"),
                        created_at=candidate.created_at,
                    )
                    .on_conflict_do_nothing()
                )
                await connection.execute(
                    pg_insert(experience_candidate_revisions)
                    .values(
                        candidate_id=candidate.candidate_id,
                        revision=candidate.candidate_revision,
                        previous_status=None,
                        status=candidate.status.value,
                        actor_id=candidate.created_by,
                        reason="compiler candidate creation",
                        revision_hash=candidate.content_hash,
                        payload_json={
                            "candidate_id": str(candidate.candidate_id),
                            "revision": candidate.candidate_revision,
                            "status": candidate.status.value,
                            "candidate_hash": candidate.content_hash,
                        },
                        created_at=candidate.created_at,
                    )
                    .on_conflict_do_nothing()
                )
                if candidate.source_refs:
                    await connection.execute(
                        pg_insert(experience_candidate_sources)
                        .values(
                            [
                                {
                                    "candidate_id": candidate.candidate_id,
                                    "candidate_revision": candidate.candidate_revision,
                                    "source_order": index,
                                    "compilation_id": compilation_id,
                                    "source_type": item.source_type.value,
                                    "source_id": item.source_id,
                                    "source_revision": item.source_revision,
                                    "source_hash": item.source_content_hash,
                                }
                                for index, item in enumerate(candidate.source_refs)
                            ]
                        )
                        .on_conflict_do_nothing()
                    )

    async def record_decision(self, decision: CompilationDecision) -> None:
        async with postgres_transaction(self._engine) as connection:
            await connection.execute(
                pg_insert(experience_decisions)
                .values(
                    compilation_id=decision.compilation_id,
                    decision=decision.decision.value,
                    decision_hash=decision.content_hash,
                    verifier_bundle_id=decision.verifier_bundle_id,
                    verifier_bundle_hash=decision.verifier_bundle_hash,
                    payload_json=decision.model_dump(mode="json"),
                    created_at=decision.decided_at,
                )
                .on_conflict_do_nothing()
            )

    async def append_candidate_revision(
        self, revision: CandidateRevision, *, expected_revision: int
    ) -> None:
        async with postgres_transaction(self._engine) as connection:
            await connection.execute(
                pg_insert(experience_candidate_revisions).values(
                    candidate_id=revision.candidate_id,
                    revision=revision.revision,
                    previous_status=revision.previous_status.value,
                    status=revision.status.value,
                    actor_id=revision.actor_id,
                    reason=revision.reason,
                    revision_hash=revision.content_hash,
                    payload_json=revision.model_dump(mode="json"),
                    created_at=revision.created_at,
                )
            )
            advanced = await connection.scalar(
                text(
                    "SELECT cognitive_os.advance_experience_candidate("
                    ":candidate_id, :expected_revision, :expected_status, "
                    ":next_revision, :next_status)"
                ),
                {
                    "candidate_id": revision.candidate_id,
                    "expected_revision": expected_revision,
                    "expected_status": revision.previous_status.value,
                    "next_revision": revision.revision,
                    "next_status": revision.status.value,
                },
            )
            if not advanced:
                raise ExperienceConflictError("stale candidate status revision")

    async def record_manifest(self, manifest: CompilationManifest) -> None:
        status = (
            "completed"
            if manifest.compilation_decision
            in {
                CompilationDecisionType.COMPLETED,
                CompilationDecisionType.COMPLETED_WITH_WARNINGS,
            }
            else "cancelled"
            if manifest.compilation_decision is CompilationDecisionType.CANCELLED
            else "failed"
        )
        async with postgres_transaction(self._engine) as connection:
            current = await connection.scalar(
                select(experience_compilations.c.manifest_hash).where(
                    experience_compilations.c.compilation_id == manifest.compilation_id
                )
            )
            if current == manifest.content_hash:
                return
            finalized = await connection.scalar(
                text(
                    "SELECT cognitive_os.finalize_experience_compilation("
                    ":compilation_id, 'requested', :status, :manifest_hash, "
                    "CAST(:manifest AS jsonb))"
                ),
                {
                    "compilation_id": manifest.compilation_id,
                    "status": status,
                    "manifest_hash": manifest.content_hash,
                    "manifest": manifest.model_dump_json(),
                },
            )
            if not finalized:
                current = await connection.scalar(
                    select(experience_compilations.c.manifest_hash).where(
                        experience_compilations.c.compilation_id == manifest.compilation_id
                    )
                )
                if current != manifest.content_hash:
                    raise ExperienceConflictError("stale compilation finalization")

    async def get_manifest(self, compilation_id: UUID) -> CompilationManifest | None:
        statement = select(experience_compilations.c.manifest_json).where(
            experience_compilations.c.compilation_id == compilation_id
        )
        async with self._engine.connect() as connection:
            payload = await connection.scalar(statement)
        return CompilationManifest.model_validate(payload) if payload is not None else None

    async def list_candidates(
        self, compilation_id: UUID, *, limit: int = 256
    ) -> tuple[ExperienceCandidate, ...]:
        statement = (
            select(experience_candidates.c.payload_json)
            .where(experience_candidates.c.compilation_id == compilation_id)
            .order_by(experience_candidates.c.candidate_type, experience_candidates.c.candidate_id)
            .limit(limit)
        )
        async with self._engine.connect() as connection:
            payloads = (await connection.scalars(statement)).all()
        return tuple(ExperienceCandidate.model_validate(item) for item in payloads)

    async def record_access(self, records: tuple[ExperienceAccessRecord, ...]) -> None:
        if not records:
            return
        async with postgres_transaction(self._engine) as connection:
            await connection.execute(
                pg_insert(experience_accesses)
                .values(
                    [
                        {
                            "access_id": item.access_id,
                            "compilation_id": item.compilation_id,
                            "access_type": item.access_type.value,
                            "source_type": item.source_type.value if item.source_type else None,
                            "source_id": item.source_id,
                            "candidate_id": item.candidate_id,
                            "actor_id": item.actor_id,
                            "access_hash": item.content_hash,
                            "accessed_at": item.accessed_at,
                        }
                        for item in records
                    ]
                )
                .on_conflict_do_nothing()
            )
