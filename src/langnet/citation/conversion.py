"""
Citation conversion utilities for backward compatibility.

This module provides functions to convert between old citation formats
and the new standardized Citation schema.
"""

from typing import Dict, List, Any

from langnet.citation.models import Citation, CitationCollection, CitationType, TextReference


def convert_diogenes_citations_to_new_format(old_citations: Dict[str, str]) -> CitationCollection:
    """
    Convert old Diogenes citation format (dict[str, str]) to new CitationCollection.

    Args:
        old_citations: Dictionary mapping Perseus URN to citation text

    Returns:
        CitationCollection with standardized citations
    """
    if not old_citations:
        return CitationCollection(citations=[])

    converted_citations = []

    for urn, citation_text in old_citations.items():
        text_reference = TextReference(
            type=CitationType.LINE_REFERENCE,
            text=citation_text,
            work="",  # Will be parsed from citation text
            author="",  # Will be parsed from citation text
            book="",  # Will be parsed from citation text
            line="",  # Will be parsed from citation text
        )

        citation = Citation(
            references=[text_reference],
            short_title=citation_text.split()[0] if citation_text else None,
            description=f"Perseus reference: {urn}",
        )
        converted_citations.append(citation)

    return CitationCollection(citations=converted_citations)


def convert_cdsl_references_to_new_format(
    old_references: List[Dict[str, Any]],
) -> CitationCollection:
    """
    Convert old CDSL references format (list[dict]) to new CitationCollection.

    Args:
        old_references: List of reference dictionaries from CDSL

    Returns:
        CitationCollection with standardized citations
    """
    if not old_references:
        return CitationCollection(citations=[])

    converted_citations = []

    for ref in old_references:
        # Extract common fields from CDSL reference
        citation_text = ref.get("text", "")
        dictionary = ref.get("dictionary", "")
        page = ref.get("page", "")

        if citation_text:
            text_reference = TextReference(
                type=CitationType.DICTIONARY_ABBREVIATION,
                text=citation_text,
                work=dictionary,
                page=page if page else None,
            )

            citation = Citation(
                references=[text_reference],
                short_title=dictionary,
                description=f"CDSL reference from {dictionary}",
            )
            converted_citations.append(citation)

    return CitationCollection(citations=converted_citations)


def convert_collection_to_diogenes_format(
    citation_collection: CitationCollection,
) -> Dict[str, str]:
    """
    Convert CitationCollection back to old Diogenes format for backward compatibility.

    Args:
        citation_collection: New format citation collection

    Returns:
        Dictionary in old Diogenes format
    """
    result = {}

    for citation in citation_collection.citations:
        # For backward compatibility, use citation description as key and get primary reference text as value
        if citation.references:
            primary_ref = citation.references[0]
            result[citation.description or "unknown"] = primary_ref.text

    return result


def convert_collection_to_cdsl_format(
    citation_collection: CitationCollection,
) -> List[Dict[str, Any]]:
    """
    Convert CitationCollection back to old CDSL format for backward compatibility.

    Args:
        citation_collection: New format citation collection

    Returns:
        List of dictionaries in old CDSL format
    """
    result = []

    for citation in citation_collection.citations:
        if citation.references:
            primary_ref = citation.references[0]
            ref_dict = {
                "text": primary_ref.text,
                "dictionary": citation.short_title or "Unknown",
                "page": primary_ref.page or "",
                "type": "reference",
            }
            result.append(ref_dict)

    return result


def is_legacy_diogenes_citations(citations: Any) -> bool:
    """
    Check if citations are in old Diogenes format.

    Args:
        citations: Field to check

    Returns:
        True if old format, False if new format
    """
    return isinstance(citations, dict)


def is_legacy_cdsl_references(references: Any) -> bool:
    """
    Check if references are in old CDSL format.

    Args:
        references: Field to check

    Returns:
        True if old format, False if new format
    """
    return isinstance(references, list) and len(references) > 0 and isinstance(references[0], dict)
