from __future__ import annotations

from collections.abc import Mapping
from typing import cast

import orjson
from query_spec import ToolStage

from langnet.clients.base import RawResponseEffect
from langnet.execution.handlers import cltk, diogenes, heritage
from tests.claim_contract import assert_claim_contract, claim_triples, find_triple, make_call


def test_diogenes_claim_contract_for_dictionary_fixture() -> None:
    fetch_call = make_call(
        "fetch.diogenes",
        "fetch-dio",
        cast(ToolStage, ToolStage.TOOL_STAGE_FETCH),
        params={"q": "lupus", "lang": "lat"},
    )
    html = """
    <h2><span>lupus</span></h2>
    <span class="origjump perseus:abo:phi,0690,001:2:63">Verg. E. 2, 63</span>
    lupus, i, m. a wolf
    """
    raw = RawResponseEffect(
        response_id="resp-dio",
        tool=fetch_call.tool,
        call_id=fetch_call.call_id,
        endpoint=fetch_call.endpoint,
        status_code=200,
        content_type="text/html",
        headers={},
        body=html.encode("utf-8"),
    )

    extract_call = make_call(
        "extract.diogenes.html",
        "extract-dio",
        cast(ToolStage, ToolStage.TOOL_STAGE_EXTRACT),
        params={"source_call_id": fetch_call.call_id},
    )
    extraction = diogenes.extract_html(extract_call, raw)

    derive_call = make_call(
        "derive.diogenes.morph",
        "derive-dio",
        cast(ToolStage, ToolStage.TOOL_STAGE_DERIVE),
        params={"source_call_id": extract_call.call_id},
    )
    derivation = diogenes.derive_morph(derive_call, extraction)

    claim_call = make_call(
        "claim.diogenes.morph",
        "claim-dio",
        cast(ToolStage, ToolStage.TOOL_STAGE_CLAIM),
        params={"source_call_id": derive_call.call_id},
    )
    claim = diogenes.claim_morph(claim_call, derivation)

    assert_claim_contract(claim)
    triples = claim_triples(claim)
    has_sense = find_triple(triples, "lex:lupus", "has_sense")
    assert has_sense is not None
    sense_anchor = has_sense["object"]
    assert isinstance(sense_anchor, str)
    assert find_triple(triples, sense_anchor, "gloss") is not None
    citation = find_triple(triples, "lex:lupus", "has_citation")
    assert citation is not None
    metadata = citation["metadata"]
    assert isinstance(metadata, Mapping)
    evidence = metadata["evidence"]
    assert isinstance(evidence, Mapping)
    assert evidence["response_id"] == raw.response_id


def test_cltk_claim_contract_for_lexicon_fixture() -> None:
    fetch_call = make_call(
        "fetch.cltk",
        "fetch-cltk",
        cast(ToolStage, ToolStage.TOOL_STAGE_FETCH),
        params={"q": "amarem", "lang": "lat"},
    )
    raw = RawResponseEffect(
        response_id="resp-cltk",
        tool=fetch_call.tool,
        call_id=fetch_call.call_id,
        endpoint=fetch_call.endpoint,
        status_code=200,
        content_type="application/json",
        headers={},
        body=orjson.dumps(
            {
                "word": "amarem",
                "lemma": "amo",
                "ipa": ["a.mo"],
                "lewis_lines": ["amo, amare, v. to love"],
            }
        ),
    )

    extract_call = make_call(
        "extract.cltk",
        "extract-cltk",
        cast(ToolStage, ToolStage.TOOL_STAGE_EXTRACT),
        params={"source_call_id": fetch_call.call_id},
    )
    extraction = cltk.extract_cltk(extract_call, raw)

    derive_call = make_call(
        "derive.cltk",
        "derive-cltk",
        cast(ToolStage, ToolStage.TOOL_STAGE_DERIVE),
        params={"source_call_id": extract_call.call_id},
    )
    derivation = cltk.derive_cltk(derive_call, extraction)

    claim_call = make_call(
        "claim.cltk",
        "claim-cltk",
        cast(ToolStage, ToolStage.TOOL_STAGE_CLAIM),
        params={"source_call_id": derive_call.call_id},
    )
    claim = cltk.claim_cltk(claim_call, derivation)

    assert_claim_contract(claim)
    triples = claim_triples(claim)
    assert find_triple(triples, "form:amarem", "inflection_of", "lex:amo") is not None
    assert find_triple(triples, "lex:amo", "has_pronunciation", "a.mo") is not None
    has_sense = find_triple(triples, "lex:amo", "has_sense")
    assert has_sense is not None


def test_heritage_claim_contract_for_morphology_fixture() -> None:
    fetch_call = make_call(
        "fetch.heritage",
        "fetch-heritage",
        cast(ToolStage, ToolStage.TOOL_STAGE_FETCH),
        params={"text": "agni"},
    )
    html = """
    <html><body><i>agni</i><span class="roma16o">agni</span></body></html>
    """
    raw = RawResponseEffect(
        response_id="resp-heritage",
        tool=fetch_call.tool,
        call_id=fetch_call.call_id,
        endpoint=fetch_call.endpoint,
        status_code=200,
        content_type="text/html",
        headers={},
        body=html.encode("utf-8"),
    )

    extract_call = make_call(
        "extract.heritage.html",
        "extract-heritage",
        cast(ToolStage, ToolStage.TOOL_STAGE_EXTRACT),
        params={"source_call_id": fetch_call.call_id},
    )
    extraction = heritage.extract_html(extract_call, raw)
    extraction.payload = {
        "lemma": "agni",
        "lemma_slp1": "agni",
        "heritage_guess": False,
        "analyses": [
            {
                "word": "agni",
                "analysis": "m. nom. sg.",
                "dictionary_url": "https://sanskrit.inria.fr/DICO/1.html#agni",
            }
        ],
    }

    derive_call = make_call(
        "derive.heritage.morph",
        "derive-heritage",
        cast(ToolStage, ToolStage.TOOL_STAGE_DERIVE),
        params={"source_call_id": extract_call.call_id},
    )
    derivation = heritage.derive_morph(derive_call, extraction)

    claim_call = make_call(
        "claim.heritage.morph",
        "claim-heritage",
        cast(ToolStage, ToolStage.TOOL_STAGE_CLAIM),
        params={"source_call_id": derive_call.call_id},
    )
    claim = heritage.claim_morph(claim_call, derivation)

    assert_claim_contract(claim)
    triples = claim_triples(claim)
    morph = find_triple(triples, "form:agni", "has_morphology")
    assert morph is not None
    metadata = morph["metadata"]
    assert isinstance(metadata, Mapping)
    evidence = metadata["evidence"]
    assert isinstance(evidence, Mapping)
    assert evidence["source_tool"] == "heritage"
    assert evidence["response_id"] == raw.response_id
