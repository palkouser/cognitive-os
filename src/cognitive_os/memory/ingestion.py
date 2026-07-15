"""Deterministic, evidence-backed Sprint 8 trajectory ingestion."""

from __future__ import annotations

from hashlib import sha256
from uuid import NAMESPACE_URL, UUID, uuid5

from pydantic import Field

from cognitive_os.application.services.memory_service import MemoryService
from cognitive_os.domain.acceptance import AcceptanceDecisionType
from cognitive_os.domain.base import ImmutableContractModel
from cognitive_os.domain.coding import CodingCommandStatus, CodingTrajectoryPackage
from cognitive_os.domain.common import Sha256Hex
from cognitive_os.domain.memory import (
    CodeContextMemoryContent,
    EpisodeMemoryContent,
    MemoryCreator,
    MemoryCreatorType,
    MemoryProvenanceBundle,
    MemoryScope,
    MemoryScopeType,
    MemorySensitivity,
    MemorySourceIdentity,
    MemorySourceRef,
    MemorySourceType,
    MemoryType,
    MemoryWriteRequest,
    TaskSummaryMemoryContent,
    VerificationSummaryMemoryContent,
)

from .errors import MemoryIntegrityError

TrajectoryMemoryContent = (
    EpisodeMemoryContent
    | TaskSummaryMemoryContent
    | VerificationSummaryMemoryContent
    | CodeContextMemoryContent
)


class TrajectoryIngestionManifest(ImmutableContractModel):
    ingestion_id: UUID
    trajectory_hash: Sha256Hex
    task_run_id: UUID
    memory_ids: tuple[UUID, ...] = Field(min_length=1)
    memory_hashes: tuple[Sha256Hex, ...] = Field(min_length=1)


def validate_accepted_trajectory(
    trajectory: CodingTrajectoryPackage, expected_hash: Sha256Hex
) -> tuple[Sha256Hex, UUID]:
    actual_hash = trajectory.canonical_hash()
    if actual_hash != expected_hash:
        raise MemoryIntegrityError("coding trajectory canonical hash mismatch")
    decision = trajectory.acceptance_decision
    if (
        decision is None
        or decision.decision is not AcceptanceDecisionType.ACCEPTED
        or not decision.required_passed
    ):
        raise MemoryIntegrityError("trajectory is not authoritatively accepted")
    if trajectory.final_diff is None:
        raise MemoryIntegrityError("accepted trajectory has no final diff artifact")
    return actual_hash, decision.task_run_id


def _repository_identity(trajectory: CodingTrajectoryPackage) -> str:
    material = (
        trajectory.problem.base_commit
        + trajectory.repository_profile.canonical_hash()
        + trajectory.context_hash
    )
    return sha256(material.encode()).hexdigest()


def _provenance(
    trajectory: CodingTrajectoryPackage, trajectory_hash: str
) -> MemoryProvenanceBundle:
    if trajectory.acceptance_decision is None or trajectory.final_diff is None:
        raise MemoryIntegrityError("trajectory authority references are incomplete")
    trajectory_id = uuid5(NAMESPACE_URL, f"coding-trajectory:{trajectory_hash}")
    decision_hash = sha256(trajectory.acceptance_decision.model_dump_json().encode()).hexdigest()
    sources = (
        MemorySourceRef(
            identity=MemorySourceIdentity(
                source_type=MemorySourceType.ACCEPTANCE_DECISION,
                source_id=trajectory.acceptance_decision.decision_id,
                content_hash=decision_hash,
            ),
            source_hash=decision_hash,
        ),
        MemorySourceRef(
            identity=MemorySourceIdentity(
                source_type=MemorySourceType.ARTIFACT,
                source_id=trajectory.final_diff.artifact.artifact_id,
                content_hash=trajectory.final_diff.artifact.content_hash,
            ),
            source_hash=trajectory.final_diff.artifact.content_hash,
        ),
        MemorySourceRef(
            identity=MemorySourceIdentity(
                source_type=MemorySourceType.CODING_TRAJECTORY,
                source_id=trajectory_id,
                content_hash=trajectory_hash,
            ),
            source_hash=trajectory_hash,
        ),
        MemorySourceRef(
            identity=MemorySourceIdentity(
                source_type=MemorySourceType.TASK_RUN,
                source_id=trajectory.acceptance_decision.task_run_id,
            ),
            source_hash=sha256(
                str(trajectory.acceptance_decision.task_run_id).encode()
            ).hexdigest(),
        ),
    )
    return MemoryProvenanceBundle(
        sources=tuple(sorted(sources, key=lambda source: source.identity.sort_key()))
    )


def project_accepted_trajectory(
    trajectory: CodingTrajectoryPackage, expected_hash: Sha256Hex
) -> tuple[TrajectoryMemoryContent, ...]:
    trajectory_hash, task_run_id = validate_accepted_trajectory(trajectory, expected_hash)
    if trajectory.acceptance_decision is None or trajectory.final_diff is None:
        raise MemoryIntegrityError("trajectory authority references are incomplete")
    repository_identity = _repository_identity(trajectory)
    required_passed = tuple(
        report.command_identity
        for report in trajectory.command_reports
        if report.status is CodingCommandStatus.PASSED
    )
    required_failed = tuple(
        report.command_identity
        for report in trajectory.command_reports
        if report.status is CodingCommandStatus.SUBJECT_FAILED
    )
    verifier_errors = tuple(
        report.command_identity
        for report in trajectory.command_reports
        if report.status
        in {
            CodingCommandStatus.EXECUTION_ERROR,
            CodingCommandStatus.TIMED_OUT,
            CodingCommandStatus.UNAVAILABLE,
        }
    )
    final_manifest = next(
        (
            attempt.application_result.manifest
            for attempt in reversed(trajectory.patch_attempts)
            if attempt.application_result is not None
            and attempt.application_result.manifest is not None
        ),
        None,
    )
    changed_paths = tuple(file.path for file in final_manifest.files) if final_manifest else ()
    return (
        EpisodeMemoryContent(
            task_run_id=task_run_id,
            title=trajectory.problem.issue_description[:1024],
            problem_summary=trajectory.problem.issue_description[:8192],
            repository_identity=repository_identity,
            base_commit=trajectory.problem.base_commit,
            outcome="accepted",
            patch_attempt_count=len(trajectory.patch_attempts),
            repair_count=len(trajectory.repair_decisions),
            verifier_summary=(
                f"{len(required_passed)} passed, {len(required_failed)} subject failures, "
                f"{len(verifier_errors)} verifier errors"
            ),
            artifact_ids=(trajectory.final_diff.artifact.artifact_id,),
            remaining_risks=tuple(risk.message[:2048] for risk in trajectory.risks),
            trajectory_hash=trajectory_hash,
        ),
        TaskSummaryMemoryContent(
            task_run_id=task_run_id,
            goal=trajectory.problem.expected_behavior[:8192],
            constraints=tuple(trajectory.problem.forbidden_paths),
            result="Accepted coding trajectory with authoritative verifier evidence.",
            review_status=trajectory.acceptance_decision.decision.value,
        ),
        VerificationSummaryMemoryContent(
            task_run_id=task_run_id,
            required_passed=required_passed,
            required_failed=required_failed,
            verifier_errors=verifier_errors,
            acceptance_decision_id=trajectory.acceptance_decision.decision_id,
            registry_snapshot_hash=trajectory_hash,
        ),
        CodeContextMemoryContent(
            repository_identity=repository_identity,
            base_commit=trajectory.problem.base_commit,
            repository_profile=(
                f"Python {trajectory.repository_profile.python_version or 'unknown'}; "
                f"pytest={trajectory.repository_profile.has_pytest}; "
                f"ruff={trajectory.repository_profile.has_ruff}; "
                f"mypy={trajectory.repository_profile.has_mypy}"
            ),
            context_hash=trajectory.context_hash,
            changed_paths=changed_paths,
            diff_artifact_id=trajectory.final_diff.artifact.artifact_id,
        ),
    )


class CodingTrajectoryIngestionService:
    def __init__(self, memory_service: MemoryService) -> None:
        self._memory_service = memory_service

    async def ingest(
        self,
        trajectory: CodingTrajectoryPackage,
        expected_hash: Sha256Hex,
        *,
        automatic: bool = False,
        dry_run: bool = False,
    ) -> TrajectoryIngestionManifest:
        trajectory_hash, task_run_id = validate_accepted_trajectory(trajectory, expected_hash)
        contents = project_accepted_trajectory(trajectory, expected_hash)
        provenance = _provenance(trajectory, trajectory_hash)
        repository_identity = _repository_identity(trajectory)
        ingestion_id = uuid5(NAMESPACE_URL, f"memory-ingestion:{trajectory_hash}")
        memory_ids: list[UUID] = []
        memory_hashes: list[str] = []
        for content in contents:
            memory_id = uuid5(
                NAMESPACE_URL,
                f"memory:{trajectory_hash}:{content.memory_type.value}",
            )
            scope = (
                MemoryScope(
                    scope_type=MemoryScopeType.REPOSITORY,
                    scope_id=repository_identity,
                )
                if content.memory_type is MemoryType.CODE_CONTEXT
                else MemoryScope(scope_type=MemoryScopeType.TASK, scope_id=str(task_run_id))
            )
            request = MemoryWriteRequest(
                request_id=uuid5(NAMESPACE_URL, f"request:{memory_id}"),
                idempotency_key=sha256(f"{ingestion_id}:{memory_id}".encode()).hexdigest(),
                memory_id=memory_id,
                memory_type=content.memory_type,
                scope=scope,
                title=content.render_search_text().splitlines()[0][:1024],
                content=content,
                confidence=1.0,
                salience=0.5,
                sensitivity=MemorySensitivity.INTERNAL,
                provenance=provenance,
                actor=MemoryCreator(
                    creator_type=MemoryCreatorType.INGESTION_SERVICE,
                    creator_id="coding-trajectory-ingestion-v1",
                ),
                automatic=automatic,
            )
            _, created = await self._memory_service.create(request, dry_run=dry_run)
            memory_ids.append(memory_id)
            memory_hashes.append(
                request.canonical_hash() if created is None else created[1].content_hash
            )
        return TrajectoryIngestionManifest(
            ingestion_id=ingestion_id,
            trajectory_hash=trajectory_hash,
            task_run_id=task_run_id,
            memory_ids=tuple(memory_ids),
            memory_hashes=tuple(memory_hashes),
        )
