from __future__ import annotations

from langnet.learning.concept_mapper import concept_ids_for_features
from langnet.paradigm.resolver import resolve_paradigm_request


def test_concept_mapper_maps_nominal_features_to_case_number_gender_and_process() -> None:
    concept_ids = concept_ids_for_features(
        {"case": "genitive", "number": "plural", "gender": "masculine"},
        part_of_speech="noun",
        paradigm_kind="declension",
    )

    assert concept_ids == [
        "case.genitive",
        "number.plural",
        "gender.masculine",
        "process.declension",
    ]


def test_concept_mapper_maps_verbal_features_to_conjugation_concepts() -> None:
    concept_ids = concept_ids_for_features(
        {
            "person": "1",
            "number": "plural",
            "tense": "present",
            "voice": "active",
            "mood": "indicative",
        },
        part_of_speech="verb",
        paradigm_kind="conjugation",
    )

    assert concept_ids == [
        "person.first",
        "number.plural",
        "tense.present",
        "mood.indicative",
        "voice.active",
        "process.conjugation",
    ]


def test_concept_mapper_maps_expanded_nominal_features() -> None:
    concept_ids = concept_ids_for_features(
        {"case": "ablative", "number": "dual", "gender": "neuter"},
        part_of_speech="noun",
        paradigm_kind="declension",
    )

    assert concept_ids == [
        "case.ablative",
        "number.dual",
        "gender.neuter",
        "process.declension",
    ]


def test_concept_mapper_maps_passive_voice() -> None:
    concept_ids = concept_ids_for_features(
        {"person": "1", "number": "singular", "tense": "present", "voice": "passive"},
        part_of_speech="verb",
        paradigm_kind="conjugation",
    )

    assert concept_ids == [
        "person.first",
        "number.singular",
        "tense.present",
        "voice.passive",
        "process.conjugation",
    ]


def test_paradigm_resolution_candidate_carries_learning_concept_ids() -> None:
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

    assert payload.candidates[0].concept_ids == [
        "case.genitive",
        "number.plural",
        "gender.masculine",
        "process.declension",
    ]
