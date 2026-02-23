from __future__ import annotations

from query_spec import ToolCallSpec, ToolStage

from langnet.clients.base import RawResponseEffect
from langnet.execution.handlers import whitakers


WHITAKER_SAMPLE = """am.arem              V      1 1 IMPF ACTIVE  SUB 1 S    
amo, amare, amavi, amatus  V (1st)   [XXXAO]  
love, like; fall in love with; be fond of; have a tendency to;
"""


def _make_call(tool: str, call_id: str, stage: ToolStage, params: dict[str, str]) -> ToolCallSpec:
    return ToolCallSpec(tool=tool, call_id=call_id, endpoint="internal://test", params=params, stage=stage)


def _find_triple(triples: list[dict[str, object]], subject: str | None, predicate: str, obj: object | None = None):
    for triple in triples:
        if subject and triple.get("subject") != subject:
            continue
        if triple.get("predicate") != predicate:
            continue
        if obj is not None and triple.get("object") != obj:
            continue
        return triple
    return None


def test_whitaker_triples_projection() -> None:
    fetch_call = _make_call(
        "fetch.whitakers", "fetch-ww", ToolStage.TOOL_STAGE_FETCH, params={"q": "amarem", "word": "amarem"}
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

    extract_call = _make_call(
        "extract.whitakers.lines",
        "extract-ww",
        ToolStage.TOOL_STAGE_EXTRACT,
        params={"source_call_id": fetch_call.call_id},
    )
    extraction = whitakers.extract_lines(extract_call, raw)

    derive_call = _make_call(
        "derive.whitakers.facts",
        "derive-ww",
        ToolStage.TOOL_STAGE_DERIVE,
        params={"source_call_id": extract_call.call_id},
    )
    derivation = whitakers.derive_facts(derive_call, extraction)

    claim_call = _make_call(
        "claim.whitakers",
        "claim-ww",
        ToolStage.TOOL_STAGE_CLAIM,
        params={"source_call_id": derive_call.call_id},
    )
    claim = whitakers.claim_whitakers(claim_call, derivation)
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

    has_interp = _find_triple(triples, form_anchor, "has_interpretation", interp_anchor)
    assert has_interp is not None
    realizes = _find_triple(triples, interp_anchor, "realizes_lexeme", lex_anchor)
    assert realizes is not None
    assert _find_triple(triples, interp_anchor, "has_pos", "verb") is not None
    assert _find_triple(triples, interp_anchor, "has_tense", "imperfect") is not None
    assert _find_triple(triples, interp_anchor, "has_mood", "subjunctive") is not None
    assert _find_triple(triples, interp_anchor, "has_voice", "active") is not None
    assert _find_triple(triples, interp_anchor, "has_person", "1") is not None
    assert _find_triple(triples, interp_anchor, "has_number", "singular") is not None

    has_sense = _find_triple(triples, lex_anchor, "has_sense", sense_anchor)
    assert has_sense is not None
    assert _find_triple(triples, sense_anchor, "gloss", sense_txt) is not None

    ev = has_interp["metadata"]["evidence"]  # type: ignore[index]
    assert ev["source_tool"] == "whitaker"
    assert ev["call_id"] == claim_call.call_id
    assert ev["derivation_id"] == derivation.derivation_id
    assert ev["extraction_id"] == extraction.extraction_id
    assert ev["claim_id"] == claim.claim_id
    assert ev["response_id"] == raw.response_id
    assert ev["raw_blob_ref"] == "raw_text"
