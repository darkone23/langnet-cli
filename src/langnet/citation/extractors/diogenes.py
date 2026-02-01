"""
Diogenes citation extractor.

This extractor converts Diogenes-specific citation formats to standardized
Citation objects.
"""

import re
from typing import List, Dict, Any, Optional
from .base import BaseCitationExtractor
from ..models import Citation, CitationCollection, TextReference, CitationType


class DiogenesCitationExtractor(BaseCitationExtractor):
    """Citation extractor for Diogenes responses."""

    def __init__(self):
        super().__init__(language="grk")  # Diogenes primarily handles Greek

    def can_extract(self, data: Any) -> bool:
        """Check if data is from Diogenes (has citations dict)."""
        if isinstance(data, dict):
            return "citations" in data and isinstance(data["citations"], dict)

        # Also check for Diogenes-specific structures
        if hasattr(data, "__dict__"):
            return hasattr(data, "citations") and isinstance(data.citations, dict)

        return False

    def extract(self, data: Any) -> CitationCollection:
        """Extract citations from Diogenes response data."""
        collection = self.create_collection(
            query=getattr(data, "term", "unknown"), source="diogenes"
        )

        citations_dict = self._get_citations_dict(data)
        if not citations_dict:
            return collection

        for abbreviation, reference_text in citations_dict.items():
            citation = self._extract_citation(abbreviation, reference_text)
            if citation:
                collection.add_citation(citation)

        return collection

    def _get_citations_dict(self, data: Any) -> Dict[str, str]:
        """Extract citations dictionary from various data formats."""
        if isinstance(data, dict):
            return data.get("citations", {})
        elif hasattr(data, "citations"):
            return data.citations or {}
        return {}

    def _extract_citation(self, abbreviation: str, reference_text: str) -> Optional[Citation]:
        """Convert a single Diogenes citation to Citation object."""
        # Normalize abbreviations
        normalized_abb = self._normalize_abbreviation(abbreviation)

        # Parse the reference text (e.g., "Hom. Il. 1.1")
        text_reference = self._parse_reference_text(reference_text, normalized_abb)

        if not text_reference:
            return None

        # Create citation with source metadata
        citation = self.create_citation(
            references=[text_reference],
            abbreviation=normalized_abb,
            full_name=self._get_full_name(normalized_abb),
            description=self._get_description(normalized_abb),
            date=self._get_date(normalized_abb),
        )

        return citation

    def _normalize_abbreviation(self, abbreviation: str) -> str:
        """Normalize common Diogenes abbreviations."""
        # Map common variations to standard forms
        mapping = {
            "perseus": "Perseus",
            "tlg": "TLG",
            "stoa": "Stoa",
            "hom": "Hom.",
            "il": "Il.",
            "od": "Od.",
            "verg": "Verg.",
            "aen": "Aen.",
            "georg": "Georg.",
            "ecl": "Ecl.",
        }

        normalized = abbreviation.lower()
        return mapping.get(normalized, abbreviation.title())

    def _parse_reference_text(self, text: str, abbreviation: str) -> Optional[TextReference]:
        """Parse reference text like "Hom. Il. 1.1" into structured components."""
        # Common patterns:
        # "Hom. Il. 1.1" -> Homer, Iliad, Book 1, Line 1
        # "Verg. Aen. 1.1" -> Vergil, Aeneid, Book 1, Line 1
        # "Hom. Od. 9.1-10" -> Homer, Odyssey, Book 9, Lines 1-10

        patterns = [
            # Author.Work Book.Line (e.g., Hom. Il. 1.1, Arist. Eth. Nic. 1.1)
            r"([A-Za-z\.]+)\.?\s+([A-Za-z\.]+(?:\s+[A-Za-z\.]+)*)\s+(\d+)(?:\.(\d+))?(?:-(\d+))?",
            # Work Book.Line (e.g., Il. 1.1)
            r"([A-Za-z\.]+)\s+(\d+)(?:\.(\d+))?(?:-(\d+))?",
            # Simple line reference (e.g., 1.1)
            r"(\d+)(?:\.(\d+))?(?:-(\d+))?",
        ]

        for pattern in patterns:
            match = re.match(pattern, text.strip())
            if match:
                return self._create_reference_from_match(match, text, abbreviation)

        # If no pattern matches, create a basic text reference
        return self.create_text_reference(CitationType.BOOK_REFERENCE, text, work=abbreviation)

    def _create_reference_from_match(
        self, match: re.Match, text: str, abbreviation: str
    ) -> TextReference:
        """Create TextReference from regex match groups."""
        groups = match.groups()

        # Parse author, work, book, line(s)
        author = groups[0] if len(groups) > 0 and groups[0] else None
        work = groups[1] if len(groups) > 1 and groups[1] else None
        book = groups[2] if len(groups) > 2 and groups[2] else None
        start_line = groups[3] if len(groups) > 3 and groups[3] else None
        end_line = groups[4] if len(groups) > 4 and groups[4] else None

        # Determine citation type
        if start_line and end_line:
            citation_type = CitationType.PASSAGE_REFERENCE
        elif start_line:
            citation_type = CitationType.LINE_REFERENCE
        else:
            citation_type = CitationType.BOOK_REFERENCE

        # Create reference with parsed components
        ref_kwargs = {
            "text": text,
            "work": work,
            "author": author,
            "book": book,
        }

        if start_line:
            if end_line:
                # Range reference
                ref_kwargs["line"] = f"{start_line}-{end_line}"
                ref_kwargs["numbering_system"] = "line_range"
            else:
                # Single line
                ref_kwargs["line"] = start_line

        return self.create_text_reference(citation_type, **ref_kwargs)

    def _get_full_name(self, abbreviation: str) -> Optional[str]:
        """Get full name for common Diogenes abbreviations."""
        names = {
            "Perseus": "Perseus Digital Library",
            "TLG": "Thesaurus Linguae Graecae",
            "Stoa": "Stoa.org",
            "Hom.": "Homer",
            "Il.": "Iliad",
            "Od.": "Odyssey",
            "Verg.": "Vergil",
            "Aen.": "Aeneid",
            "Georg.": "Georgics",
            "Ecl.": "Eclogues",
        }
        return names.get(abbreviation)

    def _get_description(self, abbreviation: str) -> Optional[str]:
        """Get description for common Diogenes abbreviations."""
        descriptions = {
            "Perseus": "Digital library of classical texts",
            "TLG": "Comprehensive collection of ancient Greek texts",
            "Stoa": "Classical text repository",
            "Hom.": "Ancient Greek epic poet",
            "Il.": "Epic poem about the Trojan War",
            "Od.": "Epic poem about Odysseus' journey",
            "Verg.": "Roman poet",
            "Aen.": "Epic poem about Aeneas",
            "Georg.": "Didactic poem about agriculture",
            "Ecl.": "Collection of pastoral poems",
        }
        return descriptions.get(abbreviation)

    def _get_date(self, abbreviation: str) -> Optional[str]:
        """Get approximate date for sources."""
        dates = {
            "Hom.": "8th century BCE",
            "Verg.": "1st century BCE",
            "Il.": "8th century BCE",
            "Od.": "8th century BCE",
            "Aen.": "29-19 BCE",
            "Georg.": "29 BCE",
            "Ecl.": "38 BCE",
        }
        return dates.get(abbreviation)
