from __future__ import annotations

from langnet.execution.handlers import spacy
from langnet.morphology.candidates import candidates_from_triples


def test_spacy_projects_morphology_to_inflected_form_anchor() -> None:
    triples = spacy._build_triples(
        {
            "tokens": [
                {
                    "text": "λόγου",
                    "lemma": "λόγος",
                    "pos": "NOUN",
                    "morph": {
                        "Case": ["Gen"],
                        "Number": ["Sing"],
                        "Gender": ["Masc"],
                    },
                }
            ]
        },
        {"source_tool": "spacy"},
    )

    assert ("form:logou", "inflection_of", "lex:logos") in _triple_set(triples)
    assert ("form:logou", "has_pos", "noun") in _triple_set(triples)
    assert ("form:logou", "has_case", "genitive") in _triple_set(triples)
    assert ("form:logou", "has_number", "singular") in _triple_set(triples)
    assert ("form:logou", "has_gender", "masculine") in _triple_set(triples)

    candidates = candidates_from_triples("grc", "λόγου", triples)
    assert candidates[0].lemma == "logos"
    assert candidates[0].foster_display == "Possessing Function; Single; Male"


def _triple_set(triples: list[dict[str, object]]) -> set[tuple[object, object, object]]:
    return {(triple["subject"], triple["predicate"], triple["object"]) for triple in triples}
