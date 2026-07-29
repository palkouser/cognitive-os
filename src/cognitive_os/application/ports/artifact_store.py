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

    #: Metadata only, never bytes; `None` when the artifact is unknown. On the port because a
    #: caller that only needs to check identity and hash should not have to load the content
    #: to do it — and because a service typed against the concrete `ArtifactService` cannot be
    #: given a substitute in a test that has no PostgreSQL.
    async def describe(self, artifact_id: UUID) -> ArtifactRef | None: ...

    async def exists(self, artifact_id: UUID) -> bool: ...

    async def find_orphan_blobs(self) -> Sequence[str]: ...
