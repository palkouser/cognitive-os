"""Transactional PostgreSQL repository for governed procedural skills."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import and_, insert, select, text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine

from cognitive_os.application.ports.skill_repository import SkillRepositoryPort
from cognitive_os.domain.skills import (
    SkillAccessRecord,
    SkillExecutionResult,
    SkillItem,
    SkillRevision,
    SkillStatistics,
)
from cognitive_os.infrastructure.postgres.engine import postgres_transaction
from cognitive_os.skills.errors import SkillConcurrencyError

from .tables import (
    skill_accesses,
    skill_execution_steps,
    skill_executions,
    skill_items,
    skill_package_artifacts,
    skill_requirements,
    skill_revisions,
    skill_sources,
    skill_statistics,
)


def _item_values(item: SkillItem) -> dict[str, object]:
    identity = item.identity
    return {
        "skill_id": identity.skill_id,
        "canonical_name": identity.canonical_name,
        "scope_type": identity.scope.scope_type.value,
        "scope_id": identity.scope.scope_id,
        "current_revision": item.current_revision,
        "current_status": item.current_status.value,
        "idempotency_key": item.idempotency_key,
        "identity_json": identity.model_dump(mode="json"),
        "created_at": identity.created_at,
    }


def _revision_values(revision: SkillRevision) -> dict[str, object]:
    return {
        "skill_id": revision.skill_id,
        "revision": revision.revision,
        "previous_revision": revision.previous_revision,
        "status": revision.status.value,
        "package_hash": revision.package_hash,
        "content_hash": revision.content_hash,
        "sensitivity": revision.sensitivity.value,
        "domains_json": list(revision.domains),
        "payload_json": revision.model_dump(mode="json"),
        "created_at": revision.created_at,
    }


async def _insert_revision(connection: AsyncConnection, revision: SkillRevision) -> None:
    await connection.execute(insert(skill_revisions).values(**_revision_values(revision)))
    if revision.source_refs:
        await connection.execute(
            insert(skill_sources),
            [
                {
                    "skill_id": revision.skill_id,
                    "revision": revision.revision,
                    "source_order": index,
                    "source_type": source.source_type.value,
                    "source_id": source.source_id,
                    "source_revision": source.source_revision,
                    "content_hash": source.content_hash,
                }
                for index, source in enumerate(revision.source_refs)
            ],
        )
    if revision.requirements:
        await connection.execute(
            insert(skill_requirements),
            [
                {
                    "skill_id": revision.skill_id,
                    "revision": revision.revision,
                    "requirement_id": requirement.requirement_id,
                    "requirement_type": requirement.requirement_type.value,
                    "capability_id": requirement.capability_id,
                    "payload_json": requirement.model_dump(mode="json"),
                }
                for requirement in revision.requirements
            ],
        )
    await connection.execute(
        insert(skill_package_artifacts).values(
            skill_id=revision.skill_id,
            revision=revision.revision,
            artifact_id=revision.package_artifact.artifact_id,
            package_hash=revision.package_hash,
        )
    )


class PostgresSkillRepository(SkillRepositoryPort):
    def __init__(self, engine: AsyncEngine) -> None:
        self._engine = engine

    async def create_skill(self, item: SkillItem, revision: SkillRevision) -> SkillItem:
        try:
            async with postgres_transaction(self._engine) as connection:
                await connection.execute(insert(skill_items).values(**_item_values(item)))
                await _insert_revision(connection, revision)
            return item
        except IntegrityError:
            current = await self.get_current(item.identity.skill_id)
            if current is None or current[0].idempotency_key != item.idempotency_key:
                raise SkillConcurrencyError("skill identity conflict") from None
            return current[0]

    async def append_revision(
        self, revision: SkillRevision, *, expected_revision: int
    ) -> SkillRevision:
        try:
            async with postgres_transaction(self._engine) as connection:
                await _insert_revision(connection, revision)
                advanced = await connection.scalar(
                    text(
                        "SELECT cognitive_os.advance_skill("
                        ":skill_id, :expected_revision, :next_revision, :next_status)"
                    ),
                    {
                        "skill_id": revision.skill_id,
                        "expected_revision": expected_revision,
                        "next_revision": revision.revision,
                        "next_status": revision.status.value,
                    },
                )
                if not advanced:
                    raise SkillConcurrencyError("stale skill revision")
            return revision
        except IntegrityError as error:
            raise SkillConcurrencyError("skill revision conflict") from error

    async def get_current(self, skill_id: UUID) -> tuple[SkillItem, SkillRevision] | None:
        statement = (
            select(skill_items, skill_revisions.c.payload_json)
            .join(
                skill_revisions,
                and_(
                    skill_items.c.skill_id == skill_revisions.c.skill_id,
                    skill_items.c.current_revision == skill_revisions.c.revision,
                ),
            )
            .where(skill_items.c.skill_id == skill_id)
        )
        async with self._engine.connect() as connection:
            row = (await connection.execute(statement)).mappings().one_or_none()
        if row is None:
            return None
        item = SkillItem.model_validate(
            {
                "identity": row["identity_json"],
                "current_revision": row["current_revision"],
                "current_status": row["current_status"],
                "idempotency_key": row["idempotency_key"],
            }
        )
        return item, SkillRevision.model_validate(row["payload_json"])

    async def get_revision(self, skill_id: UUID, revision: int) -> SkillRevision | None:
        statement = select(skill_revisions.c.payload_json).where(
            skill_revisions.c.skill_id == skill_id,
            skill_revisions.c.revision == revision,
        )
        async with self._engine.connect() as connection:
            payload = await connection.scalar(statement)
        return SkillRevision.model_validate(payload) if payload is not None else None

    async def list_revisions(
        self, skill_id: UUID, *, limit: int = 100
    ) -> tuple[SkillRevision, ...]:
        statement = (
            select(skill_revisions.c.payload_json)
            .where(skill_revisions.c.skill_id == skill_id)
            .order_by(skill_revisions.c.revision.desc())
            .limit(limit)
        )
        async with self._engine.connect() as connection:
            values = (await connection.scalars(statement)).all()
        return tuple(SkillRevision.model_validate(value) for value in reversed(values))

    async def query_candidates(
        self, *, limit: int = 200
    ) -> tuple[tuple[SkillItem, SkillRevision], ...]:
        statement = select(skill_items.c.skill_id).order_by(skill_items.c.skill_id).limit(limit)
        async with self._engine.connect() as connection:
            identities = (await connection.scalars(statement)).all()
        rows = [await self.get_current(skill_id) for skill_id in identities]
        return tuple(row for row in rows if row is not None)

    async def record_execution(self, result: SkillExecutionResult) -> SkillExecutionResult:
        values = {
            "execution_id": result.execution_id,
            "skill_id": result.skill_id,
            "revision": result.skill_revision,
            "task_run_id": result.task_run_id,
            "status": result.status.value,
            "result_hash": result.result_hash,
            "payload_json": result.model_dump(mode="json"),
            "started_at": result.started_at,
            "finished_at": result.finished_at,
        }
        try:
            async with postgres_transaction(self._engine) as connection:
                await connection.execute(insert(skill_executions).values(**values))
                if result.step_results:
                    await connection.execute(
                        insert(skill_execution_steps),
                        [
                            {
                                "execution_id": result.execution_id,
                                "step_order": index,
                                "step_id": step.step_id,
                                "status": step.status.value,
                                "payload_json": step.model_dump(mode="json"),
                            }
                            for index, step in enumerate(result.step_results)
                        ],
                    )
            return result
        except IntegrityError:
            existing = await self.get_execution(result.execution_id)
            if existing is None or existing.result_hash != result.result_hash:
                raise SkillConcurrencyError("skill execution identity conflict") from None
            return existing

    async def get_execution(self, execution_id: UUID) -> SkillExecutionResult | None:
        statement = select(skill_executions.c.payload_json).where(
            skill_executions.c.execution_id == execution_id
        )
        async with self._engine.connect() as connection:
            payload = await connection.scalar(statement)
        return SkillExecutionResult.model_validate(payload) if payload is not None else None

    async def list_executions(
        self, skill_id: UUID, revision: int
    ) -> tuple[SkillExecutionResult, ...]:
        statement = (
            select(skill_executions.c.payload_json)
            .where(
                skill_executions.c.skill_id == skill_id,
                skill_executions.c.revision == revision,
            )
            .order_by(skill_executions.c.execution_id)
        )
        async with self._engine.connect() as connection:
            values = (await connection.scalars(statement)).all()
        return tuple(SkillExecutionResult.model_validate(value) for value in values)

    async def record_access(self, records: tuple[SkillAccessRecord, ...]) -> None:
        if not records:
            return
        values = [
            {
                "access_id": item.access_id,
                "skill_id": item.skill_id,
                "revision": item.revision,
                "access_type": item.access_type.value,
                "task_run_id": item.task_run_id,
                "context_request_id": item.context_request_id,
                "scope_type": item.scope.scope_type.value,
                "scope_id": item.scope.scope_id,
                "sensitivity": item.sensitivity.value,
                "accessed_at": item.accessed_at,
                "payload_json": item.model_dump(mode="json"),
            }
            for item in records
        ]
        async with postgres_transaction(self._engine) as connection:
            await connection.execute(
                pg_insert(skill_accesses).values(values).on_conflict_do_nothing()
            )

    async def list_accesses(
        self, skill_id: UUID, revision: int, *, limit: int = 200
    ) -> tuple[SkillAccessRecord, ...]:
        statement = (
            select(skill_accesses.c.payload_json)
            .where(
                skill_accesses.c.skill_id == skill_id,
                skill_accesses.c.revision == revision,
            )
            .order_by(skill_accesses.c.accessed_at, skill_accesses.c.access_id)
            .limit(limit)
        )
        async with self._engine.connect() as connection:
            values = (await connection.scalars(statement)).all()
        return tuple(SkillAccessRecord.model_validate(value) for value in values)

    async def read_statistics(self, skill_id: UUID, revision: int) -> SkillStatistics | None:
        statement = (
            select(skill_statistics.c.payload_json)
            .where(
                skill_statistics.c.skill_id == skill_id,
                skill_statistics.c.revision == revision,
            )
            .order_by(skill_statistics.c.projection_revision.desc())
            .limit(1)
        )
        async with self._engine.connect() as connection:
            payload = await connection.scalar(statement)
        return SkillStatistics.model_validate(payload) if payload is not None else None

    async def write_statistics(self, statistics: SkillStatistics) -> None:
        values = {
            "skill_id": statistics.skill_id,
            "revision": statistics.revision,
            "projection_revision": statistics.projection_revision,
            "projection_hash": statistics.projection_hash,
            "payload_json": statistics.model_dump(mode="json"),
        }
        async with postgres_transaction(self._engine) as connection:
            await connection.execute(
                pg_insert(skill_statistics).values(**values).on_conflict_do_nothing()
            )
