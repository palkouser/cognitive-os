from contextlib import contextmanager

from cognitive_os.telemetry.best_effort import BestEffortTelemetry


class FailingTelemetry:
    @contextmanager
    def start_span(self, name):
        del name
        raise RuntimeError("telemetry unavailable")
        yield

    def get_current_context(self):
        raise RuntimeError("telemetry unavailable")

    def record_exception(self, error):
        raise RuntimeError from error

    def set_attribute(self, name, value):
        raise RuntimeError(f"{name}: {value}")


def test_best_effort_wrapper_isolates_all_telemetry_failures() -> None:
    telemetry = BestEffortTelemetry(FailingTelemetry())
    with telemetry.start_span("operation") as context:
        telemetry.set_attribute("db.system", "postgresql")
        telemetry.record_exception(ValueError("test"))
    assert context.trace_id is None
    assert telemetry.get_current_context().trace_id is None
