from __future__ import annotations

import hashlib
import importlib
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol

from query_spec import CanonicalCandidate, LanguageHint, NormalizationStep, NormalizedQuery

from langnet.normalizer.sanskrit import HeritageClientProtocol

if TYPE_CHECKING:
    from langnet.diogenes.client import (
        ParseResult,
        WordListResult,
        _levenshtein,
        _normalize_for_distance,
    )
    from langnet.diogenes.client import (
        WordListResult as DioWordListResult,
    )
else:
    ParseResult = object
    WordListResult = object
    DioWordListResult = object
    _levenshtein = None
    _normalize_for_distance = None

from .base import LanguageNormalizer
from .greek_transliterator import (
    _greek_to_betacode,
    transliterate,
    transliterate_variants,
)
from .utils import contains_greek, strip_accents

LanguageValue = LanguageHint.ValueType


def _hash_query(raw_query: str, language: LanguageValue) -> str:
    # LanguageHint protobuf enums are integers, so use them directly
    material = f"{language}:{raw_query}"
    return hashlib.sha256(material.encode("utf-8")).hexdigest()[:16]


def _load_betacode_conv():
    try:
        betacode = importlib.import_module("betacode")
        return getattr(betacode, "conv", None)
    except Exception:
        return None


@dataclass
class NormalizationResult:
    query_hash: str
    normalized: NormalizedQuery


class DiogenesLatinClientProtocol(Protocol):
    def fetch_parse(self, query: str, lang: str = "lat") -> ParseResult: ...


class DiogenesGreekClientProtocol(Protocol):
    def fetch_word_list(self, query: str) -> WordListResult: ...


class WhitakerClientProtocol(Protocol):
    def fetch(self, query: str) -> list[str]: ...


class LatinNormalizer(LanguageNormalizer):
    def __init__(
        self,
        diogenes_client: DiogenesLatinClientProtocol | None = None,
        whitaker_client: WhitakerClientProtocol | None = None,
    ) -> None:
        self.diogenes = diogenes_client
        self.whitaker = whitaker_client

    def canonical_candidates(
        self, text: str, steps: list[NormalizationStep]
    ) -> Sequence[CanonicalCandidate]:
        lemma_sources: dict[str, set[str]] = {}

        self._add_diogenes_sources(text, steps, lemma_sources)
        self._add_whitaker_sources(text, steps, lemma_sources)

        candidates: list[CanonicalCandidate] = [
            CanonicalCandidate(lemma=lemma, encodings={}, sources=sorted(sources))
            for lemma, sources in lemma_sources.items()
        ]

        if text not in lemma_sources:
            candidates.append(CanonicalCandidate(lemma=text, encodings={}, sources=["local"]))
        return candidates

    def _add_diogenes_sources(
        self, text: str, steps: list[NormalizationStep], lemma_sources: dict[str, set[str]]
    ) -> None:
        if self.diogenes is None:
            return
        try:
            parse = self.diogenes.fetch_parse(text, lang="lat")
        except Exception:  # noqa: BLE001
            return

        steps.append(
            NormalizationStep(
                operation="diogenes_parse",
                input=text,
                output=";".join(parse.lemmas),
                tool="diogenes",
            )
        )
        self._record_sources(parse.lemmas, "diogenes_parse", lemma_sources)

    def _add_whitaker_sources(
        self, text: str, steps: list[NormalizationStep], lemma_sources: dict[str, set[str]]
    ) -> None:
        if self.whitaker is None:
            return
        try:
            lemmas = self.whitaker.fetch(text)
        except Exception:  # noqa: BLE001
            return

        if not lemmas:
            return

        steps.append(
            NormalizationStep(
                operation="whitakers_lookup",
                input=text,
                output=";".join(lemmas),
                tool="whitakers",
            )
        )
        self._record_sources(lemmas, "whitakers", lemma_sources)

    def _record_sources(
        self, lemmas: list[str], source: str, lemma_sources: dict[str, set[str]]
    ) -> None:
        for lemma in lemmas:
            sources = lemma_sources.setdefault(lemma, set())
            sources.add(source)


class GreekNormalizer(LanguageNormalizer):
    """
    Greek canonicalization using betacode conversions and accent stripping.
    """

    def __init__(self, diogenes_client: DiogenesGreekClientProtocol | None = None) -> None:
        self.diogenes = diogenes_client

    def canonical_candidates(
        self, text: str, steps: list[NormalizationStep]
    ) -> Sequence[CanonicalCandidate]:
        candidates: list[CanonicalCandidate] = []
        base = text

        candidates.extend(self._diogenes_candidates(base, steps))
        candidates.extend(self._local_candidates(base, steps))
        return candidates

    def _diogenes_candidates(
        self, base: str, steps: list[NormalizationStep]
    ) -> list[CanonicalCandidate]:
        if self.diogenes is None:
            return []

        result = self._fetch_word_list_with_fallback(base, steps)
        if result is None or not result.lemmas:
            return []

        candidates: list[CanonicalCandidate] = []
        for lemma in result.lemmas:
            encodings: dict[str, str] = {}
            if result.frequencies:
                freq = result.frequencies.get(lemma)
                if freq is not None:
                    encodings["freq"] = str(freq)
            stripped = strip_accents(lemma)
            betacode_variants = _betacode_variants(lemma, stripped)
            if betacode_variants:
                encodings["betacode"] = betacode_variants[0]
            elif contains_greek(lemma):
                encodings["betacode"] = _greek_to_betacode(lemma)
            candidates.append(
                CanonicalCandidate(lemma=lemma, encodings=encodings, sources=["diogenes_word_list"])
            )
        return candidates

    def _fetch_word_list_with_fallback(
        self, base: str, steps: list[NormalizationStep]
    ) -> WordListResult | None:
        if self.diogenes is None:
            return None
        # If base is not Greek, transliterate before fetch.
        query_val = base
        variants: list[str] = []
        if not contains_greek(base):
            translits = transliterate_variants(base)
            if translits:
                # Record the primary transliteration step once
                steps.append(
                    NormalizationStep(
                        operation="greek_transliterate",
                        input=base,
                        output=translits[0].search_key,
                        tool="greek_transliterator",
                    )
                )
                query_val = translits[0].search_key
                # Only query Greek Unicode variants; skip betacode to avoid extra calls
                variants = [t.search_key for t in translits[1:] if t.search_key]

        results: list[WordListResult] = []
        primary = self._attempt_word_list(query_val, steps, "diogenes_word_list")
        if primary:
            results.append(primary)
        for alt in variants:
            if not alt:
                continue
            variant_result = self._attempt_word_list(alt, steps, "diogenes_word_list_fallback")
            if variant_result:
                results.append(variant_result)
        if not results:
            return None
        return self._merge_word_list_results(query_val, results)

    def _merge_word_list_results(self, query: str, results: list[WordListResult]) -> WordListResult:
        # Lazy import to avoid pulling BeautifulSoup-heavy diogenes client on fast paths
        from langnet.diogenes.client import (  # noqa: I001, PLC0415
            WordListResult as DioWordListResult,
            _levenshtein,
            _normalize_for_distance,
        )

        merged_lemmas: list[str] = []
        merged_freqs: dict[str, int] = {}
        seen: set[str] = set()
        for res in results:
            freqs = res.frequencies or {}
            for lemma in res.lemmas:
                if lemma not in seen:
                    seen.add(lemma)
                    merged_lemmas.append(lemma)
                if lemma in freqs:
                    current = merged_freqs.get(lemma, 0)
                    merged_freqs[lemma] = max(current, freqs[lemma])
        # Re-rank merged lemmas using the normalized distance heuristic and frequencies
        total = sum(merged_freqs.values()) or 1
        target_norm = _normalize_for_distance(query)
        ranked = sorted(
            merged_lemmas,
            key=lambda lemma: (
                _levenshtein(_normalize_for_distance(lemma), target_norm),
                -((merged_freqs.get(lemma, 0) / total) if total else 0.0),
                len(_normalize_for_distance(lemma)),
            ),
        )
        return DioWordListResult(
            query=query,
            lemmas=ranked,
            matched=True,
            frequencies=merged_freqs or None,
        )

    def _attempt_word_list(
        self, query: str, steps: list[NormalizationStep], operation: str
    ) -> WordListResult | None:
        if self.diogenes is None:
            return None
        try:
            result = self.diogenes.fetch_word_list(query)
        except Exception:  # noqa: BLE001
            return None

        if not result.lemmas:
            return None

        steps.append(
            NormalizationStep(
                operation=operation,
                input=query,
                output=";".join(result.lemmas),
                tool="diogenes",
            )
        )
        return result

    def _local_candidates(
        self, base: str, steps: list[NormalizationStep]
    ) -> list[CanonicalCandidate]:
        candidates: list[CanonicalCandidate] = []

        if contains_greek(base):
            encodings: dict[str, str] = {}
            sources = ["local"]

            stripped = strip_accents(base)
            betacode_variants = _betacode_variants(base, stripped)
            if betacode_variants:
                encodings["betacode"] = betacode_variants[0]

            candidates.append(CanonicalCandidate(lemma=base, encodings=encodings, sources=sources))
        else:
            ascii_lower = base.lower()
            encodings: dict[str, str] = {}
            sources = ["local"]

            trans = transliterate(ascii_lower)
            if trans.search_key:
                if not _has_transliterate_step(steps, ascii_lower):
                    steps.append(
                        NormalizationStep(
                            operation="greek_transliterate",
                            input=ascii_lower,
                            output=trans.search_key,
                            tool="greek_transliterator",
                        )
                    )
                if trans.betacode:
                    encodings["betacode"] = trans.betacode
                candidates.append(
                    CanonicalCandidate(lemma=trans.search_key, encodings=encodings, sources=sources)
                )
                stripped = strip_accents(trans.search_key)
                if stripped != trans.search_key:
                    encodings["accentless"] = stripped
                    candidates.append(
                        CanonicalCandidate(lemma=stripped, encodings=encodings, sources=sources)
                    )
            else:
                candidates.append(
                    CanonicalCandidate(lemma=ascii_lower, encodings=encodings, sources=sources)
                )

        return candidates


def _has_transliterate_step(steps: list[NormalizationStep], source: str) -> bool:
    return any(s.operation == "greek_transliterate" and s.input == source for s in steps)


def _betacode_variants(base: str, stripped: str) -> list[str]:
    variants: list[str] = []
    conv = _load_betacode_conv()
    if conv is None:
        return variants
    try:
        variants.append(conv.uni_to_beta(base))
        if stripped != base:
            variants.append(conv.uni_to_beta(stripped))
    except Exception:  # noqa: BLE001
        return variants
    return variants


class QueryNormalizer:
    """
    Normalization pipeline for Project Orion.

    Produces a NormalizedQuery plus a stable hash and records the steps taken.
    """

    def __init__(
        self,
        heritage_client: HeritageClientProtocol | None = None,
        diogenes_greek_client: DiogenesGreekClientProtocol | None = None,
        diogenes_latin_client: DiogenesLatinClientProtocol | None = None,
        whitaker_client: WhitakerClientProtocol | None = None,
    ) -> None:
        self._latin = LatinNormalizer(
            diogenes_client=diogenes_latin_client, whitaker_client=whitaker_client
        )
        self._greek = GreekNormalizer(diogenes_client=diogenes_greek_client)
        sanskrit_module = importlib.import_module("langnet.normalizer.sanskrit")
        sanskrit_normalizer_cls = getattr(sanskrit_module, "SanskritNormalizer")
        self._sanskrit = sanskrit_normalizer_cls(heritage_client)

    def normalize(self, raw_query: str, language: LanguageValue) -> NormalizationResult:
        steps: list[NormalizationStep] = []
        current = raw_query

        stripped = raw_query.strip()
        if stripped != current:
            steps.append(
                NormalizationStep(
                    operation="strip_whitespace",
                    input=current,
                    output=stripped,
                    tool="whitespace_normalizer",
                )
            )
            current = stripped

        lowered = current.lower()
        if lowered != current:
            steps.append(
                NormalizationStep(
                    operation="lowercase",
                    input=current,
                    output=lowered,
                    tool="case_normalizer",
                )
            )
            current = lowered

        candidates = self._canonical_candidates(current, language, steps)

        seen_lemmas: set[str] = set()
        unique_candidates: list[CanonicalCandidate] = []
        for c in candidates:
            if c.lemma not in seen_lemmas:
                seen_lemmas.add(c.lemma)
                unique_candidates.append(c)

        normalized = NormalizedQuery(
            original=raw_query,
            language=language,
            candidates=unique_candidates,
            normalizations=steps,
        )
        return NormalizationResult(
            query_hash=_hash_query(raw_query, language), normalized=normalized
        )

    def _canonical_candidates(
        self, current: str, language: LanguageHint, steps: list[NormalizationStep]
    ) -> Iterable[CanonicalCandidate]:
        if language == LanguageHint.LANGUAGE_HINT_SAN:
            return self._sanskrit.canonical_candidates(current, steps)
        if language == LanguageHint.LANGUAGE_HINT_GRC:
            return self._greek.canonical_candidates(current, steps)
        return self._latin.canonical_candidates(current, steps)


def normalize_with_index(
    normalizer: QueryNormalizer,
    raw_query: str,
    language: LanguageValue,
    index,
    use_cache: bool = True,
) -> NormalizationResult:
    """
    Helper that consults the normalization index before computing a fresh result.

    The index is duckdb-backed; callers supply a NormalizationIndex to avoid import cycles.
    """
    query_hash = _hash_query(raw_query, language)
    if use_cache:
        cached = index.get(query_hash)
        if cached is not None:
            return NormalizationResult(query_hash=query_hash, normalized=cached)

    result = normalizer.normalize(raw_query, language)
    if use_cache:
        index.upsert(
            query_hash=result.query_hash,
            raw_query=raw_query,
            language=str(language).lower(),
            normalized=result.normalized,
        )
    return result
