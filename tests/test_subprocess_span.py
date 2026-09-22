from __future__ import annotations

from opentelemetry import trace as otel_trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from langnet.clients import SubprocessToolClient

# Nose2 runs the suite in one process, and set_tracer_provider refuses a
# second install, so the recorder is wired exactly once at import. The
# module-level `get_tracer` in langnet.clients.subprocess resolves through
# the proxy tracer, meaning spans recorded before this swap are no-ops and
# spans recorded after it land in this exporter.
_span_exporter = InMemorySpanExporter()
_tracer_provider = TracerProvider()
_tracer_provider.add_span_processor(SimpleSpanProcessor(_span_exporter))
otel_trace.set_tracer_provider(_tracer_provider)


def test_subprocess_tool_client_emits_child_span() -> None:
    _span_exporter.clear()

    client = SubprocessToolClient(tool="whitakers", command=["/bin/sh", "-c", "echo hello"])
    effect = client.execute(call_id="ww-call-1")

    assert effect.status_code == 0
    assert effect.body.strip() == b"hello"

    spans = _span_exporter.get_finished_spans()
    assert len(spans) == 1
    span = spans[0]
    assert span.name == "whitakers.subprocess"
    attrs = dict(span.attributes or {})
    assert attrs["langnet.tool"] == "whitakers"
    assert attrs["langnet.call_id"] == "ww-call-1"
    # sh returns a plain str for fast foreground commands (no exit_code
    # attribute), so only assert the attributes it can always provide.
    assert attrs["langnet.command"] == "/bin/sh -c echo hello"
