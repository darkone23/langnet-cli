from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import structlog

from langnet.cologne.core import to_slp1 as cdsl_to_slp1
from langnet.heritage.client import HeritageHTTPClient
from langnet.heritage.encoding_service import EncodingService
from langnet.normalization import NormalizationPipeline
from langnet.normalization.models import CanonicalQuery, Encoding

logger = structlog.get_logger(__name__)


@dataclass(frozen=True)
class SanskritNormalizationResult:
    canonical_heritage: str
    canonical_slp1: str
    slp1_candidates: list[str]
    canonical_tokens: list[str] | None
    input_form: str


class SanskritQueryNormalizer:
    """Normalize Sanskrit queries into Heritage and SLP1 forms with fallbacks."""

    def __init__(
        self,
        heritage_client: HeritageHTTPClient | None = None,
        normalization_pipeline: NormalizationPipeline | None = None,
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

        if slp1_form == word:
            slp1_form = self._to_slp1(heritage_form)
        if not slp1_candidates:
            slp1_candidates.append(slp1_form)

        slp1_candidates.append(self._velthuis_to_slp1_basic(heritage_form))

        if self._looks_mangled_slp1(slp1_form):
            slp1_form = self._velthuis_to_slp1_basic(heritage_form)

        try:
            cdsl_slp1 = cdsl_to_slp1(heritage_form)
            if cdsl_slp1:
                slp1_candidates.append(cdsl_slp1)
                slp1_form = cdsl_slp1
        except Exception:
            pass

        # Deduplicate while preserving order
        seen: set[str] = set()
        slp1_candidates = [c for c in slp1_candidates if c and not (c in seen or seen.add(c))]

        return SanskritNormalizationResult(
            canonical_heritage=heritage_form,
            canonical_slp1=slp1_form,
            slp1_candidates=slp1_candidates,
            canonical_tokens=canonical_tokens,
            input_form=word,
        )

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
            canonical = self.heritage_client.fetch_canonical_via_sktsearch(word)  # type: ignore[operator]
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
            from indic_transliteration.detect import detect  # noqa: PLC0415
            from indic_transliteration.sanscript import (  # noqa: PLC0415
                SLP1,
                VELTHUIS,
                transliterate,
            )

            src = detect(text)
            looks_velthuis = any(ch in text for ch in [".", "~", "aa", "ii", "uu"])
            src_scheme = VELTHUIS if looks_velthuis else src
            return transliterate(text, src_scheme, SLP1)
        except Exception:
            return text

    @staticmethod
    def _first_slp1_alternate(alternates: list[str]) -> str | None:
        """Return the first SLP1-looking alternate if present."""
        try:
            from indic_transliteration.detect import detect  # noqa: PLC0415
        except Exception:
            return None

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
        try:
            from indic_transliteration.detect import detect  # noqa: PLC0415
        except Exception:
            return candidates

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
        return any(ch.isdigit() or ch in {"\"", "'"} for ch in text)
