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

_FEATURE_CONCEPT_MAPS = {
    "case": _CASE_CONCEPTS,
    "person": _PERSON_CONCEPTS,
    "number": _NUMBER_CONCEPTS,
    "gender": _GENDER_CONCEPTS,
    "tense": _TENSE_CONCEPTS,
    "mood": _MOOD_CONCEPTS,
    "voice": _VOICE_CONCEPTS,
}


def concept_ids_for_features(
    features: Mapping[str, object],
    *,
    part_of_speech: str,
    paradigm_kind: str,
) -> list[str]:
    concept_ids: list[str] = []
    normalized_features = normalize_feature_map(features)
    _append_mapped(concept_ids, _CASE_CONCEPTS, normalized_features.get("case"))
    _append_mapped(concept_ids, _PERSON_CONCEPTS, normalized_features.get("person"))
    _append_mapped(concept_ids, _NUMBER_CONCEPTS, normalized_features.get("number"))
    _append_mapped(concept_ids, _GENDER_CONCEPTS, normalized_features.get("gender"))
    _append_mapped(concept_ids, _TENSE_CONCEPTS, normalized_features.get("tense"))
    _append_mapped(concept_ids, _MOOD_CONCEPTS, normalized_features.get("mood"))
    _append_mapped(concept_ids, _VOICE_CONCEPTS, normalized_features.get("voice"))

    part_of_speech_key = _normalize_feature_value(part_of_speech)
    paradigm_kind_key = _normalize_feature_value(paradigm_kind)
    if paradigm_kind_key in {"participle", "participial"} or part_of_speech_key in {
        "participle",
        "participial",
        "part",
    }:
        concept_ids.append("process.participle")
    if paradigm_kind_key == "declension" or part_of_speech_key in {
        "noun",
        "adjective",
        "pronoun",
    }:
        concept_ids.append("process.declension")
    elif paradigm_kind_key == "conjugation" or part_of_speech_key == "verb":
        concept_ids.append("process.conjugation")

    return list(dict.fromkeys(concept_ids))


def normalize_feature_map(features: Mapping[str, object]) -> dict[str, str]:
    normalized: dict[str, str] = {}
    for key, value in features.items():
        if not isinstance(key, str) or not isinstance(value, str):
            continue
        key_name = _normalize_feature_key(key)
        value_name = _normalize_feature_value(value)
        if key_name and value_name:
            normalized[key_name] = value_name
    return normalized


def feature_mapping_diagnostics(features: Mapping[str, object]) -> dict[str, list[dict[str, str]]]:
    normalized_features = normalize_feature_map(features)
    unmapped_features: list[dict[str, str]] = []
    ignored_features: list[dict[str, str]] = []
    for key, value in normalized_features.items():
        concept_map = _FEATURE_CONCEPT_MAPS.get(key)
        if concept_map is None:
            ignored_features.append({"key": key, "value": value})
        elif value not in concept_map:
            unmapped_features.append({"key": key, "value": value})
    return {
        "unmapped_features": unmapped_features,
        "ignored_features": ignored_features,
    }


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


def _normalize_feature_key(key: str) -> str:
    return key.strip().replace("-", "_").casefold()


def _normalize_feature_value(value: str) -> str:
    return value.strip().casefold()
