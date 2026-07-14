"""Application boundary for verified artifact storage."""

from collections.abc import Sequence
from pathlib import Path
from typing import BinaryIO, Protocol
from uuid import UUID

from cognitive_os.domain.common import ArtifactRef


class ArtifactStorePort(Protocol):
    async def put_bytes(
        self, data: bytes, *, media_type: str, source_event_id: UUID | None = None
    ) -> ArtifactRef: ...

    async def put_file(
        self, path: Path, *, media_type: str, source_event_id: UUID | None = None
    ) -> ArtifactRef: ...

    async def get_bytes(self, artifact_id: UUID) -> bytes: ...

    async def open_read(self, artifact_id: UUID) -> BinaryIO: ...

    async def verify(self, artifact_id: UUID) -> bool: ...

    async def exists(self, artifact_id: UUID) -> bool: ...

    async def find_orphan_blobs(self) -> Sequence[str]: ...
