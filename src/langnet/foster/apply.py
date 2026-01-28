from langnet.foster.greek import (
    FOSTER_GREEK_CASES,
    FOSTER_GREEK_GENDERS,
    FOSTER_GREEK_MISCELLANEOUS,
    FOSTER_GREEK_NUMBERS,
    FOSTER_GREEK_TENSES,
)
from langnet.foster.latin import (
    FOSTER_LATIN_CASES,
    FOSTER_LATIN_GENDERS,
    FOSTER_LATIN_MISCELLANEOUS,
    FOSTER_LATIN_NUMBERS,
    FOSTER_LATIN_TENSES,
)
from langnet.foster.sanskrit import (
    FOSTER_SANSKRIT_CASES,
    FOSTER_SANSKRIT_GENDERS,
    FOSTER_SANSKRIT_NUMBERS,
)

_LATIN_MAPPINGS = [
    FOSTER_LATIN_CASES,
    FOSTER_LATIN_TENSES,
    FOSTER_LATIN_GENDERS,
    FOSTER_LATIN_NUMBERS,
    FOSTER_LATIN_MISCELLANEOUS,
]

_GREEK_MAPPINGS = [
    FOSTER_GREEK_CASES,
    FOSTER_GREEK_TENSES,
    FOSTER_GREEK_GENDERS,
    FOSTER_GREEK_NUMBERS,
    FOSTER_GREEK_MISCELLANEOUS,
]

_MOOD_VOICE_MAP = {
    "active": "act",
    "middle": "mid",
    "passive": "pass",
    "indicative": "indic",
    "subjunctive": "subj",
    "optative": "opt",
    "imperative": "imper",
}


def _map_tag_to_foster(tag: str, mappings: list[dict]) -> str | None:
    for mapping in mappings:
        if tag in mapping:
            return mapping[tag].value
    return None


def _get_diogenes_chunks(result: dict) -> list:
    diogenes = result.get("diogenes")
    if not diogenes:
        return []
    return diogenes.get("chunks", [])


def _process_morph(morph: dict) -> list[str]:
    tags = morph.get("tags", [])
    if not tags:
        return []

    foster_codes = []
    for tag in tags:
        latin_mapped = _map_tag_to_foster(tag, _LATIN_MAPPINGS)
        if latin_mapped:
            foster_codes.append(latin_mapped)
        else:
            greek_mapped = _map_tag_to_foster(tag, _GREEK_MAPPINGS)
            if greek_mapped:
                foster_codes.append(greek_mapped)
    return foster_codes


def _apply_to_diogenes(result: dict) -> None:
    chunks = _get_diogenes_chunks(result)
    for chunk in chunks:
        morph_data = chunk.get("morphology")
        if not morph_data:
            continue
        morphs = morph_data.get("morphs", [])
        for morph in morphs:
            codes = _process_morph(morph)
            if codes:
                morph["foster_codes"] = codes


def _get_cltk_features(result: dict) -> dict:
    cltk = result.get("cltk")
    if not cltk:
        return {}
    greek_morph = cltk.get("greek_morphology")
    if not greek_morph:
        return {}
    return greek_morph.get("morphological_features", {})


def _map_greek_features(features: dict) -> dict:
    foster_codes = {}

    case_mapped = _map_tag_to_foster(features.get("case", ""), [FOSTER_GREEK_CASES])
    if case_mapped:
        foster_codes["case"] = case_mapped

    tense_mapped = _map_tag_to_foster(features.get("tense", ""), [FOSTER_GREEK_TENSES])
    if tense_mapped:
        foster_codes["tense"] = tense_mapped

    gender_mapped = _map_tag_to_foster(features.get("gender", ""), [FOSTER_GREEK_GENDERS])
    if gender_mapped:
        foster_codes["gender"] = gender_mapped

    number_mapped = _map_tag_to_foster(features.get("number", ""), [FOSTER_GREEK_NUMBERS])
    if number_mapped:
        foster_codes["number"] = number_mapped

    for key in ("voice", "mood"):
        val = features.get(key, "")
        mapped = _MOOD_VOICE_MAP.get(val)
        if mapped:
            misc_mapped = _map_tag_to_foster(mapped, [FOSTER_GREEK_MISCELLANEOUS])
            if misc_mapped:
                foster_codes[key] = misc_mapped

    return foster_codes


def _apply_to_cltk_greek(result: dict) -> None:
    features = _get_cltk_features(result)
    if not features:
        return

    foster_codes = _map_greek_features(features)
    if foster_codes:
        cltk = result.get("cltk")
        if cltk and "greek_morphology" in cltk:
            cltk["greek_morphology"]["foster_codes"] = foster_codes


def _get_sanskrit_entries(result: dict) -> list:
    dictionaries = result.get("dictionaries")
    if not dictionaries:
        return []

    entries = []
    for entry_list in dictionaries.values():
        if isinstance(entry_list, list):
            entries.extend(entry_list)
    return entries


def _map_sanskrit_tags(grammar_tags: dict) -> dict:
    foster_codes = {}

    case_val = str(grammar_tags.get("case", ""))
    case_mapped = _map_tag_to_foster(case_val, [FOSTER_SANSKRIT_CASES])
    if case_mapped:
        foster_codes["case"] = case_mapped

    gender_val = str(grammar_tags.get("gender", ""))
    gender_mapped = _map_tag_to_foster(gender_val, [FOSTER_SANSKRIT_GENDERS])
    if gender_mapped:
        foster_codes["gender"] = gender_mapped

    number_val = str(grammar_tags.get("number", ""))
    number_mapped = _map_tag_to_foster(number_val, [FOSTER_SANSKRIT_NUMBERS])
    if number_mapped:
        foster_codes["number"] = number_mapped

    return foster_codes


def _apply_to_sanskrit(result: dict) -> None:
    entries = _get_sanskrit_entries(result)
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        grammar_tags = entry.get("grammar_tags")
        if not isinstance(grammar_tags, dict):
            continue

        foster_codes = _map_sanskrit_tags(grammar_tags)
        if foster_codes:
            entry["foster_codes"] = foster_codes


def apply_foster_view(result: dict) -> dict:
    _apply_to_diogenes(result)
    _apply_to_cltk_greek(result)
    _apply_to_sanskrit(result)
    return result
