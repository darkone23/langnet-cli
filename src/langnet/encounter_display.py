from __future__ import annotations

import re
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import cast

from langnet.pedagogy.foster import foster_codes_for_features

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

FOSTER_ANALYSIS_ALIASES = {
    "case": {
        "1": "1",
        "2": "2",
        "3": "3",
        "4": "4",
        "5": "5",
        "6": "6",
        "7": "7",
        "8": "8",
        "nom": "nom",
        "nominative": "nominative",
        "voc": "voc",
        "vocative": "vocative",
        "acc": "acc",
        "accusative": "accusative",
        "gen": "gen",
        "genitive": "genitive",
        "dat": "dat",
        "dative": "dative",
        "abl": "abl",
        "ablative": "ablative",
        "loc": "loc",
        "locative": "locative",
        "instr": "instr",
        "inst": "inst",
        "instrumental": "instrumental",
    },
    "gender": {
        "m": "m",
        "masc": "masculine",
        "masculine": "masculine",
        "f": "f",
        "fem": "feminine",
        "feminine": "feminine",
        "n": "n",
        "neut": "neuter",
        "neuter": "neuter",
    },
    "number": {
        "sg": "sg",
        "sing": "singular",
        "singular": "singular",
        "du": "du",
        "dual": "dual",
        "pl": "pl",
        "plur": "plural",
        "plural": "plural",
    },
    "tense": {
        "pres": "pres",
        "present": "present",
        "fut": "fut",
        "future": "future",
        "imperf": "imperf",
        "imperfect": "imperfect",
        "perf": "perf",
        "perfect": "perfect",
        "aor": "aor",
        "aorist": "aorist",
        "plupf": "plupf",
        "pluperfect": "pluperfect",
    },
    "mood": {
        "indic": "indic",
        "indicative": "indicative",
        "subj": "subj",
        "subjunctive": "subjunctive",
        "opt": "opt",
        "optative": "optative",
        "imper": "imper",
        "imperative": "imperative",
    },
    "voice": {
        "act": "act",
        "active": "active",
        "mid": "mid",
        "middle": "middle",
        "pass": "pass",
        "passive": "passive",
        "depon": "deponent",
        "deponent": "deponent",
        "semi-depon": "semi-deponent",
        "semi-deponent": "semi-deponent",
    },
    "participle": {
        "part": "part",
        "participle": "participle",
    },
}


@dataclass(frozen=True, slots=True)
class EncounterAnalysisView:
    form: str
    lemma: str
    analysis: str
    source: str
    foster_display: str = ""

    @property
    def display_text(self) -> str:
        foster_suffix = f" [Foster: {self.foster_display}]" if self.foster_display else ""
        return f"{self.form} -> {self.lemma}: {self.analysis}{foster_suffix} ({self.source})"


@dataclass(frozen=True, slots=True)
class SourceDetailSummary:
    cross_refs: tuple[str, ...] = field(default_factory=tuple)
    source_refs: tuple[str, ...] = field(default_factory=tuple)
    examples: tuple[str, ...] = field(default_factory=tuple)

    def format(self, *, max_items: int = 3) -> str:
        parts: list[str] = []
        for label, values in (
            ("cross refs", self.cross_refs),
            ("source refs", self.source_refs),
            ("examples", self.examples),
        ):
            if values:
                parts.append(f"{label}: {', '.join(values[:max_items])}")
        return "; ".join(parts)


@dataclass(frozen=True, slots=True)
class EncounterHeaderView:
    forms: tuple[str, ...] = field(default_factory=tuple)
    source_keys: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True, slots=True)
class EncounterMeaningView:
    display_gloss: str
    evidence_gloss: str
    evidence_length_note: str
    length_note: str
    sources: tuple[str, ...]
    witness_count: int
    confidence_label: str
    source_refs: tuple[str, ...]
    source_detail_summary: SourceDetailSummary
    translation_sources: tuple[str, ...]
    source_langs: tuple[str, ...]

    @property
    def source_text(self) -> str:
        return ", ".join(self.sources) if self.sources else "unknown"


def build_display_payload(  # noqa: PLR0913
    reduction: object,
    morphology_rows: Sequence[Mapping[str, str]],
    *,
    language: str,
    max_gloss_chars: int,
    include_foster: bool,
    include_source_details: bool,
    bucket_gloss,
    bucket_learner_gloss,
) -> dict[str, object]:
    """Build JSON-ready display metadata aligned to the sorted reduction result."""
    header_view = build_header_view(reduction)
    analysis_views = build_analysis_views(
        morphology_rows,
        language=language,
        include_foster=include_foster,
    )
    buckets = tuple(_reduction_buckets(reduction))
    meaning_views = [
        build_meaning_view(
            bucket,
            learner_gloss=bucket_learner_gloss(bucket),
            evidence_gloss=bucket_gloss(bucket),
            max_gloss_chars=max_gloss_chars,
            include_source_details=include_source_details,
        )
        for bucket in buckets
    ]
    return {
        "header": header_view_payload(header_view),
        "analysis": [analysis_view_payload(view) for view in analysis_views],
        "meanings": [
            meaning_view_payload(bucket, view) for bucket, view in zip(buckets, meaning_views)
        ],
        "options": {
            "max_gloss_chars": max_gloss_chars,
            "foster_labels": include_foster,
            "source_details": include_source_details,
        },
    }


def header_view_payload(view: EncounterHeaderView) -> dict[str, object]:
    return {
        "forms": list(view.forms),
        "source_keys": list(view.source_keys),
    }


def analysis_view_payload(view: EncounterAnalysisView) -> dict[str, object]:
    return {
        "form": view.form,
        "lemma": view.lemma,
        "analysis": view.analysis,
        "source": view.source,
        "foster_display": view.foster_display,
        "display_text": view.display_text,
    }


def source_detail_summary_payload(summary: SourceDetailSummary) -> dict[str, object]:
    return {
        "cross_refs": list(summary.cross_refs),
        "source_refs": list(summary.source_refs),
        "examples": list(summary.examples),
        "text": summary.format(),
    }


def meaning_view_payload(bucket: object, view: EncounterMeaningView) -> dict[str, object]:
    witnesses = tuple(_bucket_witnesses(bucket))
    return {
        "bucket_id": _string_value(getattr(bucket, "bucket_id", "")),
        "display_gloss": view.display_gloss,
        "evidence_gloss": view.evidence_gloss,
        "evidence_length_note": view.evidence_length_note,
        "length_note": view.length_note,
        "sources": list(view.sources),
        "source_text": view.source_text,
        "witness_count": view.witness_count,
        "confidence_label": view.confidence_label,
        "source_refs": list(view.source_refs),
        "source_detail_summary": source_detail_summary_payload(view.source_detail_summary),
        "translation_sources": list(view.translation_sources),
        "source_langs": list(view.source_langs),
        "entries": [entry_summary_payload(witness) for witness in witnesses],
    }


def entry_summary_payload(witness: object) -> dict[str, object]:
    evidence = _witness_evidence(witness)
    source_entry = _mapping_value(evidence.get("source_entry"))
    source_tool = _witness_source_tool(witness) or _string_value(evidence.get("source_tool"))
    return {
        "witness_id": _string_value(getattr(witness, "wsu_id", "")),
        "lexeme_anchor": _witness_lexeme_anchor(witness),
        "sense_anchor": _string_value(getattr(witness, "sense_anchor", "")),
        "claim_id": _string_value(getattr(witness, "claim_id", "")),
        "source_tool": source_tool,
        "source_ref": _string_value(evidence.get("source_ref")),
        "source_lang": _string_value(evidence.get("source_lang")),
        "gloss_lang": _string_value(evidence.get("gloss_lang"))
        or _string_value(evidence.get("source_lang")),
        "display_form": _entry_display_form(witness, evidence, source_entry),
        "source_key": _string_value(evidence.get("display_slp1")),
        "headword": _entry_headword(witness, evidence, source_entry),
        "entry_id": _entry_id(evidence, source_entry),
        "dictionary": _entry_dictionary(evidence, source_entry, source_tool),
        "raw_blob_ref": _string_value(evidence.get("raw_blob_ref")),
        "source_encoding": _string_value(evidence.get("source_encoding")),
        "source_entry": _source_entry_payload(source_entry),
        "source_detail_summary": source_detail_summary_payload(
            summarize_source_details([evidence])
        ),
        "translation": _translation_payload(witness, evidence),
    }


def build_header_view(reduction: object) -> EncounterHeaderView:
    forms: list[str] = []
    source_keys: list[str] = []
    for bucket in _reduction_buckets(reduction):
        for witness in _bucket_witnesses(bucket):
            evidence = _witness_evidence(witness)
            display_iast = _string_value(evidence.get("display_iast"))
            display_slp1 = _string_value(evidence.get("display_slp1"))
            if display_iast:
                forms.append(display_iast)
            else:
                forms.append(_witness_lexeme_anchor(witness).removeprefix("lex:"))
            if display_slp1:
                source_keys.append(display_slp1)
    if not forms:
        forms = [anchor.removeprefix("lex:") for anchor in _reduction_lexeme_anchors(reduction)]
    return EncounterHeaderView(
        forms=tuple(_dedupe_preserve_order(forms)),
        source_keys=tuple(_dedupe_preserve_order(source_keys)),
    )


def build_analysis_views(
    rows: Sequence[Mapping[str, str]],
    *,
    language: str,
    include_foster: bool,
) -> list[EncounterAnalysisView]:
    views: list[EncounterAnalysisView] = []
    for row in rows:
        analysis = row.get("analysis", "")
        foster_display = foster_display_for_analysis(language, analysis) if include_foster else ""
        views.append(
            EncounterAnalysisView(
                form=row.get("form", ""),
                lemma=row.get("lemma", ""),
                analysis=analysis,
                source=row.get("source_tool", "") or "unknown",
                foster_display=foster_display,
            )
        )
    return views


def foster_display_for_analysis(language: str, analysis: str) -> str:
    alternatives = [
        _foster_display_alternative(language, alternative) for alternative in analysis.split("|")
    ]
    return " / ".join(_dedupe_preserve_order([value for value in alternatives if value]))


def build_meaning_view(
    bucket: object,
    *,
    learner_gloss: str,
    evidence_gloss: str,
    max_gloss_chars: int,
    include_source_details: bool = True,
) -> EncounterMeaningView:
    witnesses = tuple(_bucket_witnesses(bucket))
    displayed_gloss = shorten_text(learner_gloss or evidence_gloss, max_gloss_chars)
    evidence_display = ""
    evidence_length_note = ""
    length_note = ""
    if learner_gloss and learner_gloss != evidence_gloss:
        shortened_evidence = shorten_text(evidence_gloss, max_gloss_chars)
        if displayed_gloss != shortened_evidence:
            evidence_display = shortened_evidence
            evidence_length_note = display_length_note(
                evidence_display,
                evidence_gloss,
                label="evidence shown",
            )
    if not evidence_display:
        length_note = display_length_note(displayed_gloss, evidence_gloss)

    evidence_items = [_witness_evidence(witness) for witness in witnesses]
    source_detail_summary = (
        summarize_source_details(evidence_items)
        if include_source_details
        else SourceDetailSummary()
    )
    return EncounterMeaningView(
        display_gloss=displayed_gloss,
        evidence_gloss=evidence_display,
        evidence_length_note=evidence_length_note,
        length_note=length_note,
        sources=tuple(
            sorted(
                {
                    source_tool
                    for witness in witnesses
                    if (source_tool := _witness_source_tool(witness))
                }
            )
        ),
        witness_count=len(witnesses),
        confidence_label=str(getattr(bucket, "confidence_label", "")),
        source_refs=tuple(
            _dedupe_preserve_order(
                [
                    source_ref
                    for evidence in evidence_items
                    if (source_ref := _string_value(evidence.get("source_ref")))
                ]
            )
        ),
        source_detail_summary=source_detail_summary,
        translation_sources=tuple(_translation_sources(witnesses)),
        source_langs=tuple(
            sorted(
                {
                    source_lang
                    for evidence in evidence_items
                    if (source_lang := _string_value(evidence.get("source_lang")))
                }
            )
        ),
    )


def shorten_text(text: str, max_chars: int) -> str:
    normalized = re.sub(r"\s+", " ", text).strip()
    if len(normalized) <= max_chars:
        return normalized
    return normalized[: max_chars - 1].rstrip() + "…"


def display_length_note(
    displayed_gloss: str,
    evidence_gloss: str,
    *,
    label: str = "shown",
) -> str:
    evidence_chars = len(re.sub(r"\s+", " ", evidence_gloss).strip())
    displayed_chars = len(displayed_gloss)
    if evidence_chars <= displayed_chars:
        return ""
    return f"{label}: {displayed_chars}/{evidence_chars} chars"


def summarize_source_details(
    evidence_items: Iterable[Mapping[str, object]],
) -> SourceDetailSummary:
    groups = {
        "cross refs": [],
        "source refs": [],
        "examples": [],
    }
    for evidence in evidence_items:
        _collect_source_notes(evidence.get("source_notes"), groups)
        _collect_source_segments(evidence.get("source_segments"), groups)
    return SourceDetailSummary(
        cross_refs=tuple(_dedupe_preserve_order(groups["cross refs"])),
        source_refs=tuple(_dedupe_preserve_order(groups["source refs"])),
        examples=tuple(_dedupe_preserve_order(groups["examples"])),
    )


def _foster_display_alternative(language: str, analysis: str) -> str:
    features = foster_features_from_analysis(analysis)
    if not features:
        return ""
    codes = foster_codes_for_features(language, features)
    labels = [
        FOSTER_DISPLAY_LABELS.get(codes[key], codes[key].replace("_", " ").title())
        for key in FOSTER_DISPLAY_ORDER
        if key in codes
    ]
    return "; ".join(_dedupe_preserve_order(labels))


def foster_features_from_analysis(analysis: str) -> dict[str, str]:
    normalized = analysis.lower().replace("_", "-")
    if "future perfect" in normalized:
        normalized = normalized.replace("future perfect", "futperf")
    if "semi deponent" in normalized:
        normalized = normalized.replace("semi deponent", "semi-deponent")
    tokens = re.findall(r"[a-z0-9]+(?:-[a-z0-9]+)?", normalized)
    features: dict[str, str] = {}
    for feature_key, aliases in FOSTER_ANALYSIS_ALIASES.items():
        for token in tokens:
            if token in aliases:
                features[feature_key] = aliases[token]
                break
    if "participle" in features:
        features.setdefault("pos", features["participle"])
    return features


def _bucket_witnesses(bucket: object) -> Sequence[object]:
    witnesses = getattr(bucket, "witnesses", ())
    if not isinstance(witnesses, Sequence) or isinstance(witnesses, (str, bytes)):
        return ()
    return witnesses


def _reduction_buckets(reduction: object) -> Sequence[object]:
    buckets = getattr(reduction, "buckets", ())
    if not isinstance(buckets, Sequence) or isinstance(buckets, (str, bytes)):
        return ()
    return buckets


def _reduction_lexeme_anchors(reduction: object) -> Sequence[str]:
    anchors = getattr(reduction, "lexeme_anchors", ())
    if not isinstance(anchors, Sequence) or isinstance(anchors, (str, bytes)):
        return ()
    return [anchor for anchor in anchors if isinstance(anchor, str)]


def _witness_evidence(witness: object) -> Mapping[str, object]:
    evidence = getattr(witness, "evidence", {})
    return cast(Mapping[str, object], evidence) if isinstance(evidence, Mapping) else {}


def _witness_source_tool(witness: object) -> str:
    return _string_value(getattr(witness, "source_tool", ""))


def _witness_lexeme_anchor(witness: object) -> str:
    return _string_value(getattr(witness, "lexeme_anchor", ""))


def _mapping_value(value: object) -> Mapping[str, object]:
    return cast(Mapping[str, object], value) if isinstance(value, Mapping) else {}


def _entry_display_form(
    witness: object,
    evidence: Mapping[str, object],
    source_entry: Mapping[str, object],
) -> str:
    return (
        _string_value(evidence.get("display_iast"))
        or _string_value(source_entry.get("key_iast"))
        or _string_value(source_entry.get("headword_norm"))
        or _string_value(source_entry.get("headword_roma"))
        or _string_value(source_entry.get("term"))
        or _witness_lexeme_anchor(witness).removeprefix("lex:")
    )


def _entry_headword(
    witness: object,
    evidence: Mapping[str, object],
    source_entry: Mapping[str, object],
) -> str:
    return (
        _string_value(source_entry.get("headword_norm"))
        or _string_value(source_entry.get("headword_roma"))
        or _string_value(source_entry.get("headword_raw"))
        or _string_value(source_entry.get("key_iast"))
        or _string_value(evidence.get("display_iast"))
        or _witness_lexeme_anchor(witness).removeprefix("lex:")
    )


def _entry_id(evidence: Mapping[str, object], source_entry: Mapping[str, object]) -> str:
    for key in (
        "entry_id",
        "reference_id",
        "line_number",
        "source_page",
        "source_ref",
    ):
        value = _string_value(source_entry.get(key))
        if value:
            return value
    source_ref = _string_value(evidence.get("source_ref"))
    if not source_ref:
        return ""
    return source_ref.rsplit(":", 1)[-1] or source_ref


def _entry_dictionary(
    evidence: Mapping[str, object],
    source_entry: Mapping[str, object],
    source_tool: str,
) -> str:
    return (
        _string_value(source_entry.get("dict"))
        or _string_value(evidence.get("source_lexicon"))
        or source_tool
    )


def _source_entry_payload(source_entry: Mapping[str, object]) -> dict[str, object]:
    if not source_entry:
        return {}
    payload: dict[str, object] = {
        key: value
        for key, value in source_entry.items()
        if key != "source_text" and value is not None and value != ""
    }
    source_text = source_entry.get("source_text")
    if isinstance(source_text, str):
        payload["source_text_chars"] = len(re.sub(r"\s+", " ", source_text).strip())
        payload["has_source_text"] = True
    return payload


def _translation_payload(witness: object, evidence: Mapping[str, object]) -> dict[str, object]:
    is_translation = (
        _witness_source_tool(witness) == "translation"
        or evidence.get("source_tool") == "translation"
        or bool(evidence.get("translation_id"))
    )
    return {
        "available": is_translation,
        "translation_id": _string_value(evidence.get("translation_id")),
        "source_lexicon": _string_value(evidence.get("source_lexicon")),
        "source_text_lang": _string_value(evidence.get("source_text_lang")),
        "target_lang": _string_value(evidence.get("target_lang")),
        "model": _string_value(evidence.get("model")),
        "source_text_hash": _string_value(evidence.get("source_text_hash")),
        "derived_from_tool": _string_value(evidence.get("derived_from_tool")),
        "derived_from_sense": _string_value(evidence.get("derived_from_sense")),
    }


def _translation_sources(witnesses: Sequence[object]) -> list[str]:
    sources: list[str] = []
    for witness in witnesses:
        evidence = _witness_evidence(witness)
        if (
            _witness_source_tool(witness) != "translation"
            and evidence.get("source_tool") != "translation"
            and evidence.get("translation_id") is None
        ):
            continue
        source_lexicon = _string_value(evidence.get("source_lexicon"))
        derived_from_tool = _string_value(evidence.get("derived_from_tool"))
        if source_lexicon:
            sources.append(source_lexicon)
        elif derived_from_tool:
            sources.append(derived_from_tool)
    return _dedupe_preserve_order(sources)


def _string_value(value: object) -> str:
    return value.strip() if isinstance(value, str) else ""


def _collect_source_notes(
    source_notes: object,
    groups: dict[str, list[str]],
) -> None:
    if not isinstance(source_notes, Mapping):
        return
    source_notes_mapping = cast(Mapping[str, object], source_notes)
    field_map: dict[str, tuple[str, ...]] = {
        "cross refs": ("cross_reference_segments", "cross_references"),
        "source refs": ("source_reference_segments", "source_references"),
        "examples": ("example_segments", "examples"),
    }
    for label, fields in field_map.items():
        for field_name in fields:
            groups[label].extend(_string_sequence(source_notes_mapping.get(field_name)))


def _collect_source_segments(
    source_segments: object,
    groups: dict[str, list[str]],
) -> None:
    if not isinstance(source_segments, Sequence) or isinstance(source_segments, (str, bytes)):
        return
    for segment in source_segments:
        if not isinstance(segment, Mapping):
            continue
        segment_mapping = cast(Mapping[str, object], segment)
        display_text = segment_mapping.get("display_text") or segment_mapping.get("raw_text")
        if not isinstance(display_text, str) or not display_text.strip():
            continue
        labels = set(_string_sequence(segment_mapping.get("labels")))
        text = display_text.strip()
        if "cross_reference" in labels:
            groups["cross refs"].append(text)
        elif "example" in labels or "citation" in labels:
            groups["examples"].append(text)
        elif "source_reference" in labels:
            groups["source refs"].append(text)


def _string_sequence(value: object) -> list[str]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        return []
    return [text for item in value if (text := str(item).strip())]


def _dedupe_preserve_order(values: Sequence[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for value in values:
        if value and value not in seen:
            seen.add(value)
            out.append(value)
    return out
