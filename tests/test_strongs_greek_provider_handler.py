from __future__ import annotations

import tempfile
from pathlib import Path

import orjson
from query_spec import ToolCallSpec

from langnet.clients.base import RawResponseEffect
from langnet.databuild.strongs_greek import StrongsGreekBuildConfig, StrongsGreekBuilder
from langnet.execution import predicates
from langnet.execution.handlers.strongs_greek import (
    StrongsGreekFetchClient,
    claim_strongs_greek_entries,
    derive_strongs_greek_entries,
    extract_strongs_greek_json,
    strongs_greek_entry_triples,
)

SAMPLE_XML = """<?xml version="1.0" encoding="UTF-8"?>
<entries>
  <entry strongs="02268">
    <strongs>2268</strongs>
    <greek BETA="*(HSAI/+AS" unicode="Ἡσαΐας" translit="Hēsaḯas"/>
    <pronunciation strongs="hay-sah-ee'-as"/>
    <strongs_derivation>of Hebrew origin (
      <strongsref language="HEBREW" strongs="03470"/>
    );</strongs_derivation>
    <strongs_def>Hesaias (i.e. Jeshajah), an Israelite</strongs_def>
    <kjv_def>Esaias.</kjv_def>
  </entry>
</entries>
"""


def _build_strongs_db(tmpdir: str) -> Path:
    base = Path(tmpdir)
    source = base / "strongsgreek.xml"
    output = base / "lex_strongs_greek.duckdb"
    source.write_text(SAMPLE_XML, encoding="utf-8")
    result = StrongsGreekBuilder(
        StrongsGreekBuildConfig(source_path=source, output_path=output)
    ).build()
    assert result.status.value == "success", result.message
    return output


def test_strongs_greek_fetch_client_returns_local_entry_for_inflected_form() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = _build_strongs_db(tmpdir)

        raw = StrongsGreekFetchClient(db_path=db_path).execute(
            "strongs-fetch-1",
            "duckdb://strongs_greek",
            params={"headword": "Ἠσαίᾳ"},
        )

    body = orjson.loads(raw.body)
    assert body["matched_headword"] == "Ἡσαΐᾳ"
    assert len(body["entries"]) == 1
    assert body["entries"][0]["strongs_number"] == "G2268"
    assert body["entries"][0]["lemma_unicode"] == "Ἡσαΐας"


def test_claim_strongs_greek_entries_emits_english_gloss_triples() -> None:
    raw = RawResponseEffect(
        response_id="raw-strongs-1",
        tool="fetch.strongs_greek",
        call_id="strongs-greek-1",
        endpoint="duckdb://strongs_greek",
        status_code=200,
        content_type="application/json",
        headers={},
        body=orjson.dumps(
            {
                "headwords": ["Ἠσαίᾳ"],
                "matched_headword": "Ἡσαΐᾳ",
                "entries": [
                    {
                        "entry_id": "strongs-greek:G2268",
                        "strongs_number": "G2268",
                        "lemma_unicode": "Ἡσαΐας",
                        "lemma_beta": "*(HSAI/+AS",
                        "lemma_translit": "Hēsaḯas",
                        "pronunciation": "hay-sah-ee'-as",
                        "derivation": "of Hebrew origin",
                        "definition": "Hesaias (i.e. Jeshajah), an Israelite",
                        "kjv_definition": "Esaias.",
                        "display_gloss": (
                            "of Hebrew origin; Hesaias (i.e. Jeshajah), an Israelite; KJV: Esaias."
                        ),
                        "entry_hash": "hash-isaiah",
                        "matched_alias_display": "Ἡσαΐᾳ",
                        "matched_alias_kind": "generated_form",
                    }
                ],
            }
        ),
    )
    extraction = extract_strongs_greek_json(
        ToolCallSpec(
            tool="extract.strongs_greek.json",
            call_id="strongs-greek-extract-1",
            params={"source_call_id": "strongs-greek-1"},
        ),
        raw,
    )
    derivation = derive_strongs_greek_entries(
        ToolCallSpec(
            tool="derive.strongs_greek.entries",
            call_id="strongs-greek-derive-1",
            params={"source_call_id": "strongs-greek-extract-1"},
        ),
        extraction,
    )
    claim = claim_strongs_greek_entries(
        ToolCallSpec(
            tool="claim.strongs_greek.entries",
            call_id="claim-strongs-greek-1",
            params={"source_call_id": "strongs-greek-derive-1"},
        ),
        derivation,
    )

    assert isinstance(claim.value, dict)
    triples = claim.value["triples"]
    assert any(
        triple["subject"] == "lex:ησαιασ" and triple["predicate"] == predicates.HAS_SENSE
        for triple in triples
    )
    gloss_triple = next(triple for triple in triples if triple["predicate"] == predicates.GLOSS)
    metadata = gloss_triple["metadata"]
    evidence = metadata["evidence"]
    assert "Hesaias" in gloss_triple["object"]
    assert metadata["source_lang"] == "en"
    assert evidence["source_tool"] == "strongs_greek"
    assert evidence["source_ref"] == "strongs_greek:G2268"
    assert metadata["source_entry"]["dict"] == "strongs_greek"


def test_strongs_greek_entry_triples_include_matched_alias_and_source_segments() -> None:
    triples = strongs_greek_entry_triples(
        {
            "entry_id": "strongs-greek:G2268",
            "strongs_number": "G2268",
            "lemma_unicode": "Ἡσαΐας",
            "lemma_beta": "*(HSAI/+AS",
            "lemma_translit": "Hēsaḯas",
            "definition": "Hesaias (i.e. Jeshajah), an Israelite",
            "display_gloss": "Hesaias (i.e. Jeshajah), an Israelite",
            "matched_alias_display": "Ἡσαΐᾳ",
            "matched_alias_kind": "generated_form",
            "entry_hash": "hash-isaiah",
        }
    )

    gloss_triple = next(triple for triple in triples if triple["predicate"] == predicates.GLOSS)
    metadata = gloss_triple["metadata"]
    assert metadata["source_lang"] == "en"
    assert metadata["source_segments"]
    assert metadata["source_entry"]["matched_alias_display"] == "Ἡσαΐᾳ"
    assert metadata["source_entry"]["matched_alias_kind"] == "generated_form"
