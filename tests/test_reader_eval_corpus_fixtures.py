from __future__ import annotations

import json
from pathlib import Path
from typing import Any

FIXTURE_PATH = Path("tests/fixtures/reader_eval_corpus_expansion.json")
REQUIRED_PASSAGES = {
    "vulgate_john_1_1": "lat",
    "greek_nt_john_1_1": "grc",
    "taittiriya_upanishad_invocation": "san",
    "taittiriya_samhita_1_1_1": "san",
    "sanskrit_seed_forms": "san",
}
MIN_PASSAGE_TOKENS = 3
REQUIRED_SANSKRIT_SEED_SURFACES = {
    "agnim",
    "jñānam",
    "dharmasya",
    "ātman",
    "yogena",
    "agnikṣetre",
    "jñānayogena",
}


def _fixture() -> dict[str, Any]:
    return json.loads(FIXTURE_PATH.read_text())


def _tokens() -> list[dict[str, Any]]:
    tokens: list[dict[str, Any]] = []
    for passage in _fixture()["passages"]:
        for token in passage["tokens"]:
            tokens.append({"language": passage["language"], **token})
    return tokens


def test_corpus_expansion_fixture_covers_requested_sources() -> None:
    fixture = _fixture()
    passages = fixture["passages"]
    by_id = {passage["id"]: passage for passage in passages}

    assert set(by_id) == set(REQUIRED_PASSAGES)
    for passage_id, language in REQUIRED_PASSAGES.items():
        passage = by_id[passage_id]
        assert passage["language"] == language
        assert passage["work"]
        assert passage["citation"]
        assert len(passage["tokens"]) >= MIN_PASSAGE_TOKENS


def test_corpus_expansion_tokens_have_reader_expectations() -> None:
    for token in _tokens():
        assert token["surface"]
        assert token["expected_lemmas"]
        assert token["expected_gloss_terms"]
        assert isinstance(token["expect_morphology"], bool)
        assert all(isinstance(value, str) and value for value in token["expected_lemmas"])
        assert all(isinstance(value, str) and value for value in token["expected_gloss_terms"])


def test_corpus_expansion_fixture_includes_sanskrit_seed_forms() -> None:
    tokens = [token for token in _tokens() if token["language"] == "san"]
    by_surface = {token["surface"]: token for token in tokens}

    assert REQUIRED_SANSKRIT_SEED_SURFACES.issubset(by_surface)
    for surface in ("agnikṣetre", "jñānayogena"):
        token = by_surface[surface]
        assert len(token.get("expected_components", [])) >= 2
        assert token["notes"]
