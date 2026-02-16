from __future__ import annotations

import importlib
import sys
from dataclasses import dataclass
from pathlib import Path

import duckdb

from langnet.diogenes.client import ParseResult, WordListResult
from langnet.normalizer.core import (
    QueryNormalizer,
    normalize_with_index,
)
from langnet.normalizer.sanskrit import HeritageClientProtocol, SanskritNormalizer
from langnet.normalizer.service import NormalizationService
from langnet.storage.normalization_index import NormalizationIndex, apply_schema

BASE_DIR = Path(__file__).resolve().parents[1]
SCHEMA_PATH = BASE_DIR / "vendor" / "langnet-spec" / "generated" / "python"
sys.path.insert(0, str(SCHEMA_PATH))

heritage_spec = importlib.import_module("heritage_spec")
query_spec = importlib.import_module("query_spec")
SktSearchResult = getattr(heritage_spec, "SktSearchResult")
MonierWilliamsResult = getattr(heritage_spec, "MonierWilliamsResult")
LanguageHint = getattr(query_spec, "LanguageHint")
NormalizationStep = getattr(query_spec, "NormalizationStep")


@dataclass(frozen=True)
class HeritageMatch:
    canonical: str
    display: str
    entry_url: str


def test_normalization_round_trip_index() -> None:
    conn = duckdb.connect(database=":memory:")
    apply_schema(conn)

    normalizer = QueryNormalizer()
    raw_query = "  Shiva "
    idx = NormalizationIndex(conn)
    result = normalize_with_index(normalizer, raw_query, LanguageHint.SAN, idx)

    loaded = idx.get(result.query_hash)
    assert loaded is not None
    assert loaded.original == raw_query
    lemmas = [c.lemma.lower() for c in loaded.candidates]
    assert any("ziva" in lemma for lemma in lemmas)
    assert loaded.normalizations, "Normalization steps should be recorded"

    result_cached = normalize_with_index(normalizer, raw_query, LanguageHint.SAN, idx)
    assert [c.lemma for c in result_cached.normalized.candidates] == [
        c.lemma for c in loaded.candidates
    ]


class _FakeHeritage(HeritageClientProtocol):
    def fetch_canonical_via_sktsearch(self, query: str) -> SktSearchResult:
        return SktSearchResult(
            original_query=query,
            bare_query=query.lower(),
            canonical_text="ziva",
            canonical_sanskrit="ziva",
            match_method="sktsearch",
            entry_url="",
        )

    def fetch_canonical_sanskrit(self, query: str) -> MonierWilliamsResult:
        return MonierWilliamsResult(
            original_query=query,
            bare_query=query.lower(),
            canonical_sanskrit="ziva",
            match_method="sktsearch",
            entry_url="",
        )

    def fetch_all_matches(self, query: str) -> list[HeritageMatch]:
        return [HeritageMatch(canonical="ziva", display="śiva", entry_url="")]


class _FakeDiogenes:
    def fetch_word_list(self, query: str) -> WordListResult:
        return WordListResult(query=query, lemmas=["λόγος", "λογος"], matched=True)

    def fetch_parse(self, query: str, lang: str = "lat") -> ParseResult:
        return ParseResult(query=query, lemmas=["lupus", "lupum"], matched=True)


class _FakeWhitaker:
    def fetch(self, query: str) -> list[str]:
        return ["is", "idem"]


def test_sanskrit_normalizer_enrichment_prefers_heritage() -> None:
    steps: list[NormalizationStep] = []
    normalizer = SanskritNormalizer(heritage_client=_FakeHeritage())
    candidates = normalizer.canonical_candidates("shiva", steps)

    lemmas = [c.lemma for c in candidates]
    assert "śiva" in lemmas
    assert any("heritage_sktsearch" in c.sources for c in candidates)
    dev = next((c for c in candidates if c.lemma == "śiva"), None)
    assert dev is not None
    assert dev.encodings.get("velthuis") == "ziva"
    assert any(step.operation.startswith("heritage_sktsearch") for step in steps)


def test_devanagari_to_velthuis_canonical() -> None:
    steps: list[NormalizationStep] = []
    normalizer = SanskritNormalizer()
    candidates = normalizer.canonical_candidates("शिव", steps)

    lemmas = [c.lemma.lower() for c in candidates]
    assert "ziva" in lemmas, lemmas
    assert any(step.operation == "to_heritage_velthuis" for step in steps)


def test_iast_to_velthuis_canonical() -> None:
    steps: list[NormalizationStep] = []
    normalizer = SanskritNormalizer()
    candidates = normalizer.canonical_candidates("śiva", steps)

    lemmas = [c.lemma.lower() for c in candidates]
    assert "ziva" in lemmas, lemmas
    assert any(step.operation == "to_heritage_velthuis" for step in steps)


def test_normalization_service_uses_index(tmp_path: Path) -> None:
    db_path = tmp_path / "norm.duckdb"
    conn = duckdb.connect(database=str(db_path))
    service = NormalizationService(conn, heritage_client=_FakeHeritage())

    first = service.normalize("shiva", LanguageHint.SAN)
    lemmas = [c.lemma for c in first.normalized.candidates]
    assert "ziva" in lemmas

    cached = service.index.get(first.query_hash)
    assert cached is not None
    assert [c.lemma for c in cached.candidates] == [c.lemma for c in first.normalized.candidates]

    second = service.normalize("shiva", LanguageHint.SAN)
    assert [c.lemma for c in second.normalized.candidates] == [c.lemma for c in cached.candidates]


def test_greek_normalizer_uses_diogenes_wordlist() -> None:
    normalizer = QueryNormalizer(diogenes_greek_client=_FakeDiogenes())
    result = normalizer.normalize("λόγος", LanguageHint.GRC)
    lemmas = [c.lemma for c in result.normalized.candidates]
    assert "λόγος" in lemmas
    assert any("diogenes_word_list" in c.sources for c in result.normalized.candidates)
    assert any(step.operation == "diogenes_word_list" for step in result.normalized.normalizations)


def test_latin_normalizer_uses_diogenes_parse() -> None:
    normalizer = QueryNormalizer(
        diogenes_latin_client=_FakeDiogenes(), whitaker_client=_FakeWhitaker()
    )
    result = normalizer.normalize("lupus", LanguageHint.LAT)
    lemmas = [c.lemma for c in result.normalized.candidates]
    assert "lupus" in lemmas
    assert any("diogenes_parse" in c.sources for c in result.normalized.candidates)
    assert any(c.sources == ["whitakers"] for c in result.normalized.candidates)
