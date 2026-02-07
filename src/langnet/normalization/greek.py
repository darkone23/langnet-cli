"""
Greek normalization with betacode conversion.
"""

import logging
import re

from .core import LanguageNormalizer
from .models import CanonicalQuery, Encoding, Language

logger = logging.getLogger(__name__)

MIN_VARIATION_LENGTH = 3
MIN_QUERY_LENGTH = 2
MAX_QUERY_LENGTH = 20


class GreekNormalizer(LanguageNormalizer):
    """
    Greek normalizer that handles betacode conversion and Unicode Greek.
    """

    def __init__(self):
        logger.info("GreekNormalizer initialized")

    def detect_encoding(self, text: str) -> str:
        """Detect the encoding of Greek text."""
        # Check for betacode (starts with * or contains / for accents)
        if self._is_betacode(text):
            return Encoding.BETAcode.value

        # Check for Unicode Greek characters
        if self._contains_unicode_greek(text):
            return Encoding.UNICODE.value

        # Check for ASCII Greek (could be transliterated)
        if re.match(r"^[a-zA-Z]+$", text):
            return Encoding.ASCII.value

        return Encoding.UNKNOWN.value

    def _is_betacode(self, text: str) -> bool:
        """Check if text is in betacode format."""
        # Betacode must start with * (required marker)
        if not text.startswith("*"):
            return False

        # Must have betacode-specific characters beyond the asterisk
        betacode_chars = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ/")
        return len(text) > 1 and all(c in betacode_chars for c in text[1:])

    def _contains_unicode_greek(self, text: str) -> bool:
        """Check if text contains Unicode Greek characters."""
        # Unicode Greek ranges
        greek_ranges = [
            (0x0370, 0x03FF),  # Greek and Coptic
            (0x1F00, 0x1FFF),  # Extended Greek
        ]

        for char in text:
            code = ord(char)
            for start, end in greek_ranges:
                if start <= code <= end:
                    return True

        return False

    def to_canonical(self, text: str, source_encoding: str) -> str:
        """Convert Greek text to Unicode canonical form."""
        if source_encoding == Encoding.UNICODE.value:
            # Already Unicode, return as-is
            return text

        elif source_encoding == Encoding.BETAcode.value:
            # Convert betacode to Unicode
            return self._betacode_to_unicode(text)

        elif source_encoding == Encoding.ASCII.value:
            # Convert ASCII Greek to Unicode (simple heuristic)
            return self._ascii_to_unicode(text)

        else:
            logger.warning(f"Unknown encoding {source_encoding}, returning as-is")
            return text

    def _betacode_to_unicode(self, betacode: str) -> str:
        """Convert betacode to Unicode Greek."""
        # This is a simplified implementation
        # In a real implementation, you'd use a proper betacode library

        # Remove leading * if present
        if betacode.startswith("*"):
            betacode = betacode[1:]

        # Basic betacode to Unicode mapping (simplified)
        # This would be much more comprehensive in practice
        betacode_map = {
            "a": "α",
            "b": "β",
            "g": "γ",
            "d": "δ",
            "e": "ε",
            "z": "ζ",
            "h": "η",
            "q": "θ",
            "i": "ι",
            "k": "κ",
            "l": "λ",
            "m": "μ",
            "n": "ν",
            "x": "ξ",
            "o": "ο",
            "p": "π",
            "r": "ρ",
            "s": "σ",
            "t": "τ",
            "u": "υ",
            "f": "φ",
            "c": "χ",
            "y": "ψ",
            "w": "ω",
            "A": "Α",
            "B": "Β",
            "G": "Γ",
            "D": "Δ",
            "E": "Ε",
            "Z": "Ζ",
            "H": "Η",
            "Q": "Θ",
            "I": "Ι",
            "K": "Κ",
            "L": "Λ",
            "M": "Μ",
            "N": "Ν",
            "X": "Ξ",
            "O": "Ο",
            "P": "Π",
            "R": "Ρ",
            "S": "Σ",
            "T": "Τ",
            "U": "Υ",
            "F": "Φ",
            "C": "Χ",
            "Y": "Ψ",
            "W": "Ω",
        }

        # Handle accents (simplified)
        result = []
        for char in betacode:
            if char == "/":
                # Accent marker - in real implementation would handle specific accents
                continue
            elif char in betacode_map:
                result.append(betacode_map[char])
            else:
                result.append(char)  # Keep unknown characters

        return "".join(result)

    def _ascii_to_unicode(self, ascii_greek: str) -> str:
        """Convert ASCII Greek to Unicode (simplified heuristic)."""
        # This is a very basic implementation
        # In practice, you'd use more sophisticated conversion

        # Basic mapping of common ASCII representations
        ascii_map = {
            "alpha": "α",
            "beta": "β",
            "gamma": "γ",
            "delta": "δ",
            "epsilon": "ε",
            "zeta": "ζ",
            "eta": "η",
            "theta": "θ",
            "iota": "ι",
            "kappa": "κ",
            "lambda": "λ",
            "mu": "μ",
            "nu": "ν",
            "xi": "ξ",
            "omicron": "ο",
            "pi": "π",
            "rho": "ρ",
            "sigma": "σ",
            "tau": "τ",
            "upsilon": "υ",
            "phi": "φ",
            "chi": "χ",
            "psi": "ψ",
            "omega": "ω",
            "ousia": "οὐσία",
            "logos": "λόγος",
        }

        # Check for exact matches
        if ascii_greek.lower() in ascii_map:
            return ascii_map[ascii_greek.lower()]

        # Simple heuristic: convert vowels to Greek vowels
        vowel_map = {
            "a": "α",
            "e": "ε",
            "i": "ι",
            "o": "ο",
            "u": "υ",
            "y": "υ",
            "A": "Α",
            "E": "Ε",
            "I": "Ι",
            "O": "Ο",
            "U": "Υ",
            "Y": "Υ",
        }

        result = []
        for char in ascii_greek:
            result.append(vowel_map.get(char, char))

        return "".join(result)

    def generate_alternates(self, canonical_text: str) -> list[str]:
        """Generate alternate forms for different tools."""
        alternates = []

        # Add original case variations
        if canonical_text:
            alternates.append(canonical_text.upper())

            # Add betacode form if applicable
            if self._contains_unicode_greek(canonical_text):
                betacode_form = self._unicode_to_betacode(canonical_text)
                if betacode_form:
                    alternates.append(betacode_form)

        return alternates

    def _unicode_to_betacode(self, unicode_text: str) -> str:
        """Convert Unicode Greek to betacode."""
        # Reverse mapping from betacode_to_unicode
        betacode_map = {
            "α": "a",
            "β": "b",
            "γ": "g",
            "δ": "d",
            "ε": "e",
            "ζ": "z",
            "η": "h",
            "θ": "q",
            "ι": "i",
            "κ": "k",
            "λ": "l",
            "μ": "m",
            "ν": "n",
            "ξ": "x",
            "ο": "o",
            "π": "p",
            "ρ": "r",
            "σ": "s",
            "τ": "t",
            "υ": "u",
            "φ": "f",
            "χ": "c",
            "ψ": "y",
            "ω": "w",
            "Α": "A",
            "Β": "B",
            "Γ": "G",
            "Δ": "D",
            "Ε": "E",
            "Ζ": "Z",
            "Η": "H",
            "Θ": "Q",
            "Ι": "I",
            "Κ": "K",
            "Λ": "L",
            "Μ": "M",
            "Ν": "N",
            "Ξ": "X",
            "Ο": "O",
            "Π": "P",
            "Ρ": "R",
            "Σ": "S",
            "Τ": "T",
            "Υ": "U",
            "Φ": "F",
            "Χ": "C",
            "Ψ": "Y",
            "Ω": "W",
        }

        # This is a simplified version
        result = []
        for char in unicode_text:
            if char in betacode_map:
                result.append(betacode_map[char])
            else:
                result.append(char)  # Keep unknown characters

        return "*" + "".join(result)  # Add betacode prefix

    def fuzzy_match_candidates(self, text: str) -> list[str]:
        """Generate possible forms for fuzzy matching."""
        candidates = [text.lower()]

        # Add common variations
        if len(text) > MIN_VARIATION_LENGTH:
            candidates.append(text[:-1])  # Remove last character
            candidates.append(text + "s")  # Add common ending

        # Remove duplicates
        return list(set(candidates))

    def normalize(self, query: str) -> CanonicalQuery:
        """Main normalization method for Greek."""
        # Detect encoding
        encoding = self.detect_encoding(query)

        # Convert to canonical form (Unicode)
        canonical_text = self.to_canonical(query, encoding)

        # Generate alternate forms
        alternates = self.generate_alternates(canonical_text)

        # Build normalization notes
        notes = [f"Detected encoding: {encoding}"]
        if encoding == Encoding.BETAcode.value:
            notes.append("Betacode converted to Unicode")
        elif encoding == Encoding.ASCII.value:
            notes.append("ASCII Greek converted to Unicode")

        return CanonicalQuery(
            original_query=query,
            language=Language.GREEK,
            canonical_text=canonical_text,
            alternate_forms=alternates,
            detected_encoding=Encoding(encoding),
            normalization_notes=notes,
        )
