from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Protocol

import structlog
from indic_transliteration.detect import detect
from indic_transliteration.sanscript import DEVANAGARI, SLP1, VELTHUIS, transliterate
from langnet.cologne.core import to_slp1 as cdsl_to_slp1
from langnet.heritage.encoding_service import EncodingService
from langnet.normalization import NormalizationPipeline
from langnet.normalization.models import CanonicalQuery

from langnet.heritage.client import HeritageHTTPClient

logger = structlog.get_logger(__name__)


@dataclass(frozen=True)
class SanskritNormalizationResult:
    canonical_heritage: str
    canonical_slp1: str
    slp1_candidates: list[str]
    canonical_tokens: list[str] | None
    input_form: str


class NormalizationPipelineProtocol(Protocol):
    _initialized: bool

    def initialize(self) -> None: ...

    def normalize_query(self, language: str, query: str) -> CanonicalQuery: ...


class HeritageClientProtocol(Protocol):
    def fetch_canonical_via_sktsearch(self, word: str) -> Mapping[str, str] | None: ...


class SanskritQueryNormalizer:
    """Normalize Sanskrit queries into Heritage and SLP1 forms with fallbacks."""

    def __init__(
        self,
        heritage_client: HeritageHTTPClient | HeritageClientProtocol | None = None,
        normalization_pipeline: NormalizationPipeline | NormalizationPipelineProtocol | None = None,
    ):
        self.heritage_client = heritage_client
        self.normalization_pipeline = normalization_pipeline

    def normalize(self, word: str) -> SanskritNormalizationResult:
        heritage_form = word
        slp1_form = word
        slp1_candidates: list[str] = []
        canonical_tokens: list[str] | None = None

        normalized_query = self._run_pipeline(word)
        if normalized_query:
            heritage_form, slp1_form, slp1_candidates, canonical_tokens = self._apply_pipeline(
                word, normalized_query
            )

        if heritage_form == word and self.heritage_client:
            heritage_form = self._canonical_from_heritage(word) or heritage_form

        slp1_form, slp1_candidates = self._build_slp1_forms(
            word, heritage_form, slp1_form, slp1_candidates
        )

        slp1_candidates = self._build_variant_candidates(slp1_candidates)
        slp1_candidates = self._deduplicate_candidates(slp1_candidates)

        return SanskritNormalizationResult(
            canonical_heritage=heritage_form,
            canonical_slp1=slp1_form,
            slp1_candidates=slp1_candidates,
            canonical_tokens=canonical_tokens,
            input_form=word,
        )

    def _build_slp1_forms(
        self, word: str, heritage_form: str, slp1_form: str, slp1_candidates: list[str]
    ) -> tuple[str, list[str]]:
        if slp1_form == word:
            slp1_form = self._to_slp1(heritage_form)
        if not slp1_candidates:
            slp1_candidates.append(slp1_form)

        slp1_candidates.append(self._velthuis_to_slp1_basic(heritage_form))

        if self._looks_mangled_slp1(slp1_form):
            slp1_form = self._velthuis_to_slp1_basic(heritage_form)

        try:
            cdsl_slp1 = cdsl_to_slp1(heritage_form, source_encoding="velthuis")
            if cdsl_slp1:
                slp1_candidates.append(cdsl_slp1)
                slp1_form = cdsl_slp1
        except Exception:
            pass

        self._add_devanagari_candidate(heritage_form, slp1_form, slp1_candidates)

        return slp1_form, slp1_candidates

    def _add_devanagari_candidate(
        self, heritage_form: str, slp1_form: str, slp1_candidates: list[str]
    ) -> None:
        try:
            source_slp1 = slp1_form if slp1_form else heritage_form
            devanagari_form = transliterate(source_slp1, SLP1, DEVANAGARI)
            if devanagari_form:
                slp1_candidates.append(devanagari_form)
        except Exception:
            pass

    def _build_variant_candidates(self, slp1_candidates: list[str]) -> list[str]:
        all_candidates = []
        for candidate in slp1_candidates:
            all_candidates.append(candidate)
            all_candidates.extend(self._generate_slp1_variants(candidate))
        return all_candidates

    def _deduplicate_candidates(self, slp1_candidates: list[str]) -> list[str]:
        seen: set[str] = set()
        return [c for c in slp1_candidates if c and not (c in seen or seen.add(c))]

    def _run_pipeline(self, word: str) -> CanonicalQuery | None:
        if not self.normalization_pipeline:
            return None

        pipeline = self.normalization_pipeline
        if not getattr(pipeline, "_initialized", False):
            try:
                pipeline.initialize()
            except Exception as exc:  # noqa: BLE001
                logger.warning("normalization_pipeline_init_failed", error=str(exc))
                return None

        try:
            return pipeline.normalize_query("san", word)
        except Exception as exc:  # noqa: BLE001
            logger.warning("normalization_pipeline_failed", word=word, error=str(exc))
            return None

    def _apply_pipeline(
        self, word: str, normalized: CanonicalQuery
    ) -> tuple[str, str, list[str], list[str] | None]:
        heritage_form = normalized.canonical_text or word
        canonical_tokens: list[str] | None = None
        if heritage_form and " " in heritage_form:
            canonical_tokens = [tok for tok in heritage_form.split(" ") if tok]
            if canonical_tokens:
                heritage_form = canonical_tokens[0]

        slp1_form = self._first_slp1_alternate(normalized.alternate_forms) or word
        slp1_candidates = self._slp1_candidates_from_alternates(normalized.alternate_forms)

        return heritage_form, slp1_form, slp1_candidates, canonical_tokens

    def _canonical_from_heritage(self, word: str) -> str | None:
        try:
            canonical = (
                self.heritage_client.fetch_canonical_via_sktsearch(word)
                if self.heritage_client
                else None
            )
            canon_text = canonical.get("canonical_text") if canonical else None
            return canon_text or None
        except Exception as exc:  # noqa: BLE001
            logger.debug("sktsearch_canonical_failed", word=word, error=str(exc))
            return None

    @staticmethod
    def detect_heritage_encoding(word: str) -> str:
        """
        Detect encoding for Heritage endpoints using the shared EncodingService.
        Falls back to velthuis to maximize hit rate.
        """
        try:
            encoding = EncodingService.detect_encoding(word)
        except Exception:
            return "velthuis"
        if encoding in {"devanagari", "iast", "hk", "slp1"}:
            return "velthuis"
        return encoding or "velthuis"

    @staticmethod
    def _to_slp1(text: str) -> str:
        """Transliterate Sanskrit text to SLP1 for CDSL/ASCII backends."""
        try:
            src = detect(text)
            looks_velthuis = any(ch in text for ch in [".", "~", "aa", "ii", "uu"])
            src_scheme = VELTHUIS if looks_velthuis else src
            return transliterate(text, src_scheme, SLP1)
        except Exception:
            return text

    @staticmethod
    def _first_slp1_alternate(alternates: list[str]) -> str | None:
        """Return the first SLP1-looking alternate if present."""
        for alt in alternates:
            try:
                if detect(alt) == "slp1":
                    return alt.lower()
            except Exception:
                continue
        return None

    @staticmethod
    def _slp1_candidates_from_alternates(alternates: list[str]) -> list[str]:
        candidates: list[str] = []
        for alt in alternates:
            try:
                if detect(alt) == "slp1":
                    candidates.append(alt.lower())
            except Exception:
                continue
        return candidates

    @staticmethod
    def _velthuis_to_slp1_basic(text: str) -> str:
        """Simple Velthuis to SLP1 mapper for fallback canonicalization."""
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

    @staticmethod
    def _looks_mangled_slp1(text: str) -> bool:
        """Detect obvious transliteration artifacts like digits/quotes in SLP1 output."""
        return any(ch.isdigit() or ch in {'"', "'"} for ch in text)

    @staticmethod
    def _generate_slp1_variants(text: str) -> list[str]:
        """Generate variant SLP1 interpretations for ambiguous ASCII input.

        ASCII transliteration is ambiguous:
        - 'sh' could be z (ś/palatal), S (ṣ/retroflex), or s (dental)
        - 'r' before consonant could be ṛ (vocalic r = f in SLP1)
        - 'ri' could be r+i or ṛ (f in SLP1) + following vowel
        """
        variants: list[str] = [text]  # Always include original

        text_lower = text.lower()

        # Generate 'sh' variants (palatal vs retroflex)
        if "sh" in text_lower:
            # Try palatal interpretation (z)
            variants.append(text_lower.replace("sh", "z"))
            # Try retroflex interpretation (S)
            variants.append(text_lower.replace("sh", "S"))

        # Generate variants for vocalic ṛ (SLP1 'f') interpretation
        # Pattern: consonant + 'r' or 'ri' + consonant
        # Examples: krishna -> kfSna (kṛṣṇa), kripa -> kfpa (kṛpā)

        # Try to identify potential vocalic ṛ positions
        # Look for 'r' or 'ri' between consonants where it might be ṛ
        for pattern in [
            r"([kgcjtdnpbmyrlvw])ri([szSZkgcjtdnpbmyrlv])",  # 'cri' pattern
            r"([kgcjtdnpbmyrlvw])r([szSZkgcjtdnpbmyrlv])",  # 'cr' pattern
        ]:
            if re.search(pattern, text_lower):
                # Replace 'ri' or 'r' with 'f' (vocalic ṛ in SLP1)
                variant = re.sub(
                    r"([kgcjtdnpbmyrlvw])ri([szSZkgcjtdnpbmyrlv])", r"\1f\2", text_lower
                )
                variant = re.sub(r"([kgcjtdnpbmyrlvw])r([szSZkgcjtdnpbmyrlv])", r"\1f\2", variant)
                if variant not in variants:
                    variants.append(variant)

        # Generate dental 's' variants for CDSL compatibility
        # CDSL uses simplified keys where z (palatal) and S (retroflex) both map to s
        dental_variants = []
        for variant in list(variants):  # Use list() to avoid modifying during iteration
            if "z" in variant or "S" in variant:
                dental = variant.replace("z", "s").replace("S", "s")
                if dental not in variants and dental not in dental_variants:
                    dental_variants.append(dental)
        variants.extend(dental_variants)

        return list(dict.fromkeys(variants))  # Deduplicate while preserving order
