"""Side-effect-free telemetry implementation."""

from collections.abc import Iterator
from contextlib import contextmanager

from cognitive_os.domain.common import JsonPrimitive

from .base import TelemetryContext


class NoOpTelemetry:
    @contextmanager
    def start_span(self, name: str) -> Iterator[TelemetryContext]:
        del name
        yield TelemetryContext()

    def get_current_context(self) -> TelemetryContext:
        return TelemetryContext()

    def record_exception(self, error: BaseException) -> None:
        del error

    def set_attribute(self, name: str, value: JsonPrimitive) -> None:
        del name, value
