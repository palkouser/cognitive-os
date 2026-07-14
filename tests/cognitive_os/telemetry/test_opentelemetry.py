import pytest

pytest.importorskip("opentelemetry.sdk")

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from cognitive_os.telemetry.opentelemetry import OpenTelemetryAdapter


def test_adapter_exports_safe_attributes_and_context() -> None:
    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    adapter = OpenTelemetryAdapter(provider.get_tracer("test"))
    with adapter.start_span("cognitive_os.event_store.append") as context:
        adapter.set_attribute("db.system", "postgresql")
        assert len(context.trace_id or "") == 32
        assert len(context.span_id or "") == 16
    span = exporter.get_finished_spans()[0]
    assert span.attributes["db.system"] == "postgresql"


def test_adapter_rejects_sensitive_or_unknown_attributes() -> None:
    adapter = OpenTelemetryAdapter(trace.get_tracer("test"))
    with pytest.raises(ValueError, match="not allowed"):
        adapter.set_attribute("event.payload", "private")
