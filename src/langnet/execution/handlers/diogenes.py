from __future__ import annotations

import re
from typing import Mapping, Sequence

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
from langnet.diogenes.parse_adapter import DiogenesParseAdapter
from langnet.normalizer.utils import strip_accents


_PARSER_PREFERENCE = ("lxml", "html5lib", "html.parser")
PERSEUS_MORPH_PART_COUNT = 2


def _make_soup(html: str) -> BeautifulSoup:
    for parser in _PARSER_PREFERENCE:
        try:
            return BeautifulSoup(html, parser)
        except Exception:
            continue
    return BeautifulSoup(html, "html.parser")


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


def _handle_morphology(soup: BeautifulSoup) -> Mapping[str, object]:
    morphs: list[Mapping[str, object]] = []
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
            morphs.append(parsed)
    payload: dict[str, object] = {"morphs": morphs}
    if warning:
        payload["warning"] = warning
    return payload


def _determine_chunk_type(is_perseus_analysis: bool, looks_like_header: bool, looks_like_reference: bool) -> str:
    if is_perseus_analysis:
        return "PerseusAnalysisHeader"
    if looks_like_header:
        return "NoMatchFoundHeader"
    if looks_like_reference:
        return "DiogenesMatchingReference"
    return "UnknownChunkType"


def _parse_diogenes_html(html: str) -> Mapping[str, object]:
    """
    Parse diogenes HTML into a structure roughly mirroring codesketch DiogenesScraper output.
    """
    result: dict[str, object] = {"chunks": [], "dg_parsed": True, "chunk_types": []}
    documents = html.split("<hr />") if html else [html]
    for doc in documents:
        soup = _make_soup(doc)
        looks_like_header = bool(soup.find_all(class_="logeion-link"))
        is_perseus_analysis = any(tag.get_text().strip().startswith("Perseus an") for tag in soup.find_all("h1"))
        looks_like_reference = False
        reference_id: str | None = None
        for tag in soup.find_all("a"):
            onclick = str(tag.attrs.get("onclick", ""))
            if onclick.startswith("prevEntry"):
                match = re.search(r"\((\d+)\)", onclick)
                if match:
                    reference_id = match.group(1)
                    looks_like_reference = True
                    break
        chunk_type = _determine_chunk_type(is_perseus_analysis, looks_like_header, looks_like_reference)
        result["chunk_types"].append(chunk_type)

        if chunk_type == "PerseusAnalysisHeader":
            morph = _handle_morphology(soup)
            result["chunks"].append({"chunk_type": chunk_type, "morphology": morph})
        elif chunk_type in {"DiogenesMatchingReference", "DiogenesFuzzyReference"}:
            blocks: list[Mapping[str, object]] = []
            term = ""
            for heading in soup.select("h2 > span:first-child"):
                term = heading.get_text()
            for heading in soup.select("h2"):
                heading.decompose()
            indent_history = [0]

            def shift_cursor(block) -> str:
                css_text = str(block.attrs.get("style", ""))
                css_match = re.search(r"padding-left:\s*([\d.]+)", css_text)
                indent = int(css_match.group(1)) if css_match else 0
                indent_history.append(indent)
                return ":".join([str(i).zfill(2) for i in indent_history])

            def insert_block(block):
                blocks.append({"indentid": shift_cursor(block), "soup": _make_soup(f"{block}")})

            for block in soup.select("#sense"):
                insert_block(block)
                block.decompose()

            blocks = [{"indentid": "00", "soup": soup}] + blocks
            for block in blocks:
                block_soup = block.pop("soup", None)
                if not block_soup:
                    continue
                block_txt = block_soup.get_text().strip().rstrip(",")
                block["entry"] = block_txt
                block["entryid"] = block.pop("indentid", "00")
                refs: dict[str, str] = {}
                for ref in block_soup.select(".origjump"):
                    ref_id = " ".join(ref.attrs.get("class", [])).strip("origjump ").lower()
                    refs[ref_id] = ref.get_text()
                if refs:
                    block["citations"] = refs
            result["chunks"].append(
                {
                    "chunk_type": chunk_type,
                    "reference_id": reference_id or "",
                    "definitions": {"term": term, "blocks": blocks},
                }
            )
        else:
            result["chunks"].append({"chunk_type": chunk_type})
    return result


def extract_html(call: ToolCallSpec, raw: RawResponseEffect) -> ExtractionEffect:
    """
    Parse Diogenes HTML directly (no refetch) using the adapter's parser to pull lemmas.
    """
    adapter = DiogenesParseAdapter(client=None, raw_index=None, extraction_index=None, endpoint="")
    html = raw.body.decode("utf-8", errors="ignore")
    parsed = _parse_diogenes_html(html)
    lemmas: list[str] = []
    for chunk in parsed.get("chunks", []):  # type: ignore[assignment]
        if not isinstance(chunk, Mapping):
            continue
        if chunk.get("chunk_type") == "PerseusAnalysisHeader":
            morph = chunk.get("morphology", {})
            if isinstance(morph, Mapping):
                for entry in morph.get("morphs", []) or []:
                    if isinstance(entry, Mapping):
                        lemmas.extend([strip_accents(s).lower() for s in entry.get("stem", []) or []])
        elif chunk.get("chunk_type") in {"DiogenesMatchingReference", "DiogenesFuzzyReference"}:
            definitions = chunk.get("definitions", {})
            if isinstance(definitions, Mapping):
                term = definitions.get("term")
                if isinstance(term, str) and term:
                    lemmas.append(strip_accents(term).lower())
    if not lemmas:
        lemmas = adapter._parse_lemmas(raw.body)  # type: ignore[attr-defined]
    query = call.params.get("q", "") or call.params.get("word", "")
    targets = {strip_accents(query).lower()} if query else set()
    if targets:
        filtered = [l for l in lemmas if strip_accents(l).lower() in targets]
        lemmas = filtered or lemmas
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
    payload: Mapping[str, object] | Sequence[object] | None = None
    if isinstance(extraction.payload, Mapping):
        lemmas = extraction.payload.get("lemmas", []) or []
        payload = {
            "parsed": extraction.payload.get("parsed"),
            "raw_html": extraction.payload.get("raw_html"),
        }
    return DerivationEffect(
        derivation_id=stable_effect_id("dio-der", call.call_id, extraction.extraction_id),
        tool=call.tool,
        call_id=call.call_id,
        source_call_id=call.params.get("source_call_id", ""),
        extraction_id=extraction.extraction_id,
        kind="diogenes.morph",
        canonical=extraction.canonical,
        payload={"lemmas": list(lemmas), "parsed": payload},
        provenance_chain=prov,
    )


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
    subject = derivation.canonical or call.call_id
    value = derivation.payload if isinstance(derivation.payload, Mapping) else {"lemmas": []}
    return ClaimEffect(
        claim_id=stable_effect_id("dio-clm", call.call_id, derivation.derivation_id),
        tool=call.tool,
        call_id=call.call_id,
        source_call_id=call.params.get("source_call_id", ""),
        derivation_id=derivation.derivation_id,
        subject=subject,
        predicate="has_lemmas",
        value=value,
        provenance_chain=prov,
    )
