from __future__ import annotations

import hashlib
import importlib
import re
import time
import unicodedata
from collections.abc import Mapping, Sequence
from functools import lru_cache
from typing import cast
from xml.etree import ElementTree

import orjson
from query_spec import ToolCallSpec

from langnet.clients.base import RawResponseEffect, _new_response_id
from langnet.databuild.paths import default_cdsl_path
from langnet.execution import predicates
from langnet.execution.effects import (
    ClaimEffect,
    DerivationEffect,
    ExtractionEffect,
    ProvenanceLink,
    stable_effect_id,
)
from langnet.execution.versioning import versioned
from langnet.storage.db import connect_duckdb_ro

_IAST_TO_SLP1 = {
    "ā": "A",
    "ī": "I",
    "ū": "U",
    "ṛ": "f",
    "ṝ": "F",
    "ḷ": "x",
    "ḹ": "X",
    "ṅ": "N",
    "ñ": "Y",
    "ṇ": "R",
    "ś": "S",
    "ṣ": "z",
    "ṃ": "M",
    "ṁ": "M",
    "ḥ": "H",
}
_IAST_MARKS = frozenset(_IAST_TO_SLP1)
_SLP1_CHARS = set("aAiIuUfFxXeEoOEkKgGNcCjJYwWqQRtTdDnpPbBmyrlvSzshMH")
_ASCII_DIGRAPH_TO_SLP1 = {
    "kh": "K",
    "gh": "G",
    "ch": "C",
    "jh": "J",
    "th": "T",
    "dh": "D",
    "ph": "P",
    "bh": "B",
    "sh": "S",
}
_VELTHUIS_MARKERS = frozenset({".", '"', "~"})
_CDSL_SLP1_DISPLAY_MARKS = str.maketrans("", "", "/\\^")
_CDSL_TOKEN_RE = re.compile(
    r"(?P<prefix>[^A-Za-z°]*)(?P<body>[A-Za-z°/\\^]+)(?P<suffix>[^A-Za-z°]*)"
)
_CDSL_SLP1_MARKERS = set("AIUFXEOKGNCJYRWQTDPSMH")
_MIN_MARKED_CDSL_TOKEN_LEN = 2
_CDSL_SOURCE_ABBREVIATIONS = {
    "AV",
    "Bhag",
    "ChUp",
    "L",
    "MBh",
    "Mn",
    "PadmaP",
    "RV",
    "Suśr",
    "Vop",
    "Yājñ",
    "NārP",
}
_HERITAGE_S_DOT_PLACEHOLDER = "\u0000"


def _heritage_velthuis_to_slp1_basic(text: str) -> str:
    """
    Convert the Heritage Platform's Velthuis flavor to CDSL SLP1.

    Heritage uses bare `z` for palatal `ś`, while CDSL SLP1 uses `S`.
    Retroflex `ṣ` arrives as `.s`, so protect it before the bare-z pass.
    """
    replacements = [
        (".rr", "F"),
        (".r", "f"),
        (".ll", "X"),
        (".l", "x"),
        ("~n", "Y"),
        (".th", "W"),
        (".t", "w"),
        (".dh", "Q"),
        (".d", "q"),
        (".n", "R"),
        (".m", "M"),
        (".h", "H"),
        ("aa", "A"),
        ("ii", "I"),
        ("uu", "U"),
    ]
    out = text.replace(".s", _HERITAGE_S_DOT_PLACEHOLDER)
    for old, new in replacements:
        out = out.replace(old, new)
    for old, new in _ASCII_DIGRAPH_TO_SLP1.items():
        out = out.replace(old, new)
    out = out.replace("z", "S")
    return out.replace(_HERITAGE_S_DOT_PLACEHOLDER, "z")


def _looks_like_slp1(text: str) -> bool:
    if any(marker in text for marker in _VELTHUIS_MARKERS):
        return False
    lowered = text.lower()
    if any(pair in lowered for pair in _ASCII_DIGRAPH_TO_SLP1):
        return False
    return bool(text) and all(c.lower() in _SLP1_CHARS for c in text if c.isalpha())


@lru_cache(maxsize=1)
def _load_sanscript_module():
    try:
        return importlib.import_module("indic_transliteration.sanscript")
    except Exception:  # noqa: BLE001
        return None


def _sanscript_transliterate(text: str, source: str, target: str) -> str | None:
    module = _load_sanscript_module()
    if module is None:
        return None
    try:
        source_scheme = getattr(module, source)
        target_scheme = getattr(module, target)
        result = module.transliterate(text, source_scheme, target_scheme)
    except Exception:  # noqa: BLE001
        return None
    return result if isinstance(result, str) else None


def _ascii_iast_to_slp1_basic(text: str) -> str:
    out = []
    i = 0
    while i < len(text):
        pair = text[i : i + 2]
        digraph = _ASCII_DIGRAPH_TO_SLP1.get(pair.lower())
        if digraph:
            out.append(digraph)
            i += 2
            continue
        ch = text[i]
        out.append(_IAST_TO_SLP1.get(ch, ch))
        i += 1
    return "".join(out)


def _clean_cdsl_slp1_for_display(text: str) -> str:
    """Drop CDSL accent markers before learner-facing transliteration."""
    return text.translate(_CDSL_SLP1_DISPLAY_MARKS).removeprefix("°")


def _token_looks_like_cdsl_slp1(token: str) -> bool:
    clean = _clean_cdsl_slp1_for_display(token)
    if not clean or clean in _CDSL_SOURCE_ABBREVIATIONS:
        return False
    if any(mark in token for mark in "/\\^"):
        return len(clean) > _MIN_MARKED_CDSL_TOKEN_LEN
    has_lower = any(ch.islower() for ch in clean)
    return has_lower and any(ch in _CDSL_SLP1_MARKERS for ch in clean[1:])


def _display_token_to_iast(token: str, source_slp1: str = "", display_iast: str = "") -> str:
    match = _CDSL_TOKEN_RE.fullmatch(token)
    if match is None:
        return token

    body = match.group("body")
    clean_body = _clean_cdsl_slp1_for_display(body)
    clean_source = _clean_cdsl_slp1_for_display(source_slp1)
    if display_iast and clean_source and clean_body == clean_source:
        converted = display_iast
    elif _token_looks_like_cdsl_slp1(body):
        converted = _slp1_to_iast(body)
    else:
        return token
    return f"{match.group('prefix')}{converted}{match.group('suffix')}"


def cdsl_text_to_iast_display(
    text: str,
    *,
    source_slp1: str = "",
    display_iast: str = "",
) -> str:
    """
    Best-effort display-only transliteration transform for CDSL gloss text.

    Raw CDSL text remains preserved in claim evidence. This helper is intentionally
    source-complete and is used only for terminal display.
    """
    return " ".join(
        _display_token_to_iast(token, source_slp1, display_iast) for token in text.split()
    )


def cdsl_display_gloss(
    text: str,
    *,
    source_slp1: str = "",
    display_iast: str = "",
) -> str:
    """
    Conservative learner-display gloss transform for CDSL entries.

    This currently preserves all source content. It only applies display-safe
    Sanskrit transliteration while leaving the raw CDSL text as the
    evidence-bearing triple object.
    """
    # High-fidelity invariant: do not drop citation/source segments here.
    # Future parsing can add explicit source-note fields, but display text stays source-complete.
    return cdsl_text_to_iast_display(
        text,
        source_slp1=source_slp1,
        display_iast=display_iast,
    )


def _source_abbreviation_tokens(text: str) -> list[str]:
    return [token.strip(".") for token in re.findall(r"[A-Za-zĀ-ž]+\.?", text)]


def _segment_structure(raw_text: str) -> dict[str, object]:
    """
    Conservatively label CDSL source segments without changing or dropping text.
    """
    tokens = [token for token in _source_abbreviation_tokens(raw_text) if token]
    lowered = [token.lower() for token in tokens]
    if lowered and lowered[0] in {"cf", "see"}:
        abbreviations = [token for token in tokens[1:] if token in _CDSL_SOURCE_ABBREVIATIONS]
        if abbreviations and len(abbreviations) == len(tokens) - 1:
            return {
                "segment_type": "cross_reference",
                "labels": ["cross_reference", "source_reference"],
                "recognized_abbreviations": abbreviations,
            }
    if tokens and all(token in _CDSL_SOURCE_ABBREVIATIONS for token in tokens):
        return {
            "segment_type": "source_reference",
            "labels": ["source_reference"],
            "recognized_abbreviations": tokens,
        }
    return {"segment_type": "unclassified", "labels": []}


def _source_segments(
    text: str,
    *,
    source_slp1: str = "",
    display_iast: str = "",
) -> list[dict[str, object]]:
    """
    Split CDSL source text into ordered, source-complete display segments.

    Segment typing is conservative: unrecognized text stays unclassified.
    """
    segments: list[dict[str, object]] = []
    for index, raw_segment in enumerate(text.split(";")):
        raw_text = raw_segment.strip()
        if not raw_text:
            continue
        segment = {
            "index": index,
            "raw_text": raw_text,
            "display_text": cdsl_text_to_iast_display(
                raw_text,
                source_slp1=source_slp1,
                display_iast=display_iast,
            ),
        }
        segment.update(_segment_structure(raw_text))
        segments.append(segment)
    return segments


def _source_notes_from_segments(segments: Sequence[Mapping[str, object]]) -> dict[str, object]:
    """
    Summarize typed CDSL source-note segments without reclassifying unknown text.
    """
    cross_reference_segments: list[str] = []
    source_reference_segments: list[str] = []
    recognized_abbreviations: list[str] = []
    seen_abbreviations: set[str] = set()

    for segment in segments:
        raw_text = segment.get("raw_text")
        segment_type = segment.get("segment_type")
        if isinstance(raw_text, str) and segment_type == "cross_reference":
            cross_reference_segments.append(raw_text)
        elif isinstance(raw_text, str) and segment_type == "source_reference":
            source_reference_segments.append(raw_text)

        abbreviations_val = segment.get("recognized_abbreviations")
        abbreviations = (
            abbreviations_val
            if isinstance(abbreviations_val, Sequence)
            and not isinstance(abbreviations_val, (str, bytes))
            else []
        )
        for abbreviation in abbreviations:
            if isinstance(abbreviation, str) and abbreviation not in seen_abbreviations:
                seen_abbreviations.add(abbreviation)
                recognized_abbreviations.append(abbreviation)

    notes: dict[str, object] = {}
    if cross_reference_segments:
        notes["cross_reference_segments"] = cross_reference_segments
    if source_reference_segments:
        notes["source_reference_segments"] = source_reference_segments
    if recognized_abbreviations:
        notes["recognized_abbreviations"] = recognized_abbreviations
    return notes


def _to_slp1(text: str) -> str:
    """
    Convert learner/planner Sanskrit input to SLP1 for CDSL lookup.
    """
    if _looks_like_slp1(text):
        return text
    if any(ch in _IAST_MARKS for ch in text):
        converted = _sanscript_transliterate(text, "IAST", "SLP1")
        if converted and converted != text:
            return converted
    heritage_converted = _heritage_velthuis_to_slp1_basic(text)
    if heritage_converted != text:
        text = heritage_converted
        if _looks_like_slp1(text):
            return text
    if any(marker in text for marker in _VELTHUIS_MARKERS):
        converted = _sanscript_transliterate(text, "VELTHUIS", "SLP1")
        if converted and converted != text:
            return converted
    converted = _sanscript_transliterate(text, "IAST", "SLP1")
    if converted and converted != text:
        return converted

    return _ascii_iast_to_slp1_basic(text)


_SLP1_TO_IAST = {
    "A": "ā",
    "I": "ī",
    "U": "ū",
    "f": "ṛ",
    "F": "ṝ",
    "x": "ḷ",
    "X": "ḹ",
    "e": "e",
    "E": "ai",
    "o": "o",
    "O": "au",
    "G": "gh",
    "N": "ṅ",
    "Y": "ñ",
    "R": "ṇ",
    "w": "ṭ",
    "W": "ṭh",
    "q": "ḍ",
    "Q": "ḍh",
    "K": "kh",
    "C": "ch",
    "J": "jh",
    "T": "th",
    "D": "dh",
    "P": "ph",
    "B": "bh",
    "S": "ś",
    "z": "ṣ",
    "M": "ṃ",
    "H": "ḥ",
}


def _slp1_to_iast(text: str) -> str:
    """
    Convert CDSL SLP1 lemmas to learner-facing IAST display.
    """
    display_text = _clean_cdsl_slp1_for_display(text)
    converted = _sanscript_transliterate(display_text, "SLP1", "IAST")
    if converted:
        return converted

    out: list[str] = []
    for ch in display_text:
        mapped = _SLP1_TO_IAST.get(ch)
        if mapped:
            out.append(mapped)
        else:
            out.append(ch)
    return "".join(out)


def _strip_accents(text: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFD", text) if unicodedata.category(c) != "Mn"
    ).lower()


def _slp1_to_ascii(text: str) -> str:
    """
    Convert a likely SLP1 token into an accentless ASCII form for DB lookup.
    """
    return _strip_accents(_slp1_to_iast(text))


def _candidate_keys(lemma: str) -> list[str]:
    raw = (lemma or "").strip()
    if not raw:
        return []
    base = raw.split("_", 1)[0]
    seeds = {raw, base}
    variants: set[str] = set()
    for seed in seeds:
        variants.add(seed)
        variants.add(seed.lower())
        variants.add(_strip_accents(seed))
        clean = "".join(ch for ch in seed if ch.isalpha())
        if clean and clean != seed:
            variants.add(clean)
            variants.add(clean.lower())
            variants.add(_strip_accents(clean))
        slp1 = _to_slp1(seed)
        if slp1:
            variants.add(slp1)
            variants.add(slp1.lower())
            if not slp1.endswith("H"):
                visarga = f"{slp1}H"
                variants.add(visarga)
                variants.add(visarga.lower())
        slp1_ascii = _slp1_to_ascii(seed)
        if slp1_ascii:
            variants.add(slp1_ascii)
    return [v for v in variants if v]


def _preferred_slp1_keys(lemma: str) -> list[str]:
    raw = (lemma or "").strip()
    if not raw:
        return []

    preferred: list[str] = []
    for seed in [raw, raw.split("_", 1)[0]]:
        slp1 = _to_slp1(seed)
        if slp1 and slp1 not in preferred:
            preferred.append(slp1)
        visarga = f"{slp1}H" if slp1 and not slp1.endswith("H") else ""
        if visarga and visarga not in preferred:
            preferred.append(visarga)
    return preferred


def _match_rank(entry: Mapping[str, object], lemma: str) -> int:
    """
    Rank CDSL candidates so IAST-like input prefers its SLP1 key.

    Example: user-facing `dharma` should prefer CDSL `Darma`, not the unrelated
    lowercase `darma` entry that shares the same normalized key.
    """
    key_values = [
        str(entry.get(name) or "")
        for name in ("key", "key2")
        if isinstance(entry.get(name), str) and entry.get(name)
    ]
    normalized_values = [
        str(entry.get(name) or "")
        for name in ("key_normalized", "key2_normalized")
        if isinstance(entry.get(name), str) and entry.get(name)
    ]
    preferred = _preferred_slp1_keys(lemma)
    candidates = _candidate_keys(lemma)

    for idx, candidate in enumerate(preferred):
        if candidate in key_values:
            return idx
    for idx, candidate in enumerate(candidates):
        if candidate in key_values:
            return 100 + idx
    for idx, candidate in enumerate(preferred):
        if candidate.lower() in normalized_values:
            return 200 + idx
    for idx, candidate in enumerate(candidates):
        if candidate.lower() in normalized_values:
            return 300 + idx
    return 1000


def _filter_best_cdsl_matches(
    entries: list[dict[str, object]], lemma: str
) -> list[dict[str, object]]:
    if len(entries) <= 1:
        return entries
    ranked = [(_match_rank(entry, lemma), entry) for entry in entries]
    best_rank = min(rank for rank, _entry in ranked)
    return [entry for rank, entry in ranked if rank == best_rank]


# --- Body parsing helpers (trimmed from codesketch cologne/parser) ---

_GENDER_MAP = {
    "m": "masculine",
    "f": "feminine",
    "n": "neuter",
    "mfn": ["masculine", "feminine", "neuter"],
}
_NUMBER_MAP = {"sg": "sg", "singular": "sg", "pl": "pl", "plural": "pl", "du": "du", "dual": "du"}
_CASE_MAP = {
    "nom": "1",
    "nominative": "1",
    "acc": "5",
    "accusative": "5",
    "gen": "2",
    "genitive": "2",
    "dat": "4",
    "dative": "4",
    "loc": "7",
    "locative": "7",
    "abl": "6",
    "ablative": "6",
    "voc": "8",
    "vocative": "8",
    "inst": "3",
    "instrumental": "3",
}


def _parse_lex_element(lex_elem, grammar: dict[str, object]) -> None:
    """Parse lex element for gender and POS hints."""
    lex_text = "".join([lex_elem.text or ""] + [child.tail or "" for child in lex_elem])
    lex_text = lex_text.strip().strip(".").lower()
    if lex_text in _GENDER_MAP:
        gender_val = _GENDER_MAP[lex_text]
        grammar["gender"] = gender_val if isinstance(gender_val, list) else [gender_val]
    pos_match = lex_text.split(".")[0]
    if pos_match:
        grammar["pos_hint"] = pos_match


def _parse_info_element(info_elem, grammar: dict[str, object]) -> None:
    """Parse info element for gender and number markers."""
    lex_attr = info_elem.get("lex", "")
    if lex_attr:
        gender_val = _GENDER_MAP.get(lex_attr)
        if gender_val:
            grammar["gender"] = gender_val if isinstance(gender_val, list) else [gender_val]
    n_val = info_elem.get("n")
    if n_val:
        if "grammar_tags" not in grammar:
            grammar["grammar_tags"] = {}
        tags_val = grammar["grammar_tags"]
        if isinstance(tags_val, dict):
            tags = cast(dict[str, object], tags_val)
            tags["number_marker"] = n_val


def _parse_body_text_features(body_text: str, grammar: dict[str, object]) -> None:
    """Parse case and number from body text."""
    lower = body_text.lower()
    for pattern, case_num in _CASE_MAP.items():
        if pattern in lower:
            grammar.setdefault("case", case_num)
            break
    for pattern, num_code in _NUMBER_MAP.items():
        if pattern in lower:
            grammar.setdefault("number", num_code)
            break


def _parse_body_metadata(body_xml: str) -> dict[str, object]:
    """Parse CDSL body XML to extract grammatical metadata."""
    if not body_xml:
        return {}
    try:
        root = ElementTree.fromstring(body_xml)
    except ElementTree.ParseError:
        return {}

    grammar: dict[str, object] = {}

    lex_elem = root.find("lex")
    if lex_elem is not None:
        _parse_lex_element(lex_elem, grammar)

    info_elem = root.find("info")
    if info_elem is not None:
        _parse_info_element(info_elem, grammar)

    body_text = ElementTree.tostring(root, encoding="unicode", method="text").strip()
    _parse_body_text_features(body_text, grammar)

    s_elem = root.find("s")
    if s_elem is not None and s_elem.text:
        sanskrit_form = s_elem.text.strip()
        grammar["sanskrit_form"] = sanskrit_form
        grammar["sanskrit_form_slp1"] = sanskrit_form
        grammar["sanskrit_form_iast"] = _slp1_to_iast(sanskrit_form)

    return grammar


@versioned("v1")
def extract_xml(call: ToolCallSpec, raw_response) -> ExtractionEffect:
    """
    Load CDSL rows returned by the DuckDB fetch client.
    """
    start = time.perf_counter()
    entries = []
    try:
        entries = orjson.loads(raw_response.body)
    except Exception:
        entries = []
    duration_ms = int((time.perf_counter() - start) * 1000)
    return ExtractionEffect(
        extraction_id=stable_effect_id("ext", call.call_id, raw_response.response_id),
        tool=call.tool,
        call_id=call.call_id,
        source_call_id=call.params.get("source_call_id", ""),
        response_id=raw_response.response_id,
        kind="cdsl_rows",
        canonical=None,
        payload={"entries": entries},
        load_duration_ms=duration_ms,
    )


@versioned("v1")
def derive_sense(call: ToolCallSpec, extraction: ExtractionEffect) -> DerivationEffect:
    """
    Convert CDSL rows into simple sense payloads.
    """
    start = time.perf_counter()
    entries: Sequence[object] = []
    payload = extraction.payload or {}
    if isinstance(payload, Mapping):
        payload_dict = cast(dict[str, object], payload)
        entries_val = payload_dict.get("entries")
        if isinstance(entries_val, Sequence):
            entries = entries_val
    senses: list[dict[str, object]] = []
    grouped: dict[str, dict[str, object]] = {}
    for entry_raw in entries or []:
        if not isinstance(entry_raw, Mapping):
            continue
        entry = cast(dict[str, object], entry_raw)

        key_val = entry.get("key")
        key2_val = entry.get("key2")
        lemma_slp1 = key_val or key2_val or ""
        lemma_slp1 = lemma_slp1.strip() if isinstance(lemma_slp1, str) else ""
        key2_slp1 = key2_val.strip() if isinstance(key2_val, str) else ""

        lemma_iast = _slp1_to_iast(lemma_slp1)

        plain_text = entry.get("plain_text")
        body_val = entry.get("body")
        data_val = entry.get("data")
        gloss = plain_text or body_val or data_val or ""
        if not isinstance(gloss, str):
            gloss = ""

        dict_id = entry.get("dict_id")
        lnum_val = entry.get("lnum")
        source_ref = ""
        if lnum_val:
            dict_id_str = dict_id.lower() if isinstance(dict_id, str) else ""
            source_ref = f"{dict_id_str}:{lnum_val}"

        grammar_input = body_val if isinstance(body_val, str) else ""
        grammar = _parse_body_metadata(grammar_input)
        source_entry = _trim_evidence(
            {
                "dict": dict_id,
                "line_number": lnum_val,
                "source_ref": source_ref,
                "key_slp1": lemma_slp1,
                "key_iast": lemma_iast,
                "key2_slp1": key2_slp1,
                "key2_iast": _slp1_to_iast(key2_slp1) if key2_slp1 else "",
            }
        )
        segments = _source_segments(
            gloss,
            source_slp1=lemma_slp1,
            display_iast=lemma_iast,
        )

        sense_obj: dict[str, object] = {
            "anchor": lemma_slp1,
            "display_slp1": lemma_slp1,
            "display_iast": lemma_iast,
            "gloss": gloss,
            "dict": dict_id,
            "lnum": lnum_val,
            "source_ref": source_ref,
            "source_entry": source_entry,
            "source_segments": segments,
        }
        if grammar:
            sense_obj["grammar"] = grammar
        senses.append(sense_obj)
        group_key = lemma_iast or lemma_slp1
        if group_key not in grouped:
            senses_list: list[dict[str, object]] = []
            grouped[group_key] = {
                "lemma": lemma_iast,
                "lemma_slp1": lemma_slp1,
                "senses": senses_list,
            }
        senses_val = grouped[group_key].get("senses")
        if isinstance(senses_val, list):
            typed_senses = cast(list[dict[str, object]], senses_val)
            typed_senses.append(sense_obj)
    duration_ms = int((time.perf_counter() - start) * 1000)
    prov = [
        ProvenanceLink(
            stage="extract",
            tool=extraction.tool,
            reference_id=extraction.extraction_id,
            metadata={"response_id": extraction.response_id},
        )
    ]
    return DerivationEffect(
        derivation_id=stable_effect_id("drv", call.call_id, extraction.extraction_id),
        tool=call.tool,
        call_id=call.call_id,
        source_call_id=call.params.get("source_call_id", ""),
        extraction_id=extraction.extraction_id,
        kind="cdsl_sense",
        canonical=None,
        payload={"lemmas": list(grouped.values())},
        derive_duration_ms=duration_ms,
        provenance_chain=prov,
    )


def _trim_evidence(evidence: Mapping[str, object]) -> dict[str, object]:
    return {k: v for k, v in evidence.items() if v is not None and v != ""}


def _extract_response_id(provenance: list[ProvenanceLink] | None) -> str | None:
    if not provenance:
        return None
    for link in provenance:
        if link.stage == "extract" and link.metadata:
            response_id = link.metadata.get("response_id")
            if isinstance(response_id, str):
                return response_id
    return None


def _make_base_evidence(
    call: ToolCallSpec,
    derivation: DerivationEffect,
    claim_id: str,
    source_ref: str | None = None,
) -> dict[str, object]:
    return _trim_evidence(
        {
            "source_tool": "cdsl",
            "call_id": call.call_id,
            "response_id": _extract_response_id(derivation.provenance_chain),
            "extraction_id": derivation.extraction_id,
            "derivation_id": derivation.derivation_id,
            "claim_id": claim_id,
            "source_ref": source_ref,
            "raw_blob_ref": "raw_json",
        }
    )


def _sense_anchor(lex_anchor: str, gloss: str, source_ref: str | None) -> str:
    material = f"{source_ref or ''}:{gloss.strip()}"
    digest = hashlib.sha256(material.encode("utf-8")).hexdigest()[:8]
    return f"sense:{lex_anchor}#{digest}"


def _make_triple(
    subject: str,
    predicate: str,
    obj: object,
    evidence: Mapping[str, object],
    metadata: Mapping[str, object] | None = None,
) -> dict[str, object]:
    meta: dict[str, object] = {"evidence": _trim_evidence(dict(evidence))}
    if metadata:
        meta.update(dict(metadata))
    return {
        "subject": subject,
        "predicate": predicate,
        "object": obj,
        "metadata": meta,
    }


@versioned("v1")
def claim_sense(call: ToolCallSpec, derivation: DerivationEffect) -> ClaimEffect:
    """
    Emit `has_sense` triples for CDSL glosses.
    """
    prov = derivation.provenance_chain[:] if derivation.provenance_chain else []
    prov.append(
        ProvenanceLink(stage="derive", tool=derivation.tool, reference_id=derivation.derivation_id)
    )
    payload = derivation.payload or {}
    payload_dict = cast(dict[str, object], payload) if isinstance(payload, Mapping) else {}
    sense_groups = payload_dict.get("lemmas") if payload_dict else None
    claim_id = stable_effect_id("clm", call.call_id, derivation.derivation_id)
    triples: list[dict[str, object]] = []
    if isinstance(sense_groups, list):
        for group_raw in sense_groups:
            if not isinstance(group_raw, Mapping):
                continue
            group = cast(dict[str, object], group_raw)

            lemma_slp1 = group.get("lemma_slp1")
            lemma_anchor = lemma_slp1.strip().lower() if isinstance(lemma_slp1, str) else ""
            subject = f"lex:{lemma_anchor}" if lemma_anchor else derivation.derivation_id

            senses_val = group.get("senses")
            senses_list = senses_val if isinstance(senses_val, Sequence) else []
            for sense_raw in senses_list:
                if not isinstance(sense_raw, Mapping):
                    continue
                sense = cast(dict[str, object], sense_raw)

                gloss_val = sense.get("gloss")
                gloss = gloss_val if isinstance(gloss_val, str) else ""

                source_ref = sense.get("source_ref")
                source_ref_str = source_ref if isinstance(source_ref, str) else None
                source_entry_val = sense.get("source_entry")
                source_entry = (
                    cast(Mapping[str, object], source_entry_val)
                    if isinstance(source_entry_val, Mapping)
                    else {}
                )
                source_segments_val = sense.get("source_segments")
                source_segments = (
                    source_segments_val
                    if isinstance(source_segments_val, Sequence)
                    and not isinstance(source_segments_val, (str, bytes))
                    else []
                )
                source_notes = _source_notes_from_segments(
                    [
                        cast(Mapping[str, object], segment)
                        for segment in source_segments
                        if isinstance(segment, Mapping)
                    ]
                )

                grammar = sense.get("grammar")
                display_iast_val = sense.get("display_iast")
                display_iast = display_iast_val if isinstance(display_iast_val, str) else ""
                display_slp1_val = sense.get("display_slp1")
                display_slp1 = display_slp1_val if isinstance(display_slp1_val, str) else ""
                display_gloss = cdsl_display_gloss(
                    gloss,
                    source_slp1=display_slp1,
                    display_iast=display_iast,
                )
                evidence = _make_base_evidence(call, derivation, claim_id, source_ref_str)
                sense_anchor = _sense_anchor(subject, gloss, source_ref_str)
                display_metadata = _trim_evidence(
                    {
                        "display_iast": display_iast,
                        "display_slp1": display_slp1,
                        "source_encoding": "slp1",
                    }
                )
                triples.append(
                    _make_triple(
                        subject, predicates.HAS_SENSE, sense_anchor, evidence, display_metadata
                    )
                )
                triples.append(
                    _make_triple(
                        sense_anchor,
                        predicates.GLOSS,
                        gloss,
                        evidence,
                        _trim_evidence(
                            {
                                "source_ref": source_ref_str,
                                "display_gloss": display_gloss,
                                "source_entry": dict(source_entry),
                                "source_segments": list(source_segments),
                                "source_notes": dict(source_notes) if source_notes else None,
                                "display_iast": display_iast,
                                "display_slp1": display_slp1,
                                "source_encoding": "slp1",
                            }
                        ),
                    )
                )
                if grammar:
                    triples.append(
                        _make_triple(
                            sense_anchor, predicates.HAS_FEATURE, {"grammar": grammar}, evidence
                        )
                    )
    value = {"lemmas": sense_groups, "triples": triples}
    return ClaimEffect(
        claim_id=claim_id,
        tool=call.tool,
        call_id=call.call_id,
        source_call_id=call.params.get("source_call_id", ""),
        derivation_id=derivation.derivation_id,
        subject=derivation.derivation_id,
        predicate=predicates.HAS_SENSE,
        value=value,
        provenance_chain=prov,
    )


class CdslFetchClient:
    """
    DuckDB-backed fetcher for CDSL dictionaries.
    """

    def __init__(self) -> None:
        self.tool = "fetch.cdsl"

    def execute(self, call_id: str, endpoint: str, params: Mapping[str, str] | None = None):
        params = params or {}
        dict_id = (params.get("dict") or "mw").lower()
        lemma = (params.get("lemma") or params.get("q") or "").strip()
        path = default_cdsl_path(dict_id)
        if not path.exists():
            body = orjson.dumps({"error": f"cdsl db missing: {path}"})
            return _empty_response(call_id, self.tool, endpoint, 404, body)
        try:
            start = time.perf_counter()
            keys = _candidate_keys(lemma)
            rows: list[tuple] = []
            cols: list[str] = []
            with connect_duckdb_ro(path) as conn:
                if keys:
                    placeholders = ",".join(["?"] * len(keys))
                    rows = conn.execute(
                        f"""
                        SELECT dict_id, key, key2, key_normalized, key2_normalized, lnum,
                               body, plain_text, data
                        FROM entries
                        WHERE key_normalized IN ({placeholders})
                           OR key2_normalized IN ({placeholders})
                        """,
                        keys + keys,
                    ).fetchall()
                    cols = [c[0] for c in conn.description]
                if not rows:
                    rows = conn.execute(
                        """
                        SELECT dict_id, key, key2, key_normalized, key2_normalized, lnum,
                               body, plain_text, data
                        FROM entries
                        WHERE key_normalized = ? OR key2_normalized = ?
                        """,
                        [lemma.lower(), lemma.lower()],
                    ).fetchall()
                    cols = [c[0] for c in conn.description]
            duration_ms = int((time.perf_counter() - start) * 1000)
            entries = [dict(zip(cols, row)) for row in rows]
            entries = _filter_best_cdsl_matches(entries, lemma)
            body = orjson.dumps(entries)
            return _empty_response(call_id, self.tool, endpoint, 200, body, duration_ms=duration_ms)
        except Exception as exc:  # noqa: BLE001
            body = orjson.dumps({"error": str(exc)})
            return _empty_response(call_id, self.tool, endpoint, 500, body)


def _empty_response(  # noqa: PLR0913
    call_id: str, tool: str, endpoint: str, status: int, body: bytes, duration_ms: int = 0
):
    return RawResponseEffect(
        response_id=_new_response_id(),
        tool=tool,
        call_id=call_id,
        endpoint=endpoint,
        status_code=status,
        content_type="application/json",
        headers={},
        body=body,
        fetch_duration_ms=duration_ms,
    )
