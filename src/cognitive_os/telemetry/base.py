"""Telemetry contracts that do not depend on an SDK."""

from __future__ import annotations

from contextlib import AbstractContextManager
from typing import Protocol

from pydantic import Field, model_validator

from cognitive_os.domain.base import ImmutableContractModel
from cognitive_os.domain.common import JsonPrimitive


class TelemetryContext(ImmutableContractModel):
    trace_id: str | None = Field(default=None, pattern=r"^[0-9a-f]{32}$")
    span_id: str | None = Field(default=None, pattern=r"^[0-9a-f]{16}$")

    @model_validator(mode="after")
    def context_is_complete(self) -> TelemetryContext:
        if (self.trace_id is None) != (self.span_id is None):
            raise ValueError("trace_id and span_id must both be present or both be absent")
        return self


class TelemetryPort(Protocol):
    def start_span(self, name: str) -> AbstractContextManager[TelemetryContext]: ...

    def get_current_context(self) -> TelemetryContext: ...

    def record_exception(self, error: BaseException) -> None: ...

    def set_attribute(self, name: str, value: JsonPrimitive) -> None: ...
