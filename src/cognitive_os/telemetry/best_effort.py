"""Failure-isolating wrapper for injected telemetry implementations."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import AbstractContextManager, contextmanager, suppress
from types import TracebackType

from cognitive_os.domain.common import JsonPrimitive

from .base import TelemetryContext, TelemetryPort


class BestEffortTelemetry:
    def __init__(self, delegate: TelemetryPort) -> None:
        self._delegate = delegate

    @contextmanager
    def start_span(self, name: str) -> Iterator[TelemetryContext]:
        manager: AbstractContextManager[TelemetryContext] | None = None
        try:
            manager = self._delegate.start_span(name)
            context = manager.__enter__()
        except Exception:
            yield TelemetryContext()
            return
        try:
            yield context
        except BaseException as operation_error:
            self._safe_exit(
                manager, type(operation_error), operation_error, operation_error.__traceback__
            )
            raise
        else:
            self._safe_exit(manager, None, None, None)

    def get_current_context(self) -> TelemetryContext:
        try:
            return self._delegate.get_current_context()
        except Exception:
            return TelemetryContext()

    def record_exception(self, error: BaseException) -> None:
        with suppress(Exception):
            self._delegate.record_exception(error)

    def set_attribute(self, name: str, value: JsonPrimitive) -> None:
        with suppress(Exception):
            self._delegate.set_attribute(name, value)

    @staticmethod
    def _safe_exit(
        manager: AbstractContextManager[TelemetryContext],
        exception_type: type[BaseException] | None,
        exception: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        with suppress(Exception):
            manager.__exit__(exception_type, exception, traceback)
