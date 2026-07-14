from cognitive_os.telemetry import NoOpTelemetry, TelemetryContext


def test_noop_context_is_empty_and_nested_spans_are_safe() -> None:
    telemetry = NoOpTelemetry()
    with (
        telemetry.start_span("outer") as outer,
        telemetry.start_span("inner") as inner,
    ):
        telemetry.set_attribute("ignored", "value")
        telemetry.record_exception(RuntimeError("test"))
    assert outer == inner == TelemetryContext()
    assert telemetry.get_current_context() == TelemetryContext()
