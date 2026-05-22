from __future__ import annotations

from collections.abc import Mapping

_CASE_CONCEPTS = {
    "nominative": "case.nominative",
    "accusative": "case.accusative",
    "genitive": "case.genitive",
    "dative": "case.dative",
    "vocative": "case.vocative",
    "ablative": "case.ablative",
    "instrumental": "case.instrumental",
    "locative": "case.locative",
}

_NUMBER_CONCEPTS = {
    "singular": "number.singular",
    "dual": "number.dual",
    "plural": "number.plural",
}

_GENDER_CONCEPTS = {
    "masculine": "gender.masculine",
    "feminine": "gender.feminine",
    "neuter": "gender.neuter",
}

_PERSON_CONCEPTS = {
    "1": "person.first",
    "first": "person.first",
}

_TENSE_CONCEPTS = {
    "present": "tense.present",
}

_MOOD_CONCEPTS = {
    "indicative": "mood.indicative",
}

_VOICE_CONCEPTS = {
    "active": "voice.active",
    "passive": "voice.passive",
}


def concept_ids_for_features(
    features: Mapping[str, object],
    *,
    part_of_speech: str,
    paradigm_kind: str,
) -> list[str]:
    concept_ids: list[str] = []
    _append_mapped(concept_ids, _CASE_CONCEPTS, features.get("case"))
    _append_mapped(concept_ids, _PERSON_CONCEPTS, features.get("person"))
    _append_mapped(concept_ids, _NUMBER_CONCEPTS, features.get("number"))
    _append_mapped(concept_ids, _GENDER_CONCEPTS, features.get("gender"))
    _append_mapped(concept_ids, _TENSE_CONCEPTS, features.get("tense"))
    _append_mapped(concept_ids, _MOOD_CONCEPTS, features.get("mood"))
    _append_mapped(concept_ids, _VOICE_CONCEPTS, features.get("voice"))

    if paradigm_kind == "declension" or part_of_speech in {"noun", "adjective", "pronoun"}:
        concept_ids.append("process.declension")
    elif paradigm_kind == "conjugation" or part_of_speech == "verb":
        concept_ids.append("process.conjugation")

    return list(dict.fromkeys(concept_ids))


def _append_mapped(
    concept_ids: list[str],
    mapping: Mapping[str, str],
    value: object,
) -> None:
    if not isinstance(value, str):
        return
    concept_id = mapping.get(value.casefold())
    if concept_id:
        concept_ids.append(concept_id)
