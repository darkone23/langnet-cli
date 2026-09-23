from __future__ import annotations

import sys
from types import ModuleType, SimpleNamespace

from opentelemetry import trace as otel_trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from langnet.cli import _create_translation_completion_with_model_fallback
from langnet.clients import SubprocessToolClient
from langnet.execution.clients import CLTKFetchClient

_TEST_TIMEOUT_SECONDS = 45.0
_TEST_FALLBACK_EVENT_COUNT = 2
_TEST_HTTP_OK = 200

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


class _FakeCompletions:
    def __init__(self, failures_by_model: dict[str, Exception] | None = None) -> None:
        self.failures_by_model = failures_by_model or {}
        self.created_models: list[str] = []

    def create(self, model: str, **_kwargs: object):
        self.created_models.append(model)
        failure = self.failures_by_model.get(model)
        if failure is not None:
            raise failure
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=" lupus est "))],
            usage=None,
        )


def test_translation_fallback_emits_llm_span() -> None:
    _span_exporter.clear()

    completions = _FakeCompletions()
    response = _create_translation_completion_with_model_fallback(
        completions,
        model_candidates=["openai:primary/model", "openai:deepseek/deepseek-v4-flash"],
        request_kwargs={"timeout": _TEST_TIMEOUT_SECONDS},
    )

    assert response.choices[0].message.content == " lupus est "
    assert completions.created_models == ["openai:primary/model"]

    spans = _span_exporter.get_finished_spans()
    assert len(spans) == 1
    span = spans[0]
    assert span.name == "llm.translation"
    attrs = dict(span.attributes or {})
    assert (
        attrs["langnet.llm.model_candidates"]
        == "openai:primary/model,openai:deepseek/deepseek-v4-flash"
    )
    assert attrs["langnet.llm.model"] == "openai:primary/model"
    assert attrs["langnet.llm.timeout_seconds"] == _TEST_TIMEOUT_SECONDS
    assert "langnet.llm.attempt_elapsed_seconds" in attrs


def test_translation_fallback_records_fallback_event_then_success() -> None:
    _span_exporter.clear()

    completions = _FakeCompletions(
        failures_by_model={"openai:primary/model": RuntimeError("provider down")}
    )
    _create_translation_completion_with_model_fallback(
        completions,
        model_candidates=["openai:primary/model", "openai:fallback/model"],
        request_kwargs={},
    )

    spans = _span_exporter.get_finished_spans()
    assert len(spans) == 1
    span = spans[0]
    assert span.status.is_ok
    events = list(span.events)
    assert len(events) == 1
    assert events[0].name == "langnet.llm.model_fallback"
    assert events[0].attributes["langnet.llm.model"] == "openai:primary/model"
    assert "provider down" in events[0].attributes["langnet.llm.error"]


def test_translation_fallback_marks_error_when_all_models_fail() -> None:
    _span_exporter.clear()

    completions = _FakeCompletions(
        failures_by_model={
            "openai:primary/model": RuntimeError("provider down"),
            "openai:fallback/model": RuntimeError("fallback down"),
        }
    )
    try:
        _create_translation_completion_with_model_fallback(
            completions,
            model_candidates=["openai:primary/model", "openai:fallback/model"],
            request_kwargs={},
        )
    except RuntimeError as exc:
        assert "fallback down" in str(exc)
    else:  # pragma: no cover - defensive
        raise AssertionError("expected the last provider exception to propagate")

    spans = _span_exporter.get_finished_spans()
    assert len(spans) == 1
    span = spans[0]
    assert not span.status.is_ok
    events = list(span.events)
    fallback_events = [event for event in events if event.name == "langnet.llm.model_fallback"]
    assert len(fallback_events) == _TEST_FALLBACK_EVENT_COUNT
    assert any(event.name == "exception" for event in events)


def _stub_cltk_fetch_client() -> CLTKFetchClient:
    client = object.__new__(CLTKFetchClient)
    client.tool = "fetch.cltk"
    client._greek_nlp = object()
    client._latin_lemmatizer = SimpleNamespace(lemmatize=lambda words: [(words[0], "lupus")])
    client._lexicon = SimpleNamespace(lookup=lambda word: "lupus lines")
    client._transcriber = SimpleNamespace(transcribe=lambda word: ["ˈluː.pʊs"])
    return client


def test_cltk_execute_emits_span_with_lang_and_word() -> None:
    _span_exporter.clear()

    client = _stub_cltk_fetch_client()
    effect = client.execute(
        call_id="cltk-call-1", endpoint="cltk://lat/lupus", params={"word": "lupus", "lang": "lat"}
    )

    assert effect.status_code == _TEST_HTTP_OK
    spans = _span_exporter.get_finished_spans()
    assert len(spans) == 1
    span = spans[0]
    assert span.name == "fetch.cltk.execute"
    attrs = dict(span.attributes or {})
    assert attrs["langnet.cltk.lang"] == "lat"
    assert attrs["langnet.cltk.word"] == "lupus"
    assert "langnet.cltk.execute_ms" in attrs


def test_cltk_greek_pipeline_load_emits_span() -> None:
    _span_exporter.clear()

    fake_cltk = ModuleType("cltk")

    class _FakeNLP:
        def __init__(self, language: str, suppress_banner: bool = False) -> None:
            assert language == "grc"

    fake_cltk.NLP = _FakeNLP  # type: ignore[attr-defined]
    sentinel = object()
    had_cltk_module = "cltk" in sys.modules
    previous_cltk = sys.modules.get("cltk", sentinel)
    sys.modules["cltk"] = fake_cltk
    try:
        client = object.__new__(CLTKFetchClient)
        client.tool = "fetch.cltk"
        client._greek_nlp = None
        client._ensure_greek_nlp()
    finally:
        if had_cltk_module:
            sys.modules["cltk"] = previous_cltk
        else:
            del sys.modules["cltk"]

    assert client._greek_nlp is not None
    spans = _span_exporter.get_finished_spans()
    assert len(spans) == 1
    span = spans[0]
    assert span.name == "cltk.grc_pipeline_load"
    attrs = dict(span.attributes or {})
    assert attrs["langnet.cltk.stage"] == "greek_nlp_load"
