"""
CDSL citation extractor.

This extractor converts CDSL-specific citation formats to standardized
Citation objects.
"""

import re
from typing import List, Dict, Any, Optional
from .base import BaseCitationExtractor
from ..models import Citation, CitationCollection, TextReference, CitationType


class CDSLCitationExtractor(BaseCitationExtractor):
    """Citation extractor for CDSL responses."""

    def __init__(self):
        super().__init__(language="san")  # CDSL handles Sanskrit

    def can_extract(self, data: Any) -> bool:
        """Check if data is from CDSL (has references list)."""
        if isinstance(data, dict):
            return "references" in data and isinstance(data["references"], list)

        # Also check for CDSL-specific structures
        if hasattr(data, "__dict__"):
            return hasattr(data, "references") and isinstance(data.references, list)

        return False

    def extract(self, data: Any) -> CitationCollection:
        """Extract citations from CDSL response data."""
        # Handle dict vs object data
        if isinstance(data, dict):
            query = data.get("term", data.get("iast", "unknown"))
        else:
            query = getattr(data, "term", getattr(data, "iast", "unknown"))

        collection = self.create_collection(query=query, source="cdsl")

        references_list = self._get_references_list(data)
        if not references_list:
            return collection

        for ref_data in references_list:
            citation = self._extract_reference(ref_data)
            if citation:
                collection.add_citation(citation)

        return collection

    def _get_references_list(self, data: Any) -> List[Dict[str, str]]:
        """Extract references list from various data formats."""
        if isinstance(data, dict):
            return data.get("references", [])
        elif hasattr(data, "references"):
            return data.references or []
        return []

    def _extract_reference(self, ref_data: Dict[str, str]) -> Optional[Citation]:
        """Convert a single CDSL reference to Citation object."""
        source_text = ref_data.get("source", "").strip()
        ref_type = ref_data.get("type", "lexicon")

        if not source_text:
            return None

        # Parse the reference text based on type
        if ref_type == "lexicon":
            return self._extract_lexicon_reference(source_text)
        elif ref_type == "cross_reference":
            return self._extract_cross_reference(source_text)
        else:
            # Unknown type, create generic reference
            return self._create_generic_reference(source_text, ref_type)

    def _extract_lexicon_reference(self, source_text: str) -> Optional[Citation]:
        """Extract lexicon reference (e.g., "L.", "MW", "Böhtlingk")."""
        # Common lexicon abbreviations
        lexicon_info = {
            "L.": {
                "full_name": "Monier-Williams Sanskrit-English Dictionary",
                "description": "Comprehensive Sanskrit-English dictionary",
                "date": "1899",
            },
            "MW": {
                "full_name": "Monier-Williams Sanskrit-English Dictionary",
                "description": "Comprehensive Sanskrit-English dictionary",
                "date": "1899",
            },
            "Böhtlingk": {
                "full_name": "Sanskrit-Wörterbuch in kürzerer Fassung",
                "description": "Sanskrit-German dictionary",
                "date": "1855-1875",
            },
            "Gérard": {
                "full_name": "Dictionnaire sanskrit-français",
                "description": "Sanskrit-French dictionary",
                "date": "1858",
            },
            "Apte": {
                "full_name": "The Practical Sanskrit-English Dictionary",
                "description": "Practical Sanskrit-English dictionary",
                "date": "1890",
            },
        }

        # Check if source_text matches known lexicons
        for abb, info in lexicon_info.items():
            if source_text.startswith(abb):
                # Create dictionary abbreviation citation
                text_ref = self.create_text_reference(
                    CitationType.DICTIONARY_ABBREVIATION,
                    source_text,
                    work=abb,
                    page=self._extract_page_number(source_text),
                )

                return self.create_citation(
                    references=[text_ref],
                    abbreviation=abb,
                    full_name=info["full_name"],
                    description=info["description"],
                    date=info["date"],
                )

        # Unknown lexicon, create generic reference
        return self._create_generic_reference(source_text, "lexicon")

    def _extract_cross_reference(self, source_text: str) -> Optional[Citation]:
        """Extract cross-reference (e.g., "cf. agni", "→ fire")."""
        # Parse cross-reference patterns
        patterns = [
            # "cf. term"
            r"cf\.\s+(.+)",
            # "→ term"
            r"→\s+(.+)",
            # Simple term reference
            r"(.+)",
        ]

        for pattern in patterns:
            match = re.match(pattern, source_text.strip())
            if match:
                term = match.group(1)
                text_ref = self.create_text_reference(
                    CitationType.CROSS_REFERENCE, source_text, work=term
                )

                return self.create_citation(
                    references=[text_ref],
                    abbreviation="cf.",
                    full_name="Cross-reference",
                    description=f"Cross-reference to {term}",
                )

        return None

    def _create_generic_reference(self, source_text: str, ref_type: str) -> Optional[Citation]:
        """Create a generic reference for unknown types."""
        text_ref = self.create_text_reference(
            CitationType.LEXICON_REFERENCE, source_text, work=ref_type
        )

        return self.create_citation(
            references=[text_ref],
            abbreviation=ref_type,
            full_name=f"{ref_type.title()} Reference",
            description=f"Reference to {ref_type}",
        )

    def _extract_page_number(self, source_text: str) -> Optional[str]:
        """Extract page number from reference text (e.g., "L. 127")."""
        # Look for page numbers at the end
        match = re.search(r"(\d+)$", source_text.strip())
        return match.group(1) if match else None
