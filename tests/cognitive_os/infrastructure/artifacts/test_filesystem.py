from pathlib import Path

import pytest

from cognitive_os.infrastructure.artifacts.filesystem import ContentAddressedFilesystem
from cognitive_os.infrastructure.errors import (
    ArtifactIntegrityError,
    ArtifactNotFoundError,
    ArtifactTooLargeError,
)


def test_write_read_deduplicate_and_permissions(tmp_path: Path) -> None:
    store = ContentAddressedFilesystem(tmp_path / "artifacts", fsync=False)
    first = store.put_bytes(b"hello")
    second = store.put_bytes(b"hello")
    assert first == second
    assert store.get_bytes(first.storage_key, first.content_hash, 5) == b"hello"
    assert (store.root / first.storage_key).stat().st_mode & 0o777 == 0o640


def test_put_file_and_orphan_detection(tmp_path: Path) -> None:
    source = tmp_path / "source.txt"
    source.write_bytes(b"artifact")
    store = ContentAddressedFilesystem(tmp_path / "artifacts", fsync=False)
    blob = store.put_file(source)
    assert store.find_orphan_files(set()) == (blob.storage_key,)
    assert store.find_orphan_files({blob.storage_key}) == ()


def test_size_limit_and_temporary_cleanup(tmp_path: Path) -> None:
    store = ContentAddressedFilesystem(tmp_path / "artifacts", maximum_size_bytes=3, fsync=False)
    with pytest.raises(ArtifactTooLargeError):
        store.put_bytes(b"four")
    assert not tuple((store.root / ".tmp").iterdir())


def test_corruption_missing_and_traversal_fail(tmp_path: Path) -> None:
    store = ContentAddressedFilesystem(tmp_path / "artifacts", fsync=False)
    blob = store.put_bytes(b"valid")
    (store.root / blob.storage_key).write_bytes(b"bad")
    with pytest.raises(ArtifactIntegrityError):
        store.verify_blob(blob.storage_key, blob.content_hash, blob.size_bytes)
    with pytest.raises(ArtifactNotFoundError):
        store.get_bytes("sha256/aa/" + "a" * 64, "a" * 64, 1)
    with pytest.raises(ArtifactIntegrityError):
        store.exists("../escape")


def test_symlink_source_is_rejected(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.write_bytes(b"data")
    link = tmp_path / "link"
    link.symlink_to(source)
    store = ContentAddressedFilesystem(tmp_path / "artifacts", fsync=False)
    with pytest.raises(ArtifactIntegrityError):
        store.put_file(link)
