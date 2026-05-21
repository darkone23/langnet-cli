from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

from langnet.pedagogy.foster import foster_display_for_features

CASE_TO_RELATION = {
    "nominative": "subject",
    "accusative": "direct_object",
    "dative": "recipient_or_goal",
    "ablative": "source_or_separation",
    "genitive": "possession_or_association",
    "locative": "location",
    "instrumental": "instrument_or_means",
    "vocative": "address",
}

FEATURE_PREDICATES = {
    "has_pos": "pos",
    "has_case": "case",
    "has_number": "number",
    "has_gender": "gender",
    "has_person": "person",
    "has_tense": "tense",
    "has_voice": "voice",
    "has_mood": "mood",
    "has_degree": "degree",
    "has_declension": "declension",
    "has_conjugation": "conjugation",
}


@dataclass(frozen=True)
class MorphologyCandidate:
    language: str
    query: str
    observed_form: str
    normalized_form: str
    lemma: str
    source: str
    part_of_speech: str | None = None
    features: dict[str, Any] = field(default_factory=dict)
    analyses: list[dict[str, Any]] = field(default_factory=list)
    functional_relations: list[str] = field(default_factory=list)
    foster_display: str = ""
    confidence: str = "low"
    provenance: list[str] = field(default_factory=list)
    ranking_reasons: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class _CandidateInput:
    language: str
    query: str
    observed: str
    lemma: str
    source: str
    features: dict[str, Any]
    analysis: object = None


def candidates_from_triples(
    language: str,
    query: str,
    triples: Sequence[Mapping[str, Any]],
) -> list[MorphologyCandidate]:
    candidates: list[MorphologyCandidate] = []
    candidates.extend(_from_morphology_objects(language, query, triples))
    candidates.extend(_from_interpretation_graph(language, query, triples))
    candidates.extend(_from_direct_form_graph(language, query, triples))
    return rank_candidates(candidates)


def rank_candidates(candidates: Sequence[MorphologyCandidate]) -> list[MorphologyCandidate]:
    return sorted(candidates, key=_rank_key)


def _from_morphology_objects(
    language: str,
    query: str,
    triples: Sequence[Mapping[str, Any]],
) -> list[MorphologyCandidate]:
    candidates: list[MorphologyCandidate] = []
    for triple in triples:
        if triple.get("predicate") != "has_morphology":
            continue
        obj = triple.get("object")
        if not isinstance(obj, Mapping):
            continue
        features = _mapping_dict(obj.get("features"))
        lemma = str(obj.get("lemma") or "").strip()
        observed = str(obj.get("form") or query).strip()
        if not lemma:
            continue
        candidates.append(
            _build_candidate(
                _CandidateInput(
                    language=language,
                    query=query,
                    observed=observed,
                    lemma=lemma,
                    source=_source(triple),
                    features=features,
                    analysis=obj.get("analysis"),
                )
            )
        )
    return candidates


def _from_interpretation_graph(
    language: str,
    query: str,
    triples: Sequence[Mapping[str, Any]],
) -> list[MorphologyCandidate]:
    by_subject: dict[str, list[Mapping[str, Any]]] = {}
    form_to_interp: list[tuple[str, str, Mapping[str, Any]]] = []
    for triple in triples:
        subject = str(triple.get("subject") or "")
        by_subject.setdefault(subject, []).append(triple)
        if triple.get("predicate") == "has_interpretation":
            form_to_interp.append((subject, str(triple.get("object") or ""), triple))

    candidates: list[MorphologyCandidate] = []
    for form_anchor, interp_anchor, link_triple in form_to_interp:
        interp_triples = by_subject.get(interp_anchor, [])
        lex_anchor = _lexeme_anchor_from_interpretation(interp_triples)
        lemma = _clean_lexeme(lex_anchor) if lex_anchor else None
        if not lex_anchor or not lemma:
            continue
        features = _features_from_predicates(by_subject.get(lex_anchor, []))
        features.update(_features_from_predicates(interp_triples))
        observed = form_anchor.removeprefix("form:") or query
        candidates.append(
            _build_candidate(
                _CandidateInput(
                    language=language,
                    query=query,
                    observed=observed,
                    lemma=lemma,
                    source=_source(interp_triples[0] if interp_triples else link_triple),
                    features=features,
                )
            )
        )
    return candidates


def _from_direct_form_graph(
    language: str,
    query: str,
    triples: Sequence[Mapping[str, Any]],
) -> list[MorphologyCandidate]:
    by_subject: dict[str, list[Mapping[str, Any]]] = {}
    lemma_by_form: dict[str, str] = {}
    lex_anchor_by_form: dict[str, str] = {}
    display_by_form: dict[str, str] = {}
    source_by_form: dict[str, str] = {}
    for triple in triples:
        subject = str(triple.get("subject") or "")
        by_subject.setdefault(subject, []).append(triple)
        if not subject.startswith("form:"):
            continue
        predicate = str(triple.get("predicate") or "")
        obj = triple.get("object")
        if predicate == "inflection_of" and isinstance(obj, str):
            lemma_by_form[subject] = _clean_lexeme(obj)
            lex_anchor_by_form[subject] = obj
            source_by_form.setdefault(subject, _source(triple))
        elif predicate == "has_form" and isinstance(obj, str) and obj:
            display_by_form[subject] = obj
            source_by_form.setdefault(subject, _source(triple))

    candidates: list[MorphologyCandidate] = []
    for form_anchor, lemma in lemma_by_form.items():
        lex_anchor = lex_anchor_by_form.get(form_anchor, f"lex:{lemma}")
        features = _features_from_predicates(by_subject.get(lex_anchor, []))
        features.update(_features_from_predicates(by_subject.get(form_anchor, [])))
        if not features:
            continue
        observed = display_by_form.get(form_anchor) or form_anchor.removeprefix("form:") or query
        candidates.append(
            _build_candidate(
                _CandidateInput(
                    language=language,
                    query=query,
                    observed=observed,
                    lemma=lemma,
                    source=source_by_form.get(form_anchor, "unknown"),
                    features=features,
                )
            )
        )
    return candidates


def _build_candidate(parts: _CandidateInput) -> MorphologyCandidate:
    relations = _functional_relations(parts.features)
    display = foster_display_for_features(parts.language, parts.features)
    reasons = _ranking_reasons(parts.observed, parts.lemma, parts.features)
    return MorphologyCandidate(
        language=parts.language,
        query=parts.query,
        observed_form=parts.observed,
        normalized_form=parts.observed,
        lemma=_clean_lexeme(parts.lemma),
        source=parts.source,
        part_of_speech=str(parts.features["pos"]) if parts.features.get("pos") else None,
        features=parts.features,
        analyses=[{"text": parts.analysis}]
        if isinstance(parts.analysis, str) and parts.analysis
        else [],
        functional_relations=relations,
        foster_display=display,
        confidence="high" if _is_strongly_determined(parts.features) else "medium",
        provenance=[parts.source],
        ranking_reasons=reasons,
    )


def _features_from_predicates(triples: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    features: dict[str, Any] = {}
    for triple in triples:
        key = FEATURE_PREDICATES.get(str(triple.get("predicate") or ""))
        if key:
            features[key] = triple.get("object")
    return features


def _functional_relations(features: Mapping[str, Any]) -> list[str]:
    case = features.get("case")
    if isinstance(case, str):
        relation = CASE_TO_RELATION.get(case)
        if relation:
            return [relation]
    return []


def _lexeme_anchor_from_interpretation(triples: Sequence[Mapping[str, Any]]) -> str | None:
    for triple in triples:
        if triple.get("predicate") == "realizes_lexeme":
            return str(triple.get("object") or "")
    return None


def _clean_lexeme(value: str) -> str:
    return value.removeprefix("lex:").split("#", 1)[0]


def _source(triple: Mapping[str, Any]) -> str:
    metadata = triple.get("metadata")
    if isinstance(metadata, Mapping):
        evidence = metadata.get("evidence")
        if isinstance(evidence, Mapping):
            source_tool = evidence.get("source_tool")
            if isinstance(source_tool, str) and source_tool:
                return source_tool
        for key in ("source", "tool"):
            value = metadata.get(key)
            if isinstance(value, str) and value:
                return value
    return "unknown"


def _ranking_reasons(observed: str, lemma: str, features: Mapping[str, Any]) -> list[str]:
    reasons: list[str] = []
    if observed:
        reasons.append("observed-form")
    if lemma:
        reasons.append("lemma")
    if {"case", "number", "gender"}.issubset(features):
        reasons.append("case-number-gender")
    if {"person", "number", "tense", "voice", "mood"}.issubset(features):
        reasons.append("person-number-tense-voice-mood")
    return reasons


def _rank_key(candidate: MorphologyCandidate) -> tuple[int, int, int, int, str]:
    confidence = {"high": 0, "medium": 1, "low": 2}.get(candidate.confidence, 3)
    exact_query = 0 if candidate.observed_form == candidate.query else 1
    strong = (
        0
        if any(
            reason.endswith("gender") or reason.endswith("mood")
            for reason in candidate.ranking_reasons
        )
        else 1
    )
    return (confidence, exact_query, strong, -len(candidate.ranking_reasons), candidate.lemma)


def _is_strongly_determined(features: Mapping[str, Any]) -> bool:
    return {"case", "number"}.issubset(features) or {
        "person",
        "number",
        "tense",
        "voice",
        "mood",
    }.issubset(features)


def _mapping_dict(value: object) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        return {}
    return {str(key): item for key, item in value.items()}
