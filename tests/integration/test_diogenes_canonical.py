from __future__ import annotations

import sys
import unittest
from pathlib import Path

import duckdb
import requests

BASE_DIR = Path(__file__).resolve().parents[2]
SCHEMA_PATH = BASE_DIR / "vendor" / "langnet-spec" / "generated" / "python"
sys.path.insert(0, str(SCHEMA_PATH))

from langnet.clients import HttpToolClient  # noqa: E402
from langnet.diogenes.adapter import DiogenesWordListAdapter  # noqa: E402
from langnet.storage.effects_index import RawResponseIndex, apply_schema  # noqa: E402
from langnet.storage.extraction_index import ExtractionIndex  # noqa: E402

DIOGENES_WORDLIST_URL = "http://localhost:8888/Diogenes.cgi"
SERVICE_DOWN_THRESHOLD = 500


def _service_available(url: str) -> bool:
    try:
        resp = requests.get(url, timeout=3)
        return resp.status_code < SERVICE_DOWN_THRESHOLD
    except Exception:
        return False


class DiogenesCanonicalTests(unittest.TestCase):
    def test_word_list_matches_canonical_accentless(self) -> None:
        if not _service_available(DIOGENES_WORDLIST_URL):
            self.skipTest("Diogenes service not available on localhost:8888")

        conn = duckdb.connect(database=":memory:")
        apply_schema(conn)
        raw_index = RawResponseIndex(conn)
        extract_index = ExtractionIndex(conn)

        client = HttpToolClient(tool="diogenes")
        adapter = DiogenesWordListAdapter(
            client=client,
            raw_index=raw_index,
            extraction_index=extract_index,
            endpoint=DIOGENES_WORDLIST_URL,
        )

        result = adapter.fetch(
            call_id="dg-logos", query="logos", canonical_targets=["logos", "λογος"]
        )
        self.assertTrue(result.lemmas, "Should parse lemmas from diogenes word_list")
        # Accept accented lemma match to accentless target
        self.assertTrue(result.matched or any("λογ" in lemma.lower() for lemma in result.lemmas))
        # Ensure extraction stored
        rows = list(extract_index.get_by_canonical(result.canonical or "logos"))
        self.assertTrue(rows)
