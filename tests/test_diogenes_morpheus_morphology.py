from __future__ import annotations

from langnet.execution.handlers import diogenes


def _predicates_for(html: str) -> list[tuple[str, str, object]]:
    parsed = diogenes._parse_diogenes_html(html)
    morph = parsed["chunks"][0]["morphology"]
    triples = diogenes._build_perseus_header_triples(
        morph,
        "lex:λόγος",
        {"source": "diogenes:morpheus"},
    )
    return [(str(t["subject"]), str(t["predicate"]), t["object"]) for t in triples]


def test_morpheus_noun_tags_become_canonical_feature_triples() -> None:
    triples = _predicates_for(
        "<h1>Perseus analysis</h1><ul><li>λόγος, λόγου: noun masc gen sg</li></ul>"
    )

    assert ("form:logos", "has_pos", "noun") in triples
    assert ("form:logos", "has_gender", "masculine") in triples
    assert ("form:logos", "has_case", "genitive") in triples
    assert ("form:logos", "has_number", "singular") in triples


def test_morpheus_verb_tags_become_canonical_feature_triples() -> None:
    triples = _predicates_for(
        "<h1>Perseus analysis</h1><ul><li>λύω: verb 1st pres act ind sg</li></ul>"
    )

    assert ("form:luw", "has_pos", "verb") in triples
    assert ("form:luw", "has_person", "1") in triples
    assert ("form:luw", "has_tense", "present") in triples
    assert ("form:luw", "has_voice", "active") in triples
    assert ("form:luw", "has_mood", "indicative") in triples
    assert ("form:luw", "has_number", "singular") in triples
