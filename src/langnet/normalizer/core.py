from __future__ import annotations

import hashlib
import importlib
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Protocol

from langnet.normalizer.sanskrit import HeritageClientProtocol
from query_spec import CanonicalCandidate, LanguageHint, NormalizationStep, NormalizedQuery

if TYPE_CHECKING:
    from langnet.diogenes.client import ParseResult, WordListResult
else:
    ParseResult = Any
    WordListResult = Any

from .base import LanguageNormalizer
from .utils import contains_greek, strip_accents


def _hash_query(raw_query: str, language: LanguageHint) -> str:
    material = f"{language.name}:{raw_query}"
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

    LATIN_TO_BETACODE = [
        ("ph", "f"),
        ("th", "q"),
        ("ch", "x"),
        ("rh", "r"),
        ("PH", "F"),
        ("TH", "Q"),
        ("CH", "X"),
        ("RH", "R"),
    ]

    def __init__(self, diogenes_client: DiogenesGreekClientProtocol | None = None) -> None:
        self.diogenes = diogenes_client

    def _latin_to_betacode(self, text: str) -> str:
        result = text
        for latin, betacode in self.LATIN_TO_BETACODE:
            result = result.replace(latin, betacode)
        result = result.replace("y", "u").replace("Y", "U")
        return result

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
            stripped = strip_accents(lemma)
            if stripped != lemma:
                encodings["accentless"] = stripped
            betacode_variants = _betacode_variants(lemma, stripped)
            if betacode_variants:
                encodings["betacode"] = betacode_variants[0]
            candidates.append(
                CanonicalCandidate(lemma=lemma, encodings=encodings, sources=["diogenes_word_list"])
            )
        return candidates

    def _fetch_word_list_with_fallback(
        self, base: str, steps: list[NormalizationStep]
    ) -> WordListResult | None:
        if self.diogenes is None:
            return None
        primary = self._attempt_word_list(base, steps, "diogenes_word_list")
        if primary:
            return primary
        betacode_form = self._latin_to_betacode(base)
        if betacode_form == base:
            return None
        return self._attempt_word_list(betacode_form, steps, "diogenes_word_list_fallback")

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
            if stripped != base:
                steps.append(
                    NormalizationStep(
                        operation="strip_accents",
                        input=base,
                        output=stripped,
                        tool="unicodedata",
                    )
                )
                encodings["accentless"] = stripped

            betacode_variants = _betacode_variants(base, stripped)
            if betacode_variants:
                encodings["betacode"] = betacode_variants[0]

            candidates.append(CanonicalCandidate(lemma=base, encodings=encodings, sources=sources))
            if stripped != base:
                candidates.append(
                    CanonicalCandidate(lemma=stripped, encodings=encodings, sources=sources)
                )
        else:
            ascii_lower = base.lower()
            encodings: dict[str, str] = {}
            sources = ["local"]

            unicode_guess = ""
            conv = _load_betacode_conv()
            if conv is not None:
                try:
                    unicode_guess = conv.beta_to_uni(ascii_lower)
                except Exception:  # noqa: BLE001
                    unicode_guess = ""

            if unicode_guess and unicode_guess != ascii_lower:
                steps.append(
                    NormalizationStep(
                        operation="betacode_to_unicode",
                        input=ascii_lower,
                        output=unicode_guess,
                        tool="betacode",
                    )
                )
                encodings["betacode"] = ascii_lower
                candidates.append(
                    CanonicalCandidate(lemma=unicode_guess, encodings=encodings, sources=sources)
                )
                stripped = strip_accents(unicode_guess)
                if stripped != unicode_guess:
                    encodings["accentless"] = stripped
                    candidates.append(
                        CanonicalCandidate(lemma=stripped, encodings=encodings, sources=sources)
                    )

            if not candidates:
                candidates.append(
                    CanonicalCandidate(lemma=ascii_lower, encodings=encodings, sources=sources)
                )

        return candidates


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

    def normalize(self, raw_query: str, language: LanguageHint) -> NormalizationResult:
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
        if language == LanguageHint.SAN:
            return self._sanskrit.canonical_candidates(current, steps)
        if language == LanguageHint.GRC:
            return self._greek.canonical_candidates(current, steps)
        return self._latin.canonical_candidates(current, steps)


def normalize_with_index(
    normalizer: QueryNormalizer,
    raw_query: str,
    language: LanguageHint,
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
            language=language.name.lower(),
            normalized=result.normalized,
        )
    return result
