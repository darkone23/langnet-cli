from __future__ import annotations

import hashlib
import re
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from types import ModuleType
from typing import Mapping

from query_spec import ToolCallSpec

from langnet.clients.base import RawResponseEffect
from langnet.execution.effects import (
    ClaimEffect,
    DerivationEffect,
    ExtractionEffect,
    ProvenanceLink,
    stable_effect_id,
)


_WHITAKER_MODULES: dict[str, ModuleType] = {}
_ANCHOR_UNKNOWN_POS = "unknown"
_SOURCE_TOOL = "whitaker"
_POS_CODE_MAP = {
    "N": "noun",
    "V": "verb",
    "ADJ": "adjective",
    "ADV": "adverb",
    "PRON": "pronoun",
    "VPAR": "participle",
    "NUM": "numeral",
    "PREP": "preposition",
    "CONJ": "conjunction",
    "INTERJ": "interjection",
    "SUPINE": "supine",
    "TACKON": "tackon",
    "PACK": "packon",
    "SUFFIX": "suffix",
    "PREFIX": "prefix",
}
_FACT_PRED_MAP = {
    "declension": "has_declension",
    "case": "has_case",
    "number": "has_number",
    "gender": "has_gender",
    "conjugation": "has_conjugation",
    "tense": "has_tense",
    "voice": "has_voice",
    "mood": "has_mood",
    "person": "has_person",
    "comparison": "has_degree",
}
_CODELINE_FEATURE_KEYS = ("source", "age", "area", "geo", "notes")


def _load_whitaker_parser(module_name: str) -> ModuleType:
    if module_name in _WHITAKER_MODULES:
        return _WHITAKER_MODULES[module_name]
    root = Path(__file__).resolve().parents[4]
    path = root / "codesketch" / "src" / "langnet" / "whitakers_words" / "lineparsers" / f"{module_name}.py"
    spec = spec_from_file_location(f"codesketch.whitakers.{module_name}", path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load Whitaker parser module {module_name}")
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    _WHITAKER_MODULES[module_name] = module
    return module


def _load_reducers():
    senses = _load_whitaker_parser("parse_senses")
    codes = _load_whitaker_parser("parse_term_codes")
    facts = _load_whitaker_parser("parse_term_facts")
    return senses.SensesReducer, codes.CodesReducer, facts.FactsReducer


def _normalize_surface(term: str | None) -> str | None:
    if not term:
        return None
    return re.sub(r"[^A-Za-z]+", "", term).lower() or None


def _normalize_lemma(raw: str | None) -> str | None:
    if not raw:
        return None
    lemma = raw.split(",")[0].strip().lower()
    lemma = lemma.replace(" ", "_")
    lemma = re.sub(r"[^a-z_]+", "", lemma)
    return lemma or None


def _normalize_pos(term: Mapping[str, object] | None, codeline: Mapping[str, object] | None) -> str:
    pos = None
    if term and isinstance(term.get("part_of_speech"), str):
        pos = term["part_of_speech"].lower()
    if not pos and codeline and isinstance(codeline.get("pos_code"), str):
        pos = _POS_CODE_MAP.get(codeline["pos_code"], codeline["pos_code"].lower())
    return pos or _ANCHOR_UNKNOWN_POS


def _lex_anchor(lemma: str, pos: str) -> str:
    return f"lex:{lemma}#{pos}"


def _interp_anchor(surface: str, lex_anchor: str) -> str:
    return f"interp:form:{surface}→{lex_anchor}"


def _sense_anchor(lex_anchor: str, sense_txt: str) -> str:
    digest = hashlib.sha256(sense_txt.strip().encode("utf-8")).hexdigest()[:8]
    return f"sense:{lex_anchor}#{digest}"


def _trim_evidence(evidence: Mapping[str, object]) -> dict[str, object]:
    return {k: v for k, v in evidence.items() if v is not None}


def _classify_line(line: str) -> Mapping[str, str]:
    line_type: str
    if ";" in line:
        line_type = "sense"
    elif "]" in line:
        line_type = "term-code"
    elif (
        "RETURN/ENTER" in line
        or "exception in PAUSE" in line
        or line == "*"
        or line.startswith("Word mod")
        or "An internal 'b'" in line
    ):
        line_type = "ui-control"
    elif line.strip() == "":
        line_type = "empty"
    elif re.match(r"^[a-z.]+(?:\.[a-z]+)*\s+[A-Z]+", line):
        line_type = "term-facts"
    else:
        line_type = "unknown"
    return {"line_txt": line, "line_type": line_type}


def _get_next_word(current: Mapping | None, last_line: Mapping | None, line_info: Mapping[str, str]):
    next_word: dict[str, object] = {"lines": [line_info]}
    start_new_word = False
    if not last_line:
        start_new_word = True
    else:
        this_line_type = line_info["line_type"]
        last_line_type = last_line["line_type"]
        if last_line_type == "term-code":
            start_new_word = this_line_type != "sense"
        elif last_line_type == "sense":
            start_new_word = this_line_type != "sense" and this_line_type != "unknown"
        elif last_line_type == "unknown":
            start_new_word = this_line_type.startswith("term-")
    if start_new_word:
        return next_word
    assert current is not None
    current["lines"].append(line_info)
    return current


def _analyze_chunk(entry: dict) -> None:
    entry["txts"] = txts = []
    entry["types"] = types = []
    for line in entry["lines"]:
        line_type = line["line_type"]
        line_txt = line["line_txt"]
        if line_type in {"ui-control", "empty"}:
            continue
        txts.append(line_txt)
        types.append(line_type)
    entry["size"] = len(txts)
    entry.pop("lines", None)


def _get_word_chunks(text: str) -> list[dict]:
    word_chunks: list[dict] = []
    current_word = None
    last_line = None
    for line in text.splitlines():
        line_info = _classify_line(line)
        next_word = _get_next_word(current_word, last_line, line_info)
        last_line = line_info
        if next_word is not current_word:
            current_word = next_word
            word_chunks.append(current_word)
    for chunk in word_chunks:
        _analyze_chunk(chunk)
    return word_chunks


def _process_chunk(word_chunk: dict, reducers: tuple[object, object, object]) -> dict | None:
    SensesReducer, CodesReducer, FactsReducer = reducers
    unknown: list[str] = []
    terms: list[Mapping[str, object]] = []
    lines: list[str] = []
    word: dict[str, object] = {"terms": terms, "raw_lines": lines, "unknown": unknown}
    for i in range(word_chunk["size"]):
        txt, line_type = word_chunk["txts"][i], word_chunk["types"][i]
        lines.append(txt)
        if line_type == "sense":
            data = SensesReducer.reduce(txt)
            word.update(data)
        elif line_type == "term-facts":
            terms.append(FactsReducer.reduce(txt))
        elif line_type == "term-code":
            data = CodesReducer.reduce(txt)
            word.setdefault("codeline", data)
        elif line_type == "unknown":
            unknown.append(txt)
    if not unknown:
        word.pop("unknown", None)
    return word if lines else None


def _fixup_word(word: dict) -> dict:
    codeline = word.get("codeline")
    if isinstance(codeline, dict) and not codeline.get("term") and word.get("terms"):
        first_term = word["terms"][0]
        if isinstance(first_term, Mapping) and first_term.get("term"):
            codeline["term"] = first_term["term"]
    return word


def _parse_whitaker_output(text: str) -> list[dict]:
    reducers = _load_reducers()
    chunks = _get_word_chunks(text)
    wordlist: list[dict] = []
    for chunk in chunks:
        word = _process_chunk(chunk, reducers)
        if word:
            wordlist.append(_fixup_word(word))
    return wordlist


def _collect_lemmas(wordlist: list[Mapping[str, object]]) -> list[str]:
    lemmas: list[str] = []
    for word in wordlist:
        codeline = word.get("codeline")
        if isinstance(codeline, Mapping):
            term = codeline.get("term")
            if isinstance(term, str):
                lemmas.append(term.split(",")[0].strip().lower())
        for term in word.get("terms", []) or []:
            if isinstance(term, Mapping):
                t = term.get("term")
                if isinstance(t, str):
                    lemmas.append(t.replace(".", ""))
    seen = set()
    deduped: list[str] = []
    for lemma in lemmas:
        if lemma not in seen:
            seen.add(lemma)
            deduped.append(lemma)
    return deduped


def _make_base_evidence(call: ToolCallSpec, derivation: DerivationEffect, claim_id: str) -> dict[str, object]:
    return _trim_evidence(
        {
            "source_tool": _SOURCE_TOOL,
            "call_id": call.call_id,
            "response_id": _extract_response_id(derivation.provenance_chain),
            "extraction_id": derivation.extraction_id,
            "derivation_id": derivation.derivation_id,
            "claim_id": claim_id,
            "raw_blob_ref": "raw_text",
        }
    )


def _make_triple(
    subject: str, predicate: str, obj: object, base_evidence: Mapping[str, object]
) -> dict[str, object]:
    return {
        "subject": subject,
        "predicate": predicate,
        "object": obj,
        "metadata": {"evidence": _trim_evidence(dict(base_evidence))},
    }


def _variant_candidates(lemmas: list[str], primary_lemma: str) -> list[str]:
    variants: list[str] = []
    for lemma in lemmas:
        normalized = _normalize_lemma(lemma) or lemma.lower()
        if normalized and normalized != primary_lemma and normalized not in variants:
            variants.append(normalized)
    return variants


def _build_triples(
    wordlist: list[Mapping[str, object]] | None, lemmas: list[str], base_evidence: Mapping[str, object]
) -> list[dict[str, object]]:
    if not isinstance(wordlist, list):
        return []
    normalized_lemmas = [_normalize_lemma(l) or l.lower() for l in lemmas if isinstance(l, str)]
    triples: list[dict[str, object]] = []
    for word in wordlist:
        if not isinstance(word, Mapping):
            continue
        raw_lines = [l for l in word.get("raw_lines", []) if isinstance(l, str)]
        codeline = word.get("codeline") if isinstance(word.get("codeline"), Mapping) else {}
        senses = word.get("senses") if isinstance(word.get("senses"), list) else []
        terms = [t for t in word.get("terms", []) if isinstance(t, Mapping)] if isinstance(word.get("terms"), list) else []

        primary_lemma = _normalize_lemma(codeline.get("term")) if isinstance(codeline, Mapping) else None
        if not primary_lemma and normalized_lemmas:
            primary_lemma = normalized_lemmas[0]
        if not primary_lemma:
            for term in terms:
                primary_lemma = _normalize_surface(term.get("term"))  # type: ignore[arg-type]
                if primary_lemma:
                    break
        pos = _normalize_pos(terms[0] if terms else None, codeline if isinstance(codeline, Mapping) else None)
        lex_anchor = _lex_anchor(primary_lemma, pos) if primary_lemma else None

        if lex_anchor:
            triples.append(_make_triple(lex_anchor, "has_pos", pos, base_evidence))
            if isinstance(codeline, Mapping):
                if codeline.get("freq"):
                    triples.append(_make_triple(lex_anchor, "has_frequency", codeline.get("freq"), base_evidence))
                if codeline.get("declension"):
                    triples.append(_make_triple(lex_anchor, "has_declension", codeline.get("declension"), base_evidence))
                if codeline.get("pos_form"):
                    triples.append(_make_triple(lex_anchor, "has_gender", codeline.get("pos_form"), base_evidence))
                extra_features = {k: codeline[k] for k in _CODELINE_FEATURE_KEYS if codeline.get(k)}
                if extra_features:
                    triples.append(_make_triple(lex_anchor, "has_feature", extra_features, base_evidence))
            for variant in _variant_candidates(normalized_lemmas, primary_lemma):
                triples.append(_make_triple(lex_anchor, "variant_form", variant, base_evidence))
            for sense in senses:
                if not isinstance(sense, str):
                    continue
                sense_txt = sense.strip()
                if not sense_txt:
                    continue
                sense_anchor = _sense_anchor(lex_anchor, sense_txt)
                triples.append(_make_triple(lex_anchor, "has_sense", sense_anchor, base_evidence))
                triples.append(_make_triple(sense_anchor, "gloss", sense_txt, base_evidence))

        for term in terms:
            surface = _normalize_surface(term.get("term")) if isinstance(term, Mapping) else None
            if not surface or not lex_anchor:
                continue
            form_anchor = f"form:{surface}"
            interp_anchor = _interp_anchor(surface, lex_anchor)
            triples.append(_make_triple(form_anchor, "has_interpretation", interp_anchor, base_evidence))
            triples.append(_make_triple(interp_anchor, "realizes_lexeme", lex_anchor, base_evidence))
            term_pos = _normalize_pos(term, codeline if isinstance(codeline, Mapping) else None)
            if term_pos:
                triples.append(_make_triple(interp_anchor, "has_pos", term_pos, base_evidence))
            for key, pred in _FACT_PRED_MAP.items():
                val = term.get(key) if isinstance(term, Mapping) else None
                if val:
                    triples.append(_make_triple(interp_anchor, pred, val, base_evidence))
            if term.get("notes"):
                triples.append(_make_triple(interp_anchor, "has_feature", {"notes": term.get("notes")}, base_evidence))
    return triples


def _extract_response_id(provenance: list[ProvenanceLink] | None) -> str | None:
    if not provenance:
        return None
    for link in provenance:
        if link.stage == "extract" and link.metadata:
            rid = link.metadata.get("response_id")
            if isinstance(rid, str):
                return rid
    return None


def extract_lines(call: ToolCallSpec, raw: RawResponseEffect) -> ExtractionEffect:
    text = raw.body.decode("utf-8", errors="ignore")
    wordlist = _parse_whitaker_output(text)
    lemmas = _collect_lemmas(wordlist)
    canonical = lemmas[0] if lemmas else None
    return ExtractionEffect(
        extraction_id=stable_effect_id("ww-ext", call.call_id, raw.response_id),
        tool=call.tool,
        call_id=call.call_id,
        source_call_id=call.params.get("source_call_id", ""),
        response_id=raw.response_id,
        kind="whitakers.lines",
        canonical=canonical,
        payload={"lemmas": lemmas, "wordlist": wordlist, "raw_text": text},
    )


def derive_facts(call: ToolCallSpec, extraction: ExtractionEffect) -> DerivationEffect:
    prov = [
        ProvenanceLink(
            stage="extract",
            tool=extraction.tool,
            reference_id=extraction.extraction_id,
            metadata={"response_id": extraction.response_id},
        )
    ]
    payload = {}
    if isinstance(extraction.payload, Mapping):
        payload = {
            "lemmas": extraction.payload.get("lemmas", []),
            "wordlist": extraction.payload.get("wordlist", []),
            "raw_text": extraction.payload.get("raw_text", ""),
        }
    return DerivationEffect(
        derivation_id=stable_effect_id("ww-der", call.call_id, extraction.extraction_id),
        tool=call.tool,
        call_id=call.call_id,
        source_call_id=call.params.get("source_call_id", ""),
        extraction_id=extraction.extraction_id,
        kind="whitakers.facts",
        canonical=extraction.canonical,
        payload=payload,
        provenance_chain=prov,
    )


def claim_whitakers(call: ToolCallSpec, derivation: DerivationEffect) -> ClaimEffect:
    prov = derivation.provenance_chain[:] if derivation.provenance_chain else []
    prov.append(
        ProvenanceLink(
            stage="derive",
            tool=derivation.tool,
            reference_id=derivation.derivation_id,
            metadata={"extraction_id": derivation.extraction_id},
        )
    )
    claim_id = stable_effect_id("ww-clm", call.call_id, derivation.derivation_id)
    subject = derivation.canonical or call.call_id
    value = derivation.payload if isinstance(derivation.payload, Mapping) else {}
    lemmas = value.get("lemmas") if isinstance(value, Mapping) else []
    base_evidence = _make_base_evidence(call, derivation, claim_id)
    triples = _build_triples(value.get("wordlist") if isinstance(value, Mapping) else None, lemmas or [], base_evidence)
    if isinstance(value, Mapping):
        value = {**value, "triples": triples}
    return ClaimEffect(
        claim_id=claim_id,
        tool=call.tool,
        call_id=call.call_id,
        source_call_id=call.params.get("source_call_id", ""),
        derivation_id=derivation.derivation_id,
        subject=subject,
        predicate="has_lemmas",
        value=value,
        provenance_chain=prov,
    )
