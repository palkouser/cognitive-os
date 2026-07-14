"""Common value objects and timestamp policy."""

from __future__ import annotations

import re
from datetime import UTC, datetime
from pathlib import PurePosixPath, PureWindowsPath
from typing import Annotated, Any

from pydantic import AfterValidator, Field, StringConstraints, field_validator, model_validator

from .base import ImmutableContractModel
from .enums import ActorType
from .identifiers import ArtifactId

type JsonPrimitive = str | int | float | bool | None
type JsonValue = JsonPrimitive | list[JsonValue] | dict[str, JsonValue]
NonEmptyStr = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
Sha256Hex = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]


def normalize_utc(value: datetime) -> datetime:
    """Reject naive datetimes and normalize aware values to UTC."""
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("timestamp must be timezone-aware")
    return value.astimezone(UTC)


UtcDatetime = Annotated[datetime, AfterValidator(normalize_utc)]


def utc_now() -> datetime:
    """Return the current timezone-aware UTC time."""
    return datetime.now(UTC)


class ActorRef(ImmutableContractModel):
    actor_type: ActorType
    actor_id: NonEmptyStr
    display_name: NonEmptyStr | None = None


class ErrorInfo(ImmutableContractModel):
    code: NonEmptyStr
    message: NonEmptyStr
    error_type: NonEmptyStr | None = None
    retryable: bool = False
    details: dict[str, JsonValue] = Field(default_factory=dict)

    @field_validator("details", mode="before")
    @classmethod
    def copy_details(cls, value: Any) -> Any:
        return dict(value) if isinstance(value, dict) else value


ExecutionError = ErrorInfo


class ArtifactRef(ImmutableContractModel):
    artifact_id: ArtifactId
    media_type: NonEmptyStr
    content_hash: Sha256Hex
    size_bytes: int = Field(ge=0)
    storage_key: NonEmptyStr
    created_at: UtcDatetime

    @field_validator("storage_key")
    @classmethod
    def storage_key_is_logical(cls, value: str) -> str:
        if PurePosixPath(value).is_absolute() or PureWindowsPath(value).is_absolute():
            raise ValueError("storage_key must be a logical relative key")
        if re.match(r"^[A-Za-z]:[\\/]", value):
            raise ValueError("storage_key must not be a host path")
        if ".." in PurePosixPath(value).parts or ".." in PureWindowsPath(value).parts:
            raise ValueError("storage_key must not traverse parent directories")
        return value


class TokenUsage(ImmutableContractModel):
    input_tokens: int | None = Field(default=None, ge=0)
    output_tokens: int | None = Field(default=None, ge=0)
    total_tokens: int | None = Field(default=None, ge=0)
    cached_input_tokens: int | None = Field(default=None, ge=0)
    reasoning_tokens: int | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def total_covers_input_and_output(self) -> TokenUsage:
        minimum = (self.input_tokens or 0) + (self.output_tokens or 0)
        if self.total_tokens is not None and self.total_tokens < minimum:
            raise ValueError("total_tokens cannot be less than input_tokens plus output_tokens")
        return self
