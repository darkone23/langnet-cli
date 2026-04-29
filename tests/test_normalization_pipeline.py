from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import duckdb
from heritage_spec import MonierWilliamsResult, SktSearchResult
from query_spec import LanguageHint, NormalizationStep

from langnet.diogenes.client import ParseResult, WordListResult
from langnet.normalizer.core import (
    QueryNormalizer,
    normalize_with_index,
)
from langnet.normalizer.sanskrit import HeritageClientProtocol, SanskritNormalizer
from langnet.normalizer.service import NormalizationService
from langnet.storage.normalization_index import NormalizationIndex, apply_schema


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
    result = normalize_with_index(normalizer, raw_query, LanguageHint.LANGUAGE_HINT_SAN, idx)

    loaded = idx.get(result.query_hash)
    assert loaded is not None
    assert loaded.original == raw_query
    lemmas = [c.lemma.lower() for c in loaded.candidates]
    assert any("ziva" in lemma for lemma in lemmas)
    assert loaded.normalizations, "Normalization steps should be recorded"

    result_cached = normalize_with_index(normalizer, raw_query, LanguageHint.LANGUAGE_HINT_SAN, idx)
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


class _GreekEpicEusDiogenes:
    def fetch_word_list(self, query: str) -> WordListResult:
        lemmas_by_query = {
            "ἀχιλῆος": ["ἀχιλῆος"],
            "ἀχιλεύς": [],
            "ἀχιλλεύς": ["ἀχιλλεύς"],
        }
        lemmas = lemmas_by_query.get(query, [])
        return WordListResult(query=query, lemmas=lemmas, matched=bool(lemmas))

    def fetch_parse(self, query: str, lang: str = "grc") -> ParseResult:
        if query == "ἀχιλλεύς":
            return ParseResult(query=query, lemmas=["αχιλλευς"], matched=True)
        return ParseResult(query=query, lemmas=["αχιλλειος"], matched=True)


class _FakeWhitaker:
    def fetch(self, query: str) -> list[str]:
        return ["is", "idem"]


class _TroiaeDiogenes:
    def fetch_parse(self, query: str, lang: str = "lat") -> ParseResult:
        return ParseResult(query=query, lemmas=["troiades"], matched=True)


class _NoWhitaker:
    def fetch(self, query: str) -> list[str]:
        return []


class _AmbiguousHeritage(_FakeHeritage):
    def fetch_all_matches(self, query: str) -> list[HeritageMatch]:
        return [
            HeritageMatch(canonical="zraaddha", display="śrāddha", entry_url=""),
            HeritageMatch(canonical="zraddhaa#1", display="śraddhā_1", entry_url=""),
            HeritageMatch(canonical="zraddhaa#2", display="śraddhā_2", entry_url=""),
        ]


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


def test_latin_normalizer_adds_ae_to_a_reader_form_candidate() -> None:
    normalizer = QueryNormalizer(
        diogenes_latin_client=_TroiaeDiogenes(),
        whitaker_client=_NoWhitaker(),
    )
    result = normalizer.normalize("Troiae", LanguageHint.LANGUAGE_HINT_LAT)

    candidates = {candidate.lemma: candidate for candidate in result.normalized.candidates}
    assert "troia" in candidates
    assert candidates["troia"].sources == ["local_form_rule"]
    assert candidates["troia"].encodings["latin_form_rule"] == "ae_to_a"


def test_greek_normalizer_adds_validated_epic_eus_candidate() -> None:
    normalizer = QueryNormalizer(diogenes_greek_client=_GreekEpicEusDiogenes())
    result = normalizer.normalize("Ἀχιλῆος", LanguageHint.LANGUAGE_HINT_GRC)

    candidates = {candidate.lemma: candidate for candidate in result.normalized.candidates}
    assert "ἀχιλλεύς" in candidates
    assert "diogenes_word_list_epic_eus" in candidates["ἀχιλλεύς"].sources
    assert "ἀχιλεύς" not in candidates


def test_sanskrit_normalizer_ranks_exact_display_match_before_related_forms() -> None:
    steps: list[NormalizationStep] = []
    normalizer = SanskritNormalizer(heritage_client=_AmbiguousHeritage())

    candidates = normalizer.canonical_candidates("śraddhā", steps)

    assert [candidate.lemma for candidate in candidates[:3]] == [
        "śraddhā_1",
        "śraddhā_2",
        "śrāddha",
    ]


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


def test_sanskrit_normalizer_handles_harvard_kyoto_retroflex_markers() -> None:
    normalizer = SanskritNormalizer()

    krsna_steps: list[NormalizationStep] = []
    krsna_candidates = normalizer.canonical_candidates("kRSNa", krsna_steps)
    krsna = krsna_candidates[0]
    assert krsna.encodings["velthuis"] == "k.r.s.na"
    assert krsna.encodings["slp1"] == "kfzRa"
    assert krsna.encodings["iast"] == "kṛṣṇa"
    assert any(step.operation == "detect_encoding" and step.output == "hk" for step in krsna_steps)

    visnu_steps: list[NormalizationStep] = []
    visnu_candidates = normalizer.canonical_candidates("viSNu", visnu_steps)
    visnu = visnu_candidates[0]
    assert visnu.encodings["velthuis"] == "vi.s.nu"
    assert visnu.encodings["slp1"] == "vizRu"
    assert visnu.encodings["iast"] == "viṣṇu"
    assert any(step.operation == "detect_encoding" and step.output == "hk" for step in visnu_steps)


def test_sanskrit_normalizer_still_accepts_slp1_cdsl_style_forms() -> None:
    steps: list[NormalizationStep] = []
    normalizer = SanskritNormalizer()
    candidates = normalizer.canonical_candidates("DarmaH", steps)

    candidate = candidates[0]
    assert candidate.encodings["velthuis"] == "dharma.h"
    assert candidate.encodings["slp1"] == "DarmaH"
    assert candidate.encodings["iast"] == "dharmaḥ"
    assert any(step.operation == "detect_encoding" and step.output == "slp1" for step in steps)


def test_normalization_service_uses_index(tmp_path: Path) -> None:
    db_path = tmp_path / "norm.duckdb"
    conn = duckdb.connect(database=str(db_path))
    service = NormalizationService(conn, heritage_client=_FakeHeritage())

    first = service.normalize("shiva", LanguageHint.LANGUAGE_HINT_SAN)
    lemmas = [c.lemma for c in first.normalized.candidates]
    assert "ziva" in lemmas

    cached = service.index.get(first.query_hash)
    assert cached is not None
    assert [c.lemma for c in cached.candidates] == [c.lemma for c in first.normalized.candidates]

    second = service.normalize("shiva", LanguageHint.LANGUAGE_HINT_SAN)
    assert [c.lemma for c in second.normalized.candidates] == [c.lemma for c in cached.candidates]


def test_greek_normalizer_uses_diogenes_wordlist() -> None:
    normalizer = QueryNormalizer(diogenes_greek_client=_FakeDiogenes())
    result = normalizer.normalize("λόγος", LanguageHint.LANGUAGE_HINT_GRC)
    lemmas = [c.lemma for c in result.normalized.candidates]
    assert "λόγος" in lemmas
    assert any("diogenes_word_list" in c.sources for c in result.normalized.candidates)
    assert any(step.operation == "diogenes_word_list" for step in result.normalized.normalizations)


def test_latin_normalizer_uses_diogenes_parse() -> None:
    normalizer = QueryNormalizer(
        diogenes_latin_client=_FakeDiogenes(), whitaker_client=_FakeWhitaker()
    )
    result = normalizer.normalize("lupus", LanguageHint.LANGUAGE_HINT_LAT)
    lemmas = [c.lemma for c in result.normalized.candidates]
    assert "lupus" in lemmas
    assert any("diogenes_parse" in c.sources for c in result.normalized.candidates)
    assert any(c.sources == ["whitakers"] for c in result.normalized.candidates)
