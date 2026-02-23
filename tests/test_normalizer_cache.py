from __future__ import annotations

import tempfile
from pathlib import Path
from typing import cast

import duckdb
from query_spec import LanguageHint, NormalizedQuery

from langnet.diogenes.client import DiogenesClient, WordListResult
from langnet.normalizer.core import _hash_query
from langnet.normalizer.service import DiogenesConfig, NormalizationService
from langnet.storage.normalization_index import NormalizationIndex, ensure_schema as ensure_norm_schema


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
