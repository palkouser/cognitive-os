"""Bounded, non-executing skill package inspection and interchange."""

from __future__ import annotations

import base64
import json
import mimetypes
import os
import re
import stat
import unicodedata
import zipfile
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path, PurePosixPath

import yaml

from cognitive_os.config.skill_config import SkillConfiguration
from cognitive_os.domain.skills import (
    SkillPackageFile,
    SkillPackageFileType,
    SkillPackageManifest,
)
from cognitive_os.memory.governance import contains_secret

from .errors import SkillPackageError

_ALLOWED_ROOT_FILES = {"SKILL.md", "metadata.yaml"}
_ALLOWED_DIRECTORIES = {"resources", "templates", "scripts", "tests"}
_TEXT_MEDIA = {
    ".json": "application/json",
    ".md": "text/markdown",
    ".py": "text/x-python",
    ".txt": "text/plain",
    ".yaml": "application/yaml",
    ".yml": "application/yaml",
}
_RESOURCE_REFERENCE = re.compile(r"(?<![\w/])(?:resources|templates)/[A-Za-z0-9_.\-/]+")


class _UniqueSafeLoader(yaml.SafeLoader):
    pass


def _construct_mapping(
    loader: yaml.SafeLoader, node: yaml.MappingNode, deep: bool = False
) -> dict[object, object]:
    keys: set[object] = set()
    for key_node, _ in node.value:
        key = loader.construct_object(key_node, deep=False)
        if key in keys:
            raise SkillPackageError(f"duplicate YAML key: {key}")
        keys.add(key)
    return yaml.SafeLoader.construct_mapping(loader, node, deep=deep)


_UniqueSafeLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _construct_mapping
)


@dataclass(frozen=True)
class LoadedSkillPackage:
    manifest: SkillPackageManifest
    metadata: dict[str, object]
    instructions: str
    files: dict[str, bytes]

    def artifact_bytes(self) -> bytes:
        return json.dumps(
            {
                "format_version": self.manifest.format_version,
                "manifest": self.manifest.model_dump(mode="json"),
                "files": {
                    path: base64.b64encode(content).decode()
                    for path, content in sorted(self.files.items())
                },
            },
            sort_keys=True,
            separators=(",", ":"),
        ).encode()


def _normalized_path(path: Path, root: Path) -> str:
    relative = PurePosixPath(path.relative_to(root).as_posix())
    normalized = unicodedata.normalize("NFC", relative.as_posix())
    parts = PurePosixPath(normalized).parts
    if not parts or ".." in parts or ".git" in parts or len(parts) > 12:
        raise SkillPackageError("unsafe skill package path")
    if len(parts) == 1 and normalized not in _ALLOWED_ROOT_FILES:
        raise SkillPackageError(f"unsupported root package file: {normalized}")
    if len(parts) > 1 and parts[0] not in _ALLOWED_DIRECTORIES:
        raise SkillPackageError(f"unsupported skill package directory: {parts[0]}")
    return normalized


def _file_type(path: str) -> SkillPackageFileType:
    if path == "SKILL.md":
        return SkillPackageFileType.INSTRUCTIONS
    if path == "metadata.yaml":
        return SkillPackageFileType.METADATA
    return SkillPackageFileType(PurePosixPath(path).parts[0].removesuffix("s"))


def inspect_package(path: Path, configuration: SkillConfiguration) -> SkillPackageManifest:
    """Inspect a directory package without following links or executing content."""
    if not path.is_dir() or path.is_symlink():
        raise SkillPackageError("skill package must be a real directory")
    entries: list[SkillPackageFile] = []
    normalized_paths: set[str] = set()
    total = 0
    for root, directories, filenames in os.walk(path, followlinks=False):
        root_path = Path(root)
        for name in directories:
            child = root_path / name
            if child.is_symlink() or name == ".git":
                raise SkillPackageError("links and .git metadata are prohibited")
        for name in filenames:
            child = root_path / name
            info = child.lstat()
            if not stat.S_ISREG(info.st_mode) or stat.S_ISLNK(info.st_mode):
                raise SkillPackageError("skill packages may contain only regular files")
            if info.st_nlink != 1:
                raise SkillPackageError("hard-linked skill package files are prohibited")
            relative = _normalized_path(child, path)
            key = relative.casefold()
            if key in normalized_paths:
                raise SkillPackageError("duplicate case-folded skill package path")
            normalized_paths.add(key)
            if info.st_size > configuration.maximum_single_file_bytes:
                raise SkillPackageError("skill package file exceeds the byte limit")
            content = child.read_bytes()
            if len(content) != info.st_size:
                raise SkillPackageError("skill package file changed during inspection")
            total += len(content)
            media_type = _TEXT_MEDIA.get(child.suffix.casefold()) or mimetypes.guess_type(name)[0]
            if media_type is None:
                media_type = "application/octet-stream"
            entries.append(
                SkillPackageFile(
                    relative_path=relative,
                    file_type=_file_type(relative),
                    media_type=media_type,
                    size_bytes=len(content),
                    content_hash=sha256(content).hexdigest(),
                )
            )
    if len(entries) > configuration.maximum_package_files:
        raise SkillPackageError("skill package exceeds the file-count limit")
    if total > configuration.maximum_package_bytes:
        raise SkillPackageError("skill package exceeds the total byte limit")
    return SkillPackageManifest(
        files=tuple(sorted(entries, key=lambda item: item.relative_path)),
        total_bytes=total,
    )


def _bounded_yaml(content: bytes, configuration: SkillConfiguration) -> dict[str, object]:
    if len(content) > configuration.maximum_metadata_bytes:
        raise SkillPackageError("skill metadata exceeds the byte limit")
    if content.count(b"&") + content.count(b"*") > 32:
        raise SkillPackageError("skill metadata aliases exceed the limit")
    try:
        value = yaml.load(  # nosec B506 - duplicate-key subclass of yaml.SafeLoader
            content, Loader=_UniqueSafeLoader
        )
    except (yaml.YAMLError, UnicodeDecodeError, SkillPackageError) as error:
        raise SkillPackageError("invalid bounded skill metadata") from error
    if not isinstance(value, dict) or not all(isinstance(key, str) for key in value):
        raise SkillPackageError("skill metadata must be a string-keyed mapping")
    _validate_yaml_shape(value)
    allowed = {
        "format_version",
        "canonical_name",
        "display_name",
        "description",
        "purpose",
        "domains",
        "scope_type",
        "scope_id",
        "sensitivity",
        "problem_signatures",
        "preconditions",
        "inputs",
        "outputs",
        "steps",
        "requirements",
        "failure_policy",
        "resource_budget",
        "regression_profile",
        "status",
    }
    unknown = set(value) - allowed
    if unknown:
        raise SkillPackageError(f"unknown skill metadata fields: {sorted(unknown)}")
    return value


def _validate_yaml_shape(value: object, *, depth: int = 0) -> None:
    if depth > 12:
        raise SkillPackageError("skill metadata exceeds the nesting limit")
    if isinstance(value, dict):
        if len(value) > 256:
            raise SkillPackageError("skill metadata mapping exceeds the entry limit")
        for key, item in value.items():
            if not isinstance(key, str) or len(key) > 256:
                raise SkillPackageError("skill metadata key exceeds the limit")
            _validate_yaml_shape(item, depth=depth + 1)
    elif isinstance(value, list):
        if len(value) > 256:
            raise SkillPackageError("skill metadata list exceeds the entry limit")
        for item in value:
            _validate_yaml_shape(item, depth=depth + 1)
    elif isinstance(value, str) and len(value) > 8_192:
        raise SkillPackageError("skill metadata scalar exceeds the limit")


def parse_skill_instructions(instructions: str) -> tuple[str, tuple[str, ...]]:
    """Validate bounded Markdown structure and return logical resource references."""
    lines = instructions.splitlines()
    if not lines or not lines[0].startswith("# ") or not lines[0][2:].strip():
        raise SkillPackageError("SKILL.md requires one leading title heading")
    headings = [line for line in lines if line.startswith("#")]
    if len(headings) > 64 or any(len(line) > 512 for line in lines):
        raise SkillPackageError("SKILL.md structure exceeds the bounded parser limits")
    references = tuple(sorted(set(_RESOURCE_REFERENCE.findall(instructions))))
    if any(".." in PurePosixPath(value).parts for value in references):
        raise SkillPackageError("SKILL.md contains an unsafe resource reference")
    return lines[0][2:].strip(), references


def load_package(path: Path, configuration: SkillConfiguration) -> LoadedSkillPackage:
    manifest = inspect_package(path, configuration)
    files = {
        item.relative_path: (path / item.relative_path).read_bytes() for item in manifest.files
    }
    instructions_bytes = files["SKILL.md"]
    if len(instructions_bytes) > configuration.maximum_instruction_bytes:
        raise SkillPackageError("skill instructions exceed the byte limit")
    try:
        instructions = instructions_bytes.decode("utf-8")
    except UnicodeDecodeError as error:
        raise SkillPackageError("skill instructions must be UTF-8") from error
    if contains_secret(instructions) or any(
        contains_secret(value.decode("utf-8", errors="ignore"))
        for name, value in files.items()
        if name != "SKILL.md"
    ):
        raise SkillPackageError("skill package failed secret scanning")
    parse_skill_instructions(instructions)
    return LoadedSkillPackage(
        manifest=manifest,
        metadata=_bounded_yaml(files["metadata.yaml"], configuration),
        instructions=instructions,
        files=files,
    )


def load_artifact_package(content: bytes, configuration: SkillConfiguration) -> LoadedSkillPackage:
    """Revalidate a stored package projection before hydration or export."""
    if len(content) > configuration.maximum_package_bytes * 2:
        raise SkillPackageError("stored skill package exceeds the byte limit")
    try:
        payload = json.loads(content)
        manifest = SkillPackageManifest.model_validate(payload["manifest"])
        encoded_files = payload["files"]
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
        raise SkillPackageError("invalid stored skill package") from error
    if not isinstance(encoded_files, dict) or not all(
        isinstance(path, str) and isinstance(value, str) for path, value in encoded_files.items()
    ):
        raise SkillPackageError("invalid stored skill package files")
    try:
        files = {
            path: base64.b64decode(value, validate=True) for path, value in encoded_files.items()
        }
    except ValueError as error:
        raise SkillPackageError("invalid stored skill package encoding") from error
    expected = {item.relative_path: item for item in manifest.files}
    if set(files) != set(expected) or any(
        len(files[path]) != item.size_bytes or sha256(files[path]).hexdigest() != item.content_hash
        for path, item in expected.items()
    ):
        raise SkillPackageError("stored skill package integrity check failed")
    try:
        instructions = files["SKILL.md"].decode("utf-8")
    except UnicodeDecodeError as error:
        raise SkillPackageError("stored skill instructions must be UTF-8") from error
    if len(instructions.encode()) > configuration.maximum_instruction_bytes:
        raise SkillPackageError("stored skill instructions exceed the byte limit")
    parse_skill_instructions(instructions)
    if any(contains_secret(value.decode("utf-8", errors="ignore")) for value in files.values()):
        raise SkillPackageError("stored skill package failed secret scanning")
    return LoadedSkillPackage(
        manifest=manifest,
        metadata=_bounded_yaml(files["metadata.yaml"], configuration),
        instructions=instructions,
        files=files,
    )


def inspect_zip(path: Path, configuration: SkillConfiguration) -> SkillPackageManifest:
    """Validate a ZIP inventory without extracting it."""
    if path.suffix.casefold() != ".zip":
        raise SkillPackageError("only ZIP skill package archives are supported")
    with zipfile.ZipFile(path) as archive:
        files = [item for item in archive.infolist() if not item.is_dir()]
        if len(files) > configuration.maximum_package_files:
            raise SkillPackageError("skill archive exceeds the file-count limit")
        compressed = max(sum(item.compress_size for item in files), 1)
        expanded = sum(item.file_size for item in files)
        if (
            expanded > configuration.maximum_package_bytes
            or expanded / compressed > configuration.maximum_archive_expansion_ratio
        ):
            raise SkillPackageError("skill archive exceeds expansion limits")
        seen: set[str] = set()
        entries = []
        for info in files:
            name = unicodedata.normalize("NFC", info.filename)
            pure = PurePosixPath(name)
            mode = info.external_attr >> 16
            if pure.is_absolute() or ".." in pure.parts or ".git" in pure.parts:
                raise SkillPackageError("unsafe skill archive path")
            if len(pure.parts) > configuration.maximum_directory_depth:
                raise SkillPackageError("skill archive path exceeds the depth limit")
            if len(pure.parts) == 1 and name not in _ALLOWED_ROOT_FILES:
                raise SkillPackageError("unsupported root skill archive file")
            if len(pure.parts) > 1 and pure.parts[0] not in _ALLOWED_DIRECTORIES:
                raise SkillPackageError("unsupported skill archive directory")
            if stat.S_ISLNK(mode) or (mode and not stat.S_ISREG(mode)):
                raise SkillPackageError("skill archive contains a non-regular file")
            if name.casefold() in seen:
                raise SkillPackageError("duplicate normalized skill archive path")
            seen.add(name.casefold())
            if info.file_size > configuration.maximum_single_file_bytes:
                raise SkillPackageError("skill archive member exceeds the byte limit")
            content = archive.read(info)
            entries.append(
                SkillPackageFile(
                    relative_path=name,
                    file_type=_file_type(name),
                    media_type=_TEXT_MEDIA.get(pure.suffix.casefold(), "application/octet-stream"),
                    size_bytes=len(content),
                    content_hash=sha256(content).hexdigest(),
                )
            )
        return SkillPackageManifest(
            files=tuple(sorted(entries, key=lambda item: item.relative_path)),
            total_bytes=expanded,
        )


def load_zip_package(path: Path, configuration: SkillConfiguration) -> LoadedSkillPackage:
    """Load a validated ZIP package directly, without filesystem extraction."""
    manifest = inspect_zip(path, configuration)
    with zipfile.ZipFile(path) as archive:
        files = {item.relative_path: archive.read(item.relative_path) for item in manifest.files}
    try:
        instructions = files["SKILL.md"].decode("utf-8")
    except UnicodeDecodeError as error:
        raise SkillPackageError("skill instructions must be UTF-8") from error
    if len(instructions.encode()) > configuration.maximum_instruction_bytes:
        raise SkillPackageError("skill instructions exceed the byte limit")
    if contains_secret(instructions) or any(
        contains_secret(value.decode("utf-8", errors="ignore"))
        for name, value in files.items()
        if name != "SKILL.md"
    ):
        raise SkillPackageError("skill package failed secret scanning")
    parse_skill_instructions(instructions)
    return LoadedSkillPackage(
        manifest=manifest,
        metadata=_bounded_yaml(files["metadata.yaml"], configuration),
        instructions=instructions,
        files=files,
    )


def export_package(package: LoadedSkillPackage, destination: Path) -> None:
    """Write a deterministic Agent Skills-compatible ZIP archive."""
    if destination.suffix.casefold() != ".zip":
        raise SkillPackageError("skill package export requires a .zip destination")
    with zipfile.ZipFile(destination, "x", compression=zipfile.ZIP_DEFLATED) as archive:
        for path, content in sorted(package.files.items()):
            info = zipfile.ZipInfo(path, date_time=(2026, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100640 << 16
            archive.writestr(info, content)
