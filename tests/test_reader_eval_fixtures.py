from __future__ import annotations

import json
from pathlib import Path
from typing import Any

FIXTURE_PATH = Path("tests/fixtures/reader_eval_classics.json")
REQUIRED_PASSAGES = {
    "aeneid_1_1_7": "lat",
    "iliad_1_1_7": "grc",
    "bhagavad_gita_1_1_2": "san",
}
MIN_PASSAGE_TOKENS = 4
MIN_COMPONENTS = 2
KNOWN_READER_MISSES = {
    ("lat", "virumque"),
    ("grc", "μῆνιν"),
    ("grc", "θεὰ"),
    ("san", "karma"),
}


def _fixture() -> dict[str, Any]:
    return json.loads(FIXTURE_PATH.read_text())


def _tokens() -> list[dict[str, Any]]:
    tokens: list[dict[str, Any]] = []
    for passage in _fixture()["passages"]:
        for token in passage["tokens"]:
            tokens.append({"language": passage["language"], **token})
    return tokens


def test_reader_eval_fixture_covers_classic_openings() -> None:
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


def test_reader_eval_tokens_have_tolerant_expectations() -> None:
    for token in _tokens():
        assert token["surface"]
        assert token["expected_lemmas"]
        assert token["expected_gloss_terms"]
        assert isinstance(token["expect_morphology"], bool)
        assert all(isinstance(value, str) and value for value in token["expected_lemmas"])
        assert all(isinstance(value, str) and value for value in token["expected_gloss_terms"])


def test_known_reader_misses_are_documented_with_negative_expectations() -> None:
    tokens = {(token["language"], token["surface"]): token for token in _tokens()}

    assert KNOWN_READER_MISSES.issubset(tokens)
    for key in KNOWN_READER_MISSES:
        token = tokens[key]
        assert token.get("known_bad_lemmas") or token.get("known_bad_gloss_terms")
        assert token.get("notes")


def test_component_expectations_are_reserved_for_reader_form_cases() -> None:
    component_cases = [token for token in _tokens() if token.get("expected_components")]

    surfaces = {token["surface"] for token in component_cases}
    assert {"virumque", "dharmakṣetre", "kurukṣetre"}.issubset(surfaces)
    for token in component_cases:
        assert len(token["expected_components"]) >= MIN_COMPONENTS
