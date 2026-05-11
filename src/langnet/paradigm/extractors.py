from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import cast

from langnet.paradigm.grammar import Confidence, FeatureValue, GrammarEvidence, LanguageCode


def extract_sanskrit_grammar_evidence(record: Mapping[str, object]) -> list[GrammarEvidence]:
    return [_build_evidence("san", record)]


def extract_latin_grammar_evidence(record: Mapping[str, object]) -> list[GrammarEvidence]:
    return [_build_evidence("lat", record)]


def extract_greek_grammar_evidence(record: Mapping[str, object]) -> list[GrammarEvidence]:
    return [_build_evidence("grc", record)]


def _build_evidence(language: LanguageCode, record: Mapping[str, object]) -> GrammarEvidence:
    metadata = _as_mapping(record.get("metadata"))
    lemma = _first_string([record, metadata], ["lemma", "headword", "canonical", "canonical_name"])
    source = _first_string([record, metadata], ["source", "dictionary"]) or "unknown"
    part_of_speech = _normalize_pos(
        _first_string([record, metadata], ["part_of_speech", "pos", "partOfSpeech"])
    )
    features = _base_features(record, metadata)
    analyses = _extract_analyses(record, metadata)
    _add_analysis_features(features, analyses)
    _add_language_derived_features(language, lemma, features)

    confidence = _confidence_for(language, part_of_speech, features)
    return GrammarEvidence(
        language=language,
        lemma=lemma,
        part_of_speech=part_of_speech,
        features=features,
        analyses=analyses,
        source=source,
        confidence=confidence,
    )


def _base_features(
    record: Mapping[str, object], metadata: Mapping[str, object]
) -> dict[str, FeatureValue]:
    features: dict[str, FeatureValue] = {}
    gender = _normalize_gender(_first_string([record, metadata], ["gender", "g"]))
    if gender:
        features["gender"] = gender
    genitive = _first_string([record, metadata], ["genitive_singular", "genitive", "gen_sg"])
    if genitive:
        features["genitive_singular"] = genitive
    article = _first_string([record, metadata], ["article"])
    if article:
        features["article"] = article
        inferred_gender = _gender_from_greek_article(article)
        if inferred_gender and "gender" not in features:
            features["gender"] = inferred_gender
    source_key = _first_string([record, metadata], ["source_key", "diogenes_key", "betacode"])
    if source_key:
        features["source_key"] = source_key
    present_class = _first_string([record, metadata], ["present_class", "class", "conjugation"])
    if present_class:
        features["present_class"] = present_class
    return features


def _add_language_derived_features(
    language: LanguageCode, lemma: str, features: dict[str, FeatureValue]
) -> None:
    genitive = features.get("genitive_singular")
    gender = features.get("gender")
    if language == "lat" and isinstance(genitive, str):
        declension = _latin_declension_from_genitive(genitive)
        if declension:
            features["declension"] = declension
    elif language == "grc" and lemma and isinstance(genitive, str):
        declension = _greek_declension_from_nom_gen(lemma, genitive)
        if declension:
            features["declension"] = declension
    elif language == "san" and isinstance(gender, str):
        heritage_gender = _heritage_gender(gender)
        if heritage_gender:
            features["heritage_gender"] = heritage_gender


def _add_analysis_features(
    features: dict[str, FeatureValue], analyses: Sequence[Mapping[str, FeatureValue]]
) -> None:
    for analysis in analyses:
        for key in ("case", "number", "person", "tense", "mood", "voice"):
            if key in analysis and key not in features:
                features[key] = analysis[key]


def _as_mapping(value: object) -> Mapping[str, object]:
    return cast(Mapping[str, object], value) if isinstance(value, Mapping) else {}


def _first_string(mappings: Sequence[Mapping[str, object]], keys: Sequence[str]) -> str:
    for mapping in mappings:
        for key in keys:
            value = mapping.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
            if isinstance(value, int | float):
                return str(value)
    return ""


def _extract_analyses(
    record: Mapping[str, object], metadata: Mapping[str, object]
) -> list[dict[str, FeatureValue]]:
    raw = record.get("analyses", metadata.get("analyses"))
    if not isinstance(raw, Sequence) or isinstance(raw, str | bytes):
        return []
    analyses: list[dict[str, FeatureValue]] = []
    for item in raw:
        if not isinstance(item, Mapping):
            continue
        analysis: dict[str, FeatureValue] = {}
        for key, value in item.items():
            if isinstance(key, str) and (
                isinstance(value, str | int | float | bool) or value is None
            ):
                analysis[key] = value
        if analysis:
            analyses.append(analysis)
    return analyses


def _normalize_pos(value: str) -> str:
    lowered = value.lower()
    if lowered in {"n", "noun", "substantive"}:
        return "noun"
    if lowered in {"v", "verb"}:
        return "verb"
    if lowered in {"adj", "adjective"}:
        return "adjective"
    if lowered in {"adv", "adverb", "particle", "indeclinable"}:
        return "indeclinable"
    return lowered or "unknown"


def _normalize_gender(value: str) -> str:
    lowered = value.lower().strip(".")
    if lowered in {"m", "mas", "masc", "masculine"}:
        return "masculine"
    if lowered in {"f", "fem", "feminine"}:
        return "feminine"
    if lowered in {"n", "neu", "neut", "neuter"}:
        return "neuter"
    return lowered


def _heritage_gender(gender: str) -> str:
    return {
        "masculine": "Mas",
        "feminine": "Fem",
        "neuter": "Neu",
    }.get(gender, "")


def _latin_declension_from_genitive(genitive: str) -> str:
    genitive_lower = genitive.casefold()
    if genitive_lower.endswith("ae"):
        return "1"
    if genitive_lower.endswith(("ī", "i")):
        return "2"
    if genitive_lower.endswith("is"):
        return "3"
    if genitive_lower.endswith(("ūs", "us")):
        return "4"
    if genitive_lower.endswith(("eī", "ēī", "ei")):
        return "5"
    return ""


def _greek_declension_from_nom_gen(nominative: str, genitive: str) -> str:
    nom = nominative.casefold()
    gen = genitive.casefold()
    if nom.endswith(("α", "η")) and gen.endswith(("ασ", "ας", "ησ", "ης")):
        return "1"
    if nom.endswith(("ασ", "ας", "ησ", "ης")) and gen.endswith("ου"):
        return "1"
    if nom.endswith(("οσ", "ος", "ον")) and gen.endswith("ου"):
        return "2"
    if gen.endswith(("οσ", "ος", "εωσ", "εως", "έωσ", "έως")):
        return "3"
    return ""


def _gender_from_greek_article(article: str) -> str:
    return {
        "ὁ": "masculine",
        "η": "feminine",
        "ἡ": "feminine",
        "το": "neuter",
        "τό": "neuter",
    }.get(article.casefold(), "")


def _confidence_for(
    language: LanguageCode, part_of_speech: str, features: Mapping[str, FeatureValue]
) -> Confidence:
    if part_of_speech == "indeclinable":
        return "high"
    if part_of_speech == "verb":
        return "high" if "present_class" in features or language in {"lat", "grc"} else "medium"
    if part_of_speech in {"noun", "adjective", "pronoun"}:
        if language == "san":
            return "high" if "heritage_gender" in features else "low"
        if language in {"lat", "grc"}:
            return "high" if "declension" in features else "medium"
    return "low"
