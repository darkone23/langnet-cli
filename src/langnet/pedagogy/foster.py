from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class FosterMappings:
    """Functional grammar labels used for optional learner-facing display."""

    cases: Mapping[str, str]
    genders: Mapping[str, str]
    numbers: Mapping[str, str]
    tenses: Mapping[str, str]
    moods: Mapping[str, str]
    voices: Mapping[str, str]
    miscellaneous: Mapping[str, str]


_CASE_LABELS = {
    "nominative": "NAMING",
    "vocative": "CALLING",
    "accusative": "RECEIVING",
    "genitive": "POSSESSING",
    "dative": "TO_FOR",
    "ablative": "BY_WITH_FROM_IN",
    "instrumental": "BY_WITH_FROM_IN",
    "locative": "IN_WHERE",
}

_GENDER_LABELS = {
    "masculine": "MALE",
    "feminine": "FEMALE",
    "neuter": "NEUTER",
}

_NUMBER_LABELS = {
    "singular": "SINGLE",
    "dual": "PAIR",
    "plural": "GROUP",
}

FOSTER_LATIN_MAPPINGS = FosterMappings(
    cases={
        **_CASE_LABELS,
        "nom": "NAMING",
        "voc": "CALLING",
        "acc": "RECEIVING",
        "gen": "POSSESSING",
        "dat": "TO_FOR",
        "abl": "BY_WITH_FROM_IN",
        "loc": "IN_WHERE",
    },
    genders={**_GENDER_LABELS, "m": "MALE", "f": "FEMALE", "n": "NEUTER"},
    numbers={**_NUMBER_LABELS, "sg": "SINGLE", "du": "PAIR", "pl": "GROUP"},
    tenses={
        "present": "TIME_NOW",
        "pres": "TIME_NOW",
        "future": "TIME_LATER",
        "fut": "TIME_LATER",
        "imperfect": "TIME_WAS_DOING",
        "imperf": "TIME_WAS_DOING",
        "perfect": "TIME_PAST",
        "perf": "TIME_PAST",
        "pluperfect": "TIME_HAD_DONE",
        "plupf": "TIME_HAD_DONE",
        "future perfect": "ONCE_DONE",
        "futperf": "ONCE_DONE",
    },
    moods={
        "indicative": "STATEMENT",
        "indic": "STATEMENT",
        "subjunctive": "WISH_MAY_BE",
        "subj": "WISH_MAY_BE",
        "imperative": "COMMAND",
        "imper": "COMMAND",
    },
    voices={
        "active": "DOING",
        "act": "DOING",
        "passive": "BEING_DONE_TO",
        "pass": "BEING_DONE_TO",
        "deponent": "FOR_SELF",
        "depon": "FOR_SELF",
        "semi-deponent": "FOR_SELF",
        "semi_depon": "FOR_SELF",
    },
    miscellaneous={"participle": "PARTICIPLE", "part": "PARTICIPLE"},
)

FOSTER_GREEK_MAPPINGS = FosterMappings(
    cases={
        **_CASE_LABELS,
        "nom": "NAMING",
        "voc": "CALLING",
        "acc": "RECEIVING",
        "gen": "POSSESSING",
        "dat": "TO_FOR",
    },
    genders={**_GENDER_LABELS, "m": "MALE", "f": "FEMALE", "n": "NEUTER"},
    numbers={**_NUMBER_LABELS, "sg": "SINGLE", "du": "PAIR", "pl": "GROUP"},
    tenses={
        "present": "TIME_NOW",
        "pres": "TIME_NOW",
        "future": "TIME_LATER",
        "fut": "TIME_LATER",
        "imperfect": "TIME_WAS_DOING",
        "imperf": "TIME_WAS_DOING",
        "aorist": "TIME_PAST",
        "aor": "TIME_PAST",
        "perfect": "TIME_HAD_DONE",
        "perf": "TIME_HAD_DONE",
        "pluperfect": "ONCE_DONE",
        "plupf": "ONCE_DONE",
    },
    moods={
        "indicative": "STATEMENT",
        "indic": "STATEMENT",
        "subjunctive": "WISH_MAY_BE",
        "subj": "WISH_MAY_BE",
        "optative": "MAYBE_WILL_DO",
        "opt": "MAYBE_WILL_DO",
        "imperative": "COMMAND",
        "imper": "COMMAND",
    },
    voices={
        "active": "DOING",
        "act": "DOING",
        "middle": "FOR_SELF",
        "mid": "FOR_SELF",
        "passive": "BEING_DONE_TO",
        "pass": "BEING_DONE_TO",
    },
    miscellaneous={"participle": "PARTICIPLE", "part": "PARTICIPLE"},
)

FOSTER_SANSKRIT_MAPPINGS = FosterMappings(
    cases={
        **_CASE_LABELS,
        "1": "NAMING",
        "2": "RECEIVING",
        "3": "BY_WITH_FROM_IN",
        "4": "TO_FOR",
        "5": "BY_WITH_FROM_IN",
        "6": "POSSESSING",
        "7": "IN_WHERE",
        "8": "CALLING",
        "nom": "NAMING",
        "voc": "CALLING",
        "acc": "RECEIVING",
        "instr": "BY_WITH_FROM_IN",
        "inst": "BY_WITH_FROM_IN",
        "dat": "TO_FOR",
        "abl": "BY_WITH_FROM_IN",
        "gen": "POSSESSING",
        "loc": "IN_WHERE",
    },
    genders={**_GENDER_LABELS, "m": "MALE", "f": "FEMALE", "n": "NEUTER"},
    numbers={**_NUMBER_LABELS, "sg": "SINGLE", "du": "PAIR", "pl": "GROUP"},
    tenses={},
    moods={},
    voices={},
    miscellaneous={},
)

_LANGUAGE_MAPPINGS = {
    "lat": FOSTER_LATIN_MAPPINGS,
    "latin": FOSTER_LATIN_MAPPINGS,
    "grc": FOSTER_GREEK_MAPPINGS,
    "greek": FOSTER_GREEK_MAPPINGS,
    "san": FOSTER_SANSKRIT_MAPPINGS,
    "sanskrit": FOSTER_SANSKRIT_MAPPINGS,
}

FOSTER_DISPLAY_LABELS = {
    "NAMING": "Naming Function",
    "CALLING": "Calling Function",
    "RECEIVING": "Receiving Function",
    "POSSESSING": "Possessing Function",
    "TO_FOR": "To-For Function",
    "BY_WITH_FROM_IN": "By-With-From-In Function",
    "IN_WHERE": "In-Where Function",
    "MALE": "Male",
    "FEMALE": "Female",
    "NEUTER": "Neuter",
    "SINGLE": "Single",
    "PAIR": "Pair",
    "GROUP": "Group",
    "TIME_NOW": "Time-Now",
    "TIME_LATER": "Time-Later",
    "TIME_WAS_DOING": "Time-Was-Doing",
    "TIME_PAST": "Time-Past",
    "TIME_HAD_DONE": "Time-Had-Done",
    "ONCE_DONE": "Once-Done",
    "STATEMENT": "Statement",
    "WISH_MAY_BE": "Wish-May-Be",
    "MAYBE_WILL_DO": "Maybe-Will-Do",
    "COMMAND": "Command",
    "DOING": "Doing",
    "BEING_DONE_TO": "Being Done To",
    "FOR_SELF": "For Self",
    "PARTICIPLE": "Participle",
}

FOSTER_DISPLAY_ORDER = (
    "case",
    "number",
    "gender",
    "tense",
    "mood",
    "voice",
    "participle",
    "pos",
)


def _normalize_feature_value(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = " ".join(value.replace("_", "-").strip().lower().split())
    return normalized or None


def _lookup(mapping: Mapping[str, str], value: object) -> str | None:
    normalized = _normalize_feature_value(value)
    if normalized is None:
        return None
    return mapping.get(normalized)


def foster_codes_for_features(
    language: str,
    features: Mapping[str, object],
) -> dict[str, str]:
    """
    Return optional Foster-style labels for grammatical feature dictionaries.

    The output is display metadata only. It does not replace exact grammatical
    predicates or source evidence.
    """
    mappings = _LANGUAGE_MAPPINGS.get(language.strip().lower())
    if mappings is None:
        return {}

    result: dict[str, str] = {}
    for output_key, feature_key, mapping in (
        ("case", "case", mappings.cases),
        ("gender", "gender", mappings.genders),
        ("number", "number", mappings.numbers),
        ("tense", "tense", mappings.tenses),
        ("mood", "mood", mappings.moods),
        ("voice", "voice", mappings.voices),
        ("participle", "participle", mappings.miscellaneous),
    ):
        label = _lookup(mapping, features.get(feature_key))
        if label is not None:
            result[output_key] = label

    pos_label = _lookup(mappings.miscellaneous, features.get("pos"))
    if pos_label is not None:
        result["pos"] = pos_label

    return result


def foster_display_for_features(language: str, features: Mapping[str, object]) -> str:
    """Return learner-facing Foster labels for a grammar feature dictionary."""
    codes = foster_codes_for_features(language, features)
    labels: list[str] = []
    for key in FOSTER_DISPLAY_ORDER:
        code = codes.get(key)
        if code is None:
            continue
        label = FOSTER_DISPLAY_LABELS.get(code, code.replace("_", " ").title())
        if label not in labels:
            labels.append(label)
    return "; ".join(labels)
