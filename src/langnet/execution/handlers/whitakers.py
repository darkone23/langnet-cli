from __future__ import annotations

import hashlib
import re
from collections.abc import Mapping, Sequence
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from types import ModuleType
from typing import Any, Protocol, TypedDict, cast

from query_spec import ToolCallSpec

from langnet.clients.base import RawResponseEffect
from langnet.execution import anchors, predicates
from langnet.execution.effects import (
    ClaimEffect,
    DerivationEffect,
    ExtractionEffect,
    ProvenanceLink,
    stable_effect_id,
)
from langnet.execution.versioning import versioned


class Reducer(Protocol):
    """Protocol for Whitaker line parser reducers."""

    @staticmethod
    def reduce(line: str) -> dict[str, Any]:
        """Parse a line and return structured data."""
        ...


class WhitakerCodeline(TypedDict, total=False):
    """Whitaker codeline structure (dictionary entry metadata)."""

    term: str
    pos_code: str
    declension: str
    freq: str
    source: str


class WhitakerTerm(TypedDict, total=False):
    """Whitaker term structure (morphological analysis)."""

    part_of_speech: str
    term: str
    stem: str
    ending: str
    conjugation: str
    declension: str
    variant: str
    tense: str
    voice: str
    mood: str
    person: str
    number: str
    case: str
    gender: str
    comparison: str


class WhitakerWord(TypedDict, total=False):
    """Whitaker word structure (complete parse result)."""

    terms: list[WhitakerTerm]
    raw_lines: list[str]
    codeline: WhitakerCodeline
    senses: list[str]
    unknown: list[str]


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
    "declension": predicates.HAS_DECLENSION,
    "case": predicates.HAS_CASE,
    "number": predicates.HAS_NUMBER,
    "gender": predicates.HAS_GENDER,
    "conjugation": predicates.HAS_CONJUGATION,
    "tense": predicates.HAS_TENSE,
    "voice": predicates.HAS_VOICE,
    "mood": predicates.HAS_MOOD,
    "person": predicates.HAS_PERSON,
    "comparison": predicates.HAS_DEGREE,
}
_CODELINE_FEATURE_KEYS = ("source", "age", "area", "geo", "notes")

# Rich code-to-label maps (adapted from the codesketch whitakers_words core)
_TENSE_MAP = {
    "PRES": "present",
    "IMP": "imperfect",
    "IMPF": "imperfect",
    "IMPFF": "imperfect",
    "PERF": "perfect",
    "FUT": "future",
    "FUTP": "future perfect",
    "PLUP": "pluperfect",
    "X": "unknown",
}
_VOICE_MAP = {"ACTIVE": "active", "PASSIVE": "passive", "X": "unknown"}
_MOOD_MAP = {
    "IND": "indicative",
    "SUB": "subjunctive",
    "IMP": "imperative",
    "INF": "infinitive",
    "PPL": "participle",
    "X": "unknown",
}
_PERSON_MAP = {"0": "0", "1": "1", "2": "2", "3": "3", "X": "unknown"}
_NUMBER_MAP = {"S": "singular", "P": "plural", "X": "unknown"}
_CASE_MAP = {
    "NOM": "nominative",
    "VOC": "vocative",
    "GEN": "genitive",
    "DAT": "dative",
    "ACC": "accusative",
    "ABL": "ablative",
    "LOC": "locative",
    "X": "unknown",
}
_GENDER_MAP = {"M": "masculine", "F": "feminine", "N": "neuter", "C": "common", "X": "unknown"}
_DEGREE_MAP = {"POS": "positive", "COMP": "comparative", "SUPER": "superlative", "X": "unknown"}
_PRONOUN_TYPE_MAP = {
    "PERS": "personal",
    "REFLEX": "reflexive",
    "DEMONS": "demonstrative",
    "INDEF": "indefinite",
    "INTERR": "interrogative",
    "REL": "relative",
    "ADJECT": "adjectival",
    "X": "unknown",
}
_NUMERAL_TYPE_MAP = {
    "CARD": "cardinal",
    "ORD": "ordinal",
    "DIST": "distributive",
    "ADVERB": "adverbial",
    "X": "unknown",
}
_AGE_MAP = {
    "A": "archaic",
    "B": "early",
    "C": "classical",
    "D": "late",
    "E": "later",
    "F": "medieval",
    "G": "scholastic",
    "H": "hispano-latin",
    "I": "modern",
    "X": "unknown",
}
_AREA_MAP = {
    "A": "Africa",
    "B": "Britain",
    "C": "China",
    "E": "Egypt",
    "F": "France/Spain",
    "G": "Germany",
    "H": "North Africa",
    "I": "Italy",
    "J": "Judea",
    "K": "Balkans",
    "L": "Low Countries",
    "M": "Mediterranean",
    "N": "Northern Europe",
    "P": "Persia",
    "Q": "Syria",
    "R": "Romania",
    "S": "Scandinavia",
    "T": "Sicily",
    "U": "Russia",
    "X": "unknown",
}
_GEO_MAP = {
    "A": "Africa",
    "B": "Britain",
    "C": "China",
    "E": "Egypt",
    "F": "France",
    "G": "Germany",
    "H": "Greece",
    "I": "Italy",
    "J": "India",
    "K": "Balkan",
    "L": "Malta",
    "M": "Macedonia",
    "N": "Northern",
    "O": "Oriental",
    "P": "Persia",
    "Q": "Syria",
    "R": "Rome",
    "S": "Spain",
    "T": "Tropic",
    "U": "Russia",
    "X": "unknown",
}
_FREQ_MAP = {
    "A": "very frequent",
    "B": "frequent",
    "C": "common",
    "D": "uncommon",
    "E": "rare",
    "F": "very rare",
    "X": "unknown",
}
_SOURCE_MAP = {
    "A": "Allen and Greenough",
    "L": "Lewis and Short",
    "S": "Supplement",
    "X": "unknown",
}


def _load_whitaker_parser(module_name: str) -> ModuleType:
    if module_name in _WHITAKER_MODULES:
        return _WHITAKER_MODULES[module_name]
    root = Path(__file__).resolve().parents[4]
    path = (
        root
        / "codesketch"
        / "src"
        / "langnet"
        / "whitakers_words"
        / "lineparsers"
        / f"{module_name}.py"
    )
    spec = spec_from_file_location(f"codesketch.whitakers.{module_name}", path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load Whitaker parser module {module_name}")
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    _WHITAKER_MODULES[module_name] = module
    return module


def _load_reducers() -> tuple[type[Reducer], type[Reducer], type[Reducer]]:
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


def _normalize_pos(term: WhitakerTerm | None, codeline: WhitakerCodeline | None) -> str:
    pos: str | None = None
    if term:
        pos_val = term.get("part_of_speech")
        if isinstance(pos_val, str):
            pos = pos_val.lower()
    if not pos and codeline:
        pos_code = codeline.get("pos_code")
        if isinstance(pos_code, str):
            pos = _POS_CODE_MAP.get(pos_code, pos_code.lower())
    return pos or _ANCHOR_UNKNOWN_POS


def _map_feature_value(code: str | None, mapping: Mapping[str, str]) -> str | None:
    if not code:
        return None
    return mapping.get(code, code)


def _lex_anchor(lemma: str, pos: str) -> str:
    """Delegate to canonical anchor module with normalization."""
    return anchors.lex_anchor(lemma, pos) if pos else anchors.lex_anchor(lemma)


def _interp_anchor(surface: str, lex_anchor: str) -> str:
    """Delegate to canonical anchor module."""
    return anchors.interp_anchor(surface, lex_anchor)


def _sense_anchor(lex_anchor: str, sense_txt: str) -> str:
    """Generate stable sense anchor with content hash."""
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


def _get_next_word(
    current: Mapping | None, last_line: Mapping | None, line_info: Mapping[str, str]
):
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
            start_new_word = this_line_type not in {"sense", "unknown"}
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


def _process_chunk(
    word_chunk: dict[str, object],
    reducers: tuple[type[Reducer], type[Reducer], type[Reducer]],
) -> WhitakerWord | None:
    SensesReducer, CodesReducer, FactsReducer = reducers
    unknown: list[str] = []
    terms: list[WhitakerTerm] = []
    lines: list[str] = []
    word: WhitakerWord = {"terms": terms, "raw_lines": lines, "unknown": unknown}

    size_val = word_chunk.get("size")
    size = size_val if isinstance(size_val, int) else 0
    txts_val = word_chunk.get("txts")
    txts = txts_val if isinstance(txts_val, Sequence) else []
    types_val = word_chunk.get("types")
    types = types_val if isinstance(types_val, Sequence) else []

    for i in range(size):
        txt_val = txts[i] if i < len(txts) else ""
        txt: str = txt_val if isinstance(txt_val, str) else ""
        type_val = types[i] if i < len(types) else ""
        line_type: str = type_val if isinstance(type_val, str) else ""
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


def _fixup_word(word: WhitakerWord) -> WhitakerWord:
    codeline = word.get("codeline")
    terms = word.get("terms", [])
    if isinstance(codeline, dict) and not codeline.get("term") and terms:
        first_term = terms[0]
        if isinstance(first_term, dict) and first_term.get("term"):
            codeline["term"] = first_term["term"]
    return word


def _parse_whitaker_output(text: str) -> list[WhitakerWord]:
    reducers = _load_reducers()
    chunks = _get_word_chunks(text)
    wordlist: list[WhitakerWord] = []
    for chunk in chunks:
        word = _process_chunk(chunk, reducers)
        if word:
            wordlist.append(_fixup_word(word))
    return wordlist


def _collect_lemmas(wordlist: list[WhitakerWord]) -> list[str]:
    lemmas: list[str] = []
    for word in wordlist:
        codeline = word.get("codeline")
        if codeline is not None:
            term = codeline.get("term")
            if isinstance(term, str):
                lemmas.append(term.split(",")[0].strip().lower())
        for term in word.get("terms", []):
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


def _collect_word_lemmas(word: WhitakerWord) -> list[str]:
    """Collect lemmas from a single Whitaker word chunk (codeline + terms)."""
    lemmas: list[str] = []
    codeline = word.get("codeline")
    if codeline is not None:
        term = codeline.get("term")
        if isinstance(term, str):
            lemmas.append(term.split(",")[0].strip().lower())
    for term in word.get("terms", []):
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


def _make_base_evidence(
    call: ToolCallSpec, derivation: DerivationEffect, claim_id: str
) -> dict[str, object]:
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


def _select_primary_lemma(
    codeline: WhitakerCodeline | None,
    normalized_word_lemmas: list[str],
    normalized_lemmas: list[str],
    terms: list[WhitakerTerm],
) -> str | None:
    """Select the primary lemma from available sources."""
    primary_lemma: str | None = None
    if codeline is not None:
        term_val = codeline.get("term")
        if isinstance(term_val, str):
            primary_lemma = _normalize_lemma(term_val)
    if not primary_lemma and normalized_word_lemmas:
        primary_lemma = normalized_word_lemmas[0]
    if not primary_lemma and normalized_lemmas:
        primary_lemma = normalized_lemmas[0]
    if not primary_lemma:
        for term in terms:
            term_str = term.get("term")
            if isinstance(term_str, str):
                primary_lemma = _normalize_surface(term_str)
                if primary_lemma:
                    break
    return primary_lemma


def _build_codeline_triples(
    lex_anchor: str,
    codeline: WhitakerCodeline,
    base_evidence: Mapping[str, object],
) -> list[dict[str, object]]:
    """Build triples for codeline features."""
    triples: list[dict[str, object]] = []
    freq_val = codeline.get("freq")
    if freq_val:
        mapped_freq = _map_feature_value(freq_val, _FREQ_MAP) or freq_val
        triples.append(_make_triple(lex_anchor, "has_frequency", mapped_freq, base_evidence))
    declension_val = codeline.get("declension")
    if declension_val:
        triples.append(
            _make_triple(lex_anchor, predicates.HAS_DECLENSION, declension_val, base_evidence)
        )
    pos_form = codeline.get("pos_form")
    if pos_form:
        pf = str(pos_form)
        pron_type = _map_feature_value(pf, _PRONOUN_TYPE_MAP)
        num_type = _map_feature_value(pf, _NUMERAL_TYPE_MAP)
        if pron_type and pron_type != pf:
            triples.append(_make_triple(lex_anchor, "has_pronoun_type", pron_type, base_evidence))
        elif num_type and num_type != pf:
            triples.append(_make_triple(lex_anchor, "has_numeral_type", num_type, base_evidence))
        else:
            triples.append(_make_triple(lex_anchor, "has_feature", {"pos_form": pf}, base_evidence))

    extra_features: dict[str, object] = {}
    for key, mapping in [
        ("age", _AGE_MAP),
        ("area", _AREA_MAP),
        ("geo", _GEO_MAP),
        ("source", _SOURCE_MAP),
    ]:
        val = codeline.get(key)  # type: ignore[misc]
        if val:
            mapped_val = _map_feature_value(str(val), mapping) or val
            extra_features[key] = mapped_val
    notes_val = codeline.get("notes")  # type: ignore[misc]
    if notes_val:
        extra_features["notes"] = notes_val
    if extra_features:
        triples.append(_make_triple(lex_anchor, "has_feature", extra_features, base_evidence))
    return triples


def _build_sense_triples(
    lex_anchor: str,
    senses: Sequence[str],
    base_evidence: Mapping[str, object],
) -> list[dict[str, object]]:
    """Build triples for word senses."""
    triples: list[dict[str, object]] = []
    for sense in senses:
        sense_txt = sense.strip()
        if not sense_txt:
            continue
        sense_anchor = _sense_anchor(lex_anchor, sense_txt)
        triples.append(_make_triple(lex_anchor, predicates.HAS_SENSE, sense_anchor, base_evidence))
        triples.append(_make_triple(sense_anchor, predicates.GLOSS, sense_txt, base_evidence))
    return triples


def _map_morphological_feature(pred: str, val: object) -> object:
    """Map morphological feature values using appropriate mapping tables."""
    predicate_map_table = {
        "has_tense": _TENSE_MAP,
        "has_voice": _VOICE_MAP,
        "has_mood": _MOOD_MAP,
        "has_person": _PERSON_MAP,
        "has_number": _NUMBER_MAP,
        "has_case": _CASE_MAP,
        "has_gender": _GENDER_MAP,
        "has_degree": _DEGREE_MAP,
    }
    feature_map = predicate_map_table.get(pred)
    return _map_feature_value(str(val), feature_map) or val if feature_map else val


def _build_term_triples(
    terms: list[WhitakerTerm],
    lex_anchor: str,
    codeline: WhitakerCodeline | None,
    base_evidence: Mapping[str, object],
) -> list[dict[str, object]]:
    """Build triples for inflected terms."""
    triples: list[dict[str, object]] = []
    for term in terms:
        term_str = term.get("term")
        surface = _normalize_surface(term_str) if isinstance(term_str, str) else None
        if not surface or not lex_anchor:
            continue
        form_anchor = f"form:{surface}"
        interp_anchor = _interp_anchor(surface, lex_anchor)
        triples.append(
            _make_triple(form_anchor, "has_interpretation", interp_anchor, base_evidence)
        )
        triples.append(_make_triple(interp_anchor, "realizes_lexeme", lex_anchor, base_evidence))
        triples.append(_make_triple(form_anchor, "inflection_of", lex_anchor, base_evidence))

        term_pos = _normalize_pos(term, codeline)
        if term_pos:
            triples.append(_make_triple(interp_anchor, predicates.HAS_POS, term_pos, base_evidence))

        for key, pred in _FACT_PRED_MAP.items():
            val = term.get(key)  # type: ignore[misc]
            if val:
                mapped_val = _map_morphological_feature(pred, str(val))
                triples.append(_make_triple(interp_anchor, pred, mapped_val, base_evidence))

        notes_val = term.get("notes")  # type: ignore[misc]
        if notes_val:
            triples.append(
                _make_triple(interp_anchor, "has_feature", {"notes": notes_val}, base_evidence)
            )
    return triples


def _build_triples(
    wordlist: list[WhitakerWord] | None,
    lemmas: list[str],
    base_evidence: Mapping[str, object],
) -> list[dict[str, object]]:
    """Build RDF-style triples from Whitakers wordlist data."""
    if not isinstance(wordlist, list):
        return []

    normalized_lemmas = [
        _normalize_lemma(lemma) or lemma.lower() for lemma in lemmas if isinstance(lemma, str)
    ]
    triples: list[dict[str, object]] = []

    for word in wordlist:
        word_lemmas = _collect_word_lemmas(word)
        normalized_word_lemmas = [
            _normalize_lemma(lemma) or lemma.lower()
            for lemma in word_lemmas
            if isinstance(lemma, str)
        ]
        codeline = word.get("codeline")
        senses = word.get("senses", [])
        terms = word.get("terms", [])

        primary_lemma = _select_primary_lemma(
            codeline,
            normalized_word_lemmas,
            normalized_lemmas,
            terms,
        )
        pos = _normalize_pos(terms[0] if terms else None, codeline)
        lex_anchor = _lex_anchor(primary_lemma, pos) if primary_lemma else None

        # primary_lemma is guaranteed non-None when lex_anchor exists
        if lex_anchor and primary_lemma:
            triples.append(_make_triple(lex_anchor, predicates.HAS_POS, pos, base_evidence))

            if codeline is not None:
                triples.extend(_build_codeline_triples(lex_anchor, codeline, base_evidence))

            for variant in _variant_candidates(normalized_word_lemmas, primary_lemma):
                triples.append(
                    _make_triple(lex_anchor, predicates.VARIANT_FORM, variant, base_evidence)
                )

            triples.extend(_build_sense_triples(lex_anchor, senses, base_evidence))

        if lex_anchor:
            triples.extend(_build_term_triples(terms, lex_anchor, codeline, base_evidence))

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


@versioned("v1")
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


@versioned("v1")
def derive_facts(call: ToolCallSpec, extraction: ExtractionEffect) -> DerivationEffect:
    prov = [
        ProvenanceLink(
            stage="extract",
            tool=extraction.tool,
            reference_id=extraction.extraction_id,
            metadata={"response_id": extraction.response_id},
        )
    ]
    payload: dict[str, object] = {}
    if isinstance(extraction.payload, Mapping):
        ext_payload = cast(dict[str, object], extraction.payload)
        lemmas = ext_payload.get("lemmas")
        wordlist = ext_payload.get("wordlist")
        raw_text = ext_payload.get("raw_text")
        payload = {
            "lemmas": cast(list[str], lemmas) if isinstance(lemmas, list) else [],
            "wordlist": cast(list[WhitakerWord], wordlist) if isinstance(wordlist, list) else [],
            "raw_text": raw_text if isinstance(raw_text, str) else "",
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


@versioned("v2")
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
    value_raw = derivation.payload if isinstance(derivation.payload, Mapping) else {}
    value = cast(dict[str, object], value_raw) if isinstance(value_raw, Mapping) else {}

    lemmas_val = value.get("lemmas") if value else []
    lemmas = list(cast(Sequence[str], lemmas_val)) if isinstance(lemmas_val, Sequence) else []
    wordlist_val = value.get("wordlist") if value else None
    wordlist = cast(list[WhitakerWord], wordlist_val) if isinstance(wordlist_val, list) else None

    base_evidence = _make_base_evidence(call, derivation, claim_id)
    triples = _build_triples(wordlist, lemmas, base_evidence)
    if value:
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
