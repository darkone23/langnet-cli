from __future__ import annotations

from collections.abc import Mapping
from typing import cast

import orjson
from query_spec import ToolStage

from langnet.clients.base import RawResponseEffect
from langnet.execution.handlers import cdsl
from tests.claim_contract import assert_claim_contract, claim_triples, find_triple, make_call


def test_cdsl_claim_preserves_source_ref_and_evidence() -> None:
    fetch_call = make_call(
        "fetch.cdsl",
        "fetch-cdsl",
        cast(ToolStage, ToolStage.TOOL_STAGE_FETCH),
        params={"lemma": "agni", "dict": "mw"},
        endpoint="duckdb://cdsl/mw",
    )
    rows = [
        {
            "key": "agni",
            "key2": "agni",
            "dict_id": "mw",
            "lnum": "123",
            "plain_text": "fire; sacrificial fire",
            "body": "<H><s>agni</s><lex>m.</lex></H>",
        }
    ]
    raw = RawResponseEffect(
        response_id="resp-cdsl",
        tool=fetch_call.tool,
        call_id=fetch_call.call_id,
        endpoint=fetch_call.endpoint,
        status_code=200,
        content_type="application/json",
        headers={},
        body=orjson.dumps(rows),
    )

    extract_call = make_call(
        "extract.cdsl.xml",
        "extract-cdsl",
        cast(ToolStage, ToolStage.TOOL_STAGE_EXTRACT),
        params={"source_call_id": fetch_call.call_id},
    )
    extraction = cdsl.extract_xml(extract_call, raw)

    derive_call = make_call(
        "derive.cdsl.sense",
        "derive-cdsl",
        cast(ToolStage, ToolStage.TOOL_STAGE_DERIVE),
        params={"source_call_id": extract_call.call_id},
    )
    derivation = cdsl.derive_sense(derive_call, extraction)

    claim_call = make_call(
        "claim.cdsl.sense",
        "claim-cdsl",
        cast(ToolStage, ToolStage.TOOL_STAGE_CLAIM),
        params={"source_call_id": derive_call.call_id},
    )
    claim = cdsl.claim_sense(claim_call, derivation)

    assert_claim_contract(claim)
    triples = claim_triples(claim)
    has_sense = find_triple(triples, "lex:agni", "has_sense")
    assert has_sense is not None
    sense_anchor = has_sense["object"]
    assert isinstance(sense_anchor, str)
    assert sense_anchor.startswith("sense:lex:agni#")

    gloss = find_triple(triples, sense_anchor, "gloss", "fire; sacrificial fire")
    assert gloss is not None
    metadata = gloss["metadata"]
    assert isinstance(metadata, Mapping)
    assert metadata["source_ref"] == "mw:123"
    evidence = metadata["evidence"]
    assert isinstance(evidence, Mapping)
    assert evidence["source_tool"] == "cdsl"
    assert evidence["source_ref"] == "mw:123"
    assert evidence["response_id"] == raw.response_id
    assert evidence["raw_blob_ref"] == "raw_json"
