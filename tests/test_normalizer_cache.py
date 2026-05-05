from __future__ import annotations

import tempfile
from pathlib import Path
from typing import cast

import duckdb
from query_spec import CanonicalCandidate, LanguageHint, NormalizedQuery

from langnet.diogenes.client import DiogenesClient, WordListResult
from langnet.normalizer.core import _hash_query
from langnet.normalizer.service import DiogenesConfig, NormalizationService
from langnet.storage.normalization_index import (
    NormalizationIndex,
)
from langnet.storage.normalization_index import (
    ensure_schema as ensure_norm_schema,
)


class GreekDiogenes:
    def __init__(
        self,
        *,
        parse_lemmas: list[str] | None = None,
        word_list_lemmas: list[str] | None = None,
    ):
        self.parse_lemmas = parse_lemmas or []
        self.word_list_lemmas = word_list_lemmas or []
        self.parse_queries: list[str] = []
        self.word_list_queries: list[str] = []

    def fetch_parse(self, query: str, lang: str = "grc"):
        from langnet.diogenes.client import ParseResult  # noqa: PLC0415

        self.parse_queries.append(query)
        return ParseResult(query=query, lemmas=self.parse_lemmas, matched=bool(self.parse_lemmas))

    def fetch_word_list(self, query: str, limit: int = 50) -> WordListResult:
        self.word_list_queries.append(query)
        return WordListResult(
            query=query,
            lemmas=self.word_list_lemmas,
            matched=bool(self.word_list_lemmas),
        )


class GreekEpicEusDiogenes:
    def fetch_parse(self, query: str, lang: str = "grc"):
        from langnet.diogenes.client import ParseResult  # noqa: PLC0415

        if query == "ἀχιλλεύς":
            return ParseResult(query=query, lemmas=["αχιλλευς"], matched=True)
        return ParseResult(query=query, lemmas=["αχιλλειος"], matched=True)

    def fetch_word_list(self, query: str, limit: int = 50) -> WordListResult:
        lemmas_by_query = {
            "ἀχιλῆος": ["ἀχιλῆος"],
            "ἀχιλεύς": [],
            "ἀχιλλεύς": ["ἀχιλλεύς"],
        }
        lemmas = lemmas_by_query.get(query, [])
        return WordListResult(query=query, lemmas=lemmas, matched=bool(lemmas))


class CountingDiogenes:
    def __init__(self, lemmas: list[str]):
        self.lemmas = lemmas
        self.calls = 0

    def fetch_word_list(self, query: str, limit: int = 50) -> WordListResult:
        self.calls += 1
        return WordListResult(query=query, lemmas=self.lemmas, matched=bool(self.lemmas))


def test_normalizer_uses_cache_and_skips_diogenes_on_second_run() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "canon.duckdb"

        # First run: populate cache
        conn1 = duckdb.connect(str(db_path))
        dio1 = CountingDiogenes(["θεά"])
        svc1 = NormalizationService(
            conn1,
            diogenes_config=DiogenesConfig(greek_client=cast(DiogenesClient, dio1)),
            use_cache=True,
        )
        result1 = svc1.normalize("thea", LanguageHint.LANGUAGE_HINT_GRC)
        # Greek normalization may issue variant word_list calls; ensure at least one
        assert dio1.calls >= 1
        assert any(c.lemma == "θεά" for c in result1.normalized.candidates)
        conn1.close()

        # Second run (new process simulation): should hit cache, not call Diogenes
        conn2 = duckdb.connect(str(db_path))
        dio2 = CountingDiogenes(["SHOULD_NOT_BE_USED"])
        svc2 = NormalizationService(
            conn2,
            diogenes_config=DiogenesConfig(greek_client=cast(DiogenesClient, dio2)),
            use_cache=True,
        )
        result2 = svc2.normalize("thea", LanguageHint.LANGUAGE_HINT_GRC)
        assert dio2.calls == 0, "Cache miss caused Diogenes call on second run"
        assert any(c.lemma == "θεά" for c in result2.normalized.candidates)
        conn2.close()

        # Cache disabled: should call Diogenes even with existing db
        conn3 = duckdb.connect(str(db_path))
        dio3 = CountingDiogenes(["fresh"])
        svc3 = NormalizationService(
            conn3,
            diogenes_config=DiogenesConfig(greek_client=cast(DiogenesClient, dio3)),
            use_cache=False,
        )
        svc3.normalize("thea", LanguageHint.LANGUAGE_HINT_GRC)
        assert dio3.calls >= 1, "Cache disabled should force Diogenes call"
        conn3.close()


def test_cached_greek_results_are_reranked_with_freq() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "canon.duckdb"
        conn = duckdb.connect(str(db_path))
        ensure_norm_schema(conn)
        index = NormalizationIndex(conn)

        normalized = NormalizedQuery(original="phos", language=LanguageHint.LANGUAGE_HINT_GRC)
        low = normalized.candidates.add()
        low.lemma = "φος"
        low.encodings["freq"] = "24"
        high = normalized.candidates.add()
        high.lemma = "φῶς"
        high.encodings["freq"] = "13636"

        index.upsert(
            query_hash=_hash_query("phos", LanguageHint.LANGUAGE_HINT_GRC),
            raw_query="phos",
            language=str(LanguageHint.LANGUAGE_HINT_GRC).lower(),
            normalized=normalized,
            source_response_ids=None,
        )
        conn.close()

        conn_read = duckdb.connect(str(db_path))
        svc = NormalizationService(conn_read, use_cache=True)
        result = svc.normalize("phos", LanguageHint.LANGUAGE_HINT_GRC)

        candidates = list(result.normalized.candidates)
        assert candidates[0].lemma == "φῶς"
        conn_read.close()


def test_cached_latin_results_are_enriched_with_ae_to_a_candidate() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "canon.duckdb"
        conn = duckdb.connect(str(db_path))
        ensure_norm_schema(conn)
        index = NormalizationIndex(conn)

        normalized = NormalizedQuery(
            original="Troiae",
            language=LanguageHint.LANGUAGE_HINT_LAT,
            candidates=[
                CanonicalCandidate(lemma="troiades", encodings={}, sources=["diogenes_parse"])
            ],
        )
        index.upsert(
            query_hash=_hash_query("Troiae", LanguageHint.LANGUAGE_HINT_LAT),
            raw_query="Troiae",
            language=str(LanguageHint.LANGUAGE_HINT_LAT).lower(),
            normalized=normalized,
            source_response_ids=None,
        )
        conn.close()

        conn_read = duckdb.connect(str(db_path))
        svc = NormalizationService(conn_read, use_cache=True)
        result = svc.normalize("Troiae", LanguageHint.LANGUAGE_HINT_LAT)

        candidates = {candidate.lemma: candidate for candidate in result.normalized.candidates}
        assert "troia" in candidates
        assert candidates["troia"].sources == ["local_form_rule"]
        conn_read.close()


def test_ascii_greek_normalization_skips_raw_diogenes_parse() -> None:
    conn = duckdb.connect(database=":memory:")
    dio = GreekDiogenes(word_list_lemmas=["ἕν"])
    svc = NormalizationService(
        conn,
        diogenes_config=DiogenesConfig(greek_client=cast(DiogenesClient, dio)),
        use_cache=False,
    )

    result = svc.normalize("hen", LanguageHint.LANGUAGE_HINT_GRC)

    assert dio.parse_queries == []
    assert "hen" not in dio.word_list_queries
    assert dio.word_list_queries == ["ἕν"]
    assert result.normalized.candidates[0].lemma == "ἕν"
    conn.close()


def test_cached_ascii_greek_results_are_enriched_with_exact_transliteration() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "canon.duckdb"
        conn = duckdb.connect(str(db_path))
        ensure_norm_schema(conn)
        index = NormalizationIndex(conn)
        stale = NormalizedQuery(
            original="hen",
            language=LanguageHint.LANGUAGE_HINT_GRC,
            candidates=[CanonicalCandidate(lemma="εν", encodings={}, sources=["local"])],
        )
        index.upsert(
            query_hash=_hash_query("hen", LanguageHint.LANGUAGE_HINT_GRC),
            raw_query="hen",
            language=str(LanguageHint.LANGUAGE_HINT_GRC).lower(),
            normalized=stale,
            source_response_ids=None,
        )
        conn.close()

        conn_read = duckdb.connect(str(db_path))
        svc = NormalizationService(conn_read, use_cache=True)
        result = svc.normalize("hen", LanguageHint.LANGUAGE_HINT_GRC)

        assert result.normalized.candidates[0].lemma == "ἕν"
        conn_read.close()


def test_cached_homo_results_are_reranked_to_real_headword() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "canon.duckdb"
        conn = duckdb.connect(str(db_path))
        ensure_norm_schema(conn)
        index = NormalizationIndex(conn)
        stale = NormalizedQuery(
            original="homo",
            language=LanguageHint.LANGUAGE_HINT_GRC,
            candidates=[
                CanonicalCandidate(lemma="ὁμο.", encodings={}, sources=["diogenes_word_list"]),
                CanonicalCandidate(lemma="ὁμο", encodings={}, sources=["diogenes_word_list"]),
                CanonicalCandidate(lemma="ὁμός", encodings={}, sources=["diogenes_word_list"]),
            ],
        )
        index.upsert(
            query_hash=_hash_query("homo", LanguageHint.LANGUAGE_HINT_GRC),
            raw_query="homo",
            language=str(LanguageHint.LANGUAGE_HINT_GRC).lower(),
            normalized=stale,
            source_response_ids=None,
        )
        conn.close()

        conn_read = duckdb.connect(str(db_path))
        svc = NormalizationService(conn_read, use_cache=True)
        result = svc.normalize("homo", LanguageHint.LANGUAGE_HINT_GRC)

        assert result.normalized.candidates[0].lemma == "ὁμός"
        conn_read.close()


def test_cached_greek_compatibility_symbol_result_is_recomputed() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "canon.duckdb"
        conn = duckdb.connect(str(db_path))
        ensure_norm_schema(conn)
        index = NormalizationIndex(conn)
        stale = NormalizedQuery(
            original="ὄμϐρος",
            language=LanguageHint.LANGUAGE_HINT_GRC,
            candidates=[CanonicalCandidate(lemma="α-", encodings={}, sources=["diogenes_parse"])],
        )
        index.upsert(
            query_hash=_hash_query("ὄμϐρος", LanguageHint.LANGUAGE_HINT_GRC),
            raw_query="ὄμϐρος",
            language=str(LanguageHint.LANGUAGE_HINT_GRC).lower(),
            normalized=stale,
            source_response_ids=None,
        )
        conn.close()

        conn_read = duckdb.connect(str(db_path))
        dio = GreekDiogenes(parse_lemmas=["ombros"], word_list_lemmas=["ὄμβρος"])
        svc = NormalizationService(
            conn_read,
            diogenes_config=DiogenesConfig(greek_client=cast(DiogenesClient, dio)),
            use_cache=True,
        )
        result = svc.normalize("ὄμϐρος", LanguageHint.LANGUAGE_HINT_GRC)

        assert dio.parse_queries == ["ὄμβρος"]
        assert dio.word_list_queries == ["ὄμβρος"]
        assert "α-" not in [candidate.lemma for candidate in result.normalized.candidates]
        assert {candidate.lemma for candidate in result.normalized.candidates} >= {
            "ombros",
            "ὄμβρος",
        }
        conn_read.close()


def test_greek_rerank_prefers_lexical_sigma_candidate_over_surface_nu() -> None:
    conn = duckdb.connect(database=":memory:")
    svc = NormalizationService(
        conn,
        diogenes_config=DiogenesConfig(
            greek_client=cast(
                DiogenesClient,
                GreekDiogenes(parse_lemmas=["μηνιν", "μηνις"], word_list_lemmas=["μῆνιν"]),
            )
        ),
        use_cache=False,
    )

    result = svc.normalize("μῆνιν", LanguageHint.LANGUAGE_HINT_GRC)

    assert result.normalized.candidates[0].lemma == "μηνις"
    conn.close()


def test_greek_rerank_prefers_final_acute_lemma_for_grave_surface() -> None:
    conn = duckdb.connect(database=":memory:")
    svc = NormalizationService(
        conn,
        diogenes_config=DiogenesConfig(
            greek_client=cast(
                DiogenesClient,
                GreekDiogenes(parse_lemmas=["θεα"], word_list_lemmas=["θεά", "θέα", "θεα"]),
            )
        ),
        use_cache=False,
    )

    result = svc.normalize("θεὰ", LanguageHint.LANGUAGE_HINT_GRC)

    assert result.normalized.candidates[0].lemma == "θεά"
    conn.close()


def test_greek_rerank_prefers_validated_epic_eus_candidate() -> None:
    conn = duckdb.connect(database=":memory:")
    svc = NormalizationService(
        conn,
        diogenes_config=DiogenesConfig(greek_client=cast(DiogenesClient, GreekEpicEusDiogenes())),
        use_cache=False,
    )

    result = svc.normalize("Ἀχιλῆος", LanguageHint.LANGUAGE_HINT_GRC)

    assert result.normalized.candidates[0].lemma == "ἀχιλλεύς"
    conn.close()


def test_stale_cached_greek_epic_eus_result_is_recomputed() -> None:
    conn = duckdb.connect(database=":memory:")
    ensure_norm_schema(conn)
    index = NormalizationIndex(conn)
    stale = NormalizedQuery(
        original="Ἀχιλῆος",
        language=LanguageHint.LANGUAGE_HINT_GRC,
        candidates=[
            CanonicalCandidate(
                lemma="ἀχιλλειος",
                encodings={},
                sources=["diogenes_parse", "diogenes_word_list"],
            )
        ],
    )
    index.upsert(
        query_hash=_hash_query("Ἀχιλῆος", LanguageHint.LANGUAGE_HINT_GRC),
        raw_query="Ἀχιλῆος",
        language=str(LanguageHint.LANGUAGE_HINT_GRC).lower(),
        normalized=stale,
    )
    svc = NormalizationService(
        conn,
        diogenes_config=DiogenesConfig(greek_client=cast(DiogenesClient, GreekEpicEusDiogenes())),
        use_cache=True,
    )

    result = svc.normalize("Ἀχιλῆος", LanguageHint.LANGUAGE_HINT_GRC)

    lemmas = [candidate.lemma for candidate in result.normalized.candidates]
    assert result.normalized.candidates[0].lemma == "ἀχιλλεύς", lemmas
    assert "diogenes_word_list_epic_eus" in result.normalized.candidates[0].sources
    conn.close()
