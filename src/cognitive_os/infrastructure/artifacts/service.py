"""Artifact service coordinating filesystem bytes and PostgreSQL metadata."""

from __future__ import annotations

from pathlib import Path
from typing import BinaryIO
from uuid import UUID

from cognitive_os.domain.common import ArtifactRef
from cognitive_os.domain.identifiers import new_id
from cognitive_os.telemetry.base import TelemetryPort
from cognitive_os.telemetry.best_effort import BestEffortTelemetry
from cognitive_os.telemetry.noop import NoOpTelemetry

from ..postgres.artifact_repository import PostgresArtifactRepository
from .filesystem import ContentAddressedFilesystem, StoredBlob


class ArtifactService:
    def __init__(
        self,
        filesystem: ContentAddressedFilesystem,
        repository: PostgresArtifactRepository,
        telemetry: TelemetryPort | None = None,
    ) -> None:
        self._filesystem = filesystem
        self._repository = repository
        self._telemetry = BestEffortTelemetry(telemetry or NoOpTelemetry())

    async def put_bytes(
        self, data: bytes, *, media_type: str, source_event_id: UUID | None = None
    ) -> ArtifactRef:
        with self._telemetry.start_span("cognitive_os.artifact_store.put"):
            return await self._persist(
                self._filesystem.put_bytes(data), media_type, source_event_id
            )

    async def put_file(
        self, path: Path, *, media_type: str, source_event_id: UUID | None = None
    ) -> ArtifactRef:
        with self._telemetry.start_span("cognitive_os.artifact_store.put"):
            return await self._persist(self._filesystem.put_file(path), media_type, source_event_id)

    async def _persist(
        self, blob: StoredBlob, media_type: str, source_event_id: UUID | None
    ) -> ArtifactRef:
        artifact = await self._repository.create_artifact(
            artifact_id=new_id(),
            content_hash=blob.content_hash,
            size_bytes=blob.size_bytes,
            storage_key=blob.storage_key,
            media_type=media_type,
            source_event_id=source_event_id,
        )
        self._telemetry.set_attribute("cogos.artifact_id", str(artifact.artifact_id))
        self._telemetry.set_attribute("cogos.artifact_size_bytes", artifact.size_bytes)
        return artifact

    async def get_bytes(self, artifact_id: UUID) -> bytes:
        with self._telemetry.start_span("cognitive_os.artifact_store.get"):
            artifact = await self._repository.require_artifact(artifact_id)
            return self._filesystem.get_bytes(
                artifact.storage_key, artifact.content_hash, artifact.size_bytes
            )

    async def open_read(self, artifact_id: UUID) -> BinaryIO:
        artifact = await self._repository.require_artifact(artifact_id)
        return self._filesystem.open_verified(
            artifact.storage_key, artifact.content_hash, artifact.size_bytes
        )

    async def verify(self, artifact_id: UUID) -> bool:
        artifact = await self._repository.require_artifact(artifact_id)
        return self._filesystem.verify_blob(
            artifact.storage_key, artifact.content_hash, artifact.size_bytes
        )

    async def exists(self, artifact_id: UUID) -> bool:
        artifact = await self._repository.get_artifact(artifact_id)
        return artifact is not None and self._filesystem.exists(artifact.storage_key)

    async def find_orphan_blobs(self) -> tuple[str, ...]:
        known = await self._repository.list_blob_storage_keys()
        return self._filesystem.find_orphan_files(known)
