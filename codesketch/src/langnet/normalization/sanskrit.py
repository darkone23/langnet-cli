"""
Sanskrit normalization with Heritage Platform enrichment.
"""

import logging
import re
from dataclasses import dataclass
from typing import cast

from langnet.heritage.encoding_service import EncodingService
from langnet.types import JSONMapping

from langnet.heritage.client import HeritageHTTPClient

from .core import LanguageNormalizer
from .models import CanonicalQuery, Encoding, Language

logger = logging.getLogger(__name__)
MIN_TOKENS_FOR_CANONICAL = 2
EXTENDED_ASCII_THRESHOLD = 127


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
MAX_SIMPLE_WORD_LENGTH = 6  # Reduced from 10 to ensure common words use sktsearch
SIMPLE_ENCODINGS = {Encoding.ASCII.value, Encoding.SLP1.value}


class SanskritNormalizer(LanguageNormalizer):
    """
    Sanskrit normalizer that builds on existing encoding services
    and adds Heritage Platform enrichment for bare ASCII queries.
    """

    def __init__(self, heritage_client=None):
        # Allow injection for tests; default to a real Heritage client.
        self.heritage_client = heritage_client or HeritageHTTPClient()
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

    def to_canonical(self, text: str, source_encoding: str) -> tuple[str, JSONMapping | None]:
        """
        Convert Sanskrit text to canonical Velthuis using Heritage Platform lookup.

        Returns the canonical text and any metadata gathered during lookup.
        """
        canonical_metadata: JSONMapping | None = None

        try:
            lookup_text = text
            # Normalize non-ASCII scripts to Velthuis before hitting sktsearch.
            if source_encoding not in {
                Encoding.ASCII.value,
                Encoding.VELTHUIS.value,
                Encoding.HK.value,
            }:
                lookup_text = self._to_velthuis(text, source_encoding)

            if " " in lookup_text:
                phrase_canon, phrase_meta = self._canonicalize_phrase_via_sktsearch(lookup_text)
                if phrase_canon:
                    return phrase_canon, phrase_meta

            canonical_result = self._canonical_via_sktsearch(lookup_text)

            if canonical_result and canonical_result.get("canonical_text"):
                canonical_metadata = cast(JSONMapping, canonical_result)
                return canonical_result["canonical_text"], canonical_metadata

            # Fallback: try fetch_canonical_sanskrit for MW entries
            fallback_result = self.heritage_client.fetch_canonical_sanskrit(lookup_text)
            if fallback_result["canonical_sanskrit"]:
                canonical_metadata = cast(JSONMapping, fallback_result)
                return fallback_result["canonical_sanskrit"], canonical_metadata

            # If Heritage lookup fails, use basic conversion logic
            logger.debug(f"Heritage lookup failed for '{text}', using basic conversion")
            return self._basic_to_canonical(text, source_encoding), canonical_metadata

        except Exception as e:
            logger.warning(f"Canonical lookup failed for '{text}': {e}, using basic conversion")
            return self._basic_to_canonical(text, source_encoding), canonical_metadata

    def _basic_to_canonical(self, text: str, source_encoding: str) -> str:
        """Basic canonical conversion when Heritage lookup fails."""
        sanitized = text.strip()
        if source_encoding == Encoding.SLP1.value:
            return sanitized.lower()

        elif source_encoding == Encoding.ASCII.value:
            # Without enrichment we cannot guess long vowels; normalize case only.
            return sanitized.lower()

        elif source_encoding == Encoding.DEVANAGARI.value:
            # Would convert Devanagari to SLP1 using indic_transliteration
            return self._to_velthuis(sanitized, Encoding.DEVANAGARI.value)

        elif source_encoding == Encoding.IAST.value:
            return self._to_velthuis(sanitized, Encoding.IAST.value)

        elif source_encoding == Encoding.VELTHUIS.value:
            return sanitized.lower()

        else:
            logger.warning(f"Unknown encoding {source_encoding}, returning as-is")
            return sanitized.lower()

    def _canonical_via_sktsearch(self, text: str) -> JSONMapping | None:
        """Hit sktsearch once to avoid duplicated lookups across code paths."""
        if not self.heritage_client:
            return None

        try:
            canonical_result = self.heritage_client.fetch_canonical_via_sktsearch(text)
            if canonical_result.get("canonical_text"):
                return cast(JSONMapping, canonical_result)
        except Exception as exc:  # noqa: BLE001
            logger.debug("sktsearch_canonical_failed for %s: %s", text, exc)
        return None

    def _canonicalize_phrase_via_sktsearch(
        self, text: str
    ) -> tuple[str | None, JSONMapping | None]:
        """
        When sktsearch cannot handle full phrases, try canonicalizing tokens individually.
        Returns joined canonical tokens when at least one token is enriched.
        """
        tokens = [tok for tok in re.split(r"\s+", text.strip()) if tok]
        if len(tokens) < MIN_TOKENS_FOR_CANONICAL or not self.heritage_client:
            return None, None

        canonical_tokens: list[str] = []
        token_meta: list[JSONMapping] = []
        enriched = False

        for tok in tokens:
            tok_result = self._canonical_via_sktsearch(tok) or {}
            canon_value = tok_result.get("canonical_text")
            canon_tok = str(canon_value) if canon_value is not None else tok
            if canon_value:
                enriched = True
            canonical_tokens.append(canon_tok)
            if tok_result:
                token_meta.append(tok_result)

        if not enriched:
            return None, None

        joined = " ".join(canonical_tokens)
        return joined, {
            "canonical_text": joined,
            "match_method": "sktsearch_tokens",
            "token_metadata": token_meta,
        }

    def _to_velthuis(self, text: str, source_encoding: str) -> str:
        """Transliterate input into Velthuis where possible."""
        try:
            from indic_transliteration.detect import detect  # noqa: PLC0415
            from indic_transliteration.sanscript import (  # noqa: PLC0415
                DEVANAGARI,
                HK,
                IAST,
                SLP1,
                VELTHUIS,
                transliterate,
            )

            # Map our enum to sanscript constants; HK handles ASCII-ish inputs.
            source_map = {
                Encoding.DEVANAGARI.value: DEVANAGARI,
                Encoding.IAST.value: IAST,
                Encoding.VELTHUIS.value: VELTHUIS,
                Encoding.SLP1.value: SLP1,
                Encoding.HK.value: HK,
                Encoding.ASCII.value: detect(text) or HK,
            }
            src_scheme = source_map.get(source_encoding, detect(text) or HK)
            return transliterate(text, src_scheme, VELTHUIS).lower()
        except Exception as exc:  # noqa: BLE001
            logger.debug("velthuis_transliteration_failed: %s", exc)
            return text.lower()

    def generate_alternates(
        self, canonical_text: str, source_encoding: str | None = None
    ) -> list[str]:
        """Generate alternate forms for different tools."""
        alternates = []

        encoding_for_variants = source_encoding or self.detect_encoding(canonical_text)
        if (
            encoding_for_variants in {Encoding.IAST.value, Encoding.DEVANAGARI.value}
            and canonical_text.isascii()
        ):
            encoding_for_variants = Encoding.VELTHUIS.value

        if canonical_text:
            alternates.append(canonical_text)

        # Add transliteration variants (SLP1 for CDSL, IAST/Devanagari for display)
        if canonical_text:
            variants = self._transliterate_variants(canonical_text, encoding_for_variants)
            alternates.extend(variants)

        # Add uppercase Velthuis as a loose fallback for legacy tools
        if canonical_text:
            alternates.append(canonical_text.upper())

        # Remove duplicates while preserving order
        seen: set[str] = set()
        return [alt for alt in alternates if alt not in seen and not seen.add(alt)]

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

        canonical_text, canonical_meta = self.to_canonical(query, encoding)

        # Decide source encoding for alternates: prefer Velthuis when sktsearch provided canonical.
        encoding_for_alternates = (
            Encoding.VELTHUIS.value
            if (canonical_meta and canonical_meta.get("match_method") == "sktsearch")
            else encoding
        )

        # Generate alternate forms
        alternates = self.generate_alternates(canonical_text, encoding_for_alternates)

        # Build normalization notes
        notes = [f"Detected encoding: {encoding}"]
        if enrichment_metadata:
            notes.append(f"Heritage enrichment: {enrichment_metadata.get('source', 'unknown')}")
        if encoding == Encoding.ASCII.value and self._is_sanskrit_word(query):
            notes.append("Bare ASCII Sanskrit detected")
        if canonical_meta and canonical_meta.get("match_method"):
            notes.append(f"Canonical match: {canonical_meta.get('match_method')}")

        enrichment_payload: JSONMapping | None = None
        if canonical_meta or enrichment_metadata:
            enrichment_payload = {}
            if canonical_meta:
                enrichment_payload.update(canonical_meta)
            if enrichment_metadata:
                enrichment_payload.update(enrichment_metadata)

        return CanonicalQuery(
            original_query=query,
            language=Language.SANSKRIT,
            canonical_text=canonical_text,
            alternate_forms=alternates,
            detected_encoding=Encoding(encoding),
            normalization_notes=notes,
            enrichment_metadata=enrichment_payload,
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

    def _enrich_with_heritage(self, query: str) -> JSONMapping | None:
        """Enrich a bare ASCII query using Heritage Platform canonical lookup."""
        try:
            client = self.heritage_client
            # Use sktsearch to find canonical forms
            canonical_result = client.fetch_canonical_via_sktsearch(query)

            if canonical_result["canonical_text"]:
                enrichment = {
                    "source": "heritage_sktsearch",
                    "original_query": query,
                    "enrichment_type": "ascii_to_sanskrit",
                    "canonical_form": canonical_result["canonical_text"],
                    "entry_url": canonical_result.get("entry_url"),
                    "lexicon": canonical_result.get("lexicon"),
                    "suggestions": [
                        {
                            "term": canonical_result["canonical_text"],
                            "form": canonical_result["canonical_text"],
                            "encoding": "velthuis",
                            "entry_url": canonical_result.get("entry_url"),
                        }
                    ],
                }
                logger.debug(f"Heritage enrichment result: {enrichment}")
                return enrichment

            # Fallback: try MW dictionary lookup
            mw_result = client.fetch_canonical_sanskrit(query)
            if mw_result["canonical_sanskrit"]:
                enrichment = {
                    "source": "heritage_mw",
                    "original_query": query,
                    "enrichment_type": "ascii_to_sanskrit",
                    "canonical_form": mw_result["canonical_sanskrit"],
                    "entry_url": mw_result.get("entry_url"),
                    "lexicon": mw_result.get("lexicon"),
                    "suggestions": [
                        {
                            "term": mw_result["canonical_sanskrit"],
                            "form": mw_result["canonical_sanskrit"],
                            "encoding": "devanagari",
                            "entry_url": mw_result.get("entry_url"),
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

    def _transliterate_variants(self, canonical_text: str, source_encoding: str) -> list[str]:
        """
        Produce transliteration variants from a canonical Velthuis (preferred) form.

        Includes SLP1 for CDSL and IAST/Devanagari for display when possible.
        """
        variants: list[str] = []
        try:
            from indic_transliteration.sanscript import (  # noqa: PLC0415
                DEVANAGARI,
                IAST,
                SLP1,
                VELTHUIS,
                transliterate,
            )

            # Default to Velthuis since canonical_text typically comes from sktsearch.
            src_scheme = VELTHUIS
            if source_encoding == Encoding.SLP1.value:
                src_scheme = SLP1
            elif source_encoding == Encoding.IAST.value and any(
                ord(c) > EXTENDED_ASCII_THRESHOLD for c in canonical_text
            ):
                src_scheme = IAST
            elif source_encoding == Encoding.DEVANAGARI.value:
                src_scheme = DEVANAGARI

            if src_scheme == VELTHUIS:
                slp1 = self._velthuis_to_slp1_basic(canonical_text)
            else:
                slp1 = transliterate(canonical_text, src_scheme, SLP1)
            variants.append(slp1)
            if slp1.lower() != slp1:
                variants.append(slp1.lower())
            variants.append(transliterate(canonical_text, src_scheme, IAST))
            variants.append(transliterate(canonical_text, src_scheme, DEVANAGARI))
        except Exception as exc:  # noqa: BLE001
            logger.debug("transliteration_variants_failed: %s", exc)

        return [v for v in variants if v]

    def _velthuis_to_slp1_basic(self, text: str) -> str:
        """Lightweight Velthuis → SLP1 for cases where library detection misfires."""
        replacements = [
            ("aa", "A"),
            ("ii", "I"),
            ("uu", "U"),
            ("~n", "Y"),
            (".rr", "F"),
            (".r", "f"),
            (".ll", "X"),
            (".l", "x"),
            (".n", "R"),
            (".t", "w"),
            (".d", "q"),
            (".s", "z"),
            ("'s", "S"),
        ]
        out = text
        for old, new in replacements:
            out = out.replace(old, new)
        return out
