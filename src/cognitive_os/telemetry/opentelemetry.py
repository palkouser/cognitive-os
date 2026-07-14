"""Optional OpenTelemetry adapter with safe attribute filtering."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

from cognitive_os.domain.common import JsonPrimitive

from .base import TelemetryContext

ALLOWED_ATTRIBUTES = frozenset(
    {
        "cogos.stream_id",
        "cogos.stream_type",
        "cogos.expected_stream_version",
        "cogos.committed_stream_version",
        "cogos.event_count",
        "cogos.event_type",
        "cogos.global_position",
        "cogos.correlation_id",
        "cogos.artifact_id",
        "cogos.artifact_size_bytes",
        "cogos.replay_event_count",
        "db.system",
    }
)


class OpenTelemetryAdapter:
    def __init__(self, tracer: Any) -> None:
        self._tracer = tracer

    @contextmanager
    def start_span(self, name: str) -> Iterator[TelemetryContext]:
        with self._tracer.start_as_current_span(name):
            yield self.get_current_context()

    def get_current_context(self) -> TelemetryContext:
        from opentelemetry import trace

        context = trace.get_current_span().get_span_context()
        if not context.is_valid:
            return TelemetryContext()
        return TelemetryContext(
            trace_id=f"{context.trace_id:032x}",
            span_id=f"{context.span_id:016x}",
        )

    def record_exception(self, error: BaseException) -> None:
        from opentelemetry import trace

        trace.get_current_span().record_exception(error)

    def set_attribute(self, name: str, value: JsonPrimitive) -> None:
        if name not in ALLOWED_ATTRIBUTES:
            raise ValueError(f"telemetry attribute is not allowed: {name}")
        if value is not None:
            from opentelemetry import trace

            trace.get_current_span().set_attribute(name, value)
