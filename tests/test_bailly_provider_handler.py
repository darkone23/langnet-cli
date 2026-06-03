from __future__ import annotations

import tempfile
from pathlib import Path

import duckdb
import orjson
from query_spec import ToolCallSpec

from langnet.clients.base import RawResponseEffect
from langnet.databuild.bailly import apply_bailly_schema, insert_pdf_structural_entry
from langnet.execution import predicates
from langnet.execution.handlers.bailly import (
    BaillyFetchClient,
    bailly_entry_triples,
    claim_bailly_entries,
    derive_bailly_entries,
    extract_bailly_json,
)

AGELAIOS_PAGE = 90


def test_bailly_fetch_client_returns_local_entries() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "lex_bailly.duckdb"
        with duckdb.connect(str(db_path)) as conn:
            apply_bailly_schema(conn)
            insert_pdf_structural_entry(
                conn,
                {
                    "entry_id": "bailly-p090-c1-0004",
                    "lemma": "ἀγελαῖος",
                    "lemma_norm": "agelaios",
                    "source": {
                        "kind": "pdf",
                        "page_start": AGELAIOS_PAGE,
                        "page_end": AGELAIOS_PAGE,
                    },
                    "raw_text": "ἀγελαῖος, α, ον [ ᾰγ ] I qui forme un troupeau",
                    "blocks": [
                        {"path": "00", "marker": "head", "text": "ἀγελαῖος, α, ον [ ᾰγ ]"},
                        {"path": "01", "marker": "I", "text": "qui forme un troupeau"},
                    ],
                },
            )

        raw = BaillyFetchClient(db_path=db_path).execute(
            "bailly-fetch-1",
            "duckdb://bailly",
            params={"headword": "agelaios"},
        )
    body = orjson.loads(raw.body)

    assert len(body["entries"]) == 1
    entry = body["entries"][0]
    assert entry["lemma"] == "ἀγελαῖος"
    assert entry["page_start"] == AGELAIOS_PAGE
    assert [(block["path"], block["marker"]) for block in entry["blocks"]] == [
        ("00", "head"),
        ("01", "I"),
    ]


def test_claim_bailly_entries_emits_french_gloss_triples() -> None:
    extract_call = ToolCallSpec(
        tool="extract.bailly.json",
        call_id="bailly-extract-1",
        params={"source_call_id": "bailly-1"},
    )
    raw = RawResponseEffect(
        response_id="raw-bailly-1",
        tool="fetch.bailly",
        call_id="bailly-1",
        endpoint="duckdb://bailly",
        status_code=200,
        content_type="application/json",
        headers={},
        body=orjson.dumps(
            {
                "headwords": ["agelaios"],
                "entries": [
                    {
                        "entry_id": "bailly-p090-c1-0004",
                        "lemma": "ἀγελαῖος",
                        "lemma_norm": "agelaios",
                        "page_start": 90,
                        "page_end": 90,
                        "raw_text": "ἀγελαῖος, α, ον [ ᾰγ ] I qui forme un troupeau",
                        "blocks": [
                            {
                                "path": "00",
                                "marker": "head",
                                "text": "ἀγελαῖος, α, ον [ ᾰγ ]",
                            },
                            {"path": "01", "marker": "I", "text": "qui forme un troupeau"},
                        ],
                    }
                ],
            }
        ),
    )
    extraction = extract_bailly_json(extract_call, raw)
    derive_call = ToolCallSpec(
        tool="derive.bailly.entries",
        call_id="bailly-derive-1",
        params={"source_call_id": "bailly-extract-1"},
    )
    derivation = derive_bailly_entries(derive_call, extraction)
    claim_call = ToolCallSpec(
        tool="claim.bailly.entries",
        call_id="claim-bailly-1",
        params={"source_call_id": "bailly-derive-1"},
    )

    claim = claim_bailly_entries(claim_call, derivation)

    assert isinstance(claim.value, dict)
    triples = claim.value["triples"]
    assert any(
        triple["subject"] == "lex:agelaios" and triple["predicate"] == predicates.HAS_SENSE
        for triple in triples
    )
    gloss_triple = next(triple for triple in triples if triple["predicate"] == predicates.GLOSS)
    metadata = gloss_triple["metadata"]
    evidence = metadata["evidence"]
    source_entry = metadata["source_entry"]
    assert "qui forme un troupeau" in gloss_triple["object"]
    assert metadata["source_lang"] == "fr"
    assert evidence["source_tool"] == "bailly"
    assert evidence["source_ref"].startswith("bailly:")
    assert source_entry["dict"] == "bailly"


def test_bailly_fallback_match_sets_claim_subject_to_resolved_entry() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "lex_bailly.duckdb"
        with duckdb.connect(str(db_path)) as conn:
            apply_bailly_schema(conn)
            insert_pdf_structural_entry(
                conn,
                {
                    "entry_id": "bailly-p090-c1-0004",
                    "lemma": "ἀγελαῖος",
                    "lemma_norm": "agelaios",
                    "source": {
                        "kind": "pdf",
                        "page_start": AGELAIOS_PAGE,
                        "page_end": AGELAIOS_PAGE,
                    },
                    "raw_text": "ἀγελαῖος, α, ον [ ᾰγ ] I qui forme un troupeau",
                    "blocks": [
                        {"path": "00", "marker": "head", "text": "ἀγελαῖος, α, ον [ ᾰγ ]"},
                        {"path": "01", "marker": "I", "text": "qui forme un troupeau"},
                    ],
                },
            )

        raw = BaillyFetchClient(db_path=db_path).execute(
            "bailly-fetch-2",
            "duckdb://bailly",
            params={"headword": "missing-surface", "lemma": "agelaios"},
        )
    payload = orjson.loads(raw.body)
    extract_call = ToolCallSpec(
        tool="extract.bailly.json",
        call_id="bailly-extract-2",
        params={"source_call_id": "bailly-2"},
    )
    extraction = extract_bailly_json(extract_call, raw)
    derivation = derive_bailly_entries(
        ToolCallSpec(
            tool="derive.bailly.entries",
            call_id="bailly-derive-2",
            params={"source_call_id": "bailly-extract-2"},
        ),
        extraction,
    )
    claim = claim_bailly_entries(
        ToolCallSpec(
            tool="claim.bailly.entries",
            call_id="claim-bailly-2",
            params={"source_call_id": "bailly-derive-2"},
        ),
        derivation,
    )

    assert payload["matched_headword"] == "agelaios"
    assert extraction.canonical == "agelaios"
    assert claim.subject == "lex:agelaios"


def test_bailly_fetch_resolves_ascii_greekish_separator_candidates() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "lex_bailly.duckdb"
        with duckdb.connect(str(db_path)) as conn:
            apply_bailly_schema(conn)
            insert_pdf_structural_entry(
                conn,
                {
                    "entry_id": "bailly-p2258-c2-0016",
                    "lemma": "τελευταῖος",
                    "lemma_norm": "teleutaios",
                    "source": {"kind": "pdf", "page_start": 2258, "page_end": 2258},
                    "raw_text": "τελευταῖος, α, ον final",
                    "blocks": [
                        {"path": "00", "marker": "head", "text": "τελευταῖος, α, ον"},
                        {"path": "01", "marker": "I", "text": "final"},
                    ],
                },
            )

        raw = BaillyFetchClient(db_path=db_path).execute(
            "bailly-fetch-teleutaios",
            "duckdb://bailly",
            params={
                "headword": "teleutaiais",
                "lemma": "teleut_aios",
                "lemma_candidates": "teleut-aios;teleut_aios",
            },
        )

    payload = orjson.loads(raw.body)

    assert payload["matched_headword"] == "teleut_aios"
    assert payload["entries"][0]["lemma_norm"] == "teleutaios"


def test_bailly_fetch_skips_distant_greek_fallback_candidates() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "lex_bailly.duckdb"
        with duckdb.connect(str(db_path)) as conn:
            apply_bailly_schema(conn)
            insert_pdf_structural_entry(
                conn,
                {
                    "entry_id": "bailly-p1119-c1-0011",
                    "lemma": "ἥσθημα",
                    "lemma_norm": "hs1qhma",
                    "source": {
                        "kind": "pdf",
                        "page_start": 1119,
                        "page_end": 1119,
                    },
                    "raw_text": "ἥσθημα, ατος (τὸ) joy",
                    "blocks": [
                        {"path": "00", "marker": "head", "text": "ἥσθημα, ατος (τὸ)"},
                        {"path": "01", "marker": "I", "text": "joy"},
                    ],
                },
            )

        raw = BaillyFetchClient(db_path=db_path).execute(
            "bailly-fetch-isaiah",
            "duckdb://bailly",
            params={
                "headword": "Ἡσαΐας",
                "lemma": "ἡσαίας",
                "lemma_candidates": "ἡσαίας;ἠσαίας;ἡσαΐας;νησαίας;ησθημα",
            },
        )

    payload = orjson.loads(raw.body)

    assert payload["matched_headword"] is None
    assert payload["entries"] == []


def test_bailly_entry_without_id_gets_stable_generated_source_ref() -> None:
    triples = bailly_entry_triples(
        {
            "lemma": "ἀγελαῖος",
            "lemma_norm": "agelaios",
            "page_start": AGELAIOS_PAGE,
            "page_end": AGELAIOS_PAGE,
            "raw_text": "qui forme un troupeau",
            "blocks": [],
        }
    )

    gloss_triple = next(triple for triple in triples if triple["predicate"] == predicates.GLOSS)
    source_ref = gloss_triple["metadata"]["source_ref"]
    assert source_ref.startswith("bailly:generated:")
    assert source_ref != "bailly:None"
    assert gloss_triple["metadata"]["source_entry"]["source_ref"] == source_ref


def test_bailly_source_text_keeps_input_order_for_malformed_ordinals() -> None:
    triples = bailly_entry_triples(
        {
            "entry_id": "bailly-p090-c1-0004",
            "lemma": "ἀγελαῖος",
            "lemma_norm": "agelaios",
            "blocks": [
                {"marker": "I", "ordinal": "not-a-number", "text": "premier sens"},
                {"marker": "II", "text": "second sens"},
            ],
        }
    )

    gloss_triple = next(triple for triple in triples if triple["predicate"] == predicates.GLOSS)
    assert gloss_triple["object"] == "premier sens second sens"


def test_bailly_source_text_falls_back_to_raw_text_when_blocks_have_no_body() -> None:
    triples = bailly_entry_triples(
        {
            "entry_id": "bailly-p090-c1-0004",
            "lemma": "ἀγελαῖος",
            "lemma_norm": "agelaios",
            "raw_text": "ἀγελαῖος, α, ον [ ᾰγ ] I qui forme un troupeau",
            "blocks": [
                {"marker": "head", "ordinal": "bad", "text": "ἀγελαῖος, α, ον [ ᾰγ ]"},
            ],
        }
    )

    gloss_triple = next(triple for triple in triples if triple["predicate"] == predicates.GLOSS)
    assert "qui forme un troupeau" in gloss_triple["object"]
