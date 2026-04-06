from __future__ import annotations

from langnet.execution.handlers import cltk as cltk_handlers
from langnet.execution.handlers import diogenes as dio_handlers


def test_diogenes_normalizes_greek_to_ascii_anchor() -> None:
    assert dio_handlers._normalize_token("λόγος") == "logos"
    assert dio_handlers._normalize_token("λόγος") == "logos"
    # Betacode-style inputs should converge too.
    assert dio_handlers._normalize_token("lo/gos") == "logos"


def test_diogenes_triples_use_greek_anchors() -> None:
    base_evidence = {"source_tool": "diogenes", "call_id": "c1", "claim_id": "cl1"}
    parsed = {
        "chunks": [
            {
                "chunk_type": "PerseusAnalysisHeader",
                "morphology": {"morphs": [{"stem": ["λόγος"], "tags": ["noun"], "defs": ["word"]}]},
            },
            {
                "chunk_type": "DiogenesMatchingReference",
                "definitions": {
                    "term": "λόγος",
                    "blocks": [{"entry": "λόγος, word"}],
                },
            },
        ]
    }
    triples = dio_handlers._build_triples(parsed, ["λόγος"], base_evidence)
    subjects = {t["subject"] for t in triples}
    predicates = {(t["subject"], t["predicate"]) for t in triples}
    assert "lex:logos" in subjects
    assert ("form:logos", "inflection_of") in predicates
    assert any(t["predicate"] == "has_sense" and t["subject"] == "lex:logos" for t in triples)


def test_cltk_normalizes_greek_tokens() -> None:
    assert cltk_handlers._normalize_token("λόγος") == "logos"
    assert cltk_handlers._normalize_token("λόγος") == "logos"
