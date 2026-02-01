import re
from typing import Any

from indic_transliteration.sanscript import (
    DEVANAGARI,
    HK,
    ITRANS,
    SLP1,
    VELTHUIS,
    WX,
    transliterate,
)

# Try to import indic_transliteration library
try:
    HAS_INDIC_TRANSLIT = True
    DEVANAGARI_AVAILABLE = DEVANAGARI
    VELTHUIS_AVAILABLE = VELTHUIS
    ITRANS_AVAILABLE = ITRANS
    SLP1_AVAILABLE = SLP1
    HK_AVAILABLE = HK
    WX_AVAILABLE = WX
except ImportError:
    HAS_INDIC_TRANSLIT = False
    transliterate: Any | None = None
    DEVANAGARI_AVAILABLE = None
    VELTHUIS_AVAILABLE = None
    ITRANS_AVAILABLE = None
    SLP1_AVAILABLE = None
    HK_AVAILABLE = None
    WX_AVAILABLE = None


class EncodingService:
    """Service for handling Sanskrit text encoding conversions"""

    # Constants for encoding detection
    MIN_SPECIFIC_CONSONANTS_FOR_SLP1 = 2

    @staticmethod
    def detect_encoding(text: str) -> str:
        """Detect the encoding of input text by analyzing its attributes."""
        if not text:
            return "ascii"

        # Analyze text attributes
        attributes = {
            "has_devanagari": any("\u0900" <= c <= "\u097f" for c in text),
            "has_iast": any(c in "āīūṛṝḹḹṃḥṅñṭḍṇṣśḻḽ" for c in text),
            "has_uppercase": any(c.isupper() for c in text),
            "has_retroflex_upper": any(c in "RTDNS" for c in text),
            "has_macrons": any(c in "āīūṛṝḹḹ" for c in text),
            "is_all_alpha": text.isalpha(),
            "is_all_uppercase": text.isupper(),
        }

        # Clear detection based on attributes
        if attributes["has_devanagari"]:
            return "devanagari"

        if attributes["has_iast"]:
            return "iast"

        # SLP1 detection: must have multiple SLP1-specific consonants AND mixed case
        # OR look like typical SLP1 with specific patterns
        slp1_specific_consonants = "CFGJKQWX"  # These are exclusively SLP1
        retroflex_consonants = "RTDNS"  # Retroflex consonants that appear in both SLP1 and Velthuis

        specific_consonants_found = [c for c in text if c in slp1_specific_consonants]
        retroflex_found = [c for c in text if c in retroflex_consonants]

        # Check if text contains SLP1-specific patterns
        slp1_pattern_match = any(
            c in "aAiIuUfFxXEeOoKkKGgGHhjJYcCwWqQrRNdzZbBpPmMtTdDsSnNlLvvyYsSz" for c in text
        )

        # Only detect SLP1 if:
        # 1. Multiple specific consonants AND mixed case, OR
        # 2. Has at least two specific consonants (regardless of case)
        # Don't detect SLP1 based on single specific consonant + mixed case,
        # as that conflicts with Velthuis detection
        min_consonants = EncodingService.MIN_SPECIFIC_CONSONANTS_FOR_SLP1
        is_slp1 = (
            (
                len(specific_consonants_found) >= min_consonants
                and not attributes["is_all_uppercase"]
            )
            or (len(specific_consonants_found) >= min_consonants)
        ) and slp1_pattern_match

        if is_slp1:
            return "slp1"

        # Velthuis detection: must have retroflex uppercase AND mixed case.
        # Velthuis can have some chars also in SLP1, but pattern should be Velthuis-like.
        is_velthuis = (
            attributes["has_retroflex_upper"]
            and attributes["has_uppercase"]
            and not attributes["is_all_uppercase"]
            and (
                # No SLP1-specific consonants, OR
                len(specific_consonants_found) == 0
                # OR if it has SLP1-specific consonants but the pattern suggests Velthuis
                or (
                    len(specific_consonants_found) == 1
                    and len(retroflex_found) >= 1
                    and not attributes["is_all_uppercase"]
                )
            )
        )

        if is_velthuis:
            return "velthuis"

        if attributes["has_macrons"]:
            return "hk"

        if attributes["is_all_alpha"]:
            return "ascii"

        return "ascii"

    @staticmethod
    def to_velthuis(text: str, source_encoding: str | None = None) -> str:
        """Convert text to Velthuis encoding (for Heritage Platform)"""
        if not HAS_INDIC_TRANSLIT or not transliterate:
            # Fallback to simple conversion
            return EncodingService._fallback_to_velthuis(text)

        # Auto-detect source encoding if not provided
        if source_encoding is None:
            source_encoding = EncodingService.detect_encoding(text)

        try:
            if source_encoding == "devanagari" and DEVANAGARI_AVAILABLE and VELTHUIS_AVAILABLE:
                return transliterate(text, DEVANAGARI_AVAILABLE, VELTHUIS_AVAILABLE)
            elif source_encoding == "itrans" and ITRANS_AVAILABLE and VELTHUIS_AVAILABLE:
                return transliterate(text, ITRANS_AVAILABLE, VELTHUIS_AVAILABLE)
            elif source_encoding == "iast" and ITRANS_AVAILABLE and VELTHUIS_AVAILABLE:
                # Treat IAST same as ITRANS for conversion purposes
                return transliterate(text, ITRANS_AVAILABLE, VELTHUIS_AVAILABLE)
            elif source_encoding == "slp1" and SLP1_AVAILABLE and VELTHUIS_AVAILABLE:
                return transliterate(text, SLP1_AVAILABLE, VELTHUIS_AVAILABLE)
            else:
                # Try to convert from whatever encoding was detected
                detected = EncodingService.detect_encoding(text)
                if (
                    detected in [DEVANAGARI_AVAILABLE, ITRANS_AVAILABLE, SLP1_AVAILABLE]
                    and VELTHUIS_AVAILABLE
                ):
                    return transliterate(text, detected, VELTHUIS_AVAILABLE)
                else:
                    return text
        except Exception:
            return EncodingService._fallback_to_velthuis(text)

    @staticmethod
    def to_slp1(text: str, source_encoding: str | None = None) -> str:
        """Convert text to SLP1 encoding (for CDSL lookup)"""
        if not HAS_INDIC_TRANSLIT or not transliterate:
            # Fallback to simple conversion
            return EncodingService._fallback_to_slp1(text)

        # Auto-detect source encoding if not provided
        if source_encoding is None:
            source_encoding = EncodingService.detect_encoding(text)

        try:
            if source_encoding == "devanagari" and DEVANAGARI_AVAILABLE and SLP1_AVAILABLE:
                result = transliterate(text, DEVANAGARI_AVAILABLE, SLP1_AVAILABLE)
                return result.lower()
            elif source_encoding == "itrans" and ITRANS_AVAILABLE and SLP1_AVAILABLE:
                result = transliterate(text, ITRANS_AVAILABLE, SLP1_AVAILABLE)
                return result.lower()
            elif source_encoding == "iast" and ITRANS_AVAILABLE and SLP1_AVAILABLE:
                # Treat IAST same as ITRANS for conversion purposes
                result = transliterate(text, ITRANS_AVAILABLE, SLP1_AVAILABLE)
                return result.lower()
            elif source_encoding == "velthuis" and VELTHUIS_AVAILABLE and SLP1_AVAILABLE:
                result = transliterate(text, VELTHUIS_AVAILABLE, SLP1_AVAILABLE)
                return result.lower()
            else:
                # Try to convert from whatever encoding was detected
                detected = EncodingService.detect_encoding(text)
                if (
                    detected in [DEVANAGARI_AVAILABLE, ITRANS_AVAILABLE, VELTHUIS_AVAILABLE]
                    and SLP1_AVAILABLE
                ):
                    result = transliterate(text, detected, SLP1_AVAILABLE)
                    return result.lower()
                else:
                    return text.lower()
        except Exception:
            return EncodingService._fallback_to_slp1(text)

    @staticmethod
    def to_iast(text: str, source_encoding: str | None = None) -> str:
        """Convert text to IAST encoding (academic standard)"""
        if not HAS_INDIC_TRANSLIT or not transliterate:
            return text

        # Auto-detect source encoding if not provided
        if source_encoding is None:
            source_encoding = EncodingService.detect_encoding(text)

        try:
            if source_encoding == "devanagari" and DEVANAGARI_AVAILABLE and ITRANS_AVAILABLE:
                return transliterate(text, DEVANAGARI_AVAILABLE, ITRANS_AVAILABLE)
            elif source_encoding == "velthuis" and VELTHUIS_AVAILABLE and ITRANS_AVAILABLE:
                return transliterate(text, VELTHUIS_AVAILABLE, ITRANS_AVAILABLE)
            elif source_encoding == "slp1" and SLP1_AVAILABLE and ITRANS_AVAILABLE:
                return transliterate(text, SLP1_AVAILABLE, ITRANS_AVAILABLE)
            else:
                return text
        except Exception:
            return text

    @staticmethod
    def normalize_for_cdsl(text: str) -> str:
        """Convert text to normalized SLP1 format for CDSL lookup"""
        slp1_text = EncodingService.to_slp1(text)
        # Additional normalization: remove extra characters, normalize
        slp1_text = slp1_text.strip()
        slp1_text = slp1_text.lower()
        return slp1_text

    @staticmethod
    def _fallback_to_velthuis(text: str) -> str:
        """Fallback Velthuis conversion using simple mapping"""
        # Basic Velthuis mapping
        velthuis_map = {
            "अ": "a",
            "आ": "A",
            "इ": "i",
            "ई": "I",
            "उ": "u",
            "ऊ": "U",
            "ए": "e",
            "ऐ": "E",
            "ओ": "o",
            "औ": "O",
            "अं": "M",
            "अः": "H",
            "क": "k",
            "ख": "Kh",
            "ग": "g",
            "घ": "Gh",
            "ङ": "N",
            "च": "c",
            "छ": "Ch",
            "ज": "j",
            "झ": "Jh",
            "ञ": "Y",
            "ट": "T",
            "ठ": "Th",
            "ड": "D",
            "ढ": "Dh",
            "ण": "N",
            "त": "t",
            "थ": "th",
            "द": "d",
            "ध": "dh",
            "न": "n",
            "प": "p",
            "फ": "ph",
            "ब": "b",
            "भ": "bh",
            "म": "m",
            "य": "y",
            "र": "r",
            "ल": "l",
            "व": "v",
            "श": "z",
            "ष": "S",
            "स": "s",
            "ह": "h",
            "ळ": "L",
            "क्ष": "K",
            "ज्ञ": "J",
            "ा": "a",
            "ि": "i",
            "ी": "I",
            "ु": "u",
            "ू": "U",
            "े": "e",
            "ै": "E",
            "ो": "o",
            "ौ": "O",
            "ं": "M",
            "ः": "H",
            "्": "",
            "ँ": "~",
            "ऽ": "'",
            "ॐ": "OM",
        }

        result = ""
        for char in text:
            if char in velthuis_map:
                result += velthuis_map[char]
            else:
                result += char

        return result

    @staticmethod
    def _fallback_to_slp1(text: str) -> str:
        """Fallback SLP1 conversion using simple mapping"""
        # Basic SLP1 mapping
        slp1_map = {
            "अ": "a",
            "आ": "A",
            "इ": "i",
            "ई": "I",
            "उ": "u",
            "ऊ": "U",
            "ए": "e",
            "ऐ": "E",
            "ओ": "o",
            "औ": "O",
            "अं": "M",
            "अः": "H",
            "क": "k",
            "ख": "K",
            "ग": "g",
            "घ": "G",
            "ङ": "N",
            "च": "c",
            "छ": "C",
            "ज": "j",
            "झ": "J",
            "ञ": "Y",
            "ट": "w",
            "ठ": "W",
            "ड": "q",
            "ढ": "Q",
            "ण": "R",
            "त": "t",
            "थ": "T",
            "द": "d",
            "ध": "D",
            "न": "n",
            "प": "p",
            "फ": "P",
            "ब": "b",
            "भ": "B",
            "म": "m",
            "य": "y",
            "र": "r",
            "ल": "l",
            "व": "v",
            "श": "S",
            "ष": "z",
            "स": "s",
            "ह": "h",
            "ळ": "Z",
            "क्ष": "kz",
            "ज्ञ": "d~Z",
            "ा": "A",
            "ि": "i",
            "ी": "I",
            "ु": "u",
            "ू": "U",
            "े": "e",
            "ै": "E",
            "ो": "o",
            "ौ": "O",
            "ं": "M",
            "ः": "H",
            "्": "",
            "ँ": "~",
            "ऽ": "'",
            "ॐ": "aM",
        }

        result = ""
        for char in text:
            if char in slp1_map:
                result += slp1_map[char]
            else:
                result += char

        return result.lower()


class SmartVelthuisNormalizer:
    """Smart normalization for Velthuis input variations."""

    # Common Sanskrit vowel patterns
    VOWEL_PATTERNS = {
        r"\ba([^a]|$)": "a",  # Short a at word beginning or before consonant
        r"aa\b": "aa",  # Long aa at word end
        r"\bi([^i]|$)": "i",  # Short i
        r"ii\b": "ii",  # Long ii at word end
        r"\bu([^u]|$)": "u",  # Short u
        r"uu\b": "uu",  # Long uu at word end
    }

    # Common word endings that should be long
    LONG_ENDING_PATTERNS = [
        ("a$", "aa"),  # Final a often should be aa
        ("i$", "ii"),  # Final i often should be ii
        ("u$", "uu"),  # Final u often should be uu
    ]

    @classmethod
    def normalize(cls, text: str, aggressive: bool = False) -> list[str]:
        """Generate normalized Velthuis variants for a given input.

        Returns list of variants to try, ordered by likelihood.
        """
        variants = [text]  # Original first

        # Apply common corrections
        corrected = cls._apply_common_corrections(text)
        if corrected != text:
            variants.append(corrected)

        # Try long vowel variants for word endings
        if aggressive:
            long_variants = cls._generate_long_vowel_variants(text)
            variants.extend(long_variants)

        # Remove duplicates while preserving order
        seen = set()
        unique_variants = []
        for v in variants:
            if v not in seen:
                seen.add(v)
                unique_variants.append(v)

        return unique_variants

    @classmethod
    def _apply_common_corrections(cls, text: str) -> str:
        """Apply common Velthuis corrections."""
        corrections = [
            ("sh", "z"),  # sha → za
            ("Sh", "S"),  # Sha → Sa (retroflex)
            (".a", ".a"),  # Preserve avagraha
            ("RR", "RR"),  # Preserve vowel r
            ("LL", "LL"),  # Preserve vowel l
        ]

        result = text
        for wrong, right in corrections:
            result = result.replace(wrong, right)

        return result

    @classmethod
    def _generate_long_vowel_variants(cls, text: str) -> list[str]:
        """Generate variants with long vowel endings."""
        variants = []

        for pattern, replacement in cls.LONG_ENDING_PATTERNS:
            if re.search(pattern, text):
                long_version = re.sub(pattern, replacement, text)
                variants.append(long_version)

        # Also try adding H (visarga) for nouns
        if text and text[-1].isalpha():
            variants.append(text + "H")

        return variants


class HeritageCdslBridge:
    """Bridge between Heritage Platform and CDSL using proper encoding conversion"""

    def __init__(self):
        self.encoding_service = EncodingService()

    def search_heritage_and_lookup_cdsl(self, query: str, lexicon: str = "MW") -> dict[str, Any]:
        """Search Heritage Platform and lookup results in CDSL"""
        results = {
            "query": query,
            "heritage_search": None,
            "cdsl_lookup": None,
            "encoding_conversions": {},
        }

        try:
            # Convert query to Velthuis for Heritage Platform
            velthuis_query = self.encoding_service.to_velthuis(query)
            slp1_query = self.encoding_service.normalize_for_cdsl(query)

            # Store encoding conversions
            results["encoding_conversions"] = {
                "original": query,
                "detected_encoding": self.encoding_service.detect_encoding(query),
                "velthuis": velthuis_query,
                "slp1": slp1_query,
            }

            # This would be where we call Heritage Platform
            heritage_url = f"/cgi-bin/skt/sktindex?lex={lexicon}&q={velthuis_query}&t=VH"
            results["heritage_search"] = {
                "url": heritage_url,
                "parameters": {
                    "lex": lexicon,
                    "q": velthuis_query,
                    "t": "VH",
                },
            }

            # This would be where we call CDSL
            # For now, just show what the query would be
            results["cdsl_lookup"] = {
                "slp1_key": slp1_query,
                "cdsl_query": f"SELECT * FROM entries WHERE key_normalized = '{slp1_query}'",
            }

        except Exception as e:
            results["error"] = str(e)

        return results

    def process_heritage_response_for_cdsl(self, heritage_response_text: str) -> dict[str, Any]:
        """Process Heritage Platform response and convert headwords for CDSL lookup"""
        try:
            # Extract headwords and POS from Heritage response
            # Pattern to match: headword [ POS ] (POS is grammatical info, not headword)
            # Example: "jātu [ Ind. ]", "agni [ N. ] fire", "deva [ m. ] god"
            headword_pattern = r"([a-zA-Zāīūṛṝḹḹṃḥṅñṭḍṇṣśḻḽ]+)\s*\[([^\]]+)\]"

            # Find all headword-POS pairs
            matches = re.findall(headword_pattern, heritage_response_text)

            if not matches:
                # Fallback: try to find any standalone headwords
                simple_pattern = r"\b([a-zA-Zāīūṛṝḹḹṃḥṅñṭḍṇṣśḻḽ]{3,})\b"
                simple_matches = re.findall(simple_pattern, heritage_response_text)
                if simple_matches:
                    # Use first match as potential headword
                    headword = simple_matches[0]
                    matches = [(headword, "unknown")]
                else:
                    return {"error": "No headwords found in Heritage response"}

            # Convert each headword to SLP1 for CDSL lookup
            cdsl_lookups = []
            pos_info = {}

            for headword, pos in matches:
                # Clean up POS (remove extra spaces)
                pos_clean = pos.strip()

                # Convert headword to SLP1 for CDSL lookup
                try:
                    slp1_headword = self.encoding_service.to_slp1(headword)
                    cdsl_key = slp1_headword.lower()
                except Exception:
                    # Fallback to lowercase
                    slp1_headword = headword
                    cdsl_key = headword.lower()

                cdsl_lookups.append(
                    {
                        "iast": headword,
                        "slp1": slp1_headword,
                        "cdsl_key": cdsl_key,
                        "cdsl_query": f"SELECT * FROM entries WHERE key_normalized = '{cdsl_key}'",
                        "pos": pos_clean,
                    }
                )

                # Store POS info
                pos_info[headword] = pos_clean

            return {
                "heritage_response_text": heritage_response_text,
                "extracted_headwords_pos": matches,
                "headwords_only": [headword for headword, _ in matches],
                "pos_info": pos_info,
                "cdsl_lookups": cdsl_lookups,
            }

        except Exception as e:
            return {"error": str(e)}
