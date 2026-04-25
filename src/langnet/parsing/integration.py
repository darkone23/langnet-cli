"""Integration helpers for using entry parsers with existing handlers."""

from __future__ import annotations

import re
from collections.abc import Sequence
from typing import TypedDict

from bs4 import BeautifulSoup

from langnet.parsing.cltk_normalizer import normalize_cltk_lewis_line
from langnet.parsing.diogenes_parser import DiogenesEntryParser, ParsedEntry
from langnet.parsing.french_parser import parse_french_glosses, parse_gaffiot_entry


class CleanedEntryHeader(TypedDict, total=False):
    """Cleaned entry header data for use in handlers."""

    lemma: str
    principal_parts: list[str]
    pos: str | None
    gender: str | None
    root: str | None
    parse_success: bool


def extract_diogenes_header_from_html(html_block: str) -> CleanedEntryHeader | None:
    """
    Extract clean entry header from Diogenes HTML block.

    This function:
    1. Extracts text from the HTML entry header
    2. Parses it with the Lark grammar
    3. Returns structured header data

    Args:
        html_block: Raw HTML block containing entry header

    Returns:
        CleanedEntryHeader if parsing succeeds, None otherwise

    Example:
        >>> html = '<h2><span>lupus, -i, m.</span></h2>'
        >>> header = extract_diogenes_header_from_html(html)
        >>> header['lemma']
        'lupus'
    """
    try:
        soup = BeautifulSoup(html_block, "lxml")
        # Try common Diogenes header patterns
        header_text = None

        # Pattern 1: Full <h2> text (includes principal parts, gender, etc.)
        # e.g., <h2><span>lupus</span>, i, m.</h2> -> "lupus, i, m."
        h2 = soup.find("h2")
        if h2:
            header_text = h2.get_text().strip()

        # Pattern 2: Just the span text (fallback for malformed HTML)
        if not header_text:
            h2_span = soup.select_one("h2 > span:first-child")
            if h2_span:
                header_text = h2_span.get_text().strip()

        if not header_text:
            return None

        # Parse with Lark grammar
        parser = DiogenesEntryParser()
        parsed = parser.parse_safe(header_text)

        if not parsed or "header" not in parsed:
            return None

        header_data = parsed["header"]
        return {
            "lemma": header_data.get("lemma", ""),
            "principal_parts": header_data.get("principal_parts", []),
            "pos": header_data.get("pos"),
            "gender": header_data.get("gender"),
            "root": header_data.get("root"),
            "parse_success": True,
        }

    except Exception:
        return None


def enrich_extraction_with_parsed_header(extraction_payload: dict, html: str) -> dict:
    """
    Enrich extraction payload with parsed header data.

    Takes existing extraction payload from handler and adds
    cleaned header fields from grammar parsing.

    Args:
        extraction_payload: Existing payload from extract handler
        html: Raw HTML response

    Returns:
        Updated payload with 'parsed_header' field if parsing succeeds

    Example:
        >>> payload = {"lemmas": ["lupus"], "parsed": {...}}
        >>> enriched = enrich_extraction_with_parsed_header(payload, html)
        >>> enriched['parsed_header']['lemma']
        'lupus'
    """
    header = extract_diogenes_header_from_html(html)

    if header:
        return {**extraction_payload, "parsed_header": header}

    return extraction_payload


def strip_latin_enclitics(word: str) -> str:
    """
    Strip Latin enclitic particles from word.

    Handles common enclitics: -que (and), -ve (or), -ne (question).

    Args:
        word: Latin word possibly ending with enclitic

    Returns:
        Word with enclitic stripped if present, otherwise original word

    Example:
        >>> strip_latin_enclitics("albanique")
        'albani'
        >>> strip_latin_enclitics("adventumque")
        'adventum'
        >>> strip_latin_enclitics("lupus")
        'lupus'
    """
    # Strip -que, -ve, -ne if they appear at word end
    # Use word boundary to ensure we're matching the suffix
    stripped = re.sub(r"(que|ve|ne)$", "", word, flags=re.IGNORECASE)

    # Only return stripped version if something was actually removed
    # and the result is not empty
    if stripped and stripped != word:
        return stripped

    return word


def extract_lemma_fallback(text: str) -> str | None:
    """
    Extract lemma from dictionary entry using simple regex (fallback).

    Used when full grammar parsing fails but we still want to preserve
    at least the headword/lemma from the entry.

    Args:
        text: Normalized dictionary entry text

    Returns:
        Extracted lemma or None if extraction fails

    Example:
        >>> extract_lemma_fallback("lupus, -i, m.")
        'lupus'
        >>> extract_lemma_fallback("amo, amare, amavi")
        'amo'
    """
    # Try to extract the first word (before comma or space)
    # This handles most Lewis & Short entries where lemma comes first
    match = re.match(r"^([a-zA-ZāēīōūăĕĭŏŭæœëÄäÖöÜü-]+)", text.strip())

    if match:
        lemma = match.group(1).strip().rstrip(",.-")
        # Ensure we got something meaningful
        if lemma and len(lemma) > 1:
            return lemma

    return None


def parse_lewis_lines(
    lewis_lines: Sequence[str], query_word: str | None = None
) -> list[ParsedEntry]:
    """
    Parse Lewis & Short dictionary lines from CLTK.

    This function now includes automatic normalization to handle real CLTK format.
    CLTK uses macrons, irregular spacing, and different structure than the standard
    Diogenes format. The normalizer preprocesses CLTK data to make it compatible.

    Real CLTK format (automatically normalized):
        "lupus\\n\\n\\n ī, \\nm\\n\\n a wolf: Torva leaena..."
        → normalized to → "lupus, -i, m."

    Expected format (also works):
        "lupus, -i, m. I. a wolf"

    Args:
        lewis_lines: List of Lewis & Short dictionary entry strings
        query_word: Original query word (for fallback when no data available)

    Returns:
        List of ParsedEntry objects (one per successfully parsed line)
        If all parsing fails but query_word provided, returns minimal entry with lemma

    Example:
        >>> lines = ["lupus, -i, m. I. a wolf", "amo, amare, amavi, amatum, v."]
        >>> parsed = parse_lewis_lines(lines)
        >>> len(parsed)
        2
        >>> parsed[0]["header"]["lemma"]
        'lupus'
    """
    parser = DiogenesEntryParser()
    parsed_entries: list[ParsedEntry] = []

    for line in lewis_lines:
        if not isinstance(line, str) or not line.strip():
            continue

        # Normalize CLTK format to Diogenes-compatible format
        normalized = normalize_cltk_lewis_line(line.strip())

        # Try parsing with Diogenes grammar
        entry = parser.parse_safe(normalized)
        if entry:
            parsed_entries.append(entry)
        else:
            # Partial data preservation: try to extract at least the lemma
            lemma = extract_lemma_fallback(normalized)
            if lemma:
                # Return minimal entry with extracted lemma
                fallback_entry: ParsedEntry = {
                    "header": {
                        "lemma": lemma,
                        "principal_parts": [],
                        "pos": None,
                        "gender": None,
                        "root": None,
                    }
                }
                parsed_entries.append(fallback_entry)

    # Fallback: If no entries parsed but we have a query word, return minimal entry
    if not parsed_entries and query_word:
        # Try stripping Latin enclitics (-que, -ve, -ne) to get base form
        # e.g., "albanique" → "albani", "adventumque" → "adventum"
        lemma = strip_latin_enclitics(query_word)

        # Return minimal entry with the (possibly stripped) lemma
        fallback_entry: ParsedEntry = {
            "header": {
                "lemma": lemma,
                "principal_parts": [],
                "pos": None,
                "gender": None,
                "root": None,
            }
        }
        parsed_entries.append(fallback_entry)

    return parsed_entries


def enrich_cltk_with_parsed_lewis(
    cltk_payload: dict,
) -> dict:
    """
    Enrich CLTK extraction payload with parsed Lewis & Short entries.

    Takes existing CLTK payload and parses lewis_lines into structured
    data using the Lewis & Short grammar. Includes fallback to return
    at least the query word when dictionary data is unavailable.

    Args:
        cltk_payload: Existing payload from CLTK extract handler

    Returns:
        Updated payload with 'parsed_lewis' field

    Example:
        >>> payload = {"lemma": "lupus", "lewis_lines": ["lupus, -i, m. I. a wolf"]}
        >>> enriched = enrich_cltk_with_parsed_lewis(payload)
        >>> enriched['parsed_lewis'][0]['header']['lemma']
        'lupus'
    """
    lewis_lines = cltk_payload.get("lewis_lines", [])
    query_word = cltk_payload.get("word") or cltk_payload.get("lemma")

    # Always try to parse, even if lewis_lines is empty (fallback will handle it)
    parsed = parse_lewis_lines(lewis_lines, query_word=query_word)

    if parsed:
        return {**cltk_payload, "parsed_lewis": parsed}

    return cltk_payload


def parse_heritage_french_definitions(dictionary_url: str | None, html: str) -> list[str]:
    """
    Extract French definitions from Heritage dictionary URLs/HTML.

    Heritage provides French lexicon definitions in dictionary_url fields
    or embedded in HTML. This extracts and parses those French glosses.

    Args:
        dictionary_url: URL to Heritage French dictionary entry
        html: Raw HTML containing French definitions

    Returns:
        List of French gloss strings

    Example:
        >>> parse_heritage_french_definitions(None, "<div>amour, passion</div>")
        ['amour', 'passion']
    """
    # For now, use simple extraction from HTML
    # TODO: Fetch and parse dictionary_url if provided
    if not html:
        return []

    soup = BeautifulSoup(html, "lxml")

    # Extract text from common French definition patterns
    # Heritage often has definitions in <div> or <span> tags
    text_content = soup.get_text(" ", strip=True)

    if text_content:
        return parse_french_glosses(text_content)

    return []


def enrich_gaffiot_with_parsed_french(entry_data: dict) -> dict:
    """
    Enrich Gaffiot entry data with parsed French glosses.

    Takes raw Gaffiot entry and parses the plain_text field into
    structured French glosses.

    Args:
        entry_data: Dict with 'headword_raw' and 'plain_text' fields

    Returns:
        Updated dict with 'parsed_french' field

    Example:
        >>> entry = {"headword_raw": "amor", "plain_text": "ardor, caritas"}
        >>> enriched = enrich_gaffiot_with_parsed_french(entry)
        >>> enriched['parsed_french']['glosses']
        ['ardor', 'caritas']
    """
    headword = entry_data.get("headword_raw", "")
    plain_text = entry_data.get("plain_text", "")

    if not plain_text:
        return entry_data

    parsed = parse_gaffiot_entry(headword, plain_text)

    return {**entry_data, "parsed_french": parsed}


def enrich_heritage_with_french_glosses(heritage_payload: dict) -> dict:
    """
    Enrich Heritage payload with parsed French lexicon glosses.

    Extracts French definitions from Heritage analyses and parses them
    into structured glosses.

    Args:
        heritage_payload: Heritage extraction/derivation payload

    Returns:
        Updated payload with 'french_glosses' in analyses

    Example:
        >>> payload = {"analyses": [{"dictionary_url": "..."}]}
        >>> enriched = enrich_heritage_with_french_glosses(payload)
    """
    analyses = heritage_payload.get("analyses", [])
    if not analyses or not isinstance(analyses, Sequence):
        return heritage_payload

    enriched_analyses = []
    for analysis in analyses:
        if not isinstance(analysis, dict):
            enriched_analyses.append(analysis)
            continue

        dictionary_url = analysis.get("dictionary_url")
        # For now, we don't have HTML to parse
        # This is a placeholder for future French lexicon integration
        enriched_analysis = {**analysis}

        if dictionary_url:
            # TODO: Fetch and parse French lexicon from dictionary_url
            enriched_analysis["has_french_lexicon_url"] = True

        enriched_analyses.append(enriched_analysis)

    return {**heritage_payload, "analyses": enriched_analyses}
