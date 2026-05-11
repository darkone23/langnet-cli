from __future__ import annotations

from langnet.paradigm.resolver import resolve_paradigm_request

PUELLAE_ANALYSIS_COUNT = 3


def test_resolver_maps_sanskrit_inflected_noun_to_declension_request() -> None:
    payload = resolve_paradigm_request(
        "san",
        "putraa.naam",
        [
            {
                "normalized_form": "putrāṇām",
                "lemma": "putra",
                "part_of_speech": "noun",
                "gender": "masculine",
                "source": "heritage:sktreader",
                "analyses": [{"case": "genitive", "number": "plural"}],
            }
        ],
    )

    candidate = payload.candidates[0]
    assert payload.normalized_form == "putrāṇām"
    assert candidate.lemma == "putra"
    assert candidate.entry_type == "variant"
    assert candidate.paradigm_request is not None
    assert candidate.paradigm_request.source == "heritage:sktdeclin"
    assert candidate.paradigm_request.options == {"gender": "Mas"}
    assert candidate.functional_analyses[0].relation == "possession_or_association"


def test_resolver_preserves_sanskrit_syncretic_case_ambiguity() -> None:
    payload = resolve_paradigm_request(
        "san",
        "devebhyaḥ",
        [
            {
                "normalized_form": "devebhyaḥ",
                "lemma": "deva",
                "part_of_speech": "noun",
                "gender": "masculine",
                "source": "heritage:sktreader",
                "analyses": [
                    {"case": "dative", "number": "plural"},
                    {"case": "ablative", "number": "plural"},
                ],
            }
        ],
    )

    candidate = payload.candidates[0]
    assert [analysis.features["case"] for analysis in candidate.native_analyses] == [
        "dative",
        "ablative",
    ]
    assert {analysis.relation for analysis in candidate.functional_analyses} == {
        "recipient_or_goal",
        "source_or_separation",
    }


def test_resolver_keeps_latin_puellae_ambiguous_under_one_lemma() -> None:
    payload = resolve_paradigm_request(
        "lat",
        "puellae",
        [
            {
                "lemma": "puella",
                "part_of_speech": "noun",
                "genitive_singular": "puellae",
                "gender": "feminine",
                "source": "whitakers",
                "analyses": [
                    {"case": "genitive", "number": "singular"},
                    {"case": "dative", "number": "singular"},
                    {"case": "nominative", "number": "plural"},
                ],
            }
        ],
    )

    candidate = payload.candidates[0]
    assert candidate.lemma == "puella"
    assert len(candidate.native_analyses) == PUELLAE_ANALYSIS_COUNT
    assert candidate.paradigm_request is not None
    assert candidate.paradigm_request.source == "diogenes:inflect"
    assert candidate.paradigm_request.lemma == "puella"


def test_resolver_maps_greek_inflected_noun_to_diogenes_request() -> None:
    payload = resolve_paradigm_request(
        "grc",
        "λόγοις",
        [
            {
                "lemma": "λόγος",
                "source_key": "lo/gos",
                "part_of_speech": "noun",
                "genitive_singular": "λόγου",
                "article": "ὁ",
                "gender": "masculine",
                "source": "diogenes:lsj",
                "analyses": [{"case": "dative", "number": "plural"}],
            }
        ],
    )

    candidate = payload.candidates[0]
    assert candidate.lemma == "λόγος"
    assert candidate.paradigm_request is not None
    assert candidate.paradigm_request.source == "diogenes:inflect"
    assert candidate.paradigm_request.lemma == "lo/gos"
    assert {analysis.relation for analysis in candidate.functional_analyses} == {
        "recipient_or_goal",
        "location",
        "instrument_or_means",
    }


def test_resolver_maps_greek_learner_key_to_diogenes_request() -> None:
    payload = resolve_paradigm_request(
        "grc",
        "logos",
        [{"lemma": "logos", "part_of_speech": "unknown", "source": "cli"}],
    )

    assert any(
        candidate.paradigm_request is not None
        and candidate.paradigm_request.lemma == "lo/gos"
        and candidate.paradigm_request.kind == "declension"
        for candidate in payload.candidates
    )


def test_resolver_reports_unmapped_greek_learner_key_distinctly() -> None:
    payload = resolve_paradigm_request(
        "grc",
        "notagreekmotdkey",
        [{"lemma": "notagreekmotdkey", "part_of_speech": "unknown", "source": "cli"}],
    )

    assert payload.candidates[0].unresolved_reason == "greek_learner_key_not_resolved_to_source_key"


def test_resolver_refuses_sanskrit_declension_when_gender_is_missing() -> None:
    payload = resolve_paradigm_request(
        "san",
        "agni",
        [
            {
                "lemma": "agni",
                "part_of_speech": "noun",
                "source": "cdsl:mw",
            }
        ],
    )

    candidate = payload.candidates[0]
    assert candidate.paradigm_request is None
    assert candidate.unresolved_reason == "missing_gender_or_declension"
    assert candidate.confidence == "low"
