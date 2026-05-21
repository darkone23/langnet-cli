from __future__ import annotations

from langnet.morphology.candidates import candidates_from_triples, rank_candidates


def test_heritage_morphology_object_projects_to_foster_candidate() -> None:
    triples = [
        {
            "subject": "form:putra",
            "predicate": "has_morphology",
            "object": {
                "lemma": "putra",
                "form": "putrāṇām",
                "features": {"case": "genitive", "number": "plural", "gender": "masculine"},
                "analysis": "m. gen. pl.",
            },
            "metadata": {"source": "heritage:sktreader"},
        }
    ]

    candidates = candidates_from_triples("san", "putraa.naam", triples)

    assert candidates[0].lemma == "putra"
    assert candidates[0].observed_form == "putrāṇām"
    assert candidates[0].features["case"] == "genitive"
    assert candidates[0].functional_relations == ["possession_or_association"]
    assert candidates[0].foster_display == "Possessing Function; Group; Male"


def test_whitaker_interpretation_graph_projects_to_foster_candidate() -> None:
    triples = [
        {
            "subject": "form:puellae",
            "predicate": "has_interpretation",
            "object": "interp:puellae:1",
            "metadata": {"source": "whitakers"},
        },
        {
            "subject": "interp:puellae:1",
            "predicate": "realizes_lexeme",
            "object": "lex:puella",
            "metadata": {"source": "whitakers"},
        },
        {
            "subject": "interp:puellae:1",
            "predicate": "has_pos",
            "object": "noun",
            "metadata": {"source": "whitakers"},
        },
        {
            "subject": "interp:puellae:1",
            "predicate": "has_case",
            "object": "genitive",
            "metadata": {"source": "whitakers"},
        },
        {
            "subject": "interp:puellae:1",
            "predicate": "has_number",
            "object": "singular",
            "metadata": {"source": "whitakers"},
        },
        {
            "subject": "interp:puellae:1",
            "predicate": "has_gender",
            "object": "feminine",
            "metadata": {"source": "whitakers"},
        },
        {
            "subject": "lex:puella",
            "predicate": "has_declension",
            "object": "1",
            "metadata": {"source": "whitakers"},
        },
    ]

    candidates = candidates_from_triples("lat", "puellae", triples)

    assert candidates[0].lemma == "puella"
    assert candidates[0].features["case"] == "genitive"
    assert candidates[0].features["declension"] == "1"
    assert candidates[0].functional_relations == ["possession_or_association"]
    assert candidates[0].foster_display == "Possessing Function; Single; Female"


def test_diogenes_form_graph_projects_morpheus_candidate() -> None:
    triples = [
        {
            "subject": "form:logou",
            "predicate": "inflection_of",
            "object": "lex:logos",
            "metadata": {"source": "diogenes:morpheus"},
        },
        {
            "subject": "form:logou",
            "predicate": "has_form",
            "object": "λόγου",
            "metadata": {"source": "diogenes:morpheus"},
        },
        {
            "subject": "form:logou",
            "predicate": "has_pos",
            "object": "noun",
            "metadata": {"source": "diogenes:morpheus"},
        },
        {
            "subject": "form:logou",
            "predicate": "has_case",
            "object": "genitive",
            "metadata": {"source": "diogenes:morpheus"},
        },
        {
            "subject": "form:logou",
            "predicate": "has_number",
            "object": "singular",
            "metadata": {"source": "diogenes:morpheus"},
        },
        {
            "subject": "form:logou",
            "predicate": "has_gender",
            "object": "masculine",
            "metadata": {"source": "diogenes:morpheus"},
        },
        {
            "subject": "lex:logos",
            "predicate": "has_declension",
            "object": "2",
            "metadata": {"source": "diogenes:morpheus"},
        },
    ]

    candidates = candidates_from_triples("grc", "λόγου", triples)

    assert candidates[0].lemma == "logos"
    assert candidates[0].observed_form == "λόγου"
    assert candidates[0].features["case"] == "genitive"
    assert candidates[0].features["declension"] == "2"
    assert candidates[0].functional_relations == ["possession_or_association"]
    assert candidates[0].foster_display == "Possessing Function; Single; Male"
    assert candidates[0].ranking_reasons == ["observed-form", "lemma", "case-number-gender"]


def test_ranking_prefers_strongly_determined_supported_candidate() -> None:
    triples = [
        {
            "subject": "form:noise",
            "predicate": "has_morphology",
            "object": {
                "lemma": "noise",
                "form": "putrāṇām",
                "features": {"case": "nominative"},
            },
            "metadata": {"source": "heritage:sktreader"},
        },
        {
            "subject": "form:putra",
            "predicate": "has_morphology",
            "object": {
                "lemma": "putra",
                "form": "putrāṇām",
                "features": {"case": "genitive", "number": "plural", "gender": "masculine"},
            },
            "metadata": {"source": "heritage:sktreader"},
        },
    ]

    ranked = rank_candidates(candidates_from_triples("san", "putraa.naam", triples))

    assert ranked[0].lemma == "putra"
    assert "case-number-gender" in ranked[0].ranking_reasons
