from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import cast

from langnet.paradigm.extractors import (
    extract_greek_grammar_evidence,
    extract_latin_grammar_evidence,
    extract_sanskrit_grammar_evidence,
)
from langnet.paradigm.grammar import (
    EntryType,
    FeatureValue,
    FetchableParadigmKind,
    FunctionalAnalysis,
    FunctionalRelation,
    GrammarEvidence,
    LanguageCode,
    NativeAnalysis,
    ParadigmKind,
    ParadigmRequest,
    ParadigmResolutionCandidate,
    ParadigmResolutionPayload,
)
from langnet.paradigm.greek_learner_keys import (
    greek_learner_paradigm_record,
    is_unresolved_greek_learner_key,
)
from langnet.pedagogy.foster import foster_display_for_features


def resolve_paradigm_request(
    language: LanguageCode, searched_form: str, lookup_records: Sequence[Mapping[str, object]]
) -> ParadigmResolutionPayload:
    normalized_form = _normalized_form(searched_form, lookup_records)
    enriched_records = _enrich_lookup_records(language, searched_form, lookup_records)
    candidates = [
        _candidate_from_evidence(searched_form, evidence, record)
        for record in enriched_records
        for evidence in _extract_for_language(language, record)
    ]
    candidates.sort(key=_candidate_sort_key)
    if not candidates:
        candidates.append(
            ParadigmResolutionCandidate(
                lemma=normalized_form,
                entry_type="unknown",
                part_of_speech="unknown",
                paradigm_kind="unknown",
                confidence="low",
                provenance=["resolver"],
                unresolved_reason="no_grammar_evidence",
            )
        )
    return ParadigmResolutionPayload(
        searched_form=searched_form,
        normalized_form=normalized_form,
        language=language,
        candidates=candidates,
    )


def _candidate_sort_key(candidate: ParadigmResolutionCandidate) -> tuple[int, int]:
    confidence_rank = {"high": 0, "medium": 1, "low": 2}
    return (
        0 if candidate.paradigm_request is not None else 1,
        confidence_rank.get(candidate.confidence, 2),
    )


def _enrich_lookup_records(
    language: LanguageCode,
    searched_form: str,
    records: Sequence[Mapping[str, object]],
) -> list[Mapping[str, object]]:
    enriched: list[Mapping[str, object]] = list(records)
    if language != "grc":
        return enriched

    for value in _greek_hint_inputs(searched_form, records):
        hint_record = greek_learner_paradigm_record(value)
        if hint_record is None:
            continue
        hint_key = _record_source_key(hint_record)
        if hint_key and any(_record_source_key(record) == hint_key for record in enriched):
            continue
        enriched.append(hint_record)
    return enriched


def _greek_hint_inputs(
    searched_form: str,
    records: Sequence[Mapping[str, object]],
) -> list[str]:
    values = [searched_form]
    for record in records:
        for key in ("lemma", "normalized_form", "canonical", "canonical_name", "source_key"):
            value = record.get(key)
            if isinstance(value, str) and value:
                values.append(value)
    return list(dict.fromkeys(values))


def _record_source_key(record: Mapping[str, object]) -> str:
    for key in ("source_key", "diogenes_key", "betacode"):
        value = record.get(key)
        if isinstance(value, str) and value:
            return value
    metadata = record.get("metadata")
    if isinstance(metadata, Mapping):
        return _record_source_key(cast(Mapping[str, object], metadata))
    return ""


def _extract_for_language(
    language: LanguageCode, record: Mapping[str, object]
) -> list[GrammarEvidence]:
    if language == "san":
        return extract_sanskrit_grammar_evidence(record)
    if language == "lat":
        return extract_latin_grammar_evidence(record)
    if language == "grc":
        return extract_greek_grammar_evidence(record)
    return []


def _normalized_form(searched_form: str, records: Sequence[Mapping[str, object]]) -> str:
    for record in records:
        value = record.get("normalized_form")
        if isinstance(value, str) and value:
            return value
    return searched_form


def _candidate_from_evidence(
    searched_form: str,
    evidence: GrammarEvidence,
    record: Mapping[str, object],
) -> ParadigmResolutionCandidate:
    paradigm_kind = _paradigm_kind(evidence.part_of_speech)
    native_analyses = _native_analyses(evidence)
    functional_analyses = [
        relation
        for native in native_analyses
        for relation in _functional_analyses(evidence.language, native.features)
    ]
    request, unresolved_reason = _build_request(evidence, paradigm_kind)
    entry_type = _entry_type(searched_form, evidence)
    observed_form = _record_observed_form(record, searched_form)
    slot_features = _primary_slot_features(native_analyses)
    foster_display = _record_foster_display(record, evidence.language, slot_features)
    return ParadigmResolutionCandidate(
        lemma=evidence.lemma,
        entry_type=entry_type,
        part_of_speech=evidence.part_of_speech,
        paradigm_kind=paradigm_kind,
        observed_form=observed_form,
        slot_features=slot_features,
        foster_display=foster_display,
        display_summary=_candidate_display_summary(
            evidence.lemma,
            slot_features,
            foster_display,
        ),
        ranking_reasons=_record_string_list(record, "ranking_reasons"),
        native_analyses=native_analyses,
        functional_analyses=functional_analyses,
        paradigm_request=request,
        confidence=evidence.confidence if request is not None else "low",
        provenance=[evidence.source],
        unresolved_reason=unresolved_reason,
    )


def _record_observed_form(record: Mapping[str, object], searched_form: str) -> str:
    for key in ("observed_form", "normalized_form", "form"):
        value = record.get(key)
        if isinstance(value, str) and value:
            return value
    return searched_form


def _primary_slot_features(native_analyses: Sequence[NativeAnalysis]) -> dict[str, FeatureValue]:
    if not native_analyses:
        return {}
    features = native_analyses[0].features
    return {
        key: value
        for key, value in features.items()
        if key in {"case", "number", "gender", "person", "tense", "voice", "mood"}
    }


def _record_foster_display(
    record: Mapping[str, object],
    language: LanguageCode,
    features: Mapping[str, FeatureValue],
) -> str:
    value = record.get("foster_display")
    if isinstance(value, str):
        return value
    return foster_display_for_features(language, features)


def _candidate_display_summary(
    lemma: str,
    features: Mapping[str, FeatureValue],
    foster_display: str,
) -> str | None:
    if not foster_display:
        return None
    grammar_bits = [
        str(features[key])
        for key in ("case", "number", "gender", "person", "tense", "voice", "mood")
        if features.get(key)
    ]
    grammar = " ".join(grammar_bits)
    return f"{lemma}: {grammar} ({foster_display})" if grammar else f"{lemma}: {foster_display}"


def _record_string_list(record: Mapping[str, object], key: str) -> list[str]:
    value = record.get(key)
    if not isinstance(value, Sequence) or isinstance(value, str | bytes):
        return []
    return [item for item in value if isinstance(item, str)]


def _entry_type(searched_form: str, evidence: GrammarEvidence) -> EntryType:
    if evidence.part_of_speech == "indeclinable":
        return "indeclinable"
    if evidence.source == "langnet:greek_learner_paradigm_hints":
        return "root"
    if evidence.analyses and searched_form.casefold() != evidence.lemma.casefold():
        return "variant"
    if evidence.lemma and searched_form.casefold() == evidence.lemma.casefold():
        return "root"
    return "unknown"


def _paradigm_kind(part_of_speech: str) -> ParadigmKind:
    if part_of_speech in {"noun", "adjective", "pronoun"}:
        return "declension"
    if part_of_speech == "verb":
        return "conjugation"
    if part_of_speech == "indeclinable":
        return "none"
    return "unknown"


def _native_analyses(evidence: GrammarEvidence) -> list[NativeAnalysis]:
    if evidence.analyses:
        return [
            NativeAnalysis(
                language=evidence.language,
                features={**evidence.features, **analysis},
                source=evidence.source,
            )
            for analysis in evidence.analyses
        ]
    return [
        NativeAnalysis(
            language=evidence.language,
            features=dict(evidence.features),
            source=evidence.source,
        )
    ]


def _functional_analyses(
    language: LanguageCode, features: Mapping[str, FeatureValue]
) -> list[FunctionalAnalysis]:
    case_value = features.get("case")
    case = case_value.casefold() if isinstance(case_value, str) else ""
    number = features.get("number")
    native_feature: dict[str, FeatureValue] = {"case": case, "number": number}
    if language == "grc" and case == "dative":
        return [
            FunctionalAnalysis(
                relation="recipient_or_goal",
                native_feature=native_feature,
                confidence="medium",
            ),
            FunctionalAnalysis(
                relation="location", native_feature=native_feature, confidence="low"
            ),
            FunctionalAnalysis(
                relation="instrument_or_means",
                native_feature=native_feature,
                confidence="low",
            ),
        ]
    relation_map: dict[str, FunctionalRelation] = {
        "nominative": "subject",
        "accusative": "direct_object",
        "dative": "recipient_or_goal",
        "ablative": "source_or_separation",
        "genitive": "possession_or_association",
        "locative": "location",
        "instrumental": "instrument_or_means",
        "vocative": "address",
    }
    relation = relation_map.get(case, "unknown")
    return [
        FunctionalAnalysis(
            relation=relation,
            native_feature=native_feature,
            confidence="high" if relation != "unknown" else "low",
        )
    ]


def _build_request(
    evidence: GrammarEvidence, paradigm_kind: ParadigmKind
) -> tuple[ParadigmRequest | None, str | None]:
    if paradigm_kind == "none":
        return None, "indeclinable"
    if paradigm_kind not in {"declension", "conjugation"}:
        if evidence.language == "grc" and is_unresolved_greek_learner_key(evidence.lemma):
            return None, "greek_learner_key_not_resolved_to_source_key"
        return None, "unsupported_part_of_speech"
    if evidence.language == "san":
        return _build_sanskrit_request(evidence, paradigm_kind)
    if evidence.language in {"lat", "grc"}:
        return _build_diogenes_request(evidence, paradigm_kind)
    return None, "unsupported_language"


def _build_sanskrit_request(
    evidence: GrammarEvidence, paradigm_kind: ParadigmKind
) -> tuple[ParadigmRequest | None, str | None]:
    if paradigm_kind == "declension":
        gender = evidence.features.get("heritage_gender")
        if not isinstance(gender, str) or not gender:
            return None, "missing_gender_or_declension"
        return (
            ParadigmRequest(
                source="heritage:sktdeclin",
                language="san",
                lemma=evidence.lemma,
                kind="declension",
                options={"gender": gender},
            ),
            None,
        )
    present_class = evidence.features.get("present_class")
    if not isinstance(present_class, str) or not present_class:
        return None, "missing_present_class"
    return (
        ParadigmRequest(
            source="heritage:sktconjug",
            language="san",
            lemma=evidence.lemma,
            kind="conjugation",
            options={"class": present_class},
        ),
        None,
    )


def _build_diogenes_request(
    evidence: GrammarEvidence, paradigm_kind: ParadigmKind
) -> tuple[ParadigmRequest | None, str | None]:
    if paradigm_kind not in {"declension", "conjugation"}:
        return None, "unsupported_part_of_speech"
    fetchable_kind = cast(FetchableParadigmKind, paradigm_kind)
    lemma = evidence.features.get("source_key") if evidence.language == "grc" else evidence.lemma
    if evidence.language == "grc" and not isinstance(lemma, str):
        hint_record = greek_learner_paradigm_record(evidence.lemma)
        if hint_record is not None:
            lemma = _record_source_key(hint_record)
    if not isinstance(lemma, str) or not lemma:
        return None, "missing_lemma"
    return (
        ParadigmRequest(
            source="diogenes:inflect",
            language=evidence.language,
            lemma=lemma,
            kind=fetchable_kind,
            options={},
        ),
        None,
    )
