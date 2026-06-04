from __future__ import annotations

from typing import cast

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


def test_diogenes_definition_triples_add_learner_source_structure() -> None:
    base_evidence = {"source_tool": "diogenes", "call_id": "c1", "claim_id": "cl1"}
    parsed = {
        "chunks": [
            {
                "chunk_type": "DiogenesMatchingReference",
                "reference_id": "lsj:logos",
                "definitions": {
                    "term": "λόγος",
                    "blocks": [
                        {
                            "entryid": "logos-1",
                            "entry": "λόγος, ου, ὁ: word; speech; account; reason | example",
                        }
                    ],
                },
            }
        ]
    }

    triples = dio_handlers._build_triples(parsed, ["λόγος"], base_evidence)
    gloss = next(triple for triple in triples if triple["predicate"] == "gloss")

    assert gloss["metadata"]["learner_gloss"] == "word; speech; account; reason"
    assert gloss["metadata"]["learner_segments"] == [
        {
            "index": 0,
            "raw_text": "word; speech; account; reason",
            "display_text": "word; speech; account; reason",
            "segment_type": "learner_gloss",
            "labels": ["definition", "learner_summary"],
        }
    ]
    assert gloss["metadata"]["source_segments"][0]["segment_type"] == "dictionary_entry"


def test_diogenes_surface_morphology_triples_can_exclude_definitions() -> None:
    base_evidence = {"source_tool": "diogenes", "call_id": "c1", "claim_id": "cl1"}
    parsed = {
        "chunks": [
            {
                "chunk_type": "PerseusAnalysisHeader",
                "morphology": {
                    "morphs": [{"stem": ["μῆνις"], "tags": ["fem", "acc", "sg"], "defs": ["wrath"]}]
                },
            },
            {
                "chunk_type": "DiogenesFuzzyReference",
                "definitions": {
                    "term": "μῆνις",
                    "blocks": [{"entry": "wrath"}],
                },
            },
        ]
    }

    triples = dio_handlers._build_triples(
        parsed,
        ["μῆνις"],
        base_evidence,
        include_definitions=False,
    )

    assert any(t["predicate"] == "inflection_of" for t in triples)
    assert any(t["predicate"] == "has_feature" for t in triples)
    assert not any(t["predicate"] == "has_sense" for t in triples)


def test_diogenes_no_match_fuzzy_reference_does_not_become_definition_evidence() -> None:
    base_evidence = {"source_tool": "diogenes", "call_id": "c1", "claim_id": "cl1"}
    parsed = {
        "chunks": [
            {"chunk_type": "NoMatchFoundHeader"},
            {
                "chunk_type": "DiogenesFuzzyReference",
                "reference_id": "45070726",
                "definitions": {
                    "term": "ἥσθημα",
                    "blocks": [{"entry": "= ἡδονή, Eup. 131.", "entryid": "00:00"}],
                },
            },
        ]
    }

    triples = dio_handlers._build_triples(parsed, ["Ἠσαίᾳ"], base_evidence)

    assert not any(t["predicate"] == "has_sense" for t in triples)
    assert not any(t["predicate"] == "gloss" for t in triples)


def test_diogenes_no_match_fuzzy_reference_does_not_become_lemma() -> None:
    chunks = cast(
        list[dio_handlers.DiogenesChunk],
        [
            {"chunk_type": "NoMatchFoundHeader"},
            {
                "chunk_type": "DiogenesFuzzyReference",
                "definitions": {"term": "ἥσθημα", "blocks": []},
            },
        ],
    )

    assert dio_handlers._extract_lemmas_from_chunks(chunks) == []


def test_cltk_normalizes_greek_tokens() -> None:
    assert cltk_handlers._normalize_token("λόγος") == "logos"
    assert cltk_handlers._normalize_token("λόγος") == "logos"
