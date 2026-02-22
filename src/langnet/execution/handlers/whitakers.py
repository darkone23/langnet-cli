from __future__ import annotations

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
    subject = derivation.canonical or call.call_id
    value = derivation.payload if isinstance(derivation.payload, Mapping) else {}
    triples: list[dict[str, object]] = []
    wordlist = value.get("wordlist") if isinstance(value, Mapping) else None
    if isinstance(wordlist, list):
        for word in wordlist:
            if not isinstance(word, Mapping):
                continue
            senses = word.get("senses") if isinstance(word.get("senses"), list) else []
            terms = word.get("terms") if isinstance(word.get("terms"), list) else []
            for term in terms:
                if not isinstance(term, Mapping):
                    continue
                term_txt = term.get("term")
                subj = (term_txt.replace(".", "") if isinstance(term_txt, str) else subject) or subject
                # Core grammatical features
                for pred, key in [
                    ("has_pos", "part_of_speech"),
                    ("has_declension", "declension"),
                    ("has_case", "case"),
                    ("has_number", "number"),
                    ("has_gender", "gender"),
                    ("has_conjugation", "conjugation"),
                    ("has_tense", "tense"),
                    ("has_voice", "voice"),
                    ("has_mood", "mood"),
                    ("has_person", "person"),
                    ("has_comparison", "comparison"),
                ]:
                    val = term.get(key)
                    if val:
                        triples.append({"subject": subj, "predicate": pred, "object": val})
            for sense in senses:
                if isinstance(sense, str) and sense:
                    triples.append({"subject": subject, "predicate": "has_sense", "object": sense})
            codeline = word.get("codeline") if isinstance(word.get("codeline"), Mapping) else None
            if codeline:
                cl_term = codeline.get("term")
                cl_subject = (cl_term.split(",")[0].strip() if isinstance(cl_term, str) else subject) or subject
                for pred, key in [
                    ("has_pos", "pos_code"),
                    ("has_declension", "declension"),
                    ("has_gender", "pos_form"),
                    ("has_frequency", "freq"),
                    ("has_source", "source"),
                ]:
                    val = codeline.get(key)
                    if val:
                        triples.append({"subject": cl_subject, "predicate": pred, "object": val})
    if isinstance(value, Mapping):
        value = {**value, "triples": triples}
    return ClaimEffect(
        claim_id=stable_effect_id("ww-clm", call.call_id, derivation.derivation_id),
        tool=call.tool,
        call_id=call.call_id,
        source_call_id=call.params.get("source_call_id", ""),
        derivation_id=derivation.derivation_id,
        subject=subject,
        predicate="has_lemmas",
        value=value,
        provenance_chain=prov,
    )
