from __future__ import annotations

import importlib
import logging
import re
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Protocol, cast

from heritage_spec import MonierWilliamsResult, SktSearchResult
from query_spec import CanonicalCandidate, NormalizationStep

from langnet.heritage.velthuis_converter import to_heritage_velthuis

from .base import LanguageNormalizer

logger = logging.getLogger(__name__)

ENC_ASCII = "ascii"
ENC_DEVANAGARI = "devanagari"
ENC_IAST = "iast"
ENC_VELTHUIS = "velthuis"
ENC_SLP1 = "slp1"
ENC_HK = "hk"

MIN_TOKENS_FOR_CANONICAL = 2
MIN_QUERY_LENGTH_HERITAGE = 2
MAX_QUERY_LENGTH_HERITAGE = 50
MIN_SANSKRIT_LENGTH = 3
MAX_SANSKRIT_LENGTH = 15
MIN_SANSKRIT_CONFIDENCE = 0.5
MAX_ASCII_CODE = 127
DEVANAGARI_UNICODE_START = 0x0900
DEVANAGARI_UNICODE_END = 0x097F


class HeritageClientProtocol(Protocol):
    def fetch_canonical_via_sktsearch(self, query: str) -> SktSearchResult: ...
    def fetch_canonical_sanskrit(self, query: str) -> MonierWilliamsResult: ...
    def fetch_all_matches(self, query: str) -> list: ...


class SanscriptModule(Protocol):
    DEVANAGARI: object
    HK: object
    IAST: object
    SLP1: object
    VELTHUIS: object
    transliterate: Callable[[str, object, object], str]


@dataclass(frozen=True)
class SktSearchMatch:
    canonical: str  # Velthuis form for internal use
    display: str  # IAST form from Heritage
    entry_url: str


class HeritageCanonicalizer:
    """
    Thin wrapper for Heritage lookups. It is intentionally dumb: callers inject
    a client with fetch_* methods or rely on heuristics when unavailable.
    """

    def __init__(self, client: HeritageClientProtocol | None = None) -> None:
        self.client = client

    def all_matches(self, text: str) -> list[SktSearchMatch]:
        if self.client is None:
            return []
        try:
            matches = self.client.fetch_all_matches(text)
            return [
                SktSearchMatch(canonical=m.canonical, display=m.display, entry_url=m.entry_url)
                for m in matches
            ]
        except Exception as exc:  # noqa: BLE001
            logger.debug("sktsearch_lookup_failed", extra={"error": str(exc)})
        return []

    def canonical_via_sktsearch(self, text: str) -> SktSearchResult | None:
        if self.client is None:
            return None
        try:
            result = self.client.fetch_canonical_via_sktsearch(text)
            if result.canonical_text:
                return result
        except Exception as exc:  # noqa: BLE001
            logger.debug("sktsearch_lookup_failed", extra={"error": str(exc)})
        return None

    def canonical_via_mw(self, text: str) -> MonierWilliamsResult | None:
        if self.client is None:
            return None
        try:
            result = self.client.fetch_canonical_sanskrit(text)
            if result.canonical_sanskrit:
                return result
        except Exception as exc:  # noqa: BLE001
            logger.debug("heritage_mw_lookup_failed", extra={"error": str(exc)})
        return None


@dataclass(frozen=True)
class HeritageEnrichment:
    """Internal record of Heritage enrichment result."""

    canonical_text: str
    match_method: str
    entry_url: str = ""


def _levenshtein(a: str, b: str) -> int:
    if a == b:
        return 0
    if not a:
        return len(b)
    if not b:
        return len(a)
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, start=1):
        curr = [i]
        for j, cb in enumerate(b, start=1):
            cost = 0 if ca == cb else 1
            curr.append(min(prev[j] + 1, curr[j - 1] + 1, prev[j - 1] + cost))
        prev = curr
    return prev[-1]


def _normalize_for_comparison(text: str) -> str:
    """Normalize to lowercase IAST-like form for comparison."""
    normalized = text.lower()
    normalized = re.sub(r"\.", "", normalized)
    normalized = re.sub(r"[^a-zāīūṛṝḷḹṃṅñṇṭḍṣśṛ]", "", normalized)
    return normalized


def _rank_heritage_matches(input_text: str, matches: list[SktSearchMatch]) -> list[SktSearchMatch]:
    """Rank Heritage matches by similarity to input."""
    if len(matches) <= 1:
        return matches

    input_norm = _normalize_for_comparison(input_text)

    @dataclass(order=True)
    class RankedMatch:
        dist: int
        len_diff: int
        canonical: str = ""
        display: str = ""
        entry_url: str = ""

    ranked: list[RankedMatch] = []
    for m in matches:
        candidate_norm = _normalize_for_comparison(m.canonical)
        dist = _levenshtein(input_norm, candidate_norm)
        len_diff = abs(len(input_norm) - len(candidate_norm))
        ranked.append(
            RankedMatch(
                dist=dist,
                len_diff=len_diff,
                canonical=m.canonical,
                display=m.display,
                entry_url=m.entry_url,
            )
        )

    ranked.sort()
    return [
        SktSearchMatch(canonical=r.canonical, display=r.display, entry_url=r.entry_url)
        for r in ranked
    ]


class SanskritNormalizer(LanguageNormalizer):
    """
    Sanskrit canonicalization with Heritage dialect handling and optional enrichment.
    """

    def __init__(self, heritage_client: HeritageClientProtocol | None = None) -> None:
        self.heritage = HeritageCanonicalizer(heritage_client)

    def canonical_candidates(
        self, text: str, steps: list[NormalizationStep]
    ) -> Sequence[CanonicalCandidate]:
        if not text:
            return [CanonicalCandidate(lemma=text, encodings={}, sources=["local"])]

        stripped = text.strip()
        encoding = self._detect_encoding(stripped)
        steps.append(
            NormalizationStep(
                operation="detect_encoding",
                input=stripped,
                output=encoding,
                tool="sanskrit_detection",
            )
        )

        velthuis_form = self._to_velthuis(stripped, encoding, steps)

        candidates: list[CanonicalCandidate] = []

        heritage_query = self._strip_to_alpha(velthuis_form)
        if heritage_query:
            matches = self.heritage.all_matches(heritage_query)
            if matches:
                ranked_matches = _rank_heritage_matches(stripped, matches)
                steps.append(
                    NormalizationStep(
                        operation="heritage_sktsearch",
                        input=heritage_query,
                        output=";".join(m.display for m in ranked_matches),
                        tool="heritage_sktsearch",
                    )
                )
                for match in ranked_matches:
                    encodings: dict[str, str] = {
                        "velthuis": match.canonical,
                        "iast": match.display,
                    }
                    candidates.append(
                        CanonicalCandidate(
                            lemma=match.display,
                            encodings=encodings,
                            sources=["heritage_sktsearch"],
                        )
                    )

        if not candidates:
            encodings = self._build_encodings(velthuis_form, encoding, steps)
            candidates.append(
                CanonicalCandidate(lemma=velthuis_form, encodings=encodings, sources=["local"])
            )

        return self._dedupe_candidates(candidates)

    def _dedupe_candidates(self, candidates: list[CanonicalCandidate]) -> list[CanonicalCandidate]:
        seen: set[str] = set()
        result: list[CanonicalCandidate] = []
        for c in candidates:
            if c.lemma not in seen:
                seen.add(c.lemma)
                result.append(c)
        return result

    def _build_encodings(
        self,
        canonical: str,
        source_encoding: str,
        steps: list[NormalizationStep],
    ) -> dict[str, str]:
        encodings: dict[str, str] = {ENC_VELTHUIS: canonical}

        sanscript = self._load_sanscript_module()
        if sanscript is not None:
            try:
                src_scheme = (
                    sanscript.HK if source_encoding in {ENC_ASCII, ENC_HK} else sanscript.VELTHUIS
                )

                encodings[ENC_SLP1] = sanscript.transliterate(canonical, src_scheme, sanscript.SLP1)
                encodings[ENC_IAST] = sanscript.transliterate(canonical, src_scheme, sanscript.IAST)
                encodings[ENC_DEVANAGARI] = sanscript.transliterate(
                    canonical, src_scheme, sanscript.DEVANAGARI
                )
                encodings[ENC_HK] = sanscript.transliterate(
                    canonical, src_scheme, sanscript.HK
                ).lower()

                steps.append(
                    NormalizationStep(
                        operation="transliteration_variants",
                        input=canonical,
                        output=";".join(
                            [encodings.get(k, "") for k in [ENC_SLP1, ENC_IAST, ENC_DEVANAGARI]]
                        ),
                        tool="indic_transliteration.sanscript",
                    )
                )
                return encodings
            except Exception:  # noqa: BLE001
                encodings[ENC_SLP1] = self._velthuis_to_slp1_basic(canonical)

        if ENC_SLP1 not in encodings:
            encodings[ENC_SLP1] = self._velthuis_to_slp1_basic(canonical)

        steps.append(
            NormalizationStep(
                operation="transliteration_variants",
                input=canonical,
                output=encodings[ENC_SLP1],
                tool="velthuis_basic_fallback",
            )
        )

        return encodings

    def _build_alternate_candidates(
        self, canonical: str, encodings: dict[str, str], steps: list[NormalizationStep]
    ) -> list[tuple[str, dict[str, str]]]:
        alternates: list[tuple[str, dict[str, str]]] = []

        return alternates

    def _detect_encoding(self, text: str) -> str:
        if any(DEVANAGARI_UNICODE_START <= ord(c) <= DEVANAGARI_UNICODE_END for c in text):
            return ENC_DEVANAGARI

        if self._contains_iast(text):
            return ENC_IAST

        if self._looks_like_velthuis(text):
            return ENC_VELTHUIS

        if self._is_slp1_compatible(text):
            return ENC_SLP1

        detected_encoding = ENC_ASCII
        detect_module = self._load_detect_module()
        if detect_module is not None:
            detect_fn = getattr(detect_module, "detect", None)
            if detect_fn is not None:
                try:
                    detected = detect_fn(text)
                except Exception:  # noqa: BLE001
                    detected = None
                if detected:
                    detected_str = str(detected).lower()
                    mapping = {
                        "devanagari": ENC_DEVANAGARI,
                        "iast": ENC_IAST,
                        "hk": ENC_HK,
                        "itrans": ENC_HK,
                        "velthuis": ENC_VELTHUIS,
                        "slp1": ENC_SLP1,
                    }
                    detected_encoding = mapping.get(detected_str, ENC_ASCII)

        return detected_encoding

    def _contains_iast(self, text: str) -> bool:
        iast_chars = set("āīūṛṝḷḹṃṅñṇṟṣśṭḍḥṁ")
        return any(c in iast_chars for c in text)

    def _looks_like_velthuis(self, text: str) -> bool:
        markers = ["_", ".", "~", "^", "aa", "ii", "uu"]
        return any(marker in text for marker in markers)

    def _is_slp1_compatible(self, text: str) -> bool:
        slp1_valid = set("aAiIuUfFxXeEoOkgGcCjJwWqQRtTdDpbBmnyYrlvSzshN")
        if not all(c.lower() in slp1_valid for c in text if c.isalpha()):
            return False
        return any(c.isupper() for c in text)

    def _to_velthuis(self, text: str, encoding: str, steps: list[NormalizationStep]) -> str:
        if encoding in {ENC_ASCII, ENC_HK}:
            velthuis = text.replace("Sh", "S").replace("sh", "z").lower()
            if velthuis != text.lower():
                steps.append(
                    NormalizationStep(
                        operation="to_heritage_velthuis",
                        input=text,
                        output=velthuis,
                        tool="ascii_to_velthuis_map",
                    )
                )
            return velthuis

        if encoding in {ENC_DEVANAGARI, ENC_IAST}:
            vel = to_heritage_velthuis(text).lower()
            if vel != text:
                steps.append(
                    NormalizationStep(
                        operation="to_heritage_velthuis",
                        input=text,
                        output=vel,
                        tool="heritage_velthuis_converter",
                    )
                )
            return vel

        sanscript = self._load_sanscript_module()
        if sanscript is not None:
            try:
                source_map: dict[str, object] = {
                    ENC_DEVANAGARI: sanscript.DEVANAGARI,
                    ENC_IAST: sanscript.IAST,
                    ENC_VELTHUIS: sanscript.VELTHUIS,
                    ENC_SLP1: sanscript.SLP1,
                    ENC_HK: sanscript.HK,
                    ENC_ASCII: sanscript.HK,
                }
                src_scheme = source_map.get(encoding, sanscript.HK)
                velthuis = sanscript.transliterate(text, src_scheme, sanscript.VELTHUIS).lower()
                if velthuis != text:
                    steps.append(
                        NormalizationStep(
                            operation="to_heritage_velthuis",
                            input=text,
                            output=velthuis,
                            tool="indic_transliteration.sanscript",
                        )
                    )
                return velthuis
            except Exception:  # noqa: BLE001
                pass

        velthuis = to_heritage_velthuis(text).lower()
        if velthuis != text:
            steps.append(
                NormalizationStep(
                    operation="to_heritage_velthuis",
                    input=text,
                    output=velthuis,
                    tool="heritage_velthuis_converter",
                )
            )
        return velthuis

    def _load_sanscript_module(self) -> SanscriptModule | None:
        try:
            module = importlib.import_module("indic_transliteration.sanscript")
            return cast(SanscriptModule, module)
        except Exception:  # noqa: BLE001
            return None

    def _load_detect_module(self) -> object | None:
        try:
            return importlib.import_module("indic_transliteration.detect")
        except Exception:  # noqa: BLE001
            return None

    def _strip_to_alpha(self, text: str) -> str:
        return re.sub(r"[^a-zA-Z]", "", text)

    def _velthuis_to_slp1_basic(self, text: str) -> str:
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
