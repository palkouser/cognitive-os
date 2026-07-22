"""Transactional PostgreSQL repository for controlled changes."""

from typing import Any, TypeVar
from uuid import UUID

from pydantic import BaseModel
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncEngine

from cognitive_os.application.ports.changes import ChangeRepositoryPort
from cognitive_os.changes.service import ChangeConflictError
from cognitive_os.domain.changes import (
    ChangeAccessRecord,
    ChangeCandidate,
    ChangeExperiment,
    ChangeExperimentRevision,
    ChangeIsolationManifest,
    ChangeRunManifest,
    EvaluationRun,
    PromotionAssessment,
    PromotionBundle,
    PromotionReceipt,
    PromotionReview,
    RegressionComparison,
    RollbackReceipt,
)
from cognitive_os.domain.experience import HashedExperienceContract
from cognitive_os.infrastructure.postgres.engine import postgres_transaction

from .tables import (
    change_experiment_revisions,
    change_experiments,
    change_promotions,
)

ModelT = TypeVar("ModelT", bound=BaseModel)


class PostgresChangeRepository(ChangeRepositoryPort):
    def __init__(self, engine: AsyncEngine) -> None:
        self._engine = engine

    async def create(
        self, experiment: ChangeExperiment, revision: ChangeExperimentRevision
    ) -> None:
        async with postgres_transaction(self._engine) as connection:
            created = await connection.scalar(
                text(
                    "SELECT cognitive_os.create_change_experiment("
                    "CAST(:experiment AS jsonb), CAST(:revision AS jsonb))"
                ),
                {
                    "experiment": experiment.model_dump_json(),
                    "revision": revision.model_dump_json(),
                },
            )
        if not created:
            raise ChangeConflictError("change experiment creation conflict")

    async def append_revision(
        self, revision: ChangeExperimentRevision, *, expected_revision: int
    ) -> None:
        async with postgres_transaction(self._engine) as connection:
            advanced = await connection.scalar(
                text(
                    "SELECT cognitive_os.append_change_experiment_revision("
                    ":experiment_id, :expected_revision, CAST(:payload AS jsonb))"
                ),
                {
                    "experiment_id": revision.experiment_id,
                    "expected_revision": expected_revision,
                    "payload": revision.model_dump_json(),
                },
            )
        if not advanced:
            raise ChangeConflictError("stale or illegal change experiment revision")

    async def get_exact_revision(
        self, experiment_id: UUID, revision: int
    ) -> ChangeExperimentRevision | None:
        statement = select(change_experiment_revisions.c.payload_json).where(
            change_experiment_revisions.c.experiment_id == experiment_id,
            change_experiment_revisions.c.revision == revision,
        )
        return await self._one(statement, ChangeExperimentRevision)

    async def get_current_revision(self, experiment_id: UUID) -> ChangeExperimentRevision | None:
        statement = (
            select(change_experiment_revisions.c.payload_json)
            .join(
                change_experiments,
                (change_experiments.c.experiment_id == change_experiment_revisions.c.experiment_id)
                & (change_experiments.c.current_revision == change_experiment_revisions.c.revision),
            )
            .where(change_experiments.c.experiment_id == experiment_id)
        )
        return await self._one(statement, ChangeExperimentRevision)

    async def find_by_request_signature(self, signature: str) -> ChangeExperiment | None:
        statement = select(change_experiments.c.payload_json).where(
            change_experiments.c.request_signature == signature
        )
        return await self._one(statement, ChangeExperiment)

    async def record_isolation(self, value: ChangeIsolationManifest) -> None:
        await self._component("isolation", value)

    async def record_candidate(self, value: ChangeCandidate) -> None:
        await self._component("candidate", value)

    async def record_evaluation(self, value: EvaluationRun) -> None:
        await self._component("evaluation", value)

    async def record_comparison(self, value: RegressionComparison) -> None:
        await self._component("comparison", value)

    async def record_assessment(self, value: PromotionAssessment) -> None:
        await self._component("assessment", value)

    async def record_review(self, value: PromotionReview) -> None:
        await self._promotion("review", value)

    async def get_review(self, review_id: UUID) -> PromotionReview | None:
        statement = select(change_promotions.c.payload_json).where(
            change_promotions.c.promotion_record_id == review_id,
            change_promotions.c.record_kind == "review",
        )
        return await self._one(statement, PromotionReview)

    async def record_bundle(self, value: PromotionBundle) -> None:
        await self._promotion("bundle", value)

    async def record_promotion(self, value: PromotionReceipt) -> None:
        await self._promotion("promotion", value)

    async def record_rollback(self, value: RollbackReceipt) -> None:
        await self._component("rollback", value)

    async def record_access(self, value: ChangeAccessRecord) -> None:
        await self._call("record_change_access", value.model_dump_json())

    async def record_manifest(self, value: ChangeRunManifest) -> None:
        await self._component("manifest", value)

    async def list_current(self) -> tuple[ChangeExperimentRevision, ...]:
        statement = (
            select(change_experiment_revisions.c.payload_json)
            .join(
                change_experiments,
                (change_experiments.c.experiment_id == change_experiment_revisions.c.experiment_id)
                & (change_experiments.c.current_revision == change_experiment_revisions.c.revision),
            )
            .order_by(change_experiment_revisions.c.experiment_id)
        )
        async with self._engine.connect() as connection:
            payloads = (await connection.scalars(statement)).all()
        return tuple(ChangeExperimentRevision.model_validate(item) for item in payloads)

    async def _component(self, kind: str, value: HashedExperienceContract) -> None:
        await self._call(
            "record_change_component",
            value.model_dump_json(),
            kind,
        )

    async def _promotion(self, kind: str, value: HashedExperienceContract) -> None:
        await self._call(
            "record_change_promotion",
            value.model_dump_json(),
            kind,
        )

    async def _call(self, function: str, payload: str, kind: str | None = None) -> None:
        sql = (
            f"SELECT cognitive_os.{function}(:kind, CAST(:payload AS jsonb))"
            if kind
            else f"SELECT cognitive_os.{function}(CAST(:payload AS jsonb))"
        )
        parameters = {"payload": payload, **({"kind": kind} if kind else {})}
        async with postgres_transaction(self._engine) as connection:
            recorded = await connection.scalar(text(sql), parameters)
        if not recorded:
            raise ChangeConflictError(f"controlled-change {kind or function} record conflict")

    async def _one(self, statement: Any, model: type[ModelT]) -> ModelT | None:
        async with self._engine.connect() as connection:
            payload = await connection.scalar(statement)
        return model.model_validate(payload) if payload else None
