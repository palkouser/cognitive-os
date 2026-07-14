"""PostgreSQL artifact and blob metadata repository."""

from __future__ import annotations

from uuid import UUID

from pydantic import Field
from sqlalchemy import insert, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncEngine

from cognitive_os.domain.base import ImmutableContractModel
from cognitive_os.domain.common import ArtifactRef, Sha256Hex, UtcDatetime
from cognitive_os.infrastructure.errors import ArtifactMetadataError, ArtifactNotFoundError

from .engine import postgres_transaction
from .tables import artifact_blobs, artifacts


class BlobMetadata(ImmutableContractModel):
    content_hash: Sha256Hex
    size_bytes: int = Field(ge=0)
    storage_key: str
    created_at: UtcDatetime


class PostgresArtifactRepository:
    def __init__(self, engine: AsyncEngine) -> None:
        self._engine = engine

    async def create_artifact(
        self,
        *,
        artifact_id: UUID,
        content_hash: str,
        size_bytes: int,
        storage_key: str,
        media_type: str,
        source_event_id: UUID | None,
    ) -> ArtifactRef:
        try:
            async with postgres_transaction(self._engine) as connection:
                blob_result = await connection.execute(
                    pg_insert(artifact_blobs)
                    .values(
                        content_hash=content_hash,
                        size_bytes=size_bytes,
                        storage_key=storage_key,
                    )
                    .on_conflict_do_nothing(index_elements=[artifact_blobs.c.content_hash])
                    .returning(artifact_blobs.c.created_at)
                )
                blob_created_at = blob_result.scalar_one_or_none()
                if blob_created_at is None:
                    existing = (
                        (
                            await connection.execute(
                                select(artifact_blobs).where(
                                    artifact_blobs.c.content_hash == content_hash
                                )
                            )
                        )
                        .mappings()
                        .one()
                    )
                    size_differs = existing["size_bytes"] != size_bytes
                    key_differs = existing["storage_key"] != storage_key
                    if size_differs or key_differs:
                        raise ArtifactMetadataError("existing blob metadata is inconsistent")
                artifact_row = (
                    await connection.execute(
                        insert(artifacts)
                        .values(
                            artifact_id=artifact_id,
                            content_hash=content_hash,
                            media_type=media_type,
                            source_event_id=source_event_id,
                        )
                        .returning(artifacts.c.created_at)
                    )
                ).one()
            return ArtifactRef(
                artifact_id=artifact_id,
                media_type=media_type,
                content_hash=content_hash,
                size_bytes=size_bytes,
                storage_key=storage_key,
                created_at=artifact_row.created_at,
            )
        except ArtifactMetadataError:
            raise
        except (IntegrityError, SQLAlchemyError) as error:
            raise ArtifactMetadataError("artifact metadata insertion failed") from error

    async def get_artifact(self, artifact_id: UUID) -> ArtifactRef | None:
        statement = (
            select(
                artifacts.c.artifact_id,
                artifacts.c.media_type,
                artifacts.c.created_at,
                artifact_blobs.c.content_hash,
                artifact_blobs.c.size_bytes,
                artifact_blobs.c.storage_key,
            )
            .join(artifact_blobs, artifacts.c.content_hash == artifact_blobs.c.content_hash)
            .where(artifacts.c.artifact_id == artifact_id)
        )
        async with self._engine.connect() as connection:
            row = (await connection.execute(statement)).mappings().one_or_none()
        if row is None:
            return None
        return ArtifactRef.model_validate(dict(row))

    async def get_blob_metadata(self, content_hash: str) -> BlobMetadata | None:
        async with self._engine.connect() as connection:
            row = (
                (
                    await connection.execute(
                        select(artifact_blobs).where(artifact_blobs.c.content_hash == content_hash)
                    )
                )
                .mappings()
                .one_or_none()
            )
        return BlobMetadata.model_validate(dict(row)) if row is not None else None

    async def list_artifacts_for_event(self, event_id: UUID) -> tuple[ArtifactRef, ...]:
        statement = (
            select(
                artifacts.c.artifact_id,
                artifacts.c.media_type,
                artifacts.c.created_at,
                artifact_blobs.c.content_hash,
                artifact_blobs.c.size_bytes,
                artifact_blobs.c.storage_key,
            )
            .join(artifact_blobs, artifacts.c.content_hash == artifact_blobs.c.content_hash)
            .where(artifacts.c.source_event_id == event_id)
            .order_by(artifacts.c.created_at, artifacts.c.artifact_id)
        )
        async with self._engine.connect() as connection:
            rows = (await connection.execute(statement)).mappings().all()
        return tuple(ArtifactRef.model_validate(dict(row)) for row in rows)

    async def list_blob_storage_keys(self) -> set[str]:
        async with self._engine.connect() as connection:
            result = await connection.execute(select(artifact_blobs.c.storage_key))
            values = result.scalars().all()
        return set(values)

    async def require_artifact(self, artifact_id: UUID) -> ArtifactRef:
        artifact = await self.get_artifact(artifact_id)
        if artifact is None:
            raise ArtifactNotFoundError(f"artifact not found: {artifact_id}")
        return artifact
