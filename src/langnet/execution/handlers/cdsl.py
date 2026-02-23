from __future__ import annotations

import time
import unicodedata
from typing import Any, Mapping
from xml.etree import ElementTree

import orjson
from query_spec import ToolCallSpec

from langnet.databuild.paths import default_cdsl_path
from langnet.execution.effects import (
    ClaimEffect,
    DerivationEffect,
    ExtractionEffect,
    ProvenanceLink,
    stable_effect_id,
)
from langnet.storage.db import connect_duckdb_ro


_IAST_TO_SLP1 = {
    "ā": "A",
    "ī": "I",
    "ū": "U",
    "ṛ": "f",
    "ṝ": "F",
    "ḷ": "x",
    "ḹ": "X",
    "ṅ": "G",
    "ñ": "Y",
    "ṇ": "R",
    "ś": "S",
    "ṣ": "z",
    "ṃ": "M",
    "ṁ": "M",
    "ḥ": "H",
}
_SLP1_CHARS = set("aAiIuUfFxXeEoOkgGcCjJwWqQRtTdDpbBmnyYrlvSzshN")
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


def _looks_like_slp1(text: str) -> bool:
    lowered = text.lower()
    if any(pair in lowered for pair in _ASCII_DIGRAPH_TO_SLP1):
        return False
    return bool(text) and all(c.lower() in _SLP1_CHARS for c in text if c.isalpha())


def _to_slp1(text: str) -> str:
    """
    Minimal IAST/ASCII → SLP1 converter (coverage sufficient for lookup).
    """
    if _looks_like_slp1(text):
        return text

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
    "Y": "ñ",
    "R": "ṇ",
    "w": "ṭ",
    "W": "ṭh",
    "q": "ḍ",
    "Q": "ḍh",
    "K": "kh",
    "G'": "gh",
    "C": "ch",
    "J": "jh",
    "T": "th",
    "D": "dh",
    "P": "ph",
    "B": "bh",
    "S": "ś",
    "z": "ṣ",
}


def _slp1_to_iast(text: str) -> str:
    """
    Minimal SLP1 → IAST converter (coverage sufficient for lemma display).
    """
    out: list[str] = []
    for ch in text:
        mapped = _SLP1_TO_IAST.get(ch)
        if mapped:
            out.append(mapped)
        else:
            out.append(ch)
    return "".join(out)


def _strip_accents(text: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", text) if unicodedata.category(c) != "Mn").lower()


def _slp1_to_ascii(text: str) -> str:
    """
    Convert a likely SLP1 token into an accentless ASCII form for DB lookup.
    """
    rev: dict[str, str] = {}
    for iast, slp1 in _IAST_TO_SLP1.items():
        rev[slp1] = iast
    out: list[str] = []
    i = 0
    while i < len(text):
        # Handle digraphs like RR/LL first.
        two = text[i : i + 2]
        if two in rev:
            out.append(rev[two])
            i += 2
            continue
        ch = text[i]
        out.append(rev.get(ch, ch))
        i += 1
    return _strip_accents("".join(out))


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
        slp1_ascii = _slp1_to_ascii(seed)
        if slp1_ascii:
            variants.add(slp1_ascii)
    return [v for v in variants if v]


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


def _parse_body_metadata(body_xml: str) -> dict[str, Any]:
    if not body_xml:
        return {}
    try:
        root = ElementTree.fromstring(body_xml)
    except ElementTree.ParseError:
        return {}
    grammar: dict[str, Any] = {}
    lex_elem = root.find("lex")
    if lex_elem is not None:
        lex_text = "".join([lex_elem.text or ""] + [child.tail or "" for child in lex_elem])
        lex_text = lex_text.strip().strip(".").lower()
        if lex_text in _GENDER_MAP:
            gender_val = _GENDER_MAP[lex_text]
            grammar["gender"] = gender_val if isinstance(gender_val, list) else [gender_val]
        pos_match = lex_text.split(".")[0]
        if pos_match:
            grammar["pos_hint"] = pos_match
    info_elem = root.find("info")
    if info_elem is not None:
        lex_attr = info_elem.get("lex", "")
        if lex_attr:
            gender_val = _GENDER_MAP.get(lex_attr)
            if gender_val:
                grammar["gender"] = gender_val if isinstance(gender_val, list) else [gender_val]
        if info_elem.get("n"):
            grammar.setdefault("grammar_tags", {})["number_marker"] = info_elem.get("n")
    body_text = ElementTree.tostring(root, encoding="unicode", method="text").strip()
    lower = body_text.lower()
    for pattern, case_num in _CASE_MAP.items():
        if pattern in lower:
            grammar.setdefault("case", case_num)
            break
    for pattern, num_code in _NUMBER_MAP.items():
        if pattern in lower:
            grammar.setdefault("number", num_code)
            break
    if root.find("s") is not None and root.find("s").text:
        grammar["sanskrit_form"] = root.find("s").text.strip()
    return grammar


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


def derive_sense(call: ToolCallSpec, extraction: ExtractionEffect) -> DerivationEffect:
    """
    Convert CDSL rows into simple sense payloads.
    """
    start = time.perf_counter()
    entries = []
    payload = extraction.payload or {}
    if isinstance(payload, Mapping):
        entries = payload.get("entries", [])
    senses: list[dict[str, Any]] = []
    grouped: dict[str, dict[str, Any]] = {}
    for entry in entries or []:
        lemma_slp1 = (entry.get("key") or entry.get("key2") or "").strip()
        lemma_iast = _slp1_to_iast(lemma_slp1)
        gloss = entry.get("plain_text") or entry.get("body") or entry.get("data") or ""
        source_ref = f"{entry.get('dict_id', '').lower()}:{entry.get('lnum')}" if entry.get("lnum") else ""
        grammar = _parse_body_metadata(entry.get("body") or "")
        sense_obj: dict[str, Any] = {
            "anchor": lemma_slp1,
            "gloss": gloss,
            "dict": entry.get("dict_id"),
            "lnum": entry.get("lnum"),
            "source_ref": source_ref,
        }
        if grammar:
            sense_obj["grammar"] = grammar
        senses.append(sense_obj)
        group_key = lemma_iast or lemma_slp1
        if group_key not in grouped:
            grouped[group_key] = {
                "lemma": lemma_iast,
                "lemma_slp1": lemma_slp1,
                "senses": [],
            }
        grouped[group_key]["senses"].append(sense_obj)
    duration_ms = int((time.perf_counter() - start) * 1000)
    prov = [
        ProvenanceLink(
            stage="extract", tool=extraction.tool, reference_id=extraction.extraction_id
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


def claim_sense(call: ToolCallSpec, derivation: DerivationEffect) -> ClaimEffect:
    """
    Emit `has_sense` triples for CDSL glosses.
    """
    prov = derivation.provenance_chain[:] if derivation.provenance_chain else []
    prov.append(
        ProvenanceLink(stage="derive", tool=derivation.tool, reference_id=derivation.derivation_id)
    )
    payload = derivation.payload or {}
    sense_groups = payload.get("lemmas") if isinstance(payload, Mapping) else None
    triples: list[dict[str, Any]] = []
    if isinstance(sense_groups, list):
        for group in sense_groups:
            lemma_anchor = (group.get("lemma_slp1") or "").strip().lower()
            subject = f"lex:{lemma_anchor}" if lemma_anchor else derivation.derivation_id
            for sense in group.get("senses", []):
                obj = {"gloss": sense.get("gloss", "")}
                if sense.get("source_ref"):
                    obj["source_ref"] = sense["source_ref"]
                grammar = sense.get("grammar")
                if grammar:
                    obj["grammar"] = grammar
                triples.append(
                    {
                        "subject": subject,
                        "predicate": "has_sense",
                        "object": obj,
                    }
                )
    value = {"lemmas": sense_groups, "triples": triples}
    return ClaimEffect(
        claim_id=stable_effect_id("clm", call.call_id, derivation.derivation_id),
        tool=call.tool,
        call_id=call.call_id,
        source_call_id=call.params.get("source_call_id", ""),
        derivation_id=derivation.derivation_id,
        subject=derivation.derivation_id,
        predicate="has_sense",
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
        lemma = (params.get("lemma") or params.get("q") or "").lower()
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
                        SELECT dict_id, key, key2, key_normalized, key2_normalized, lnum, body, plain_text, data
                        FROM entries
                        WHERE key_normalized IN ({placeholders}) OR key2_normalized IN ({placeholders})
                        """,
                        keys + keys,
                    ).fetchall()
                    cols = [c[0] for c in conn.description]
                if not rows:
                    rows = conn.execute(
                        """
                        SELECT dict_id, key, key2, key_normalized, key2_normalized, lnum, body, plain_text, data
                        FROM entries
                        WHERE key_normalized = ? OR key2_normalized = ?
                        """,
                        [lemma, lemma],
                    ).fetchall()
                    cols = [c[0] for c in conn.description]
            duration_ms = int((time.perf_counter() - start) * 1000)
            entries = [dict(zip(cols, row)) for row in rows]
            body = orjson.dumps(entries)
            return _empty_response(
                call_id, self.tool, endpoint, 200, body, duration_ms=duration_ms
            )
        except Exception as exc:  # noqa: BLE001
            body = orjson.dumps({"error": str(exc)})
            return _empty_response(call_id, self.tool, endpoint, 500, body)


def _empty_response(
    call_id: str, tool: str, endpoint: str, status: int, body: bytes, duration_ms: int = 0
):
    from langnet.clients.base import RawResponseEffect, _new_response_id

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
