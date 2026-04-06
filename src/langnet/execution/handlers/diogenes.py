from __future__ import annotations

import hashlib
import re
from collections.abc import Mapping, Sequence
from typing import TypedDict, cast

from bs4 import BeautifulSoup, Tag
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
from langnet.normalizer.utils import contains_greek, normalize_greekish_token, strip_accents


class DiogenesMorphology(TypedDict, total=False):
    """Perseus morphological analysis."""

    morphs: list[dict[str, object]]
    warning: str


class DiogenesDefinitionBlock(TypedDict, total=False):
    """Diogenes definition block with hierarchical structure."""

    indentid: str
    soup: BeautifulSoup
    text: str
    lemma: str | None
    senses: list[str]
    diogenes_warning: str
    citations: dict[str, str]
    entry: str
    entryid: str


class DiogenesDefinitions(TypedDict, total=False):
    """Diogenes definitions container."""

    blocks: list[DiogenesDefinitionBlock]


class DiogenesChunk(TypedDict, total=False):
    """Diogenes parsed chunk (either morphology or dictionary reference)."""

    chunk_type: str
    morphology: DiogenesMorphology
    reference_id: str
    definitions: DiogenesDefinitions


class DiogenesParsedResult(TypedDict, total=False):
    """Complete Diogenes parse result."""

    chunks: list[DiogenesChunk]
    dg_parsed: bool
    chunk_types: list[str]
    is_fuzzy_overall: bool


_PARSER_PREFERENCE = ("lxml", "html5lib", "html.parser")
PERSEUS_MORPH_PART_COUNT = 2
_POS_CANONICAL = {
    "verb": "verb",
    "v": "verb",
    "noun": "noun",
    "n": "noun",
    "adj": "adjective",
    "adjective": "adjective",
    "adv": "adverb",
    "adverb": "adverb",
    "pron": "pronoun",
    "pronoun": "pronoun",
    "part": "participle",
    "participle": "participle",
    "prep": "preposition",
    "preposition": "preposition",
    "conj": "conjunction",
    "conjunction": "conjunction",
    "interj": "interjection",
}


def _make_soup(html: str) -> BeautifulSoup:
    for parser in _PARSER_PREFERENCE:
        try:
            return BeautifulSoup(html, parser)
        except Exception:
            continue
    return BeautifulSoup(html, "html.parser")


def _find_nd_coordinate(event_id: str) -> tuple[int, ...]:
    """
    Translate padding indent histories into n-dimensional array coordinates.
    """
    values = list(map(int, event_id.split(":")))
    unique_values = list(dict.fromkeys(values))
    level_counters: dict[tuple[int, ...], int] = {}
    coordinates: list[tuple[int, ...]] = []
    stack: list[int] = []

    for value in values:
        dimension_index = unique_values.index(value)
        stack = stack[:dimension_index]
        count = level_counters.get(tuple(stack), 0)
        level_counters[tuple(stack)] = count + 1
        stack.append(count)
        coordinates.append(tuple(stack))
    return coordinates[-1] if coordinates else tuple()


def _extract_parentheses_text(text: str) -> tuple[str, str]:
    extracted = " ".join(re.findall(r"\((.*?)\)", text, re.DOTALL))
    cleaned_text = re.sub(r"\s*\(.*?\)\s*", " ", text, flags=re.DOTALL).strip()
    return cleaned_text, extracted


def _parse_perseus_morph(tag) -> Mapping[str, object]:
    perseus_morph = tag.get_text()
    parts = perseus_morph.split(":")
    if len(parts) != PERSEUS_MORPH_PART_COUNT:
        return {}
    stems, tag_parts = parts

    cleaned_defs: list[str] = []
    cleaned_stems: list[str] = []
    stem_part, maybe_def = _extract_parentheses_text(stems)
    for word_def in maybe_def.split(","):
        cleaned_def = re.sub(r"\d+", "", word_def).strip()
        if cleaned_def:
            cleaned_defs.append(cleaned_def)
    for perseus_stem in stem_part.split(","):
        cleaned_stems.append(re.sub(r"\d+", "", perseus_stem).strip())

    cleaned_tags: list[str] = []
    tag_parts = re.sub(r"[()]+", "", tag_parts)
    for t in tag_parts.replace("/", " ").split():
        pos = t.strip()
        if pos and pos not in cleaned_tags:
            cleaned_tags.append(pos)

    morph: dict[str, object] = {"stem": cleaned_stems, "tags": cleaned_tags}
    if cleaned_defs:
        morph["defs"] = cleaned_defs
    return morph


def _trim_evidence(evidence: Mapping[str, object]) -> dict[str, object]:
    return {k: v for k, v in evidence.items() if v is not None}


def _normalize_token(text: str | None) -> str | None:
    """
    Normalize lemmas/forms for anchor minting.

    Greek paths first try a Greek-aware collapse (accents removed, final sigma
    folded, betacode collapsed to ASCII) and then fall back to the previous
    ASCII-only normalization for Latin/others.
    """
    if not text:
        return None
    greekish = normalize_greekish_token(text)
    if greekish:
        return greekish
    normalized = strip_accents(text).lower()
    # Preserve bare Greek code points even if no betacode markers were present.
    if contains_greek(normalized):
        normalized = normalized.replace("ς", "σ")
    normalized = re.sub(r"[^a-z0-9_]+", "_", normalized)
    normalized = re.sub(r"_+", "_", normalized).strip("_")
    return normalized or None


def _lex_anchor(lemma: str) -> str:
    return f"lex:{lemma}"


def _form_anchor(form: str) -> str:
    return f"form:{form}"


def _sense_anchor(lex_anchor: str, gloss: str) -> str:
    digest = hashlib.sha256(gloss.strip().encode("utf-8")).hexdigest()[:8]
    return f"sense:{lex_anchor}#{digest}"


def _make_triple(
    subject: str, predicate: str, obj: object, base_evidence: Mapping[str, object]
) -> dict[str, object]:
    return {
        "subject": subject,
        "predicate": predicate,
        "object": obj,
        "metadata": {"evidence": _trim_evidence(dict(base_evidence))},
    }


def _extract_response_id(provenance: list[ProvenanceLink] | None) -> str | None:
    if not provenance:
        return None
    for link in provenance:
        if link.stage == "extract" and link.metadata:
            rid = link.metadata.get("response_id")
            if isinstance(rid, str):
                return rid
    return None


def _make_base_evidence(
    call: ToolCallSpec, derivation: DerivationEffect, claim_id: str
) -> Mapping[str, object]:
    return _trim_evidence(
        {
            "source_tool": "diogenes",
            "call_id": call.call_id,
            "response_id": _extract_response_id(derivation.provenance_chain),
            "extraction_id": derivation.extraction_id,
            "derivation_id": derivation.derivation_id,
            "claim_id": claim_id,
            "raw_blob_ref": "raw_html",
        }
    )


def _normalize_pos(tags: Sequence[str]) -> str | None:
    for tag in tags:
        key = re.sub(r"[^A-Za-z]+", "", tag).lower()
        if not key:
            continue
        pos = _POS_CANONICAL.get(key)
        if pos:
            return pos
    return None


def _lex_for_chunk(
    term: str | None, normalized_lemmas: Sequence[str], default: str | None
) -> str | None:
    normalized_term = _normalize_token(term)
    if normalized_term:
        return _lex_anchor(normalized_term)
    for lemma in normalized_lemmas:
        if lemma:
            return _lex_anchor(lemma)
    return default


def _to_cts_urn(ref: str | None) -> str | None:
    """
    Convert Diogenes jump refs (e.g., perseus:abo:phi,0474,003:1:2) to CTS URNs.
    """
    if not ref:
        return None
    ref = ref.strip()
    match = re.match(r"perseus:abo:([a-z]+),([0-9]+),([0-9]+):(.*)", ref)
    if not match:
        return None
    ns_raw, author, work, loc = match.groups()
    ns = "latinLit" if ns_raw.startswith(("phi", "lat")) else "greekLit"
    loc = loc.replace(":", ".")
    return f"urn:cts:{ns}:{ns_raw}{author}.{ns_raw}{work}:{loc}"


def _handle_morphology(soup: BeautifulSoup) -> DiogenesMorphology:
    morphs: list[dict[str, object]] = []
    maybe_morph_els = list(soup.find_all("li"))
    warning: str | None = None
    for tag in soup.find_all("p"):
        if not maybe_morph_els:
            maybe_morph_els.append(tag)
        else:
            _, warning_txt = _extract_parentheses_text(tag.get_text())
            warning = warning_txt or warning
    for tag in maybe_morph_els:
        parsed = _parse_perseus_morph(tag)
        if parsed:
            morphs.append(dict(parsed))
    result: DiogenesMorphology = {"morphs": morphs}
    if warning:
        result["warning"] = warning
    return result


def _process_block(block: Mapping[str, object], soup: BeautifulSoup) -> DiogenesDefinitionBlock:
    block_dict = dict(block)
    for p in soup.select("p"):
        _, warning = _extract_parentheses_text(p.get_text())
        if warning:
            block_dict["diogenes_warning"] = warning.replace("\n", " ")
        p.decompose()

    refs: dict[str, str] = {}
    for ref in soup.select(".origjump"):
        ref_id = " ".join(ref.attrs.get("class", [])).strip("origjump ").lower()
        ref_txt = ref.get_text()
        urn = _to_cts_urn(ref_id)
        refs[urn or ref_id] = ref_txt
    if refs:
        block_dict["citations"] = refs

    block_txt = soup.get_text().strip().rstrip(",")
    block_dict["entry"] = block_txt
    indentid_val = block_dict.get("indentid", "0")
    coords = _find_nd_coordinate(cast(str, indentid_val) if isinstance(indentid_val, str) else "0")
    block_dict["entryid"] = ":".join([str(i).zfill(2) for i in coords]) if coords else "00"
    block_dict.pop("indentid", None)
    block_dict.pop("soup", None)
    return cast(DiogenesDefinitionBlock, block_dict)


def _handle_references(soup: BeautifulSoup) -> DiogenesDefinitions:
    references: DiogenesDefinitions = {}
    for term in soup.select("h2 > span:first-child"):
        references["term"] = term.get_text()  # type: ignore[typeddict-item]
    for term in soup.select("h2"):
        term.decompose()

    blocks: list[dict[str, object]] = []
    indent_history: list[int] = [0]

    def shift_cursor(block: Tag | BeautifulSoup) -> str:
        css_text = str(block.attrs.get("style", ""))
        css_match = re.search(r"padding-left:\s*([\d.]+)", css_text)
        indent = int(css_match.group(1)) if css_match else 0
        indent_history.append(indent)
        return ":".join([str(i).zfill(2) for i in indent_history])

    def insert_block(block: Tag | BeautifulSoup) -> None:
        blocks.append({"indentid": shift_cursor(block), "soup": _make_soup(f"{block}")})

    for block in soup.select("#sense"):
        insert_block(block)
        block.decompose()

    # Root node
    blocks = [{"indentid": "00", "soup": soup}] + blocks
    processed: list[DiogenesDefinitionBlock] = []
    for block in blocks:
        block_soup = block.get("soup")
        if isinstance(block_soup, BeautifulSoup):
            processed_block = _process_block(block, block_soup)
            processed.append(processed_block)
    references["blocks"] = processed
    return references


def _determine_chunk_type(
    is_perseus_analysis: bool, looks_like_header: bool, looks_like_reference: bool, is_fuzzy: bool
) -> str:
    if is_perseus_analysis:
        return "PerseusAnalysisHeader"
    if looks_like_header:
        return "NoMatchFoundHeader"
    if looks_like_reference:
        return "DiogenesFuzzyReference" if is_fuzzy else "DiogenesMatchingReference"
    return "UnknownChunkType"


def _parse_diogenes_html(html: str) -> DiogenesParsedResult:
    """
    Parse diogenes HTML into a structure roughly mirroring codesketch DiogenesScraper output.
    """
    if not html:
        return {"chunks": [], "dg_parsed": False, "chunk_types": []}
    is_fuzzy_overall = (
        "could not find dictionary headword" in html.lower()
        or "showing nearest entry" in html.lower()
    )
    result: DiogenesParsedResult = {
        "chunks": [],
        "dg_parsed": True,
        "chunk_types": [],
        "is_fuzzy_overall": is_fuzzy_overall,
    }
    documents = html.split("<hr />")
    fuzzy_flag = is_fuzzy_overall
    for doc in documents:
        soup = _make_soup(doc)
        looks_like_header = bool(soup.find_all(class_="logeion-link"))
        is_perseus_analysis = any(
            tag.get_text().strip().startswith("Perseus an") for tag in soup.find_all("h1")
        )
        looks_like_reference = bool(soup.find_all("h2"))
        reference_id: str | None = None
        for tag in soup.find_all("a"):
            onclick = str(tag.attrs.get("onclick", ""))
            if onclick.startswith("prevEntry"):
                match = re.search(r"\((\d+)\)", onclick)
                if match:
                    reference_id = match.group(1)
                    looks_like_reference = True
                    break
        chunk_type = _determine_chunk_type(
            is_perseus_analysis, looks_like_header, looks_like_reference, is_fuzzy_overall
        )
        if "chunk_types" not in result:
            result["chunk_types"] = []
        result["chunk_types"].append(chunk_type)
        if chunk_type in {"NoMatchFoundHeader", "DiogenesFuzzyReference"}:
            fuzzy_flag = True

        if chunk_type == "PerseusAnalysisHeader":
            morph = _handle_morphology(soup)
            chunk: DiogenesChunk = {"chunk_type": chunk_type, "morphology": morph}
            result["chunks"].append(chunk)
        elif chunk_type in {"DiogenesMatchingReference", "DiogenesFuzzyReference"}:
            chunk_with_defs: DiogenesChunk = {
                "chunk_type": chunk_type,
                "reference_id": reference_id or "",
                "definitions": _handle_references(soup),
            }
            result["chunks"].append(chunk_with_defs)
        else:
            unknown_chunk: DiogenesChunk = {"chunk_type": chunk_type}
            result["chunks"].append(unknown_chunk)
    result["is_fuzzy_overall"] = fuzzy_flag
    return result


def _extract_lemmas_from_chunks(chunks: Sequence[DiogenesChunk]) -> list[str]:
    """Extract lemmas from parsed Diogenes chunks."""
    lemmas: list[str] = []
    for chunk in chunks:
        if not isinstance(chunk, Mapping):
            continue

        chunk_type = chunk.get("chunk_type")
        if chunk_type == "PerseusAnalysisHeader":
            morph = chunk.get("morphology", {})
            if isinstance(morph, Mapping):
                morphs = morph.get("morphs", [])
                morphs_list = morphs if isinstance(morphs, Sequence) else []
                for entry in morphs_list:
                    if isinstance(entry, Mapping):
                        stem_val = entry.get("stem", [])
                        stems = stem_val if isinstance(stem_val, Sequence) else []
                        normalized_stems = [
                            strip_accents(s).lower() for s in stems if isinstance(s, str)
                        ]
                        lemmas.extend(normalized_stems)
        elif chunk_type in {"DiogenesMatchingReference", "DiogenesFuzzyReference"}:
            definitions = chunk.get("definitions", {})
            if isinstance(definitions, Mapping):
                term = definitions.get("term")
                if isinstance(term, str) and term:
                    lemmas.append(strip_accents(term).lower())
    return lemmas


def _filter_lemmas_by_query(lemmas: list[str], query: str) -> list[str]:
    """Filter lemmas to match query, or return all if no matches."""
    targets = {strip_accents(query).lower()} if query else set()
    if targets:
        filtered = [lemma for lemma in lemmas if strip_accents(lemma).lower() in targets]
        return filtered or lemmas
    return lemmas


def _parse_fallback_lemmas(body: bytes) -> list[str]:
    """
    Fallback lemma parsing from HTML body.
    Extracts lemmas from <i>, <b>, <em>, <strong> tags or Lemma: patterns.
    """
    lemmas: list[str] = []
    try:
        soup = BeautifulSoup(body, "html.parser")
        # Common diogenes parse pages have lemmas in <i> or bold tags.
        for tag in soup.find_all(["i", "b", "em", "strong"]):
            text = (tag.get_text() or "").strip()
            if text and re.match(r"^[A-Za-z]+$", text):
                lemmas.append(text.lower())
        if not lemmas:
            text = soup.get_text(" ", strip=True)
            candidates = re.findall(r"Lemma[:\\s]+([A-Za-z]+)", text, flags=re.IGNORECASE)
            lemmas.extend([c.lower() for c in candidates])
    except Exception:
        pass
    # Deduplicate while preserving order
    seen: set[str] = set()
    out: list[str] = []
    for lemma in lemmas:
        if lemma not in seen:
            seen.add(lemma)
            out.append(lemma)
    return out


@versioned("v1")
def extract_html(call: ToolCallSpec, raw: RawResponseEffect) -> ExtractionEffect:
    """
    Parse Diogenes HTML directly (no refetch) to extract lemmas and definitions.
    """
    html = raw.body.decode("utf-8", errors="ignore")
    parsed = _parse_diogenes_html(html)

    chunks_val = parsed.get("chunks")
    chunks = chunks_val if isinstance(chunks_val, Sequence) else []
    lemmas = _extract_lemmas_from_chunks(chunks)
    if not lemmas:
        lemmas = _parse_fallback_lemmas(raw.body)

    query = call.params.get("q", "") or call.params.get("word", "")
    lemmas = _filter_lemmas_by_query(lemmas, query)
    canonical = lemmas[0] if lemmas else None
    return ExtractionEffect(
        extraction_id=stable_effect_id("dio-ext", call.call_id, raw.response_id),
        tool=call.tool,
        call_id=call.call_id,
        source_call_id=call.params.get("source_call_id", ""),
        response_id=raw.response_id,
        kind="diogenes.html",
        canonical=canonical,
        payload={"lemmas": lemmas, "parsed": parsed, "raw_html": html},
    )


@versioned("v1")
def derive_morph(call: ToolCallSpec, extraction: ExtractionEffect) -> DerivationEffect:
    prov = [
        ProvenanceLink(
            stage="extract",
            tool=extraction.tool,
            reference_id=extraction.extraction_id,
            metadata={"response_id": extraction.response_id},
        )
    ]
    lemmas: Sequence[str] = []
    payload: Mapping[str, object] | None = None
    raw_html: str | None = None
    if isinstance(extraction.payload, Mapping):
        ext_payload = cast(dict[str, object], extraction.payload)
        lemmas_val = ext_payload.get("lemmas")
        lemmas = cast(Sequence[str], lemmas_val) if isinstance(lemmas_val, Sequence) else []
        payload_val = ext_payload.get("parsed")
        if isinstance(payload_val, Mapping):
            payload = cast(Mapping[str, object], payload_val)
        else:
            payload = None
        raw_html_val = ext_payload.get("raw_html")
        raw_html = raw_html_val if isinstance(raw_html_val, str) else None
    return DerivationEffect(
        derivation_id=stable_effect_id("dio-der", call.call_id, extraction.extraction_id),
        tool=call.tool,
        call_id=call.call_id,
        source_call_id=call.params.get("source_call_id", ""),
        extraction_id=extraction.extraction_id,
        kind="diogenes.morph",
        canonical=extraction.canonical,
        payload={"lemmas": list(lemmas), "parsed": payload, "raw_html": raw_html},
        provenance_chain=prov,
    )


def _build_perseus_header_triples(
    morph: Mapping[str, object],
    default_lex: str | None,
    base_evidence: Mapping[str, object],
) -> list[dict[str, object]]:
    """Build triples from Perseus morphology analysis header."""
    triples: list[dict[str, object]] = []
    morph_dict = cast(dict[str, object], morph)
    entries_val = morph_dict.get("morphs")
    entries = entries_val if isinstance(entries_val, Sequence) else []
    for entry in entries:
        if not isinstance(entry, Mapping):
            continue
        entry_dict = cast(dict[str, object], entry)
        stem_val = entry_dict.get("stem")
        if isinstance(stem_val, Sequence):
            stems = [s for s in stem_val if isinstance(s, str)]
        else:
            stems = []
        tags_val = entry_dict.get("tags")
        tags = [t for t in tags_val if isinstance(t, str)] if isinstance(tags_val, Sequence) else []
        defs_val = entry_dict.get("defs")
        defs = [d for d in defs_val if isinstance(d, str)] if isinstance(defs_val, Sequence) else []
        pos = _normalize_pos(tags)
        for stem in stems:
            normalized_stem = _normalize_token(stem)
            if not normalized_stem:
                continue
            form_anchor = _form_anchor(normalized_stem)
            if default_lex:
                triples.append(
                    _make_triple(form_anchor, "inflection_of", default_lex, base_evidence)
                )
            triples.append(_make_triple(form_anchor, "has_form", stem, base_evidence))
            if pos:
                triples.append(_make_triple(form_anchor, "has_pos", pos, base_evidence))
            if tags:
                triples.append(
                    _make_triple(form_anchor, "has_feature", {"tags": tags}, base_evidence)
                )
            if defs:
                triples.append(
                    _make_triple(form_anchor, "has_feature", {"defs": defs}, base_evidence)
                )
    return triples


def _build_definition_triples(
    definitions: Mapping[str, object],
    normalized_lemmas: list[str],
    default_lex: str | None,
    base_evidence: Mapping[str, object],
) -> list[dict[str, object]]:
    """Build triples from Diogenes lexical definitions."""
    triples: list[dict[str, object]] = []
    defs_dict = cast(dict[str, object], definitions)
    term_val = defs_dict.get("term")
    term = term_val if isinstance(term_val, str) else None
    lex_anchor = _lex_for_chunk(term, normalized_lemmas, default_lex)
    blocks_val = defs_dict.get("blocks")
    blocks = blocks_val if isinstance(blocks_val, Sequence) else []
    if not lex_anchor:
        return triples

    for block in blocks:
        if not isinstance(block, Mapping):
            continue
        block_dict = cast(dict[str, object], block)
        entry_txt = block_dict.get("entry")
        if isinstance(entry_txt, str):
            gloss = entry_txt.strip()
            if gloss:
                sense_anchor = _sense_anchor(lex_anchor, gloss)
                triples.append(_make_triple(lex_anchor, "has_sense", sense_anchor, base_evidence))
                triples.append(_make_triple(sense_anchor, "gloss", gloss, base_evidence))

        citations = block_dict.get("citations")
        if isinstance(citations, Mapping):
            for ref_class, ref_text in citations.items():
                if not isinstance(ref_class, str) or not isinstance(ref_text, str):
                    continue
                ref_txt = ref_text.strip()
                if not ref_txt:
                    continue
                urn = _to_cts_urn(ref_class)
                obj = urn or ref_txt
                triples.append(
                    {
                        "subject": lex_anchor,
                        "predicate": "has_citation",
                        "object": obj,
                        "metadata": {
                            "evidence": _trim_evidence(dict(base_evidence)),
                            "citation_text": ref_txt,
                            "citation_ref": ref_class,
                        },
                    }
                )
    return triples


def _build_triples(
    parsed: Mapping[str, object] | None, lemmas: Sequence[str], base_evidence: Mapping[str, object]
) -> list[dict[str, object]]:
    """Build RDF-style triples from Diogenes parsed data."""
    if not isinstance(parsed, Mapping):
        return []

    triples: list[dict[str, object]] = []
    normalized_lemmas = [
        n for lemma in lemmas if isinstance(lemma, str) if (n := _normalize_token(lemma))
    ]
    default_lex = _lex_anchor(normalized_lemmas[0]) if normalized_lemmas else None
    parsed_dict = cast(dict[str, object], parsed)
    chunks = parsed_dict.get("chunks")

    if not isinstance(chunks, Sequence):
        return triples

    for chunk in chunks:
        if not isinstance(chunk, Mapping):
            continue
        chunk_dict = cast(dict[str, object], chunk)

        chunk_type = chunk_dict.get("chunk_type")
        if chunk_type == "PerseusAnalysisHeader":
            morph = chunk_dict.get("morphology")
            if isinstance(morph, Mapping):
                morph_typed = cast(Mapping[str, object], morph)
                perseus_triples = _build_perseus_header_triples(
                    morph_typed, default_lex, base_evidence
                )
                triples.extend(perseus_triples)
        elif chunk_type in {"DiogenesMatchingReference", "DiogenesFuzzyReference"}:
            definitions = chunk_dict.get("definitions")
            if isinstance(definitions, Mapping):
                defs_typed = cast(Mapping[str, object], definitions)
                triples.extend(
                    _build_definition_triples(
                        defs_typed, normalized_lemmas, default_lex, base_evidence
                    )
                )

    return triples


@versioned("v1")
def claim_morph(call: ToolCallSpec, derivation: DerivationEffect) -> ClaimEffect:
    prov = derivation.provenance_chain[:] if derivation.provenance_chain else []
    prov.append(
        ProvenanceLink(
            stage="derive",
            tool=derivation.tool,
            reference_id=derivation.derivation_id,
            metadata={"extraction_id": derivation.extraction_id},
        )
    )
    claim_id = stable_effect_id("dio-clm", call.call_id, derivation.derivation_id)
    subject = derivation.canonical or call.call_id
    value = derivation.payload if isinstance(derivation.payload, Mapping) else {"lemmas": []}
    base_evidence = _make_base_evidence(call, derivation, claim_id)
    triples: list[dict[str, object]] = []
    if isinstance(value, Mapping):
        value_dict = cast(dict[str, object], value)
        parsed_val = value_dict.get("parsed")
        parsed = cast(Mapping[str, object], parsed_val) if isinstance(parsed_val, Mapping) else None
        lemmas_val = value_dict.get("lemmas")
        lemmas_list = cast(Sequence[str], lemmas_val) if isinstance(lemmas_val, Sequence) else []
        triples = _build_triples(parsed, lemmas_list, base_evidence)
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
