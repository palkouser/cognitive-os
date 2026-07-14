"""Dataset provenance manifest validation without download or extraction."""

from __future__ import annotations

from pathlib import PurePosixPath, PureWindowsPath

from pydantic import Field, field_validator

from cognitive_os.domain.base import ImmutableContractModel
from cognitive_os.domain.common import NonEmptyStr, Sha256Hex, UtcDatetime


class DatasetManifest(ImmutableContractModel):
    dataset_id: NonEmptyStr
    version: NonEmptyStr
    source: NonEmptyStr
    source_revision: NonEmptyStr
    license: NonEmptyStr
    downloaded_at: UtcDatetime | None = None
    content_hash: Sha256Hex
    case_count: int = Field(ge=0)
    local_path: NonEmptyStr

    @field_validator("local_path")
    @classmethod
    def logical_path(cls, value: str) -> str:
        posix, windows = PurePosixPath(value), PureWindowsPath(value)
        if (
            posix.is_absolute()
            or windows.is_absolute()
            or ".." in posix.parts
            or ".." in windows.parts
        ):
            raise ValueError("dataset local path must be a logical storage identifier")
        return value


def validate_archive_members(names: tuple[str, ...]) -> None:
    for name in names:
        path = PurePosixPath(name)
        if path.is_absolute() or ".." in path.parts:
            raise ValueError("archive member escapes the dataset root")
