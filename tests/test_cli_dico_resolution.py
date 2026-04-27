from __future__ import annotations

import tempfile
from pathlib import Path

import duckdb
import orjson
from query_spec import ToolCallSpec

from langnet.clients.base import RawResponseEffect
from langnet.execution.handlers.dico import (
    DicoFetchClient,
    claim_dico_entries,
    derive_dico_entries,
    dico_entry_triples,
    expand_dico_headword_candidates,
    extract_dico_json,
    extract_dico_refs_from_claims,
    lookup_dico_entries,
    lookup_dico_entries_by_headword,
)


class _Claim:
    def __init__(self, value: dict) -> None:
        self.value = value


def test_extract_dico_refs_from_heritage_morphology() -> None:
    claims = [
        _Claim(
            {
                "triples": [
                    {
                        "subject": "form:dharma",
                        "predicate": "has_morphology",
                        "object": {
                            "lemma": "dharman",
                            "dictionary_url": "/skt/DICO/34.html#dharma",
                        },
                    },
                    {
                        "subject": "form:dharman",
                        "predicate": "has_morphology",
                        "object": {
                            "lemma": "dharman",
                            "dictionary_url": "/skt/DICO/34.html#dharman",
                        },
                    },
                ]
            }
        )
    ]

    assert extract_dico_refs_from_claims(claims) == [("34", "dharma"), ("34", "dharman")]


def test_extract_dico_refs_preserves_numbered_anchor_suffix() -> None:
    claims = [
        _Claim(
            {
                "triples": [
                    {
                        "subject": "form:nirudha",
                        "predicate": "has_morphology",
                        "object": {
                            "lemma": "nirūḍha",
                            "dictionary_url": "/skt/DICO/36.html#niruu.dha#1",
                        },
                    }
                ]
            }
        )
    ]

    assert extract_dico_refs_from_claims(claims) == [("36", "niruu.dha#1")]


def test_lookup_dico_entries_by_page_and_anchor() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "lex_dico.duckdb"
        with duckdb.connect(str(db_path)) as conn:
            conn.execute(
                """
                CREATE TABLE entries_fr (
                    entry_id VARCHAR,
                    occurrence INTEGER,
                    headword_deva VARCHAR,
                    headword_roma VARCHAR,
                    headword_norm VARCHAR,
                    plain_text VARCHAR,
                    source_page VARCHAR
                )
                """
            )
            conn.execute(
                """
                INSERT INTO entries_fr VALUES
                ('dharma', 0, 'धर्म', 'dharma', 'dharma', 'loi, condition', '34')
                """
            )

        entries = lookup_dico_entries([("34", "dharma")], db_path)

    assert len(entries) == 1
    assert entries[0]["entry_id"] == "dharma"
    assert entries[0]["plain_text"] == "loi, condition"


def test_lookup_dico_entries_by_headword_candidates() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "lex_dico.duckdb"
        with duckdb.connect(str(db_path)) as conn:
            conn.execute(
                """
                CREATE TABLE entries_fr (
                    entry_id VARCHAR,
                    occurrence INTEGER,
                    headword_deva VARCHAR,
                    headword_roma VARCHAR,
                    headword_norm VARCHAR,
                    plain_text VARCHAR,
                    source_page VARCHAR
                )
                """
            )
            conn.execute(
                """
                INSERT INTO entries_fr VALUES
                ('k.r.s.na', 0, 'कृष्ण', 'kṛṣṇa', 'k.r.s.na', 'noir, bleu-noir', '42')
                """
            )

        entries = lookup_dico_entries_by_headword(["kṛṣṇa", "k.r.s.na"], db_path)

    assert len(entries) == 1
    assert entries[0]["entry_id"] == "k.r.s.na"


def test_lookup_dico_entries_by_headword_strips_numbered_anchor_suffix() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "lex_dico.duckdb"
        with duckdb.connect(str(db_path)) as conn:
            conn.execute(
                """
                CREATE TABLE entries_fr (
                    entry_id VARCHAR,
                    occurrence INTEGER,
                    headword_deva VARCHAR,
                    headword_roma VARCHAR,
                    headword_norm VARCHAR,
                    plain_text VARCHAR,
                    source_page VARCHAR
                )
                """
            )
            conn.execute(
                """
                INSERT INTO entries_fr VALUES
                ('niruu.dha#1', 0, 'निरूढ', 'nirūḍha_1', 'niruu.dha', 'tiré, séparé', '36'),
                ('niruu.dha#2', 0, 'निरूढ', 'nirūḍha_2', 'niruu.dha', 'développé, mûr', '36')
                """
            )

        entries = lookup_dico_entries_by_headword(["niruu.dha#1"], db_path)

    assert [entry["entry_id"] for entry in entries] == ["niruu.dha#1", "niruu.dha#2"]


def test_dico_fetch_client_uses_content_addressed_response_ids() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "lex_dico.duckdb"
        with duckdb.connect(str(db_path)) as conn:
            conn.execute(
                """
                CREATE TABLE entries_fr (
                    entry_id VARCHAR,
                    occurrence INTEGER,
                    headword_deva VARCHAR,
                    headword_roma VARCHAR,
                    headword_norm VARCHAR,
                    plain_text VARCHAR,
                    source_page VARCHAR
                )
                """
            )
            conn.execute(
                """
                INSERT INTO entries_fr VALUES
                ('dharma', 0, 'धर्म', 'dharma', 'dharma', 'loi, condition', '34')
                """
            )

        client = DicoFetchClient(db_path)
        first = client.execute(
            call_id="dico-fetch-1",
            endpoint="duckdb://dico",
            params={"headword": "dharma"},
        )
        second = client.execute(
            call_id="dico-fetch-2",
            endpoint="duckdb://dico",
            params={"headword": "dharma"},
        )

    assert first.response_id == second.response_id
    assert first.response_id.startswith("raw-fetch-dico-")
    assert first.body == second.body


def test_expand_dico_headword_candidates_adds_velthuis() -> None:
    assert "k.r.s.na" in expand_dico_headword_candidates(["kṛṣṇa"])


def test_expand_dico_headword_candidates_adds_base_anchor() -> None:
    candidates = expand_dico_headword_candidates(["niruu.dha#1"])

    assert "niruu.dha#1" in candidates
    assert "niruu.dha" in candidates


def test_dico_entry_triples_mark_source_language_and_evidence() -> None:
    triples = dico_entry_triples(
        {
            "entry_id": "dharma",
            "occurrence": 0,
            "headword_norm": "dharma",
            "plain_text": "loi, condition",
            "source_page": "34",
        }
    )

    assert triples[0]["predicate"] == "has_sense"
    assert triples[1]["predicate"] == "gloss"
    assert triples[1]["object"] == "loi, condition"
    assert triples[1]["metadata"]["source_lang"] == "fr"
    assert triples[1]["metadata"]["evidence"]["source_tool"] == "dico"
    assert triples[1]["metadata"]["display_gloss"] == "loi, condition"
    assert triples[1]["metadata"]["source_entry"] == {
        "dict": "dico",
        "source_ref": "dico:34.html#dharma:0",
        "entry_id": "dharma",
        "occurrence": 0,
        "source_page": "34",
        "headword_norm": "dharma",
        "source_text": "loi, condition",
    }
    assert triples[1]["metadata"]["source_segments"] == [
        {
            "index": 0,
            "raw_text": "loi, condition",
            "display_text": "loi, condition",
            "segment_type": "definition_segment",
            "labels": ["definition"],
        }
    ]


def test_dico_staged_handlers_emit_claim_triples() -> None:
    extract_call = ToolCallSpec(
        tool="extract.dico.json",
        call_id="dico-extract-1",
        params={"source_call_id": "dico-1"},
    )
    raw = RawResponseEffect(
        response_id="raw-dico-1",
        tool="fetch.dico",
        call_id="dico-1",
        endpoint="duckdb://dico",
        status_code=200,
        content_type="application/json",
        headers={},
        body=orjson.dumps(
            {
                "headwords": ["dharma"],
                "entries": [
                    {
                        "entry_id": "dharma",
                        "occurrence": 0,
                        "headword_norm": "dharma",
                        "plain_text": "loi, condition",
                        "source_page": "34",
                    }
                ],
            }
        ),
    )
    extraction = extract_dico_json(extract_call, raw)
    derive_call = ToolCallSpec(
        tool="derive.dico.entries",
        call_id="dico-derive-1",
        params={"source_call_id": "dico-extract-1"},
    )
    derivation = derive_dico_entries(derive_call, extraction)
    claim_call = ToolCallSpec(
        tool="claim.dico.entries",
        call_id="claim-dico-1",
        params={"source_call_id": "dico-derive-1"},
    )

    claim = claim_dico_entries(claim_call, derivation)

    assert claim.tool == "claim.dico.entries"
    assert claim.subject == "lex:dharma"
    assert isinstance(claim.value, dict)
    triples = claim.value["triples"]
    assert len(triples) == 2  # noqa: PLR2004
    assert triples[1]["metadata"]["source_lang"] == "fr"
