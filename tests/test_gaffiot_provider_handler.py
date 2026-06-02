from __future__ import annotations

import tempfile
from pathlib import Path

import duckdb
import orjson

from langnet.databuild.gaffiot import SCHEMA_SQL
from langnet.execution.handlers.gaffiot import GaffiotFetchClient


def test_gaffiot_fetch_skips_distant_fallback_candidates() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "lex_gaffiot.duckdb"
        with duckdb.connect(str(db_path)) as conn:
            conn.execute(SCHEMA_SQL)
            conn.execute(
                """
                INSERT INTO entries_fr (
                    entry_id,
                    headword_raw,
                    headword_norm,
                    variant_num,
                    tei_xml,
                    plain_text,
                    entry_hash
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    "gaffiot:amo",
                    "amo",
                    "amo",
                    None,
                    "<entryFree><orth>amo</orth></entryFree>",
                    "aimer",
                    "hash-amo",
                ],
            )

        raw = GaffiotFetchClient(db_path=db_path).execute(
            "gaffiot-fetch-fallback",
            "duckdb://gaffiot",
            params={
                "headword": "lupus",
                "lemma": "lupus",
                "lemma_candidates": "lupus;amo",
            },
        )

    body = orjson.loads(raw.body)

    assert body["entries"] == []
