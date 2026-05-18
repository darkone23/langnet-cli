from __future__ import annotations

import tempfile
from pathlib import Path

import orjson
from query_spec import ToolCallSpec

from langnet.clients.base import RawResponseEffect
from langnet.databuild.lewis_1890 import Lewis1890BuildConfig, Lewis1890Builder
from langnet.execution import predicates
from langnet.execution.handlers.lewis_1890 import (
    Lewis1890FetchClient,
    claim_lewis_1890_entries,
    derive_lewis_1890_entries,
    extract_lewis_1890_json,
    lewis_1890_entry_triples,
)


def _build_lewis_db(tmpdir: str) -> Path:
    base = Path(tmpdir)
    source = base / "lewis.yaml"
    output = base / "lex_lewis_1890.duckdb"
    source.write_text(
        'lupus: "lupus ī, m a wolf: lupa, V.; lupus in fabula."\n'
        'amo: "amō āvī ātus āre, to love, like."\n',
        encoding="utf-8",
    )
    result = Lewis1890Builder(Lewis1890BuildConfig(source_path=source, output_path=output)).build()
    assert result.status.value == "success", result.message
    return output


def test_lewis_1890_fetch_client_returns_local_entries() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = _build_lewis_db(tmpdir)

        raw = Lewis1890FetchClient(db_path=db_path).execute(
            "lewis-fetch-1",
            "duckdb://lewis_1890",
            params={"headword": "lupus"},
        )

    body = orjson.loads(raw.body)
    assert body["matched_headword"] == "lupus"
    assert len(body["entries"]) == 1
    assert body["entries"][0]["source_key"] == "lupus"
    assert "wolf" in body["entries"][0]["plain_text"]


def test_claim_lewis_1890_entries_emits_english_gloss_triples() -> None:
    raw = RawResponseEffect(
        response_id="raw-lewis-1",
        tool="fetch.lewis_1890",
        call_id="lewis-1890-1",
        endpoint="duckdb://lewis_1890",
        status_code=200,
        content_type="application/json",
        headers={},
        body=orjson.dumps(
            {
                "headwords": ["lupus"],
                "matched_headword": "lupus",
                "entries": [
                    {
                        "entry_id": "lewis-1890:lupus",
                        "headword_raw": "lupus",
                        "headword_norm": "lupus",
                        "source_key": "lupus",
                        "plain_text": "lupus ī, m a wolf: lupa, V.; lupus in fabula.",
                        "entry_hash": "hash-lupus",
                    }
                ],
            }
        ),
    )
    extraction = extract_lewis_1890_json(
        ToolCallSpec(
            tool="extract.lewis_1890.json",
            call_id="lewis-1890-extract-1",
            params={"source_call_id": "lewis-1890-1"},
        ),
        raw,
    )
    derivation = derive_lewis_1890_entries(
        ToolCallSpec(
            tool="derive.lewis_1890.entries",
            call_id="lewis-1890-derive-1",
            params={"source_call_id": "lewis-1890-extract-1"},
        ),
        extraction,
    )
    claim = claim_lewis_1890_entries(
        ToolCallSpec(
            tool="claim.lewis_1890.entries",
            call_id="claim-lewis-1890-1",
            params={"source_call_id": "lewis-1890-derive-1"},
        ),
        derivation,
    )

    assert isinstance(claim.value, dict)
    triples = claim.value["triples"]
    assert any(
        triple["subject"] == "lex:lupus" and triple["predicate"] == predicates.HAS_SENSE
        for triple in triples
    )
    gloss_triple = next(triple for triple in triples if triple["predicate"] == predicates.GLOSS)
    metadata = gloss_triple["metadata"]
    evidence = metadata["evidence"]
    assert "wolf" in gloss_triple["object"]
    assert metadata["source_lang"] == "en"
    assert evidence["source_tool"] == "lewis_1890"
    assert evidence["source_ref"] == "lewis_1890:lupus"
    assert metadata["source_entry"]["dict"] == "lewis_1890"


def test_lewis_1890_entry_triples_include_source_segments() -> None:
    triples = lewis_1890_entry_triples(
        {
            "entry_id": "lewis-1890:lupus",
            "headword_raw": "lupus",
            "headword_norm": "lupus",
            "source_key": "lupus",
            "plain_text": "lupus ī, m a wolf: lupa, V.; lupus in fabula.",
            "entry_hash": "hash-lupus",
        }
    )

    gloss_triple = next(triple for triple in triples if triple["predicate"] == predicates.GLOSS)
    metadata = gloss_triple["metadata"]
    assert metadata["source_lang"] == "en"
    assert metadata["source_segments"]
    assert "wolf" in metadata["learner_gloss"]
