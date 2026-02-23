from __future__ import annotations

import time
from typing import Mapping, Any

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
            features = _parse_analysis_code(analysis.get("analysis", ""))
            word = analysis.get("word", "")
            word_slp1 = _velthuis_to_slp1(word)
            analyses.append(
                {
                    "word": word,
                    "word_slp1": word_slp1,
                    "analysis": analysis.get("analysis", ""),
                    "dictionary_url": analysis.get("dictionary_url"),
                    "solution_number": analysis.get("solution_number"),
                    "color": analysis.get("color"),
                    "segments": analysis.get("segments", []),
                    "features": features,
                }
            )
    enriched_payload = dict(payload)
    enriched_payload["parsed_analyses"] = analyses
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
        morph_obj: dict[str, Any] = {
            "lemma": lemma or word_slp1,
            "form": word_slp1,
            "analysis": analysis.get("analysis", ""),
            "features": analysis.get("features", {}),
        }
        if analysis.get("dictionary_url"):
            morph_obj["dictionary_url"] = analysis["dictionary_url"]
        if analysis.get("solution_number"):
            morph_obj["solution_number"] = analysis["solution_number"]
        if analysis.get("color"):
            morph_obj["color"] = analysis["color"]
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
VOICE_MAP = {"act": "active", "mid": "middle", "pass": "passive"}
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


def _parse_analysis_code(code: str) -> dict[str, Any]:
    """
    Parse Heritage compact/text analysis codes into feature dicts.
    """
    features: dict[str, Any] = {
        "pos": "unknown",
        "case": None,
        "gender": None,
        "number": None,
        "person": None,
        "tense": None,
        "voice": None,
        "mood": None,
        "compound_role": None,
    }
    if not code or code == "?":
        return features
    # Multiple analyses separated by '|' → take first for now.
    if "|" in code:
        code = code.split("|", 1)[0].strip()
    compound_markers = {
        "iic": "initial",
        "ifc": "final",
    }
    code_lower = code.lower().rstrip(".")
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
        _map_part_to_feature(part, features, pos_indicators)
    if features["pos"] == "unknown":
        features["pos"] = _infer_pos(pos_indicators)
    return features


def _map_part_to_feature(part: str, features: dict[str, Any], pos_indicators: list[str]) -> None:
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
