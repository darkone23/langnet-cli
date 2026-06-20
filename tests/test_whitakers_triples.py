from __future__ import annotations

from typing import cast

from query_spec import ToolStage

from langnet.clients.base import RawResponseEffect
from langnet.execution.handlers import whitakers
from tests.claim_contract import assert_claim_contract, find_triple, make_call

WHITAKER_SAMPLE = """am.arem              V      1 1 IMPF ACTIVE  SUB 1 S    
amo, amare, amavi, amatus  V (1st)   [XXXAO]  
love, like; fall in love with; be fond of; have a tendency to;
"""

GAUDIUM_SAMPLE = """gaudi.um             N      2 4 NOM S N                 
gaudi.um             N      2 4 VOC S N                 
gaudi.um             N      2 4 ACC S N                 
gaudium, gaudi(i)  N (2nd) N   [XXXBO]  
joy, delight, gladness; source/cause of joy; physical/sensual delight;
everlasting blessedness; gaud/gaudy, bead of rosary (Latham);
*
"""


def test_whitaker_triples_projection() -> None:
    fetch_call = make_call(
        "fetch.whitakers",
        "fetch-ww",
        cast(ToolStage, ToolStage.TOOL_STAGE_FETCH),
        params={"q": "amarem", "word": "amarem"},
    )
    raw = RawResponseEffect(
        response_id="resp-ww",
        tool=fetch_call.tool,
        call_id=fetch_call.call_id,
        endpoint=fetch_call.endpoint,
        status_code=200,
        content_type="text/plain",
        headers={},
        body=WHITAKER_SAMPLE.encode("utf-8"),
    )

    extract_call = make_call(
        "extract.whitakers.lines",
        "extract-ww",
        cast(ToolStage, ToolStage.TOOL_STAGE_EXTRACT),
        params={"source_call_id": fetch_call.call_id},
    )
    extraction = whitakers.extract_lines(extract_call, raw)

    derive_call = make_call(
        "derive.whitakers.facts",
        "derive-ww",
        cast(ToolStage, ToolStage.TOOL_STAGE_DERIVE),
        params={"source_call_id": extract_call.call_id},
    )
    derivation = whitakers.derive_facts(derive_call, extraction)

    claim_call = make_call(
        "claim.whitakers",
        "claim-ww",
        cast(ToolStage, ToolStage.TOOL_STAGE_CLAIM),
        params={"source_call_id": derive_call.call_id},
    )
    claim = whitakers.claim_whitakers(claim_call, derivation)
    assert_claim_contract(claim)
    value = claim.value or {}
    triples = value.get("triples") or []

    lex_anchor = "lex:amo#verb"
    form_anchor = "form:amarem"
    interp_anchor = f"interp:form:amarem→{lex_anchor}"
    sense_txt = ""
    wordlist = value.get("wordlist") or []
    if wordlist and isinstance(wordlist[0], dict):
        senses = wordlist[0].get("senses") or []
        if senses:
            sense_txt = senses[0]
    assert sense_txt
    sense_anchor = whitakers._sense_anchor(lex_anchor, sense_txt)  # type: ignore[attr-defined]

    has_interp = find_triple(triples, form_anchor, "has_interpretation", interp_anchor)
    assert has_interp is not None
    realizes = find_triple(triples, interp_anchor, "realizes_lexeme", lex_anchor)
    assert realizes is not None
    assert find_triple(triples, interp_anchor, "has_pos", "verb") is not None
    assert find_triple(triples, interp_anchor, "has_tense", "imperfect") is not None
    assert find_triple(triples, interp_anchor, "has_mood", "subjunctive") is not None
    assert find_triple(triples, interp_anchor, "has_voice", "active") is not None
    assert find_triple(triples, interp_anchor, "has_person", "1") is not None
    assert find_triple(triples, interp_anchor, "has_number", "singular") is not None

    has_sense = find_triple(triples, lex_anchor, "has_sense", sense_anchor)
    assert has_sense is not None
    gloss_triple = find_triple(triples, sense_anchor, "gloss", sense_txt)
    assert gloss_triple is not None
    gloss_metadata = gloss_triple["metadata"]  # type: ignore[index]
    assert gloss_metadata["display_gloss"] == "love, like"
    assert gloss_metadata["learner_gloss"] == "love, like"
    assert gloss_metadata["source_segments"] == [
        {
            "index": 0,
            "raw_text": "love, like",
            "display_text": "love, like",
            "segment_type": "definition_segment",
            "labels": ["definition"],
        }
    ]
    assert gloss_metadata["source_entry"] == {
        "dictionary": "whitaker",
        "headword": "amo",
        "pos": "verb",
        "source_order": 0,
    }

    ev = has_interp["metadata"]["evidence"]  # type: ignore[index]
    assert ev["source_tool"] == "whitaker"
    assert ev["call_id"] == claim_call.call_id
    assert ev["derivation_id"] == derivation.derivation_id
    assert ev["extraction_id"] == extraction.extraction_id
    assert ev["claim_id"] == claim.claim_id
    assert ev["response_id"] == raw.response_id
    assert ev["raw_blob_ref"] == "raw_text"


def test_whitaker_parser_accumulates_multiline_senses() -> None:
    wordlist = whitakers._parse_whitaker_output(GAUDIUM_SAMPLE)  # type: ignore[attr-defined]

    assert len(wordlist) == 1
    assert wordlist[0]["senses"] == [
        "joy, delight, gladness",
        "source/cause of joy",
        "physical/sensual delight",
        "everlasting blessedness",
        "gaud/gaudy, bead of rosary (Latham)",
    ]
