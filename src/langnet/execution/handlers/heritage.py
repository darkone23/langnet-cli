from __future__ import annotations

import time
from typing import Mapping, Any
import re
import json
from pathlib import Path
from functools import lru_cache

from bs4 import BeautifulSoup
from query_spec import ToolCallSpec

from langnet.execution.effects import (
    ClaimEffect,
    DerivationEffect,
    ExtractionEffect,
    ProvenanceLink,
    stable_effect_id,
)
from langnet.heritage.html_extractor import extract_solutions

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


def _get_param(params: Any, key: str) -> str:
    try:
        if hasattr(params, "get"):
            return params.get(key, "")
    except Exception:
        return ""
    return ""


def extract_html(call: ToolCallSpec, raw_response) -> ExtractionEffect:
    """
    Decode Heritage HTML and capture structured solutions/patterns for derivation.
    """
    start = time.perf_counter()
    html = raw_response.body.decode("utf-8", errors="ignore") if raw_response.body else ""
    soup = BeautifulSoup(html, "html.parser")
    # Grab first <i> or roma16o span as lemma hint; fall back to the query text (Velthuis) from params.
    lemma = ""
    first_i = soup.find("i")
    if first_i and isinstance(first_i.text, str):
        lemma = first_i.text.strip()
    if not lemma:
        roma_span = soup.find("span", class_="roma16o")
        if roma_span and isinstance(roma_span.text, str):
            lemma = roma_span.text.strip()
    if not lemma:
        lemma = _get_param(call.params, "text") or _get_param(call.params, "q")
    if not lemma:
        try:
            lemma = call.params.get("text", "")  # type: ignore[attr-defined]
        except Exception:
            lemma = ""
    slp1 = _velthuis_to_slp1(lemma)

    solutions = extract_solutions(html)
    analyses: list[dict[str, Any]] = []
    for solution in solutions:
        for pattern in solution.get("patterns", []):
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
    payload = {
        "raw_ref": raw_response.response_id,
        "raw_html": html,
        "request_url": raw_response.endpoint,
        "lemma": lemma,
        "lemma_slp1": slp1,
        "solutions": solutions,
        "analyses": analyses,
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


def derive_morph(call: ToolCallSpec, extraction: ExtractionEffect) -> DerivationEffect:
    """
    Build a richer derivation record from extracted Heritage HTML.
    """
    start = time.perf_counter()
    payload = extraction.payload or {}
    canonical = None
    analyses: list[dict[str, Any]] = []
    if isinstance(payload, Mapping):
        canonical = payload.get("lemma_slp1") or payload.get("lemma")
        for analysis in payload.get("analyses", []) or []:
            analysis_variants = _parse_analysis_variants(analysis.get("analysis", ""))
            word = analysis.get("word", "")
            word_slp1 = _velthuis_to_slp1(word)
            analyses.append(
                {
                    "word": word,
                    "word_slp1": word_slp1,
                    "analysis": analysis.get("analysis", ""),
                    "analysis_variants": analysis_variants,
                    "dictionary_url": analysis.get("dictionary_url"),
                    "solution_number": analysis.get("solution_number"),
                    "color": analysis.get("color"),
                    "segments": analysis.get("segments", []),
                }
            )
    enriched_payload = dict(payload)
    enriched_payload["parsed_analyses"] = analyses
    enriched_payload["compound_solutions"] = _group_compounds(analyses, payload.get("solutions", []))
    prov = [
        ProvenanceLink(
            stage="extract", tool=extraction.tool, reference_id=extraction.extraction_id
        )
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


def claim_morph(call: ToolCallSpec, derivation: DerivationEffect) -> ClaimEffect:
    """
    Emit `has_morphology` claims with parsed Heritage payload preserved.
    """
    prov = derivation.provenance_chain[:] if derivation.provenance_chain else []
    prov.append(
        ProvenanceLink(stage="derive", tool=derivation.tool, reference_id=derivation.derivation_id)
    )
    payload = derivation.payload or {}
    lemma = ""
    if isinstance(payload, Mapping):
        lemma = payload.get("lemma_slp1") or payload.get("lemma") or ""
    if not lemma and derivation.canonical:
        lemma = derivation.canonical
    if not lemma:
        text_param = _get_param(call.params, "text")
        lemma = _velthuis_to_slp1(text_param) or text_param
    if not lemma and isinstance(call.params, Mapping):
        text_param = call.params.get("text", "")
        lemma = _velthuis_to_slp1(text_param) or text_param
    lemma = (lemma or "").strip()
    if not lemma:
        subject = derivation.derivation_id
    else:
        subject = f"lex:{lemma}"

    triples: list[dict[str, Any]] = []
    analyses = []
    if isinstance(payload, Mapping):
        analyses = payload.get("parsed_analyses") or payload.get("analyses") or []
    for analysis in analyses or []:
        word_slp1 = _velthuis_to_slp1(analysis.get("word", ""))
        variants = analysis.get("analysis_variants") or [
            {"analysis": analysis.get("analysis", ""), "features": _analysis_features(analysis)}
        ]
        color_class = analysis.get("color")
        color_norm = _normalize_color_class(color_class)
        color_meaning = COLOR_MEANINGS.get(color_norm or "", None)
        for idx, variant in enumerate(variants):
            morph_obj: dict[str, Any] = {
                "lemma": lemma or word_slp1,
                "form": word_slp1,
                "analysis": variant.get("analysis", ""),
            }
            variant_features = variant.get("features")
            if len(variants) > 1:
                morph_obj["variant_index"] = idx + 1
            if analysis.get("dictionary_url"):
                morph_obj["dictionary_url"] = analysis["dictionary_url"]
            if analysis.get("solution_number"):
                morph_obj["solution_number"] = analysis["solution_number"]
            if color_class:
                morph_obj["color"] = color_class
            if color_norm:
                morph_obj["color_normalized"] = color_norm
            if color_meaning:
                morph_obj["color_meaning"] = color_meaning
            if variant_features:
                morph_obj["features"] = variant_features
            triples.append(
                {
                    "subject": f"form:{word_slp1}" if word_slp1 else subject,
                    "predicate": "has_morphology",
                    "object": morph_obj,
                }
            )
    value: dict[str, Any] = {"triples": triples}
    if isinstance(payload, Mapping) and payload.get("analyses"):
        value["analyses"] = payload.get("analyses")
    if isinstance(payload, Mapping) and payload.get("compound_solutions"):
        value["compounds"] = payload.get("compound_solutions")
    if isinstance(payload, Mapping) and payload.get("raw_ref"):
        value["raw_ref"] = payload.get("raw_ref")
    if isinstance(payload, Mapping) and payload.get("raw_html"):
        value["raw_html"] = payload.get("raw_html")
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


def _default_features() -> dict[str, Any]:
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


def _parse_analysis_variants(code: str) -> list[dict[str, Any]]:
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
    parsed: list[dict[str, Any]] = []
    for variant in variants:
        parsed.append({"analysis": variant, "features": _parse_analysis_code(variant)})
    return parsed


def _parse_analysis_code(code: str) -> dict[str, Any]:
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
            if features["pos"].startswith("unknown"):
                features["pos"] = "compound_member"
            return features
    if "." in code and " " in code:
        return _parse_text_description(code, features)
    return _parse_compact_code(code, features)


def _parse_text_description(code: str, features: dict[str, Any]) -> dict[str, Any]:
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


def _apply_abbr_marker(part: str, features: dict[str, Any]) -> bool:
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


def _analysis_features(analysis: dict[str, Any]) -> dict[str, Any]:
    """
    Prefer first variant features; fall back to any legacy 'features' key.
    """
    variants = analysis.get("analysis_variants")
    if variants and isinstance(variants, list) and variants[0].get("features"):
        return variants[0]["features"]
    return analysis.get("features", _default_features())


def _group_compounds(parsed: list[dict[str, Any]], solutions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Group parsed analyses by Heritage solution, preserving pattern order.
    """
    if not parsed or not solutions:
        return []
    grouped: list[dict[str, Any]] = []
    for sol in solutions:
        sol_num = sol.get("solution_number")
        if sol_num is None:
            continue
        members: list[dict[str, Any]] = []
        patterns = sol.get("patterns") or []
        color_class = sol.get("color")
        color_norm = _normalize_color_class(color_class)
        color_meaning = COLOR_MEANINGS.get(color_norm or "", None)
        used: set[int] = set()
        for pat in patterns:
            word = pat.get("word")
            analysis = pat.get("analysis")
            match_idx = None
            for idx, pa in enumerate(parsed):
                if idx in used:
                    continue
                if pa.get("solution_number") != sol_num:
                    continue
                if word and pa.get("word") != word:
                    continue
                if analysis and pa.get("analysis") != analysis:
                    continue
                match_idx = idx
                break
            if match_idx is None:
                continue
            used.add(match_idx)
            pa = parsed[match_idx]
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


def _map_part_to_feature(part: str, features: dict[str, Any], pos_indicators: list[str]) -> None:
    class_match = re.match(r"\[(\d+)\]$", part)
    if class_match:
        features["verb_class"] = int(class_match.group(1))
        pos_indicators.append("verb")
        return
    if part.endswith(("st", "nd", "rd", "th")) and len(part) > 2:
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


def _parse_compact_code(code: str, features: dict[str, Any]) -> dict[str, Any]:
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
