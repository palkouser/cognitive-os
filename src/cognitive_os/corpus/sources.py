"""Bounded local source inspection that never executes source content."""

from __future__ import annotations

import io
import mimetypes
import stat
import tarfile
import unicodedata
import zipfile
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path, PurePosixPath, PureWindowsPath

from cognitive_os.config.corpus_config import CorpusConfiguration
from cognitive_os.domain.corpus import (
    CorpusSourceType,
    SourceFileEntry,
    SourceInspectionReport,
)
from cognitive_os.domain.experience import ExperienceCandidate

from .errors import CorpusSourceError


@dataclass(frozen=True)
class SourceMaterial:
    relative_path: str
    data: bytes
    media_type: str
    encoding: str | None = None
    archive_origin: str | None = None

    @property
    def content_hash(self) -> str:
        return sha256(self.data).hexdigest()


@dataclass(frozen=True)
class InspectedSource:
    source_type: CorpusSourceType
    source_identity: str
    source_revision: str
    materials: tuple[SourceMaterial, ...]
    report: SourceInspectionReport


def _safe_path(value: str) -> str:
    normalized = unicodedata.normalize("NFC", value.replace("\\", "/"))
    path = PurePosixPath(normalized)
    if (
        path.is_absolute()
        or PureWindowsPath(value).is_absolute()
        or ".." in path.parts
        or normalized in {"", "."}
    ):
        raise CorpusSourceError("source path is absolute, empty, or traverses a parent")
    return path.as_posix()


def _media_type(path: str) -> str:
    return mimetypes.guess_type(path)[0] or "application/octet-stream"


def _encoding(data: bytes) -> str | None:
    try:
        data.decode("utf-8")
    except UnicodeDecodeError:
        return None
    return "utf-8"


def _build_source(
    source_type: CorpusSourceType,
    identity: str,
    revision: str,
    materials: list[SourceMaterial],
    config: CorpusConfiguration,
    *,
    warnings: tuple[str, ...] = (),
) -> InspectedSource:
    if not materials:
        raise CorpusSourceError("source contains no regular files")
    if len(materials) > config.maximum_source_files:
        raise CorpusSourceError("source file-count limit exceeded")
    total = sum(len(item.data) for item in materials)
    if total > config.maximum_source_bytes:
        raise CorpusSourceError("source byte limit exceeded")
    seen: set[str] = set()
    entries: list[SourceFileEntry] = []
    ordered = sorted(materials, key=lambda item: _safe_path(item.relative_path))
    for material in ordered:
        path = _safe_path(material.relative_path)
        collision_key = unicodedata.normalize("NFC", path).casefold()
        if collision_key in seen:
            raise CorpusSourceError("duplicate normalized source path")
        seen.add(collision_key)
        if len(material.data) > config.maximum_single_file_bytes:
            raise CorpusSourceError("single source file limit exceeded")
        entries.append(
            SourceFileEntry(
                relative_path=path,
                size_bytes=len(material.data),
                media_type=material.media_type,
                file_hash=material.content_hash,
                encoding=material.encoding,
                archive_origin=material.archive_origin,
            )
        )
    report = SourceInspectionReport(
        source_identity=identity,
        entries=tuple(entries),
        total_bytes=total,
        warnings=warnings,
        safe=True,
    )
    return InspectedSource(source_type, identity, revision, tuple(ordered), report)


def inspect_local_file(
    path: Path,
    *,
    source_type: CorpusSourceType,
    source_identity: str,
    source_revision: str,
    config: CorpusConfiguration,
) -> InspectedSource:
    if path.is_symlink() or not path.is_file() or path.stat().st_nlink != 1:
        raise CorpusSourceError("local source must be one regular non-linked file")
    data = path.read_bytes()
    return _build_source(
        source_type,
        source_identity,
        source_revision,
        [SourceMaterial(path.name, data, _media_type(path.name), _encoding(data))],
        config,
    )


def inspect_local_directory(
    path: Path,
    *,
    source_identity: str,
    source_revision: str,
    config: CorpusConfiguration,
    include_hidden: bool = False,
) -> InspectedSource:
    root = path.resolve()
    if path.is_symlink() or not root.is_dir():
        raise CorpusSourceError("local directory source must be a non-linked directory")
    materials: list[SourceMaterial] = []
    for candidate in sorted(root.rglob("*")):
        relative = candidate.relative_to(root)
        if len(relative.parts) > config.maximum_directory_depth:
            raise CorpusSourceError("directory depth limit exceeded")
        if not include_hidden and any(part.startswith(".") for part in relative.parts):
            continue
        if candidate.is_symlink():
            raise CorpusSourceError("directory symlink is forbidden")
        if candidate.is_dir():
            continue
        if not candidate.is_file() or candidate.stat().st_nlink != 1:
            raise CorpusSourceError("directory hard links and special files are forbidden")
        data = candidate.read_bytes()
        relative_path = relative.as_posix()
        materials.append(
            SourceMaterial(relative_path, data, _media_type(relative_path), _encoding(data))
        )
    return _build_source(
        CorpusSourceType.DOCUMENT,
        source_identity,
        source_revision,
        materials,
        config,
    )


def inspect_local_archive(
    path: Path,
    *,
    source_identity: str,
    source_revision: str,
    config: CorpusConfiguration,
) -> InspectedSource:
    if path.is_symlink() or not path.is_file() or path.stat().st_nlink != 1:
        raise CorpusSourceError("archive source must be one regular non-linked file")
    if path.stat().st_size > config.maximum_archive_bytes:
        raise CorpusSourceError("archive byte limit exceeded")
    data = path.read_bytes()
    suffixes = "".join(path.suffixes[-2:]).lower()
    materials = (
        _read_zip(data, path.name, config)
        if path.suffix.lower() == ".zip"
        else _read_tar(data, path.name, config)
        if suffixes in {".tar.gz", ".tar.bz2", ".tar.xz"} or path.suffix.lower() in {".tar", ".tgz"}
        else None
    )
    if materials is None:
        raise CorpusSourceError("archive format is not allowlisted")
    return _build_source(
        CorpusSourceType.EXTERNAL_LOCAL_ARCHIVE,
        source_identity,
        source_revision,
        materials,
        config,
    )


def _read_zip(data: bytes, origin: str, config: CorpusConfiguration) -> list[SourceMaterial]:
    try:
        archive = zipfile.ZipFile(io.BytesIO(data))
    except zipfile.BadZipFile as error:
        raise CorpusSourceError("malformed ZIP archive") from error
    materials: list[SourceMaterial] = []
    with archive:
        members = archive.infolist()
        if len(members) > config.maximum_archive_files:
            raise CorpusSourceError("archive file-count limit exceeded")
        expanded = 0
        for member in members:
            if member.is_dir():
                continue
            mode = member.external_attr >> 16
            if stat.S_ISLNK(mode) or not (stat.S_ISREG(mode) or stat.S_IFMT(mode) == 0):
                raise CorpusSourceError("archive links and special files are forbidden")
            relative = _safe_path(member.filename)
            if len(PurePosixPath(relative).parts) > config.maximum_archive_depth:
                raise CorpusSourceError("archive depth limit exceeded")
            expanded += member.file_size
            if expanded > config.maximum_source_bytes:
                raise CorpusSourceError("archive expanded-byte limit exceeded")
            if member.file_size > config.maximum_single_file_bytes:
                raise CorpusSourceError("archive member byte limit exceeded")
            if (
                member.file_size
                > max(1, member.compress_size) * config.maximum_archive_expansion_ratio
            ):
                raise CorpusSourceError("archive expansion ratio limit exceeded")
            with archive.open(member) as stream:
                member_data = stream.read(config.maximum_single_file_bytes + 1)
            if len(member_data) != member.file_size:
                raise CorpusSourceError("archive member size is inconsistent")
            materials.append(
                SourceMaterial(
                    relative, member_data, _media_type(relative), _encoding(member_data), origin
                )
            )
    return materials


def _read_tar(data: bytes, origin: str, config: CorpusConfiguration) -> list[SourceMaterial]:
    try:
        archive = tarfile.open(fileobj=io.BytesIO(data), mode="r:*")  # noqa: SIM115
    except tarfile.TarError as error:
        raise CorpusSourceError("malformed TAR archive") from error
    materials: list[SourceMaterial] = []
    with archive:
        members = archive.getmembers()
        if len(members) > config.maximum_archive_files:
            raise CorpusSourceError("archive file-count limit exceeded")
        expanded = 0
        for member in members:
            if member.isdir():
                continue
            if not member.isfile() or member.issym() or member.islnk() or member.isdev():
                raise CorpusSourceError("archive links and special files are forbidden")
            relative = _safe_path(member.name)
            if len(PurePosixPath(relative).parts) > config.maximum_archive_depth:
                raise CorpusSourceError("archive depth limit exceeded")
            expanded += member.size
            if expanded > config.maximum_source_bytes:
                raise CorpusSourceError("archive expanded-byte limit exceeded")
            if member.size > config.maximum_single_file_bytes:
                raise CorpusSourceError("archive member byte limit exceeded")
            extracted = archive.extractfile(member)
            if extracted is None:
                raise CorpusSourceError("archive member cannot be read")
            member_data = extracted.read(config.maximum_single_file_bytes + 1)
            materials.append(
                SourceMaterial(
                    relative, member_data, _media_type(relative), _encoding(member_data), origin
                )
            )
    if expanded > max(1, len(data)) * config.maximum_archive_expansion_ratio:
        raise CorpusSourceError("archive expansion ratio limit exceeded")
    return materials


def inspect_experience_candidate(
    candidate: ExperienceCandidate,
    *,
    source_revision: str,
    config: CorpusConfiguration,
) -> InspectedSource:
    if candidate.status.value != "proposed":
        raise CorpusSourceError("Experience candidate must retain proposed status")
    data = candidate.canonical_json().encode()
    identity = f"experience-candidate:{candidate.candidate_id}"
    return _build_source(
        CorpusSourceType.EXPERIENCE_CANDIDATE,
        identity,
        source_revision,
        [SourceMaterial("candidate.json", data, "application/json", "utf-8")],
        config,
    )
