from __future__ import annotations

from importlib.machinery import SourceFileLoader
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[1] / ".justscripts" / "lex_translation_demo.py"
lex_module = SourceFileLoader("lex_translation_demo", str(MODULE_PATH)).load_module()

EXPECTED_TRANSLATION_CHUNKS = 2


class _DummyCompletions:
    def __init__(self, outer) -> None:
        self.outer = outer

    def create(self, model, messages):
        self.outer.calls.append({"model": model, "messages": messages})
        # simple stub response
        choice = type("Choice", (), {"message": type("Msg", (), {"content": "out"})()})
        return type("Resp", (), {"choices": [choice]})()


class _DummyClient:
    def __init__(self) -> None:
        self.calls = []
        self.chat = type("Chat", (), {})()
        self.chat.completions = _DummyCompletions(self)


def test_split_paragraphs_handles_marker_and_newlines() -> None:
    text = "amor ¶ ardor\n¶ caritas"
    chunks = lex_module.split_paragraphs(text)
    assert chunks == ["amor", "ardor", "caritas"]


def test_translate_entry_rejoins_with_paragraph_marker_separator() -> None:
    client = _DummyClient()
    entry = {"entry_id": "gaffiot_1"}
    chunks = ["first", "second"]
    separator = "\n¶ "

    # silence noisy CLI echoes for multi-chunk paths
    original_echo = lex_module.click.echo
    lex_module.click.echo = lambda *args, **kwargs: None
    try:
        result = lex_module.translate_entry(
            client=client,
            model="dummy",
            entry=entry,
            hints=["hint"],
            chunks=chunks,
            separator=separator,
        )
    finally:
        lex_module.click.echo = original_echo

    assert len(client.calls) == EXPECTED_TRANSLATION_CHUNKS
    assert result == [("hint", "out\n¶ out")]


def test_build_entry_translation_key_uses_gaffiot_variant_as_occurrence() -> None:
    entry = {
        "entry_id": "gaffiot_38776",
        "occurrence": 1,
        "headword_norm": "lupus",
        "plain_text": "loup\nCic.",
    }

    key = lex_module.build_entry_translation_key(
        entry=entry,
        mode="latin",
        model="test:model",
        hints=["keep Latin"],
    )

    assert key.source_lexicon == "gaffiot"
    assert key.occurrence == 1
    assert key.headword_norm == "lupus"


def test_source_text_for_cache_matches_gaffiot_claim_projection() -> None:
    assert lex_module.source_text_for_cache("latin", "loup\n  Cic.") == "loup Cic."
    assert lex_module.source_text_for_cache("sanskrit", "loi\n devoir") == "loi\n devoir"
