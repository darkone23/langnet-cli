from __future__ import annotations

import importlib
import logging
import re
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from types import ModuleType
from typing import Protocol, cast

from heritage_spec import MonierWilliamsResult, SktSearchResult
from query_spec import CanonicalCandidate, NormalizationStep

from langnet.heritage.velthuis_converter import to_heritage_velthuis

from .base import LanguageNormalizer

logger = logging.getLogger(__name__)
SanscriptCode = str

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
ASCII_FINAL_VOWEL_COMPLETION_MIN_LENGTH = 4


class HeritageClientProtocol(Protocol):
    def fetch_canonical_via_sktsearch(self, query: str) -> SktSearchResult: ...
    def fetch_canonical_sanskrit(self, query: str) -> MonierWilliamsResult: ...
    def fetch_all_matches(self, query: str) -> list: ...
    def fetch_user_feedback_matches(self, velthuis_text: str) -> list: ...


class SanscriptModule(Protocol):
    DEVANAGARI: SanscriptCode
    HK: SanscriptCode
    IAST: SanscriptCode
    SLP1: SanscriptCode
    VELTHUIS: SanscriptCode
    transliterate: Callable[[str, SanscriptCode, SanscriptCode], str]


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

    def user_feedback_matches(self, velthuis_text: str) -> list[SktSearchMatch]:
        if self.client is None:
            return []
        try:
            matches = self.client.fetch_user_feedback_matches(velthuis_text)
            return [
                SktSearchMatch(canonical=m.canonical, display=m.display, entry_url=m.entry_url)
                for m in matches
            ]
        except Exception as exc:  # noqa: BLE001
            logger.debug("sktuser_lookup_failed", extra={"error": str(exc)})
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


def _ascii_fold_for_reader_match(text: str) -> str:
    """Fold Sanskrit diacritics to a reader-typed ASCII comparison key."""
    replacements = {
        "ā": "aa",
        "ī": "ii",
        "ū": "uu",
        "ṛ": "r",
        "ṝ": "rr",
        "ḷ": "l",
        "ḹ": "ll",
        "ṃ": "m",
        "ṁ": "m",
        "ṅ": "n",
        "ñ": "n",
        "ṇ": "n",
        "ṭ": "t",
        "ḍ": "d",
        "ṣ": "s",
        "ś": "s",
        "ḥ": "h",
    }
    return "".join(replacements.get(char, char) for char in text)


def _reader_fold_score(input_text: str, candidate_norms: list[str]) -> tuple[int, int, int, int]:
    input_fold = _ascii_fold_for_reader_match(_normalize_for_comparison(input_text))
    folded = [_ascii_fold_for_reader_match(norm) for norm in candidate_norms if norm]
    if not input_fold or not folded:
        return (1, 1, 10**9, 10**9)
    best = min(
        folded,
        key=lambda norm: (
            _levenshtein(input_fold, norm),
            abs(len(input_fold) - len(norm)),
            len(norm),
        ),
    )
    exact = 0 if best == input_fold else 1
    prefix = 0 if best.startswith(input_fold) or input_fold.startswith(best) else 1
    return (
        exact,
        prefix,
        _levenshtein(input_fold, best),
        abs(len(input_fold) - len(best)),
    )


def sanskrit_candidate_sort_key(input_text: str, candidate: CanonicalCandidate) -> tuple:
    encodings = candidate.encodings or {}
    candidate_norms = [
        norm
        for norm in (
            _normalize_for_comparison(candidate.lemma or ""),
            _normalize_for_comparison(encodings.get(ENC_IAST, "")),
            _normalize_for_comparison(encodings.get(ENC_VELTHUIS, "")),
            _normalize_for_comparison(encodings.get(ENC_SLP1, "")),
        )
        if norm
    ]
    reader_score = _reader_fold_score(input_text, candidate_norms)
    input_norm = _normalize_for_comparison(input_text)
    best_norm = min(
        candidate_norms or [""],
        key=lambda norm: (_levenshtein(input_norm, norm), abs(len(input_norm) - len(norm))),
    )
    return (
        *reader_score,
        _levenshtein(input_norm, best_norm),
        abs(len(input_norm) - len(best_norm)),
        candidate.lemma or "",
    )


def _rank_heritage_matches(input_text: str, matches: list[SktSearchMatch]) -> list[SktSearchMatch]:
    """Rank Heritage matches by similarity to input."""
    if len(matches) <= 1:
        return matches

    input_norm = _normalize_for_comparison(input_text)

    @dataclass(order=True)
    class RankedMatch:
        reader_exact: int
        reader_prefix: int
        reader_dist: int
        reader_len_diff: int
        dist: int
        len_diff: int
        canonical: str = ""
        display: str = ""
        entry_url: str = ""

    ranked: list[RankedMatch] = []
    for m in matches:
        candidate_norms = [
            norm
            for norm in (
                _normalize_for_comparison(m.display),
                _normalize_for_comparison(m.canonical),
            )
            if norm
        ]
        best_norm = min(
            candidate_norms,
            key=lambda norm: (_levenshtein(input_norm, norm), abs(len(input_norm) - len(norm))),
        )
        dist = _levenshtein(input_norm, best_norm)
        len_diff = abs(len(input_norm) - len(best_norm))
        reader_exact, reader_prefix, reader_dist, reader_len_diff = _reader_fold_score(
            input_text,
            candidate_norms,
        )
        ranked.append(
            RankedMatch(
                reader_exact=reader_exact,
                reader_prefix=reader_prefix,
                reader_dist=reader_dist,
                reader_len_diff=reader_len_diff,
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
        mixed_normalized = self._normalize_mixed_iast_ascii_digraphs(stripped)
        if mixed_normalized != stripped:
            steps.append(
                NormalizationStep(
                    operation="mixed_iast_ascii_digraph",
                    input=stripped,
                    output=mixed_normalized,
                    tool="reader_input_normalizer",
                )
            )
            stripped = mixed_normalized
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

        candidates = self._heritage_candidates_for_reader_query(
            stripped,
            encoding,
            velthuis_form,
            steps,
        )

        # Ambiguity fallback: heuristically diacritize reader ASCII and retry Heritage.
        if not candidates and self._should_retry_reader_ascii_variants(stripped, encoding):
            fallback_candidates = self._heritage_retry_with_variants(stripped, steps)
            if fallback_candidates:
                candidates.extend(fallback_candidates)

        if not candidates:
            feedback_candidates = self._heritage_user_feedback(velthuis_form, stripped, steps)
            if feedback_candidates:
                candidates.extend(feedback_candidates)

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

    def _heritage_candidates_for_reader_query(
        self,
        stripped: str,
        encoding: str,
        velthuis_form: str,
        steps: list[NormalizationStep],
    ) -> list[CanonicalCandidate]:
        heritage_query = self._strip_to_alpha(velthuis_form)
        if not heritage_query:
            return []

        matches = self.heritage.all_matches(heritage_query)
        if encoding in {ENC_ASCII, ENC_HK, ENC_SLP1}:
            matches.extend(
                self._final_vowel_completion_matches(
                    stripped,
                    heritage_query,
                    steps,
                )
            )
        if not matches:
            return []

        ranked_matches = _rank_heritage_matches(stripped, matches)
        steps.append(
            NormalizationStep(
                operation="heritage_sktsearch",
                input=heritage_query,
                output=";".join(m.display for m in ranked_matches),
                tool="heritage_sktsearch",
            )
        )
        return [
            CanonicalCandidate(
                lemma=match.display,
                encodings={
                    ENC_VELTHUIS: match.canonical,
                    ENC_IAST: match.display,
                },
                sources=["heritage_sktsearch"],
            )
            for match in ranked_matches
        ]

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
                encodings[ENC_SLP1] = sanscript.transliterate(
                    canonical, sanscript.VELTHUIS, sanscript.SLP1
                )
                encodings[ENC_IAST] = sanscript.transliterate(
                    canonical, sanscript.VELTHUIS, sanscript.IAST
                )
                encodings[ENC_DEVANAGARI] = sanscript.transliterate(
                    canonical, sanscript.VELTHUIS, sanscript.DEVANAGARI
                )
                encodings[ENC_HK] = sanscript.transliterate(
                    canonical, sanscript.VELTHUIS, sanscript.HK
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

    def _heritage_retry_with_variants(
        self, text: str, steps: list[NormalizationStep]
    ) -> list[CanonicalCandidate]:
        """
        When Heritage returns no matches for bare ASCII, try diacritic/long-vowel
        variants and retry.
        """
        variants = self._heuristic_ascii_variants(text)
        candidates: list[CanonicalCandidate] = []
        for variant in variants:
            vel = to_heritage_velthuis(variant).lower()
            heritage_query = self._strip_to_alpha(vel)
            steps.append(
                NormalizationStep(
                    operation="heritage_retry_variant",
                    input=variant,
                    output=vel,
                    tool="ascii_variant",
                )
            )
            if not heritage_query:
                continue
            matches = self.heritage.all_matches(heritage_query)
            if not matches:
                steps.append(
                    NormalizationStep(
                        operation="heritage_retry_variant_result",
                        input=variant,
                        output="miss",
                        tool="heritage_sktsearch",
                    )
                )
                continue
            ranked_matches = _rank_heritage_matches(variant, matches)
            steps.append(
                NormalizationStep(
                    operation="heritage_retry_variant_result",
                    input=variant,
                    output=";".join(m.display for m in ranked_matches),
                    tool="heritage_sktsearch",
                )
            )
            for match in ranked_matches:
                encodings = {
                    ENC_VELTHUIS: match.canonical,
                    ENC_IAST: match.display,
                }
                encodings.update(self._build_encodings(match.canonical, ENC_VELTHUIS, steps))
                candidates.append(
                    CanonicalCandidate(
                        lemma=match.display,
                        encodings=encodings,
                        sources=["heritage_sktsearch_retry"],
                    )
                )
            # Stop after first successful variant to limit search.
            if candidates:
                break
        if not candidates:
            candidates.extend(self._local_reader_ascii_variant_candidates(text, variants, steps))
        return candidates

    def _local_reader_ascii_variant_candidates(
        self,
        original_text: str,
        variants: Sequence[str],
        steps: list[NormalizationStep],
    ) -> list[CanonicalCandidate]:
        original = original_text.lower()
        candidates: list[CanonicalCandidate] = []
        for variant in variants:
            if variant == original or not self._contains_iast(variant):
                continue
            vel = to_heritage_velthuis(variant).lower()
            encodings = self._build_encodings(vel, ENC_VELTHUIS, steps)
            candidates.append(
                CanonicalCandidate(
                    lemma=encodings.get(ENC_IAST, variant),
                    encodings=encodings,
                    sources=["local_reader_ascii_variant"],
                )
            )
            break
        return candidates

    def _final_vowel_completion_matches(
        self,
        original_text: str,
        heritage_query: str,
        steps: list[NormalizationStep],
    ) -> list[SktSearchMatch]:
        """
        Add bounded Sanskrit final-vowel completions for reader-style truncated ASCII.

        This catches common searches like ``karun`` where the user is aiming for
        ``karuṇa``/``karuṇā`` but Heritage's bare ``sktsearch`` prefers ``karin``.
        """
        raw = original_text.strip().lower()
        if (
            len(raw) < ASCII_FINAL_VOWEL_COMPLETION_MIN_LENGTH
            or not raw.isascii()
            or not raw[-1].isalpha()
            or raw[-1] in "aeiou"
        ):
            return []
        matches: list[SktSearchMatch] = []
        seen = {(match.canonical, match.display) for match in matches}
        for query in (f"{heritage_query}a", f"{heritage_query}aa"):
            for match in self.heritage.all_matches(query):
                key = (match.canonical, match.display)
                if key in seen:
                    continue
                seen.add(key)
                matches.append(match)
            if matches:
                steps.append(
                    NormalizationStep(
                        operation="heritage_final_vowel_completion",
                        input=original_text,
                        output=query,
                        tool="heritage_sktsearch",
                    )
                )
        return matches

    def _heritage_user_feedback(
        self, velthuis_form: str, original_text: str, steps: list[NormalizationStep]
    ) -> list[CanonicalCandidate]:
        """Last-resort: hit Heritage sktuser feedback page for guesses."""
        matches = self.heritage.user_feedback_matches(velthuis_form)
        if not matches:
            steps.append(
                NormalizationStep(
                    operation="heritage_sktuser_guess",
                    input=original_text,
                    output="miss",
                    tool="heritage_sktuser_guess",
                )
            )
            return []
        ranked = _rank_heritage_matches(original_text, matches)
        steps.append(
            NormalizationStep(
                operation="heritage_sktuser_guess",
                input=original_text,
                output=";".join(m.display for m in ranked),
                tool="heritage_sktuser_guess",
            )
        )
        candidates: list[CanonicalCandidate] = []
        for match in ranked:
            encodings = {
                ENC_VELTHUIS: match.canonical,
                ENC_IAST: match.display,
            }
            encodings.update(self._build_encodings(match.canonical, ENC_VELTHUIS, steps))
            candidates.append(
                CanonicalCandidate(
                    lemma=match.display,
                    encodings=encodings,
                    sources=["heritage_sktuser_guess"],
                )
            )
        return candidates

    def _heuristic_ascii_variants(self, text: str) -> list[str]:
        """
        Generate a small set of ASCII-with-diacritics variants to catch common Heritage misses.
        """
        base = text.lower()
        bases = [base]
        if (
            len(base) >= ASCII_FINAL_VOWEL_COMPLETION_MIN_LENGTH
            and base.isascii()
            and base[-1].isalpha()
            and base[-1] not in "aeiou"
        ):
            bases.insert(0, f"{base}a")

        variants: list[str] = []

        def add(value: str) -> None:
            if value and value not in variants:
                variants.append(value)

        for candidate_base in bases:
            add(candidate_base)
            # Long vowels
            add(candidate_base.replace("aa", "ā").replace("ii", "ī").replace("uu", "ū"))
            # ś vs ṣ vs s/h
            sh_variant = candidate_base.replace("sh", "ś")
            add(sh_variant)
            add(sh_variant.replace("z", "ṣ"))
            # Retroflex-only swap for bare z → ṣ
            add(candidate_base.replace("z", "ṣ"))
            # Reader ASCII often types plain n for palatal ñ before c/j.
            add(re.sub(r"n(?=(?:ch|jh|[cj]))", "ñ", candidate_base))
            for long_vowel_variant in self._reader_ascii_long_vowel_variants(candidate_base):
                add(long_vowel_variant)
        return variants

    def _should_retry_reader_ascii_variants(self, text: str, encoding: str) -> bool:
        if encoding == ENC_ASCII:
            return True
        return encoding == ENC_HK and text.isascii() and text == text.lower()

    def _reader_ascii_long_vowel_variants(self, text: str) -> list[str]:
        if not text.isascii() or len(text) < MIN_SANSKRIT_LENGTH:
            return []
        variants: list[str] = []
        bases = [text]
        if text.endswith("a"):
            final_long = f"{text[:-1]}ā"
            bases.insert(0, final_long)
        for base in bases:
            for idx, char in enumerate(base):
                replacement = {"a": "ā", "i": "ī", "u": "ū"}.get(char)
                if replacement is None:
                    continue
                variant = f"{base[:idx]}{replacement}{base[idx + 1 :]}"
                if variant != text and variant not in variants:
                    variants.append(variant)
        if text.endswith("a"):
            final_long = f"{text[:-1]}ā"
            if final_long not in variants:
                variants.append(final_long)
        return variants

    def _normalize_mixed_iast_ascii_digraphs(self, text: str) -> str:
        if not self._contains_iast(text):
            return text
        return re.sub(r"([śṣ])h", r"\1", text)

    def _detect_encoding(self, text: str) -> str:
        encoding = ENC_ASCII
        if any(DEVANAGARI_UNICODE_START <= ord(c) <= DEVANAGARI_UNICODE_END for c in text):
            encoding = ENC_DEVANAGARI
        elif self._contains_iast(text):
            encoding = ENC_IAST
        elif self._looks_like_velthuis(text):
            encoding = ENC_VELTHUIS
        elif "sh" not in text.lower():
            detected_encoding = self._detect_with_library(text)
            if detected_encoding == ENC_HK and any(marker in text for marker in "RN"):
                encoding = ENC_HK
            elif self._is_slp1_compatible(text):
                encoding = ENC_SLP1
            elif detected_encoding != ENC_ASCII:
                encoding = detected_encoding
        return encoding

    def _detect_with_library(self, text: str) -> str:
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

    def _ascii_to_velthuis(self, text: str, steps: list[NormalizationStep]) -> str:
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

    def _hk_to_velthuis(self, text: str, steps: list[NormalizationStep]) -> str | None:
        sanscript = self._load_sanscript_module()
        if sanscript is None:
            return None
        try:
            velthuis = sanscript.transliterate(text, sanscript.HK, sanscript.VELTHUIS).lower()
        except Exception:  # noqa: BLE001
            return None
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

    def _to_velthuis(self, text: str, encoding: str, steps: list[NormalizationStep]) -> str:
        if encoding == ENC_ASCII:
            return self._ascii_to_velthuis(text, steps)

        if encoding == ENC_HK:
            converted = self._hk_to_velthuis(text, steps)
            if converted is not None:
                return converted

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
                source_map: dict[str, SanscriptCode] = {
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

    def _load_detect_module(self) -> ModuleType | None:
        try:
            return importlib.import_module("indic_transliteration.detect")
        except Exception:  # noqa: BLE001
            return None

    def _strip_to_alpha(self, text: str) -> str:
        return re.sub(r"[^a-zA-Z]", "", text)

    def _velthuis_to_slp1_basic(self, text: str) -> str:
        s_dot_placeholder = "\u0000"
        heritage_n_placeholder = "\u0001"
        replacements = [
            ("aa", "A"),
            ("ii", "I"),
            ("uu", "U"),
            ("~n", "Y"),
            (".th", "W"),
            (".rr", "F"),
            (".r", "f"),
            (".ll", "X"),
            (".l", "x"),
            (".dh", "Q"),
            (".n", "R"),
            (".t", "w"),
            (".d", "q"),
            (".m", "M"),
            (".h", "H"),
            ("kh", "K"),
            ("gh", "G"),
            ("ch", "C"),
            ("jh", "J"),
            ("th", "T"),
            ("dh", "D"),
            ("ph", "P"),
            ("bh", "B"),
            ("sh", "S"),
            ("'s", "S"),
        ]
        out = text.replace(".s", s_dot_placeholder)
        # Heritage's dictionary anchors use bare `f` for ṅ; `.r` below still maps to SLP1 `f`.
        out = out.replace("f", heritage_n_placeholder)
        for old, new in replacements:
            out = out.replace(old, new)
        out = out.replace("z", "S")
        out = out.replace(heritage_n_placeholder, "N")
        return out.replace(s_dot_placeholder, "z")
