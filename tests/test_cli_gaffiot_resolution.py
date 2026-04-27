from __future__ import annotations

import tempfile
from pathlib import Path

import duckdb
import orjson
from query_spec import ToolCallSpec

from langnet.clients.base import RawResponseEffect
from langnet.execution.handlers.gaffiot import (
    GaffiotFetchClient,
    claim_gaffiot_entries,
    derive_gaffiot_entries,
    extract_gaffiot_json,
    gaffiot_entry_triples,
    lookup_gaffiot_entries,
    lookup_gaffiot_entries_by_headword,
    normalize_gaffiot_headword,
)

EXPECTED_LUPUS_ENTRY_COUNT = 2
EXPECTED_SECOND_VARIANT = 2


def test_normalize_gaffiot_headword_strips_numbering_and_accents() -> None:
    assert normalize_gaffiot_headword("1 lūpus, ī") == "lupus"
    assert normalize_gaffiot_headword("Lœtus") == "loetus"


def test_lookup_gaffiot_entries_by_normalized_headword() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "lex_gaffiot.duckdb"
        with duckdb.connect(str(db_path)) as conn:
            conn.execute(
                """
                CREATE TABLE entries_fr (
                    entry_id VARCHAR,
                    headword_raw VARCHAR,
                    headword_norm VARCHAR,
                    variant_num INTEGER,
                    plain_text VARCHAR,
                    entry_hash VARCHAR
                )
                """
            )
            conn.execute(
                """
                INSERT INTO entries_fr VALUES
                ('gaffiot_1', '1 lupus', 'lupus', 1, 'ī, m., loup', 'hash-1'),
                ('gaffiot_2', '2 Lupus', 'lupus', 2, 'surnom', 'hash-2')
                """
            )

        entries = lookup_gaffiot_entries("lūpus", db_path)

    assert len(entries) == EXPECTED_LUPUS_ENTRY_COUNT
    assert entries[0]["entry_id"] == "gaffiot_1"
    assert entries[1]["variant_num"] == EXPECTED_SECOND_VARIANT


def test_lookup_gaffiot_entries_uses_later_lemma_candidate() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "lex_gaffiot.duckdb"
        with duckdb.connect(str(db_path)) as conn:
            conn.execute(
                """
                CREATE TABLE entries_fr (
                    entry_id VARCHAR,
                    headword_raw VARCHAR,
                    headword_norm VARCHAR,
                    variant_num INTEGER,
                    plain_text VARCHAR,
                    entry_hash VARCHAR
                )
                """
            )
            conn.execute(
                """
                INSERT INTO entries_fr VALUES
                ('gaffiot_1', '1 lupus', 'lupus', 1, 'ī, m., loup', 'hash-1')
                """
            )

        entries = lookup_gaffiot_entries_by_headword(["lupi", "lupus"], db_path)

    assert len(entries) == 1
    assert entries[0]["entry_id"] == "gaffiot_1"


def test_gaffiot_fetch_client_uses_content_addressed_response_ids() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "lex_gaffiot.duckdb"
        with duckdb.connect(str(db_path)) as conn:
            conn.execute(
                """
                CREATE TABLE entries_fr (
                    entry_id VARCHAR,
                    headword_raw VARCHAR,
                    headword_norm VARCHAR,
                    variant_num INTEGER,
                    plain_text VARCHAR,
                    entry_hash VARCHAR
                )
                """
            )
            conn.execute(
                """
                INSERT INTO entries_fr VALUES
                ('gaffiot_1', '1 lupus', 'lupus', 1, 'ī, m., loup', 'hash-1')
                """
            )

        client = GaffiotFetchClient(db_path)
        first = client.execute(
            call_id="gaffiot-fetch-1",
            endpoint="duckdb://gaffiot",
            params={"headword": "lupus"},
        )
        second = client.execute(
            call_id="gaffiot-fetch-2",
            endpoint="duckdb://gaffiot",
            params={"headword": "lupus"},
        )

    assert first.response_id == second.response_id
    assert first.response_id.startswith("raw-fetch-gaffiot-")
    assert first.body == second.body


def test_gaffiot_entry_triples_mark_source_language_and_evidence() -> None:
    triples = gaffiot_entry_triples(
        {
            "entry_id": "gaffiot_1",
            "headword_norm": "lupus",
            "variant_num": 1,
            "plain_text": "ī, m., loup",
            "entry_hash": "hash-1",
        }
    )

    assert triples[0]["predicate"] == "has_sense"
    assert triples[1]["predicate"] == "gloss"
    assert triples[1]["object"] == "ī, m., loup"
    assert triples[1]["metadata"]["source_lang"] == "fr"
    assert triples[1]["metadata"]["evidence"]["source_tool"] == "gaffiot"
    assert triples[1]["metadata"]["evidence"]["variant_num"] == 1
    assert triples[1]["metadata"]["display_gloss"] == "ī, m., loup"
    assert triples[1]["metadata"]["source_entry"] == {
        "dict": "gaffiot",
        "source_ref": "gaffiot:gaffiot_1",
        "entry_id": "gaffiot_1",
        "headword_norm": "lupus",
        "variant_num": 1,
        "entry_hash": "hash-1",
        "source_text": "ī, m., loup",
    }
    assert triples[1]["metadata"]["source_segments"] == [
        {
            "index": 0,
            "raw_text": "ī, m., loup",
            "display_text": "ī, m., loup",
            "segment_type": "definition_segment",
            "labels": ["definition"],
        }
    ]


def test_gaffiot_staged_handlers_emit_claim_triples() -> None:
    fetch_call = ToolCallSpec(
        tool="extract.gaffiot.json",
        call_id="gaffiot-extract-1",
        params={"source_call_id": "gaffiot-1"},
    )
    raw = RawResponseEffect(
        response_id="raw-gaffiot-1",
        tool="fetch.gaffiot",
        call_id="gaffiot-1",
        endpoint="duckdb://gaffiot",
        status_code=200,
        content_type="application/json",
        headers={},
        body=orjson.dumps(
            {
                "headword": "lupus",
                "entries": [
                    {
                        "entry_id": "gaffiot_1",
                        "headword_norm": "lupus",
                        "variant_num": 1,
                        "plain_text": "ī, m., loup",
                        "entry_hash": "hash-1",
                    }
                ],
            }
        ),
    )
    extraction = extract_gaffiot_json(fetch_call, raw)
    derive_call = ToolCallSpec(
        tool="derive.gaffiot.entries",
        call_id="gaffiot-derive-1",
        params={"source_call_id": "gaffiot-extract-1"},
    )
    derivation = derive_gaffiot_entries(derive_call, extraction)
    claim_call = ToolCallSpec(
        tool="claim.gaffiot.entries",
        call_id="claim-gaffiot-1",
        params={"source_call_id": "gaffiot-derive-1"},
    )

    claim = claim_gaffiot_entries(claim_call, derivation)

    assert claim.tool == "claim.gaffiot.entries"
    assert claim.subject == "lex:lupus"
    assert isinstance(claim.value, dict)
    triples = claim.value["triples"]
    assert len(triples) == EXPECTED_LUPUS_ENTRY_COUNT
    assert triples[1]["metadata"]["source_lang"] == "fr"
