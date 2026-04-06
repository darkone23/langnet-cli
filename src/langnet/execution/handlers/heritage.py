from __future__ import annotations

import json
import re
import time
from collections.abc import Mapping, Sequence
from functools import lru_cache
from pathlib import Path
from typing import TypedDict, cast

from bs4 import BeautifulSoup
from query_spec import ToolCallSpec

from langnet.clients.base import RawResponseEffect
from langnet.execution.effects import (
    ClaimEffect,
    DerivationEffect,
    ExtractionEffect,
    ProvenanceLink,
    stable_effect_id,
)
from langnet.execution.versioning import versioned
from langnet.heritage.client import HeritageHTTPClient
from langnet.heritage.html_extractor import (
    MorphologyPattern,
    MorphologySolution,
    extract_solutions,
)


class HeritageAnalysisVariant(TypedDict, total=False):
    """Analysis variant structure."""

    feature: str
    value: str


class HeritageAnalysis(TypedDict, total=False):
    """Heritage morphological analysis structure."""

    word: str
    analysis: str
    analysis_variants: list[HeritageAnalysisVariant]
    dictionary_url: str | None
    solution_number: int | None
    color: str | None
    segments: list[str] | list[object]


class HeritageSolution(TypedDict, total=False):
    """Heritage solution from HTML extraction."""

    word: str
    analysis: str
    dictionary_url: str | None
    solution_number: int
    color: str | None
    segments: list[str]
    patterns: list[dict[str, object]]


class HeritagePayload(TypedDict, total=False):
    """Heritage extraction/derivation payload."""

    lemma: str
    lemma_slp1: str
    heritage_guess: bool
    analyses: list[HeritageSolution]
    solutions: list[dict[str, object]]
    parsed_analyses: list[HeritageAnalysis]
    compound_solutions: list[dict[str, object]]


def _velthuis_to_slp1(text: str) -> str:
    """
    Lightweight Velthuis → SLP1 converter (mirrors codesketch cologne/core).
    Keeps things simple for anchoring while fuller parser support is wired.
    """
    if not text:
        return ""
    result = text
    result = result.replace('"s', "z").replace('"S', "z")
    result = result.replace("aa", "A").replace("ii", "I").replace("uu", "U")
    result = result.replace(".rr", "RR").replace(".r", "R")
    result = result.replace(".ll", "LL").replace(".l", "L")
    result = result.replace(".m", "M").replace(".h", "H")
    result = result.replace(".s", "S").replace(".t", "w").replace(".d", "q").replace(".n", "R")
    result = result.replace("~n", "Y").replace('"n', "N")
    result = result.replace(".a", "'")
    return result.lower()


@lru_cache(maxsize=1)
def _abbr_index() -> dict[str, dict[str, str]]:
    """Load Heritage abbreviation metadata (ported from codesketch)."""
    abbr_path = Path(__file__).with_name("abbr_data.json")
    try:
        return json.loads(abbr_path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _get_param(params: Mapping[str, object] | None, key: str) -> str:
    """Extract a string parameter from a mapping, returning empty string if not found."""
    try:
        if isinstance(params, Mapping):
            val = params.get(key)
            return val if isinstance(val, str) else ""
    except Exception:
        return ""
    return ""


def _needs_guess_fallback(solutions: list[MorphologySolution]) -> bool:
    if not solutions:
        return True
    for sol in solutions:
        patterns_val = sol.get("patterns")
        patterns = patterns_val if isinstance(patterns_val, Sequence) else []
        for pat in patterns:
            if isinstance(pat, Mapping):
                pat_dict = cast(dict[str, object], pat)
                analysis = pat_dict.get("analysis")
                if analysis and analysis != "?":
                    return False
    return True


def _fallback_user_feedback(endpoint: str) -> tuple[list[MorphologySolution], str, str]:
    vel_text = _extract_velthuis_from_endpoint(endpoint)
    if not vel_text:
        return [], "", ""
    client = HeritageHTTPClient()
    matches, raw_html, request_url = client.fetch_user_feedback_page(vel_text)
    if not matches:
        return [], "", ""
    patterns: list[MorphologyPattern] = []
    for m in matches:
        pattern: MorphologyPattern = {
            "word": m.display or m.canonical,
            "analysis": m.analysis or "?",
            "dictionary_url": m.entry_url or None,
        }
        patterns.append(pattern)
    raw_lines = []
    for p in patterns:
        line = f"[{p['word']}]"
        if p.get("analysis"):
            line += "{" + str(p["analysis"]) + "}"
        raw_lines.append(line)
    solution: MorphologySolution = {
        "solution_number": 1,
        "patterns": patterns,
        "color": "deep_sky_back",
        "raw_text": "\n".join(raw_lines),
        "segments": [],
    }
    return ([solution], raw_html, request_url)


def _extract_velthuis_from_endpoint(endpoint: str) -> str:
    if not endpoint:
        return ""
    query = endpoint.split("?", 1)[1] if "?" in endpoint else endpoint
    params: dict[str, str] = {}
    for part in query.split(";"):
        if "=" not in part:
            continue
        k, v = part.split("=", 1)
        params[k] = v
    return params.get("text", "")


def _extract_lemma_from_response(soup, call_params) -> str:
    """Extract lemma from Heritage HTML or call parameters."""
    lemma = ""
    first_i = soup.find("i")
    if first_i and isinstance(first_i.text, str):
        lemma = first_i.text.strip()
    if not lemma:
        roma_span = soup.find("span", class_="roma16o")
        if roma_span and isinstance(roma_span.text, str):
            lemma = roma_span.text.strip()
    if not lemma:
        lemma = _get_param(call_params, "text") or _get_param(call_params, "q")
    if not lemma:
        try:
            lemma = call_params.get("text", "")  # type: ignore[attr-defined]
        except Exception:
            lemma = ""
    return lemma


def _apply_guess_fallback(
    solutions: list[MorphologySolution], endpoint: str, raw_response: RawResponseEffect
) -> tuple[list[MorphologySolution], str, bool, str]:
    """
    Apply user feedback guess fallback if needed.

    Returns (solutions, lemma, guess_used, html).
    """
    guess_used = False
    lemma = ""
    html = raw_response.body.decode("utf-8", errors="ignore") if raw_response.body else ""

    if _needs_guess_fallback(solutions):
        guess_solutions, guess_html, guess_url = _fallback_user_feedback(endpoint)
        if guess_solutions:
            solutions = guess_solutions
            guess_used = True
            if guess_solutions[0].get("patterns"):
                guess_word = guess_solutions[0]["patterns"][0].get("word")
                if guess_word:
                    lemma = guess_word
            if guess_html:
                html = guess_html
            if guess_url:
                raw_response.endpoint = guess_url
    return solutions, lemma, guess_used, html


def _build_analyses_from_solutions(solutions: list[MorphologySolution]) -> list[dict[str, object]]:
    """Build flat list of analyses from nested solutions/patterns."""
    analyses: list[dict[str, object]] = []
    for solution in solutions:
        patterns_val = solution.get("patterns")
        if not patterns_val:
            continue
        patterns_list = patterns_val if isinstance(patterns_val, list) else []
        for pattern in patterns_list:
            analyses.append(
                {
                    "word": pattern.get("word", ""),
                    "analysis": pattern.get("analysis", ""),
                    "dictionary_url": pattern.get("dictionary_url"),
                    "solution_number": solution.get("solution_number"),
                    "color": solution.get("color"),
                    "segments": solution.get("segments", []),
                    "raw_text": solution.get("raw_text"),
                }
            )
    return analyses


@versioned("v1")
def extract_html(call: ToolCallSpec, raw_response: RawResponseEffect) -> ExtractionEffect:
    """
    Decode Heritage HTML and capture structured solutions/patterns for derivation.
    """
    start = time.perf_counter()
    html = raw_response.body.decode("utf-8", errors="ignore") if raw_response.body else ""
    soup = BeautifulSoup(html, "html.parser")

    lemma = _extract_lemma_from_response(soup, call.params)
    slp1 = _velthuis_to_slp1(lemma)

    solutions = extract_solutions(html)
    solutions, guess_lemma, guess_used, html = _apply_guess_fallback(
        solutions, raw_response.endpoint, raw_response
    )
    if guess_lemma:
        lemma = guess_lemma
        slp1 = _velthuis_to_slp1(lemma)

    analyses = _build_analyses_from_solutions(solutions)
    payload = {
        "raw_ref": raw_response.response_id,
        "raw_html": html,
        "request_url": raw_response.endpoint,
        "lemma": lemma,
        "lemma_slp1": slp1,
        "solutions": solutions,
        "analyses": analyses,
        "heritage_guess": guess_used,
    }
    duration_ms = int((time.perf_counter() - start) * 1000)
    return ExtractionEffect(
        extraction_id=stable_effect_id("ext", call.call_id, raw_response.response_id),
        tool=call.tool,
        call_id=call.call_id,
        source_call_id=call.params.get("source_call_id", ""),
        response_id=raw_response.response_id,
        kind="heritage_html",
        canonical=slp1 or lemma,
        payload=payload,
        load_duration_ms=duration_ms,
    )


@versioned("v1")
def derive_morph(call: ToolCallSpec, extraction: ExtractionEffect) -> DerivationEffect:
    """
    Build a richer derivation record from extracted Heritage HTML.
    """
    start = time.perf_counter()
    payload_val = extraction.payload if isinstance(extraction.payload, Mapping) else {}
    payload = cast(dict[str, object], payload_val) if isinstance(payload_val, Mapping) else {}
    canonical: str | None = None
    analyses: list[HeritageAnalysis] = []
    guess_val = payload.get("heritage_guess") if payload else False
    is_guess = bool(guess_val)

    if payload:
        lemma = payload.get("lemma")
        lemma_slp1 = payload.get("lemma_slp1")
        lemma_str = lemma if isinstance(lemma, str) else ""
        lemma_slp1_str = lemma_slp1 if isinstance(lemma_slp1, str) else ""
        canonical = lemma_str if is_guess else (lemma_slp1_str or lemma_str)

        raw_analyses = payload.get("analyses")
        if isinstance(raw_analyses, Sequence):
            for analysis in raw_analyses:
                if not isinstance(analysis, Mapping):
                    continue
                analysis_dict = cast(dict[str, object], analysis)
                analysis_code = analysis_dict.get("analysis")
                analysis_variants_list: list[HeritageAnalysisVariant] = []
                for variant in _parse_analysis_variants(
                    analysis_code if isinstance(analysis_code, str) else ""
                ):
                    if isinstance(variant, Mapping):
                        feat = variant.get("feature")
                        val = variant.get("value")
                        if isinstance(feat, str) and isinstance(val, str):
                            typed_variant: HeritageAnalysisVariant = {"feature": feat, "value": val}
                            analysis_variants_list.append(typed_variant)
                word_val = analysis_dict.get("word")
                dict_url = analysis_dict.get("dictionary_url")
                sol_num = analysis_dict.get("solution_number")
                color_val = analysis_dict.get("color")
                segs_val = analysis_dict.get("segments")
                segs: list[str] | list[object] = []
                if isinstance(segs_val, list):
                    segs = cast(list[object], segs_val)
                parsed: HeritageAnalysis = {
                    "word": word_val if isinstance(word_val, str) else "",
                    "analysis": analysis_code if isinstance(analysis_code, str) else "",
                    "analysis_variants": analysis_variants_list,
                    "dictionary_url": dict_url if isinstance(dict_url, str) else None,
                    "solution_number": sol_num if isinstance(sol_num, int) else None,
                    "color": color_val if isinstance(color_val, str) else None,
                    "segments": segs,
                }
                analyses.append(parsed)

    enriched_payload: dict[str, object] = dict(payload) if payload else {}
    enriched_payload["parsed_analyses"] = analyses
    # Convert HeritageAnalysis to dict[str, object] for _group_compounds
    analyses_as_dicts: list[dict[str, object]] = [cast(dict[str, object], a) for a in analyses]
    solutions_val = payload.get("solutions")
    solutions_list = solutions_val if isinstance(solutions_val, list) else []
    enriched_payload["compound_solutions"] = _group_compounds(
        analyses_as_dicts, cast(list[dict[str, object]], solutions_list)
    )
    prov = [
        ProvenanceLink(stage="extract", tool=extraction.tool, reference_id=extraction.extraction_id)
    ]
    duration_ms = int((time.perf_counter() - start) * 1000)
    return DerivationEffect(
        derivation_id=stable_effect_id("drv", call.call_id, extraction.extraction_id),
        tool=call.tool,
        call_id=call.call_id,
        source_call_id=call.params.get("source_call_id", ""),
        extraction_id=extraction.extraction_id,
        kind="heritage_morph",
        canonical=canonical,
        payload=enriched_payload,
        derive_duration_ms=duration_ms,
        provenance_chain=prov,
    )


def _select_lemma_for_claim(
    payload: Mapping[str, object] | None,
    canonical: str | None,
    call_params: Mapping[str, object] | None,
) -> str:
    """Select the appropriate lemma for the claim subject."""
    lemma = ""
    if isinstance(payload, Mapping):
        lemma_slp1 = payload.get("lemma_slp1")
        lemma_val = payload.get("lemma")
        lemma = cast(str, lemma_slp1 or lemma_val or "")
    if not lemma and canonical:
        lemma = canonical
    if not lemma:
        text_param = _get_param(call_params, "text")
        lemma = _velthuis_to_slp1(text_param) if text_param else text_param
    if not lemma and isinstance(call_params, Mapping):
        text_val = call_params.get("text", "")
        text_param = text_val if isinstance(text_val, str) else ""
        lemma = _velthuis_to_slp1(text_param) if text_param else text_param
    return (lemma or "").strip()


def _build_morphology_object(  # noqa: PLR0913
    lemma: str,
    word_slp1: str,
    variant: Mapping[str, object],
    analysis: Mapping[str, object],
    variant_index: int | None,
    color_class: str | None,
    color_norm: str | None,
    color_meaning: str | None,
) -> dict[str, object]:
    """Build a single morphology object from variant and analysis data."""
    analysis_val = variant.get("analysis", "")
    morph_obj: dict[str, object] = {
        "lemma": lemma or word_slp1,
        "form": word_slp1,
        "analysis": analysis_val if isinstance(analysis_val, str) else "",
    }
    variant_features = variant.get("features")
    if variant_index is not None:
        morph_obj["variant_index"] = variant_index
    dict_url = analysis.get("dictionary_url")
    if dict_url:
        morph_obj["dictionary_url"] = dict_url
    sol_num = analysis.get("solution_number")
    if sol_num:
        morph_obj["solution_number"] = sol_num
    if color_class:
        morph_obj["color"] = color_class
    if color_norm:
        morph_obj["color_normalized"] = color_norm
    if color_meaning:
        morph_obj["color_meaning"] = color_meaning
    if variant_features:
        morph_obj["features"] = variant_features
    return morph_obj


def _build_morphology_triples(
    analyses: Sequence[HeritageAnalysis],
    lemma: str,
    subject: str,
) -> list[dict[str, object]]:
    """Build morphology triples from Heritage analyses."""
    triples: list[dict[str, object]] = []
    for analysis in analyses or []:
        if not isinstance(analysis, Mapping):
            continue
        word_slp1 = _velthuis_to_slp1(analysis.get("word", ""))
        analysis_dict_cast = cast(dict[str, object], analysis)
        variants = analysis.get("analysis_variants") or [
            {
                "analysis": analysis.get("analysis", ""),
                "features": _analysis_features(analysis_dict_cast),
            }
        ]
        color_class_val = analysis.get("color")
        color_class = color_class_val if isinstance(color_class_val, str) else None
        color_norm = _normalize_color_class(color_class)
        color_meaning = COLOR_MEANINGS.get(color_norm or "", None)

        for idx, variant in enumerate(variants):
            if not isinstance(variant, Mapping):
                continue
            variant_index = idx + 1 if len(variants) > 1 else None
            morph_obj = _build_morphology_object(
                lemma,
                word_slp1,
                variant,
                analysis,
                variant_index,
                color_class,
                color_norm,
                color_meaning,  # noqa: E501
            )
            triples.append(
                {
                    "subject": f"form:{word_slp1}" if word_slp1 else subject,
                    "predicate": "has_morphology",
                    "object": morph_obj,
                }
            )
    return triples


def _build_claim_value(
    triples: list[dict[str, object]],
    payload: Mapping[str, object] | None,
) -> dict[str, object]:
    """Build the claim value dict with triples and optional payload data."""
    value: dict[str, object] = {"triples": triples}
    if isinstance(payload, Mapping):
        analyses_val = payload.get("analyses")
        if analyses_val:
            value["analyses"] = analyses_val
        compounds_val = payload.get("compound_solutions")
        if compounds_val:
            value["compounds"] = compounds_val
        raw_ref_val = payload.get("raw_ref")
        if raw_ref_val:
            value["raw_ref"] = raw_ref_val
        raw_html_val = payload.get("raw_html")
        if raw_html_val:
            value["raw_html"] = raw_html_val
    return value


@versioned("v1")
def claim_morph(call: ToolCallSpec, derivation: DerivationEffect) -> ClaimEffect:
    """
    Emit `has_morphology` claims with parsed Heritage payload preserved.
    """
    prov = derivation.provenance_chain[:] if derivation.provenance_chain else []
    prov.append(
        ProvenanceLink(stage="derive", tool=derivation.tool, reference_id=derivation.derivation_id)
    )
    payload = derivation.payload or {}

    payload_for_lemma = (
        cast(Mapping[str, object], payload) if isinstance(payload, Mapping) else None
    )
    lemma = _select_lemma_for_claim(
        payload_for_lemma,
        derivation.canonical,
        call.params,
    )
    subject = derivation.derivation_id if not lemma else f"lex:{lemma}"

    analyses: Sequence[HeritageAnalysis] = []
    if isinstance(payload, Mapping):
        payload_dict = cast(dict[str, object], payload)
        analyses_val = payload_dict.get("parsed_analyses") or payload_dict.get("analyses") or []
        if isinstance(analyses_val, Sequence):
            analyses = cast(Sequence[HeritageAnalysis], analyses_val)

    triples = _build_morphology_triples(analyses, lemma, subject)
    payload_for_claim = (
        cast(Mapping[str, object], payload) if isinstance(payload, Mapping) else None
    )
    value = _build_claim_value(triples, payload_for_claim)

    return ClaimEffect(
        claim_id=stable_effect_id("clm", call.call_id, derivation.derivation_id),
        tool=call.tool,
        call_id=call.call_id,
        source_call_id=call.params.get("source_call_id", ""),
        derivation_id=derivation.derivation_id,
        subject=subject,
        predicate="has_morphology",
        value=value,
        provenance_chain=prov,
    )


# --- Analysis parsing helpers (trimmed codesketch port) ---

GENDER_MAP = {
    "m": "masculine",
    "masc": "masculine",
    "m.": "masculine",
    "f": "feminine",
    "fem": "feminine",
    "f.": "feminine",
    "n": "neuter",
    "neut": "neuter",
    "n.": "neuter",
}
NUMBER_MAP = {
    "sg": "singular",
    "sg.": "singular",
    "s": "singular",
    "du": "dual",
    "d": "dual",
    "pl": "plural",
    "pl.": "plural",
    "p": "plural",
}
CASE_MAP = {
    "nom": "nominative",
    "n": "nominative",
    "voc": "vocative",
    "v": "vocative",
    "acc": "accusative",
    "a": "accusative",
    "instr": "instrumental",
    "i": "instrumental",
    "dat": "dative",
    "d": "dative",
    "abl": "ablative",
    "gen": "genitive",
    "g": "genitive",
    "loc": "locative",
    "l": "locative",
}
PERSON_MAP = {"1": 1, "2": 2, "3": 3}
TENSE_MAP = {
    "pres": "present",
    "impf": "imperfect",
    "fut": "future",
    "perf": "perfect",
    "plup": "pluperfect",
}
MOOD_MAP = {
    "ind": "indicative",
    "imp": "imperative",
    "opt": "optative",
    "subj": "subjunctive",
}
VOICE_MAP = {"act": "active", "ac": "active", "mid": "middle", "pass": "passive"}
POS_MAP = {
    "noun": "noun",
    "n": "noun",
    "verb": "verb",
    "v": "verb",
    "adj": "adjective",
    "adjective": "adjective",
    "pron": "pronoun",
    "adv": "adverb",
    "part": "participle",
    "ind": "indeclinable",
    "inde": "indeclinable",
}
CASE_CODE_INDEX = 1
GENDER_CODE_INDEX = 2
NUMBER_CODE_INDEX = 3

COLOR_MEANINGS: dict[str, str] = {
    "blue": "noun or adjective",
    "light_blue": "pronoun",
    "deep_sky": "pronoun",
    "cyan": "final compound member",
    "red": "finite verb",
    "yellow": "compound stem",
    "mauve": "indeclinable",
    "lavender": "preverb or preposition",
    "green": "vocative",
    "orange": "periphrastic or cvi stem",
    "magenta": "phonetic or sandhi",
    "salmon": "special infinitive",
    "grey": "unknown morphology",
    "beige": "general background",
    "pink": "annotation",
}


def _normalize_color_class(css_class: str | None) -> str | None:
    if not css_class:
        return None
    cls = css_class.lower()
    if cls.endswith("_back"):
        cls = cls.removesuffix("_back")
    color_keys = {
        "deep_sky": "deep_sky",
        "light_blue": "light_blue",
        "lawngreen": "green",
        "carmin": "red",
        "gray": "grey",
    }
    for key, value in color_keys.items():
        if key in cls:
            return value
    return cls or None


def _default_features() -> dict[str, object]:
    return {
        "pos": "unknown",
        "case": None,
        "gender": None,
        "number": None,
        "person": None,
        "tense": None,
        "voice": None,
        "mood": None,
        "compound_role": None,
        "verb_class": None,
    }


def _parse_analysis_variants(code: str) -> list[dict[str, object]]:
    """
    Split a Heritage analysis string into variants (separated by '|') and parse each.
    """
    if not code:
        return [{"analysis": "", "features": _default_features()}]
    variants = [part.strip() for part in code.split("|") if part.strip()]
    # Deduplicate while preserving order
    seen: set[str] = set()
    deduped: list[str] = []
    for v in variants:
        if v in seen:
            continue
        seen.add(v)
        deduped.append(v)
    variants = deduped or [code.strip()]
    if not variants:
        variants = [code.strip()]
    parsed: list[dict[str, object]] = []
    for variant in variants:
        parsed.append({"analysis": variant, "features": _parse_analysis_code(variant)})
    return parsed


def _parse_analysis_code(code: str) -> dict[str, object]:
    """
    Parse Heritage compact/text analysis codes into feature dicts.
    """
    features = _default_features()
    if not code or code == "?":
        return features
    # Multiple analyses separated by '|' → take first for now.
    if "|" in code:
        code = code.split("|", 1)[0].strip()
    code_lower = code.lower().rstrip(".")
    if _apply_abbr_marker(code_lower, features):
        return features
    compound_markers = {"iic": "initial", "ifc": "final"}
    if code_lower in {"ind", "inde"}:
        features["pos"] = "indeclinable"
        return features
    for marker, role in compound_markers.items():
        if code_lower.startswith(marker):
            features["compound_role"] = role
            pos_val = features.get("pos")
            if isinstance(pos_val, str) and pos_val.startswith("unknown"):
                features["pos"] = "compound_member"
            return features
    if "." in code and " " in code:
        return _parse_text_description(code, features)
    return _parse_compact_code(code, features)


def _parse_text_description(code: str, features: dict[str, object]) -> dict[str, object]:
    parts = code.lower().replace(".", "").replace(",", "").split()
    pos_indicators: list[str] = []
    for part in parts:
        if not part:
            continue
        if _apply_abbr_marker(part, features):
            pos_indicators.append("compound")
            continue
        _map_part_to_feature(part, features, pos_indicators)
    if features["pos"] == "unknown":
        features["pos"] = _infer_pos(pos_indicators)
    return features


def _apply_abbr_marker(part: str, features: dict[str, object]) -> bool:
    """
    Map abbreviation tokens (from abbr_data.json) into feature hints.
    """
    entry = _abbr_index().get(part.rstrip("."))
    if not entry:
        return False
    key = part.rstrip(".")
    if key == "iic":
        features["compound_role"] = "initial"
        features["pos"] = "compound_member"
        return True
    if key == "ifc":
        features["compound_role"] = "final"
        features["pos"] = "compound_member"
        return True
    if key in {"ind", "inde"}:
        features["pos"] = "indeclinable"
        return True
    return False


def _analysis_features(analysis: dict[str, object]) -> dict[str, object]:
    """
    Prefer first variant features; fall back to any legacy 'features' key.
    """
    variants = analysis.get("analysis_variants")
    if variants and isinstance(variants, list) and variants[0].get("features"):
        features_val = variants[0]["features"]
        return features_val if isinstance(features_val, dict) else _default_features()
    features_val = analysis.get("features")
    if isinstance(features_val, dict):
        return cast(dict[str, object], features_val)
    return _default_features()


def _find_matching_analysis(
    pattern: dict[str, object], parsed: list[dict[str, object]], sol_num: int, used: set[int]
) -> int | None:
    """Find index of parsed analysis matching the pattern."""
    word = pattern.get("word")
    analysis = pattern.get("analysis")

    for idx, pa in enumerate(parsed):
        if idx in used:
            continue
        if pa.get("solution_number") != sol_num:
            continue
        if word and pa.get("word") != word:
            continue
        if analysis and pa.get("analysis") != analysis:
            continue
        return idx
    return None


def _build_compound_member(
    pa: dict[str, object],
    color_class: str | None,
    color_norm: str | None,
    color_meaning: str | None,
) -> dict[str, object]:
    """Build a compound member dict from parsed analysis."""
    member = {
        "word": pa.get("word_slp1") or pa.get("word"),
        "analysis": pa.get("analysis"),
    }
    if pa.get("analysis_variants"):
        member["analysis_variants"] = pa.get("analysis_variants")
    else:
        member["features"] = _analysis_features(pa)
    if pa.get("dictionary_url"):
        member["dictionary_url"] = pa.get("dictionary_url")
    if color_class:
        member["color"] = color_class
    if color_norm:
        member["color_normalized"] = color_norm
    if color_meaning:
        member["color_meaning"] = color_meaning
    return member


def _group_compounds(
    parsed: list[dict[str, object]], solutions: list[dict[str, object]]
) -> list[dict[str, object]]:
    """
    Group parsed analyses by Heritage solution, preserving pattern order.
    """
    if not parsed or not solutions:
        return []

    grouped: list[dict[str, object]] = []
    for sol in solutions:
        sol_num = sol.get("solution_number")
        if sol_num is None:
            continue

        members: list[dict[str, object]] = []
        patterns_val = sol.get("patterns") or []
        patterns = patterns_val if isinstance(patterns_val, list) else []
        color_class_val = sol.get("color")
        color_class = color_class_val if isinstance(color_class_val, str) else None
        color_norm = _normalize_color_class(color_class)
        color_meaning = COLOR_MEANINGS.get(color_norm or "", None)
        used: set[int] = set()

        for pat in patterns:
            if not isinstance(pat, dict):
                continue
            pat_dict = cast(dict[str, object], pat)
            sol_num_int = sol_num if isinstance(sol_num, int) else 0
            match_idx = _find_matching_analysis(pat_dict, parsed, sol_num_int, used)
            if match_idx is None:
                continue
            used.add(match_idx)
            pa = parsed[match_idx]
            member = _build_compound_member(pa, color_class, color_norm, color_meaning)
            members.append(member)

        if members:
            grouped.append(
                {
                    "solution_number": sol_num,
                    "color": color_class,
                    "color_normalized": color_norm,
                    "color_meaning": color_meaning,
                    "raw_text": sol.get("raw_text"),
                    "members": members,
                }
            )
    return grouped


def _map_part_to_feature(part: str, features: dict[str, object], pos_indicators: list[str]) -> None:
    class_match = re.match(r"\[(\d+)\]$", part)
    if class_match:
        features["verb_class"] = int(class_match.group(1))
        pos_indicators.append("verb")
        return
    if part.endswith(("st", "nd", "rd", "th")) and len(part) > 2:  # noqa: PLR2004
        person = _get_ordinal_person(part)
        if person:
            features["person"] = person
            pos_indicators.append("verb")
            return
    mappings = [
        (GENDER_MAP, "gender", "noun"),
        (NUMBER_MAP, "number", None),
        (CASE_MAP, "case", "noun"),
        (PERSON_MAP, "person", "verb"),
        (TENSE_MAP, "tense", "verb"),
        (MOOD_MAP, "mood", "verb"),
        (VOICE_MAP, "voice", "verb"),
    ]
    for mapping, feature_name, pos_indicator in mappings:
        if part in mapping:
            features[feature_name] = mapping[part]
            if pos_indicator:
                pos_indicators.append(pos_indicator)
            return
    if part in POS_MAP:
        features["pos"] = POS_MAP[part]
    elif part.startswith("verb") or part == "v":
        features["pos"] = "verb"
    elif part.startswith("noun") or part == "n":
        features["pos"] = "noun"


def _infer_pos(pos_indicators: list[str]) -> str:
    if "verb" in pos_indicators and "noun" not in pos_indicators:
        return "verb"
    if "noun" in pos_indicators:
        return "noun"
    return "unknown"


def _get_ordinal_person(part: str) -> int | None:
    num_part = part[:-2]
    return PERSON_MAP.get(num_part)


def _parse_compact_code(code: str, features: dict[str, object]) -> dict[str, object]:
    pos_mapping = {
        "N": "noun",
        "V": "verb",
        "A": "adjective",
        "P": "pronoun",
        "C": "conjunction",
        "I": "interjection",
        "D": "adverb",
        "U": "numeral",
    }
    if code:
        pos_code = code[0]
        features["pos"] = pos_mapping.get(pos_code, f"unknown({pos_code})")
    if len(code) > CASE_CODE_INDEX and code[CASE_CODE_INDEX].isdigit():
        case_num = code[CASE_CODE_INDEX]
        case_mapping = {
            "1": "nominative",
            "2": "accusative",
            "3": "instrumental",
            "4": "dative",
            "5": "ablative",
            "6": "genitive",
            "7": "locative",
            "8": "vocative",
        }
        features["case"] = case_mapping.get(case_num, f"case_{case_num}")
    if len(code) > GENDER_CODE_INDEX and code[GENDER_CODE_INDEX] in "mfn":
        gender_mapping = {
            "m": "masculine",
            "f": "feminine",
            "n": "neuter",
        }
        features["gender"] = gender_mapping.get(code[GENDER_CODE_INDEX], code[GENDER_CODE_INDEX])
    if len(code) > NUMBER_CODE_INDEX and code[NUMBER_CODE_INDEX] in "sdp":
        number_mapping = {
            "s": "singular",
            "d": "dual",
            "p": "plural",
        }
        features["number"] = number_mapping.get(code[NUMBER_CODE_INDEX], code[NUMBER_CODE_INDEX])
    return features
