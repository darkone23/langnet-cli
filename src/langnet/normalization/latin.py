"""
Latin normalization with macron handling and spelling variations.
"""

import logging
import re
from dataclasses import dataclass

from .core import LanguageNormalizer
from .models import CanonicalQuery, Encoding, Language

logger = logging.getLogger(__name__)


@dataclass
class LatinSpellingVariations:
    """Common Latin spelling variations."""

    VARIATIONS = {
        "iustitia": ["justitia"],
        "venio": ["uenio"],
        "uenio": ["venio"],
        "iuuenis": ["iuuenis", "iuuenis"],
        "gutta": ["gutta"],
        "littera": ["littera"],
        "scriptura": ["scriptura"],
        "scribo": ["scribo"],
        "lego": ["lego"],
        "legere": ["legere"],
    }


MIN_VARIATION_LENGTH = 3
MIN_QUERY_LENGTH = 2
MAX_QUERY_LENGTH = 20


class LatinNormalizer(LanguageNormalizer):
    """
    Latin normalizer that handles macron stripping and spelling variations.
    """

    def __init__(self):
        self.spelling_variations = LatinSpellingVariations()
        logger.info("LatinNormalizer initialized")

    def detect_encoding(self, text: str) -> str:
        """Detect the encoding of Latin text."""
        # Check for macrons (long vowels)
        if self._contains_macrons(text):
            return Encoding.UNICODE.value

        # Check for ASCII Latin
        if re.match(r"^[a-zA-Z]+$", text):
            return Encoding.ASCII.value

        # Check for other Latin-specific encodings if needed
        return Encoding.UNKNOWN.value

    def _contains_macrons(self, text: str) -> bool:
        """Check if text contains macrons."""
        macron_chars = set("āēīōūȳĀĒĪŪȲ")
        return any(c in macron_chars for c in text)

    def to_canonical(self, text: str, source_encoding: str) -> str:
        """Convert Latin text to ASCII canonical form (no macrons)."""
        if source_encoding == Encoding.UNICODE.value:
            # Strip macrons
            return self._strip_macrons(text)

        elif source_encoding == Encoding.ASCII.value:
            # Already ASCII, return as-is (lowercase)
            return text.lower()

        else:
            # Unknown encoding, try to strip macrons anyway
            return self._strip_macrons(text).lower()

    def _strip_macrons(self, text: str) -> str:
        """Remove macrons from Latin text."""
        macron_map = {
            "ā": "a",
            "ē": "e",
            "ī": "i",
            "ō": "o",
            "ū": "u",
            "ȳ": "y",
            "Ā": "A",
            "Ē": "E",
            "Ī": "I",
            "Ū": "U",
            "Ȳ": "Y",
        }

        result = []
        for char in text:
            result.append(macron_map.get(char, char))

        return "".join(result)

    def generate_alternates(self, canonical_text: str) -> list[str]:
        """Generate alternate forms for different tools."""
        alternates = []

        # Add original case variations
        if canonical_text:
            alternates.append(canonical_text.upper())

            # Add common spelling variations
            variations = self.spelling_variations.VARIATIONS.get(canonical_text, [])
            alternates.extend(variations)

            # Add i/j and u/v variations
            alternates.extend(self._get_ij_uv_variations(canonical_text))

        return alternates

    def _get_ij_uv_variations(self, text: str) -> list[str]:
        """Generate i/j and u/v spelling variations."""
        variations = []

        # i/j variations - only replace first occurrence
        if "i" in text and "j" not in text:
            first_i = text.find("i")
            if first_i >= 0:
                variations.append(text[:first_i] + "j" + text[first_i + 1 :])

        if "j" in text and "i" not in text:
            first_j = text.find("j")
            if first_j >= 0:
                variations.append(text[:first_j] + "i" + text[first_j + 1 :])

        # u/v variations - only replace first occurrence
        if "u" in text and "v" not in text:
            first_u = text.find("u")
            if first_u >= 0:
                variations.append(text[:first_u] + "v" + text[first_u + 1 :])

        if "v" in text and "u" not in text:
            first_v = text.find("v")
            if first_v >= 0:
                variations.append(text[:first_v] + "u" + text[first_v + 1 :])

        return variations

    def fuzzy_match_candidates(self, text: str) -> list[str]:
        """Generate possible forms for fuzzy matching."""
        candidates = [text.lower()]

        # Add common misspellings
        if len(text) > MIN_VARIATION_LENGTH:
            candidates.append(text[:-1])  # Remove last character
            candidates.append(text + "s")  # Add common ending
            candidates.append(text.replace("i", "j"))  # i/j variations
            candidates.append(text.replace("u", "v"))  # u/v variations

        # Remove duplicates
        return list(set(candidates))

    def normalize(self, query: str) -> CanonicalQuery:
        """Main normalization method for Latin."""
        # Detect encoding
        encoding = self.detect_encoding(query)

        # Convert to canonical form (strip macrons for ASCII)
        canonical_text = self.to_canonical(query, encoding)

        # Generate alternate forms
        alternates = self.generate_alternates(canonical_text)

        # Build normalization notes
        notes = [f"Detected encoding: {encoding}"]
        if encoding == Encoding.UNICODE.value:
            notes.append("Macrons stripped")
        if self._contains_macrons(query):
            notes.append("Macrons stripped")

        return CanonicalQuery(
            original_query=query,
            language=Language.LATIN,
            canonical_text=canonical_text,
            alternate_forms=alternates,
            detected_encoding=Encoding(encoding),
            normalization_notes=notes,
        )
