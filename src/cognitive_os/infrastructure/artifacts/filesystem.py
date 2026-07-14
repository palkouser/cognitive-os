"""Atomic SHA-256 content-addressed filesystem storage."""

from __future__ import annotations

import hashlib
import os
import tempfile
from collections.abc import Iterable, Iterator
from contextlib import contextmanager
from pathlib import Path, PurePosixPath
from typing import BinaryIO

from pydantic import Field

from cognitive_os.domain.base import ImmutableContractModel
from cognitive_os.domain.common import Sha256Hex
from cognitive_os.infrastructure.errors import (
    ArtifactIntegrityError,
    ArtifactNotFoundError,
    ArtifactTooLargeError,
)

DEFAULT_MAXIMUM_ARTIFACT_SIZE = 64 * 1024 * 1024


class StoredBlob(ImmutableContractModel):
    content_hash: Sha256Hex
    size_bytes: int = Field(ge=0)
    storage_key: str


class ContentAddressedFilesystem:
    def __init__(
        self,
        root: Path,
        *,
        maximum_size_bytes: int = DEFAULT_MAXIMUM_ARTIFACT_SIZE,
        fsync: bool = True,
    ) -> None:
        if maximum_size_bytes < 1:
            raise ValueError("maximum_size_bytes must be positive")
        self.root = root.resolve()
        self.maximum_size_bytes = maximum_size_bytes
        self.fsync = fsync
        self.root.mkdir(mode=0o750, parents=True, exist_ok=True)
        os.chmod(self.root, 0o750)  # nosec B103

    def put_bytes(self, data: bytes) -> StoredBlob:
        return self._put_chunks((data,))

    def put_file(self, path: Path) -> StoredBlob:
        if path.is_symlink():
            raise ArtifactIntegrityError("artifact source must not be a symlink")
        with path.open("rb") as source:
            return self._put_chunks(iter(lambda: source.read(1024 * 1024), b""))

    def _put_chunks(self, chunks: Iterable[bytes]) -> StoredBlob:
        temporary_directory = self.root / ".tmp"
        temporary_directory.mkdir(mode=0o750, parents=True, exist_ok=True)
        descriptor, temporary_name = tempfile.mkstemp(prefix="artifact-", dir=temporary_directory)
        temporary_path = Path(temporary_name)
        digest = hashlib.sha256()
        size = 0
        try:
            os.fchmod(descriptor, 0o640)
            with os.fdopen(descriptor, "wb") as output:
                for chunk in chunks:
                    size += len(chunk)
                    if size > self.maximum_size_bytes:
                        raise ArtifactTooLargeError(self.maximum_size_bytes)
                    digest.update(chunk)
                    output.write(chunk)
                output.flush()
                if self.fsync:
                    os.fsync(output.fileno())
            content_hash = digest.hexdigest()
            storage_key = f"sha256/{content_hash[:2]}/{content_hash}"
            destination = self._resolve_storage_key(storage_key)
            destination.parent.mkdir(mode=0o750, parents=True, exist_ok=True)
            if destination.exists():
                if destination.is_symlink() or destination.stat().st_size != size:
                    raise ArtifactIntegrityError("existing content-addressed blob is inconsistent")
                temporary_path.unlink()
            else:
                os.replace(temporary_path, destination)
                os.chmod(destination, 0o640)
            return StoredBlob(content_hash=content_hash, size_bytes=size, storage_key=storage_key)
        except BaseException:
            temporary_path.unlink(missing_ok=True)
            raise

    def get_bytes(self, storage_key: str, expected_hash: str, expected_size: int) -> bytes:
        with self.open_read(storage_key, expected_hash, expected_size) as source:
            return source.read()

    def open_verified(self, storage_key: str, expected_hash: str, expected_size: int) -> BinaryIO:
        path = self._resolve_storage_key(storage_key)
        if not path.exists() or path.is_symlink():
            raise ArtifactNotFoundError(f"artifact blob not found: {storage_key}")
        self.verify_blob(storage_key, expected_hash, expected_size)
        return path.open("rb")

    @contextmanager
    def open_read(
        self, storage_key: str, expected_hash: str, expected_size: int
    ) -> Iterator[BinaryIO]:
        with self.open_verified(storage_key, expected_hash, expected_size) as source:
            yield source

    def exists(self, storage_key: str) -> bool:
        path = self._resolve_storage_key(storage_key)
        return path.is_file() and not path.is_symlink()

    def verify_blob(self, storage_key: str, expected_hash: str, expected_size: int) -> bool:
        path = self._resolve_storage_key(storage_key)
        if not path.exists() or path.is_symlink():
            raise ArtifactNotFoundError(f"artifact blob not found: {storage_key}")
        digest = hashlib.sha256()
        size = 0
        with path.open("rb") as source:
            for chunk in iter(lambda: source.read(1024 * 1024), b""):
                size += len(chunk)
                digest.update(chunk)
        if size != expected_size or digest.hexdigest() != expected_hash:
            raise ArtifactIntegrityError(f"artifact blob failed verification: {storage_key}")
        return True

    def find_orphan_files(self, known_storage_keys: set[str]) -> tuple[str, ...]:
        blob_root = self.root / "sha256"
        if not blob_root.exists():
            return ()
        found = {
            path.relative_to(self.root).as_posix()
            for path in blob_root.glob("[0-9a-f][0-9a-f]/*")
            if path.is_file() and not path.is_symlink()
        }
        return tuple(sorted(found - known_storage_keys))

    def _resolve_storage_key(self, storage_key: str) -> Path:
        logical = PurePosixPath(storage_key)
        if logical.is_absolute() or ".." in logical.parts:
            raise ArtifactIntegrityError("storage key must be a safe relative path")
        candidate = self.root.joinpath(*logical.parts)
        resolved_parent = candidate.parent.resolve()
        if not resolved_parent.is_relative_to(self.root):
            raise ArtifactIntegrityError("storage key escapes the artifact root")
        return candidate
