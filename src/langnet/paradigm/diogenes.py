from __future__ import annotations

import re
from collections.abc import Sequence
from typing import cast

from bs4 import BeautifulSoup, Tag

from langnet.paradigm.grammar import FeatureValue, FetchableParadigmKind, LanguageCode
from langnet.paradigm.models import ParadigmBlock, ParadigmForm, ParadigmPayload, ParadigmSlot

CASE_MAP = {
    "nom": "nominative",
    "nominative": "nominative",
    "gen": "genitive",
    "genitive": "genitive",
    "dat": "dative",
    "dative": "dative",
    "acc": "accusative",
    "accusative": "accusative",
    "abl": "ablative",
    "ablative": "ablative",
    "voc": "vocative",
    "vocative": "vocative",
}
NUMBER_MAP = {
    "sg": "singular",
    "sing": "singular",
    "singular": "singular",
    "pl": "plural",
    "plur": "plural",
    "plural": "plural",
    "dual": "dual",
}
TENSE_MAP = {
    "pres": "present",
    "present": "present",
    "perf": "perfect",
    "perfect": "perfect",
    "imperf": "imperfect",
    "imperfect": "imperfect",
    "fut": "future",
    "future": "future",
    "aor": "aorist",
    "aorist": "aorist",
}
MOOD_MAP = {
    "ind": "indicative",
    "indicative": "indicative",
    "subj": "subjunctive",
    "subjunctive": "subjunctive",
    "opt": "optative",
    "optative": "optative",
    "imperat": "imperative",
    "imperative": "imperative",
}
VOICE_MAP = {
    "act": "active",
    "active": "active",
    "mid": "middle",
    "middle": "middle",
    "pass": "passive",
    "passive": "passive",
}
PERSON_MAP = {"1st": "1", "2nd": "2", "3rd": "3", "1": "1", "2": "2", "3": "3"}


def parse_diogenes_inflect_html(
    html: str,
    *,
    language: LanguageCode,
    lemma: str,
    kind: FetchableParadigmKind,
    request_url: str | None = None,
) -> ParadigmPayload:
    soup = BeautifulSoup(html, "html.parser")
    slots = [_slot_from_span(span) for span in soup.select("span.form_span_visible")]
    return ParadigmPayload(
        language=language,
        lemma=lemma,
        kind=kind,
        source="diogenes:inflect",
        source_request={"url": request_url or "", "params": {"q": lemma}},
        paradigms=[
            ParadigmBlock(
                label=f"{lemma} {kind}",
                dimensions=_dimensions_for_slots(slots),
                slots=slots,
            )
        ],
        warnings=[] if slots else ["diogenes_inflect_forms_not_found"],
    )


def _slot_from_span(span: Tag) -> ParadigmSlot:
    source_label = span.get("infl", "")
    source_label = source_label if isinstance(source_label, str) else ""
    source_key = _source_key(span)
    text = _visible_form_text(span)
    features = _features_from_label(source_label)
    return ParadigmSlot(
        features=cast(dict[str, FeatureValue], features),
        forms=[ParadigmForm(text=text, normalized=text, source_key=source_key or text)],
        source_label=source_label,
        is_ambiguous=_is_ambiguous_label(source_label),
    )


def _source_key(span: Tag) -> str:
    input_node = span.find("input")
    if not isinstance(input_node, Tag):
        return ""
    value = input_node.get("value", "")
    return value if isinstance(value, str) else ""


def _visible_form_text(span: Tag) -> str:
    text = " ".join(span.get_text(" ", strip=True).split())
    return text.split(":", 1)[0].strip()


def _features_from_label(label: str) -> dict[str, str]:
    features: dict[str, str] = {}
    cases: list[str] = []
    for token in _label_tokens(label):
        _apply_token(features, token, cases)
    if cases:
        features["case"] = cases[0]
    if len(cases) > 1:
        features["case_alternates"] = "/".join(cases)
    return features


def _label_tokens(label: str) -> list[str]:
    return [token.casefold() for token in re.split(r"[\s,;/()]+", label) if token]


def _apply_token(features: dict[str, str], token: str, cases: list[str]) -> None:
    if token in CASE_MAP:
        case = CASE_MAP[token]
        if case not in cases:
            cases.append(case)
    elif token in NUMBER_MAP:
        features["number"] = NUMBER_MAP[token]
    elif token in TENSE_MAP:
        features["tense"] = TENSE_MAP[token]
    elif token in MOOD_MAP:
        features["mood"] = MOOD_MAP[token]
    elif token in VOICE_MAP:
        features["voice"] = VOICE_MAP[token]
    elif token in PERSON_MAP:
        features["person"] = PERSON_MAP[token]


def _is_ambiguous_label(label: str) -> bool:
    return "/" in label or label.count("(") > 1


def _dimensions_for_slots(slots: Sequence[ParadigmSlot]) -> list[str]:
    dimensions: list[str] = []
    for slot in slots:
        for key in slot.features:
            if key not in dimensions:
                dimensions.append(key)
    return dimensions
