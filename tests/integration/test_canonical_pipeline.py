from __future__ import annotations

import contextlib
import unittest
from pathlib import Path

import requests
from query_spec import LanguageHint  # noqa: E402

from langnet.pipeline.canonical import CanonicalPipeline  # noqa: E402
from tests.integration.utils import Wiring  # noqa: E402

DIOGENES_URL = "http://localhost:8888/Diogenes.cgi"
HERITAGE_URL = "http://localhost:48080/cgi-bin/skt/sktreader"
SERVICE_DOWN_THRESHOLD = 500


def _service_available(url: str) -> bool:
    try:
        resp = requests.get(url, timeout=3)
        return resp.status_code < SERVICE_DOWN_THRESHOLD
    except Exception:
        return False


class CanonicalPipelineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.db_path = Path("tmp/canonical.duckdb")
        self.db_path.parent.mkdir(exist_ok=True)
        if self.db_path.exists():
            self.db_path.unlink()

    def tearDown(self) -> None:
        if self.db_path.exists():
            with contextlib.suppress(Exception):
                self.db_path.unlink()

    def test_greek_pipeline_uses_diogenes_word_list(self) -> None:
        if not _service_available(DIOGENES_URL):
            self.skipTest("Diogenes service not available on localhost:8888")

        with Wiring(self.db_path) as wiring:
            pipeline = CanonicalPipeline(
                norm_service=wiring.norm_service,
                raw_index=wiring.raw_index,
                extraction_index=wiring.extraction_index,
                diogenes_base=DIOGENES_URL,
            )
            result = pipeline.lookup("logos", LanguageHint.LANGUAGE_HINT_GRC)
            self.assertTrue(result.candidates, "Should produce structured candidates")
            self.assertTrue(any("λογ" in c.lemma for c in result.candidates))
            self.assertTrue(result.responses, "Should store raw response")
            self.assertTrue(result.extractions, "Should store extraction")
            self.assertTrue(result.selected, "Should select a canonical")

    def test_sanskrit_pipeline_hits_heritage(self) -> None:
        heritage_probe = f"{HERITAGE_URL}?text=agni;t=VH;max=3"
        if not _service_available(heritage_probe):
            self.skipTest("Heritage service not available on localhost:48080")

        with Wiring(self.db_path) as wiring:
            pipeline = CanonicalPipeline(
                norm_service=wiring.norm_service,
                raw_index=wiring.raw_index,
                extraction_index=wiring.extraction_index,
                heritage_base=HERITAGE_URL,
            )
            result = pipeline.lookup("krishna", LanguageHint.LANGUAGE_HINT_SAN)
            self.assertTrue(result.responses, "Should store heritage raw response")
            self.assertTrue(result.selected, "Should select a canonical")
            self.assertTrue(any("devanagari" in c.encodings for c in result.candidates))

    def test_latin_pipeline_prefers_diogenes_parse(self) -> None:
        if not _service_available(DIOGENES_URL):
            self.skipTest("Diogenes service not available on localhost:8888")

        with Wiring(self.db_path) as wiring:
            pipeline = CanonicalPipeline(
                norm_service=wiring.norm_service,
                raw_index=wiring.raw_index,
                extraction_index=wiring.extraction_index,
                diogenes_base=DIOGENES_URL,
            )
            result = pipeline.lookup("portas", LanguageHint.LANGUAGE_HINT_LAT)
            # Expect a lemma around 'porta' or 'porto' from diogenes parse (accentless)
            self.assertTrue(
                any(
                    c.lemma.startswith("porta") or c.lemma.startswith("porto")
                    for c in result.candidates
                )
            )
            self.assertTrue(result.selected, "Should select a canonical")
