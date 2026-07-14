from pathlib import Path

import pytest

from cognitive_os.infrastructure.artifacts.filesystem import ContentAddressedFilesystem
from cognitive_os.infrastructure.artifacts.service import ArtifactService
from cognitive_os.infrastructure.errors import ArtifactIntegrityError, ArtifactNotFoundError
from cognitive_os.infrastructure.postgres.artifact_repository import PostgresArtifactRepository


@pytest.mark.asyncio
async def test_artifact_metadata_deduplication_and_orphans(engines, tmp_path: Path) -> None:
    app, _admin = engines
    filesystem = ContentAddressedFilesystem(tmp_path / "artifacts", fsync=False)
    service = ArtifactService(filesystem, PostgresArtifactRepository(app))
    first = await service.put_bytes(b"same", media_type="text/plain")
    second = await service.put_bytes(b"same", media_type="text/plain")
    assert first.artifact_id != second.artifact_id
    assert first.content_hash == second.content_hash
    assert await service.get_bytes(first.artifact_id) == b"same"
    assert await service.verify(second.artifact_id)
    assert await service.find_orphan_blobs() == ()
    orphan = filesystem.put_bytes(b"orphan")
    assert await service.find_orphan_blobs() == (orphan.storage_key,)


@pytest.mark.asyncio
async def test_artifact_missing_and_corruption_are_explicit(engines, tmp_path: Path) -> None:
    app, _admin = engines
    filesystem = ContentAddressedFilesystem(tmp_path / "artifacts", fsync=False)
    service = ArtifactService(filesystem, PostgresArtifactRepository(app))
    artifact = await service.put_bytes(b"valid", media_type="application/octet-stream")
    (filesystem.root / artifact.storage_key).write_bytes(b"bad")
    with pytest.raises(ArtifactIntegrityError):
        await service.get_bytes(artifact.artifact_id)
    (filesystem.root / artifact.storage_key).unlink()
    with pytest.raises(ArtifactNotFoundError):
        await service.get_bytes(artifact.artifact_id)
