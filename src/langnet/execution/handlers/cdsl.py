from __future__ import annotations

import hashlib
import time
import unicodedata
from collections.abc import Mapping, Sequence
from typing import cast
from xml.etree import ElementTree

import orjson
from query_spec import ToolCallSpec

from langnet.clients.base import RawResponseEffect, _new_response_id
from langnet.databuild.paths import default_cdsl_path
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
    return "".join(
        c for c in unicodedata.normalize("NFD", text) if unicodedata.category(c) != "Mn"
    ).lower()


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
        grammar["sanskrit_form"] = s_elem.text.strip()

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

        sense_obj: dict[str, object] = {
            "anchor": lemma_slp1,
            "gloss": gloss,
            "dict": dict_id,
            "lnum": lnum_val,
            "source_ref": source_ref,
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

                grammar = sense.get("grammar")
                evidence = _make_base_evidence(call, derivation, claim_id, source_ref_str)
                sense_anchor = _sense_anchor(subject, gloss, source_ref_str)
                triples.append(_make_triple(subject, "has_sense", sense_anchor, evidence))
                triples.append(
                    _make_triple(
                        sense_anchor,
                        "gloss",
                        gloss,
                        evidence,
                        {"source_ref": source_ref_str} if source_ref_str else None,
                    )
                )
                if grammar:
                    triples.append(
                        _make_triple(sense_anchor, "has_feature", {"grammar": grammar}, evidence)
                    )
    value = {"lemmas": sense_groups, "triples": triples}
    return ClaimEffect(
        claim_id=claim_id,
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
                        [lemma, lemma],
                    ).fetchall()
                    cols = [c[0] for c in conn.description]
            duration_ms = int((time.perf_counter() - start) * 1000)
            entries = [dict(zip(cols, row)) for row in rows]
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
