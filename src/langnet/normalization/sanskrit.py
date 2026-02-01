"""
Sanskrit normalization with Heritage Platform enrichment.
"""

import logging
import re
from dataclasses import dataclass
from typing import Any

from langnet.heritage.client import HeritageHTTPClient
from langnet.heritage.encoding_service import EncodingService

from .core import LanguageNormalizer
from .models import CanonicalQuery, Encoding, Language

logger = logging.getLogger(__name__)


@dataclass
class CommonSanskritTerms:
    """Common Sanskrit terms for pattern matching."""

    TERMS = {
        "agni",
        "indra",
        "varuna",
        "mitra",
        "soma",
        "yajna",
        "dharma",
        "karma",
        "atman",
        "brahman",
        "maya",
        "samsara",
        "nirvana",
        "moksha",
        "yoga",
        "prana",
        "nadi",
        "chakra",
        "mantra",
        "puja",
        "pujya",
        "deva",
        "devi",
        "rishi",
        "guru",
        "shakti",
        "shiva",
        "vishnu",
        "krishna",
        "rama",
        "hanuman",
        "artha",
        "kama",
        "moksha",
        "dharma",
        "rama",
        "sita",
        "lakshmi",
        "saraswati",
    }

    SLP1_TERMS = {
        "agni",
        "indra",
        "varuna",
        "mitra",
        "soma",
        "yajna",
        "dharma",
        "karma",
        "atman",
        "brahman",
    }


MIN_WORD_LENGTH = 2
MAX_QUERY_LENGTH_HERITAGE = 50
MIN_QUERY_LENGTH_HERITAGE = 2
MIN_SANSKRIT_LENGTH = 3
MAX_SANSKRIT_LENGTH = 15
MIN_SANSKRIT_CONFIDENCE = 0.5
MIN_QUERY_LENGTH = 3
MAX_QUERY_LENGTH = 20
MAX_ASCII_CODE = 127
DEVANAGARI_START = 0x0900
DEVANAGARI_END = 0x097F
MAX_SIMPLE_WORD_LENGTH = 10
SIMPLE_ENCODINGS = {Encoding.ASCII.value, Encoding.SLP1.value}


class SanskritNormalizer(LanguageNormalizer):
    """
    Sanskrit normalizer that builds on existing encoding services
    and adds Heritage Platform enrichment for bare ASCII queries.
    """

    def __init__(self, heritage_client=None):
        self.heritage_client = heritage_client
        self.common_terms = CommonSanskritTerms()
        logger.info("SanskritNormalizer initialized")

    def _detect_indic_encodings(self, text: str) -> str | None:
        """Check for Devanagari, IAST, and HK encodings."""
        # Check for Devanagari characters
        if any(DEVANAGARI_START < ord(c) < DEVANAGARI_END for c in text):
            return Encoding.DEVANAGARI.value

        # Check for IAST diacritics
        iast_chars = set("āīūṛṝḷḹṃṅñṇṅṟṣśṭḥḻḽḿṁṅṇṉṟṝṣṣṭḍḥ")
        if any(c in iast_chars for c in text):
            return Encoding.IAST.value

        # Check for HK (Harvard-Kyoto) encoding - must have HK-specific chars
        hk_chars = set("āīūṛṝḷḹṃṅñṇṅṟṣśṭḥ")
        if re.match(r"^[a-zA-Zāīūṛṝḷḹṃṅñṇṅṟṣśṭḥ]+$", text) and any(c in hk_chars for c in text):
            return Encoding.HK.value

        return None

    def detect_encoding(self, text: str) -> str:
        """Detect the encoding of Sanskrit text using improved Heritage encoding service."""
        # Use the improved encoding detection from Heritage service
        detected = EncodingService.detect_encoding(text)

        # Map Heritage encoding names to standard encoding enum values
        encoding_mapping = {
            "devanagari": Encoding.DEVANAGARI.value,
            "iast": Encoding.IAST.value,
            "velthuis": Encoding.VELTHUIS.value,
            "hk": Encoding.HK.value,
            "slp1": Encoding.SLP1.value,
            "ascii": Encoding.ASCII.value,
        }

        return encoding_mapping.get(detected, Encoding.ASCII.value)

    def _looks_like_velthuis(self, text: str) -> bool:
        """Check if text looks like Velthuis encoding."""
        # Velthuis uses specific patterns for aspirated consonants
        # Only check for unambiguous Velthuis patterns
        velthuis_indicators = ["_", ".", "~", "^"]  # Actual Velthuis markers
        return any(indicator in text for indicator in velthuis_indicators)

    def _is_slp1_compatible(self, text: str) -> bool:
        """Check if text is compatible with SLP1 encoding."""
        # SLP1 specific character constraints
        slp1_valid = set("aAiIuUfFxXeEoOkgGcCjJwWqQRtTdDppbBmnyYrlvSzshN")
        if not all(c.lower() in slp1_valid for c in text if c.isalpha()):
            return False

        # Check if it's a known SLP1 term or has SLP1-specific characters
        if text.lower() in self.common_terms.SLP1_TERMS:
            return True

        # Check for SLP1-specific characters (uppercase consonants that are unique to SLP1)
        # These characters are not typically used in simple ASCII or Velthuis
        slp1_specific = set("ACFGJKQWX")
        if any(c in slp1_specific for c in text):
            return True

        # If text has uppercase letters but no SLP1-specific chars, it might be Velthuis
        # SLP1 requires uppercase for certain consonants, but Velthuis uses different patterns
        has_uppercase = any(c.isupper() for c in text)
        if has_uppercase:
            # Check if it follows Velthuis patterns instead
            velthuis_upper = set("GJDN")  # Common Velthuis uppercase
            if any(c in velthuis_upper for c in text):
                return False  # Likely Velthuis, not SLP1

        return False

    def to_canonical(self, text: str, source_encoding: str) -> str:
        """Convert Sanskrit text to canonical form using Heritage Platform lookup."""
        try:
            # For simple cases that don't need canonical lookup, use basic conversion
            if (
                source_encoding in SIMPLE_ENCODINGS
                and text.isalpha()
                and text.islower()
                and len(text) <= MAX_SIMPLE_WORD_LENGTH
            ):  # Simple words don't need canonical lookup
                logger.debug(f"Using basic conversion for simple {source_encoding} word: '{text}'")
                return self._basic_to_canonical(text, source_encoding)

            # First try to get canonical form via sktsearch
            with HeritageHTTPClient() as client:
                # Use sktsearch to find the canonical form
                canonical_result = client.fetch_canonical_via_sktsearch(text)

                if canonical_result["canonical_text"]:
                    # Use the canonical form from sktsearch (already in proper encoding)
                    return canonical_result["canonical_text"]

                # Fallback: try fetch_canonical_sanskrit for MW entries
                fallback_result = client.fetch_canonical_sanskrit(text)
                if fallback_result["canonical_sanskrit"]:
                    return fallback_result["canonical_sanskrit"]

            # If Heritage lookup fails, use basic conversion logic
            logger.debug(f"Heritage lookup failed for '{text}', using basic conversion")
            return self._basic_to_canonical(text, source_encoding)

        except Exception as e:
            logger.warning(f"Canonical lookup failed for '{text}': {e}, using basic conversion")
            return self._basic_to_canonical(text, source_encoding)

    def _basic_to_canonical(self, text: str, source_encoding: str) -> str:
        """Basic canonical conversion when Heritage lookup fails."""
        if source_encoding == Encoding.SLP1.value:
            return text.lower()

        elif source_encoding == Encoding.ASCII.value:
            # This is where Heritage enrichment would happen
            # For now, return as-is with lowercase
            return text.lower()

        elif source_encoding == Encoding.DEVANAGARI.value:
            # Would convert Devanagari to SLP1 using indic_transliteration
            # For now, placeholder
            return text.lower()

        elif source_encoding == Encoding.IAST.value:
            # Would convert IAST to SLP1 using indic_transliteration
            return text.lower()

        elif source_encoding == Encoding.VELTHUIS.value:
            # Would convert Velthuis to SLP1 using indic_transliteration
            return text.lower()

        else:
            logger.warning(f"Unknown encoding {source_encoding}, returning as-is")
            return text.lower()

    def generate_alternates(self, canonical_text: str) -> list[str]:
        """Generate alternate forms for different tools."""
        alternates = []

        # Add common variations
        if canonical_text:
            alternates.append(canonical_text.upper())  # Uppercase form

            # Add common transliteration variations if applicable
            if self._is_sanskrit_word(canonical_text):
                alternates.extend(self._get_transliteration_variations(canonical_text))

        return alternates

    def fuzzy_match_candidates(self, text: str) -> list[str]:
        """Generate possible forms for fuzzy matching."""
        candidates = [text.lower()]  # Basic lowercase

        # Add common misspellings and variations
        if self._is_sanskrit_word(text):
            candidates.extend(
                [
                    text + "a",  # Common ending variation
                    text[:-1],  # Remove last character
                    text + "h",  # Add aspiration
                ]
            )

        # Remove duplicates
        return list(set(candidates))

    def _is_sanskrit_word(self, text: str) -> bool:
        """Check if text appears to be a Sanskrit word."""
        if not text or len(text) < MIN_WORD_LENGTH:
            return False

        # Exclude common English words
        common_english = {
            "test",
            "the",
            "and",
            "for",
            "are",
            "but",
            "not",
            "you",
            "all",
            "can",
            "had",
            "her",
            "was",
            "one",
            "our",
            "out",
            "day",
            "get",
            "has",
            "him",
            "his",
            "how",
            "man",
            "new",
            "now",
            "old",
            "see",
            "two",
            "way",
            "who",
            "boy",
            "did",
            "its",
            "let",
            "put",
            "say",
            "she",
            "too",
            "use",
            "dad",
            "mom",
        }
        if text.lower() in common_english:
            return False

        # Check for Sanskrit-specific patterns
        sanskrit_patterns = [
            r".*[kgcjtdpb][h]?",  # Aspirated consonants
            r".*[nm]$",  # Common Sanskrit endings
            r".*[aeiou][nm]?$",  # Vowel endings
        ]

        # Also check if it looks like basic ASCII and contains Sanskrit-like patterns
        if not re.match(r"^[a-zA-Z]+$", text):
            return False

        return any(re.match(pattern, text, re.IGNORECASE) for pattern in sanskrit_patterns)

    def _get_transliteration_variations(self, text: str) -> list[str]:
        """Get common transliteration variations for a Sanskrit word."""
        variations = [text]

        # Add common spelling variations
        if text.endswith("a"):
            variations.append(text[:-1])  # Remove final 'a'

        # Add vowel variations
        if "i" in text or "u" in text:
            variations.append(text.replace("i", "ee"))
            variations.append(text.replace("u", "oo"))

        return variations

    def normalize(self, query: str) -> CanonicalQuery:
        """Main normalization method for Sanskrit."""
        # Detect encoding
        encoding = self.detect_encoding(query)

        # Check for bare ASCII Sanskrit that needs enrichment
        is_bare_ascii = encoding == Encoding.ASCII.value
        enrichment_metadata = None

        if is_bare_ascii and self.heritage_client and self._needs_heritage_enrichment(query):
            logger.info(f"Attempting Heritage enrichment for: {query}")
            enrichment_metadata = self._enrich_with_heritage(query)

        # Convert to canonical form
        canonical_text = self.to_canonical(query, encoding)

        # Generate alternate forms
        alternates = self.generate_alternates(canonical_text)

        # Calculate confidence
        confidence = self._calculate_confidence(query, encoding, enrichment_metadata)

        # Build normalization notes
        notes = [f"Detected encoding: {encoding}"]
        if enrichment_metadata:
            notes.append(f"Heritage enrichment: {enrichment_metadata.get('source', 'unknown')}")
        if encoding == Encoding.ASCII.value and self._is_sanskrit_word(query):
            notes.append("Bare ASCII Sanskrit detected")

        return CanonicalQuery(
            original_query=query,
            language=Language.SANSKRIT,
            canonical_text=canonical_text,
            alternate_forms=alternates,
            detected_encoding=Encoding(encoding),
            confidence=confidence,
            normalization_notes=notes,
            enrichment_metadata=enrichment_metadata,
        )

    def _needs_heritage_enrichment(self, query: str) -> bool:
        """Check if a bare ASCII query needs Heritage enrichment."""
        if not self.heritage_client:
            return False

        # Basic heuristics for Sanskrit-like ASCII queries
        if len(query) < MIN_QUERY_LENGTH_HERITAGE or len(query) > MAX_QUERY_LENGTH_HERITAGE:
            return False

        # Check for non-ASCII characters
        if any(ord(c) > MAX_ASCII_CODE for c in query):
            return False

        # Check for Sanskrit patterns
        sanskrit_score = 0

        # Length scoring
        if MIN_SANSKRIT_LENGTH <= len(query) <= MAX_SANSKRIT_LENGTH:
            sanskrit_score += 0.3

        # Pattern matching
        if re.match(r"^[a-z]+$", query):
            sanskrit_score += 0.2

        # Common consonant patterns
        if re.search(r"[kgcjtdpb][h]?", query):
            sanskrit_score += 0.2

        # Common endings
        if query.endswith(("na", "ni", "nu", "no", "ma", "mi", "mu", "mo")):
            sanskrit_score += 0.2

        # Common terms
        if query.lower() in self.common_terms.TERMS:
            sanskrit_score += 0.1

        return sanskrit_score >= MIN_SANSKRIT_CONFIDENCE

    def _enrich_with_heritage(self, query: str) -> dict[str, Any] | None:
        """Enrich a bare ASCII query using Heritage Platform canonical lookup."""
        try:
            with HeritageHTTPClient() as client:
                # Use sktsearch to find canonical forms
                canonical_result = client.fetch_canonical_via_sktsearch(query)

                if canonical_result["canonical_text"]:
                    enrichment = {
                        "source": "heritage_sktsearch",
                        "original_query": query,
                        "enrichment_type": "ascii_to_sanskrit",
                        "confidence": 0.9,
                        "canonical_form": canonical_result["canonical_text"],
                        "entry_url": canonical_result["entry_url"],
                        "lexicon": canonical_result["lexicon"],
                        "suggestions": [
                            {
                                "term": canonical_result["canonical_text"],
                                "form": canonical_result["canonical_text"],
                                "encoding": "velthuis",
                                "confidence": 0.9,
                                "entry_url": canonical_result["entry_url"],
                            }
                        ],
                    }
                    logger.debug(f"Heritage enrichment result: {enrichment}")
                    return enrichment

                # Fallback: try MW dictionary lookup
                mw_result = client.fetch_canonical_sanskrit(query, lexicon="MW")
                if mw_result["canonical_sanskrit"]:
                    enrichment = {
                        "source": "heritage_mw",
                        "original_query": query,
                        "enrichment_type": "ascii_to_sanskrit",
                        "confidence": 0.8,
                        "canonical_form": mw_result["canonical_sanskrit"],
                        "entry_url": mw_result["entry_url"],
                        "lexicon": mw_result["lexicon"],
                        "suggestions": [
                            {
                                "term": mw_result["canonical_sanskrit"],
                                "form": mw_result["canonical_sanskrit"],
                                "encoding": "devanagari",
                                "confidence": 0.8,
                                "entry_url": mw_result["entry_url"],
                            }
                        ],
                    }
                    logger.debug(f"Heritage fallback enrichment result: {enrichment}")
                    return enrichment

                # If no enrichment found
                logger.debug(f"No Heritage enrichment found for: {query}")
                return None

        except Exception as e:
            logger.error(f"Heritage enrichment failed: {e}")
            return None

    def _calculate_confidence(
        self, query: str, encoding: str, enrichment_metadata: dict[str, Any] | None
    ) -> float:
        """Calculate confidence score for normalization."""
        base_confidence = 0.5

        # Boost confidence for known encodings
        if encoding in [Encoding.SLP1.value, Encoding.DEVANAGARI.value, Encoding.IAST.value]:
            base_confidence = 0.9
        elif encoding == Encoding.VELTHUIS.value:
            base_confidence = 0.8
        elif encoding == Encoding.ASCII.value:
            base_confidence = 0.4

        # Boost confidence if Heritage enrichment was used
        if enrichment_metadata:
            base_confidence = min(base_confidence + 0.3, 1.0)

        # Adjust for query length
        if MIN_QUERY_LENGTH <= len(query) <= MAX_QUERY_LENGTH:
            base_confidence = min(base_confidence + 0.1, 1.0)

        return base_confidence
