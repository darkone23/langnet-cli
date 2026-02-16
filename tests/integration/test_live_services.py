from __future__ import annotations

import unittest

import duckdb
import requests

from langnet.clients import HttpToolClient  # noqa: E402
from langnet.storage.effects_index import RawResponseIndex, apply_schema  # noqa: E402

HERITAGE_URL = "http://localhost:48080/cgi-bin/skt/sktreader"
DIOGENES_URL = "http://localhost:8888/Perseus.cgi"
SERVICE_DOWN_THRESHOLD = 500


def _service_available(url: str, params: dict[str, str]) -> bool:
    try:
        resp = requests.get(url, params=params, timeout=3)
        return resp.status_code < SERVICE_DOWN_THRESHOLD
    except Exception:
        return False


class LiveServiceTests(unittest.TestCase):
    def test_live_heritage_round_trip(self) -> None:
        heritage_query = "text=agni;t=VH;max=3"
        if not _service_available(f"{HERITAGE_URL}?{heritage_query}", {}):
            self.skipTest("Heritage service not available on localhost:48080")

        conn = duckdb.connect(database=":memory:")
        apply_schema(conn)
        raw_index = RawResponseIndex(conn)

        client = HttpToolClient(tool="heritage")
        effect = client.execute(call_id="heritage-1", endpoint=f"{HERITAGE_URL}?{heritage_query}")
        self.assertEqual(effect.status_code, 200, effect.body[:200])
        self.assertTrue(effect.body)

        ref = raw_index.store(effect)
        loaded = raw_index.get(ref.response_id)
        self.assertIsNotNone(loaded)
        if loaded is not None:
            self.assertEqual(loaded.body, effect.body)

    def test_live_diogenes_round_trip(self) -> None:
        if not _service_available(DIOGENES_URL, {"do": "parse", "lang": "lat", "q": "amo"}):
            self.skipTest("Diogenes service not available on localhost:8888")

        conn = duckdb.connect(database=":memory:")
        apply_schema(conn)
        raw_index = RawResponseIndex(conn)

        client = HttpToolClient(tool="diogenes")
        effect = client.execute(
            call_id="diogenes-1",
            endpoint=DIOGENES_URL,
            params={"do": "parse", "lang": "lat", "q": "amo"},
        )
        self.assertEqual(effect.status_code, 200)
        self.assertTrue(effect.body)

        ref = raw_index.store(effect)
        loaded = raw_index.get(ref.response_id)
        self.assertIsNotNone(loaded)
        if loaded is not None:
            self.assertEqual(loaded.body, effect.body)
