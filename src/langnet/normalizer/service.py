from __future__ import annotations

import os
import unicodedata
from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol

import duckdb
from query_spec import CanonicalCandidate, LanguageHint, NormalizedQuery

from langnet.storage.effects_index import RawResponseIndex
from langnet.storage.normalization_index import NormalizationIndex
from langnet.storage.normalization_index import ensure_schema as ensure_norm_schema

from .core import (
    NormalizationResult,
    QueryNormalizer,
    _greek_epic_eus_candidates,
    _hash_query,
)
from .sanskrit import HeritageClientProtocol
from .utils import strip_accents

LanguageValue = LanguageHint.ValueType
LATIN_AE_SUFFIX_LEN = 2

if TYPE_CHECKING:
    from langnet.diogenes.client import DiogenesClient


class _HeritageFactory(Protocol):
    def __call__(self) -> HeritageClientProtocol: ...


class _WhitakerFactory(Protocol):
    def __call__(self): ...


@dataclass
class DiogenesConfig:
    greek_client: DiogenesClient | None = None
    latin_client: DiogenesClient | None = None
    endpoint: str = "http://localhost:8888/Diogenes.cgi"


class NormalizationService:
    """
    High-level normalization entry point that wraps index lookups plus compute-and-store.
    """

    def __init__(  # noqa: PLR0913
        self,
        conn: duckdb.DuckDBPyConnection,
        heritage_client: HeritageClientProtocol | _HeritageFactory | None = None,
        diogenes_config: DiogenesConfig | None = None,
        whitaker_client: _WhitakerFactory | None = None,
        use_cache: bool | None = None,
        effects_index: RawResponseIndex | None = None,
        *,
        read_only: bool = False,
    ) -> None:
        self.read_only = read_only
        if not read_only:
            ensure_norm_schema(conn)
        self.index = NormalizationIndex(conn)
        self._effects_index = None if read_only else effects_index
        self._heritage_client = heritage_client
        self._diogenes_config = diogenes_config or DiogenesConfig()
        self._whitaker_client = whitaker_client
        self.normalizer: QueryNormalizer | None = None
        self._capturing_clients: list = []
        env_nocache = os.getenv("LANGNET_NOCACHE", "").lower()
        self.use_cache = (
            use_cache if use_cache is not None else env_nocache not in ("1", "true", "yes")
        )
        if self.read_only:
            self.use_cache = False

    def _ensure_normalizer(self) -> None:
        if self.normalizer is not None:
            return
        # Lazy imports to avoid heavy modules when cache hits
        from langnet.clients import HttpToolClient  # noqa: PLC0415
        from langnet.clients.capturing import (  # noqa: PLC0415
            CapturingToolClient,
            wrap_client_if_index,
        )
        from langnet.diogenes.client import DiogenesClient  # noqa: PLC0415
        from langnet.heritage.client import HeritageHTTPClient  # noqa: PLC0415

        # Clear any previous capturing clients
        self._capturing_clients.clear()

        # Create wrapped HTTP client for capturing raw responses
        heritage_http = wrap_client_if_index(HttpToolClient("heritage"), self._effects_index)
        if isinstance(heritage_http, CapturingToolClient):
            self._capturing_clients.append(heritage_http)

        heritage = (
            self._heritage_client() if callable(self._heritage_client) else self._heritage_client
        ) or HeritageHTTPClient(tool_client=heritage_http)

        dio_cfg = self._diogenes_config
        # Wrap HTTP client with capturing behavior if effects index is configured
        diogenes_http = wrap_client_if_index(HttpToolClient("diogenes"), self._effects_index)
        if isinstance(diogenes_http, CapturingToolClient):
            self._capturing_clients.append(diogenes_http)

        default_diogenes = (
            DiogenesClient(diogenes_http, endpoint=dio_cfg.endpoint)
            if dio_cfg.greek_client is None or dio_cfg.latin_client is None
            else None
        )
        dio_greek = dio_cfg.greek_client or default_diogenes
        dio_latin = dio_cfg.latin_client or default_diogenes

        self.normalizer = QueryNormalizer(
            heritage_client=heritage,
            diogenes_greek_client=dio_greek,
            diogenes_latin_client=dio_latin,
            whitaker_client=self._whitaker_client()
            if callable(self._whitaker_client)
            else self._whitaker_client,
        )

    def _get_captured_response_ids(self) -> list[str]:
        """Collect all response IDs captured by wrapped clients."""
        response_ids = []
        for client in self._capturing_clients:
            response_ids.extend(client.get_captured_response_ids())
        return response_ids

    def _clear_captured_response_ids(self) -> None:
        """Clear captured response IDs from all wrapped clients."""
        for client in self._capturing_clients:
            client.clear_captured_response_ids()

    def normalize(self, raw_query: str, language: LanguageValue):
        """
        Resolve a query to canonical forms by checking the index first, then computing and storing.
        """
        query_hash = _hash_query(raw_query, language)
        cached = None
        if self.use_cache:
            cached = self.index.get(query_hash)
            if cached is not None:
                reranked = self._rerank_candidates(raw_query, language, cached)
                if not self._cached_greek_epic_eus_is_stale(raw_query, language, reranked):
                    return NormalizationResult(query_hash=query_hash, normalized=reranked)

        self._ensure_normalizer()
        assert self.normalizer is not None

        # Clear any previously captured response IDs
        self._clear_captured_response_ids()

        # Perform normalization
        result = self.normalizer.normalize(raw_query, language)
        reranked = self._rerank_candidates(raw_query, language, result.normalized)

        # Collect captured response IDs
        source_response_ids = self._get_captured_response_ids()

        # Store in index with provenance if caching is enabled
        if self.use_cache and not self.read_only:
            self.index.upsert(
                query_hash=result.query_hash,
                raw_query=raw_query,
                language=str(language).lower(),
                normalized=reranked,
                source_response_ids=source_response_ids if source_response_ids else None,
            )

        return NormalizationResult(query_hash=result.query_hash, normalized=reranked)

    def _cached_greek_epic_eus_is_stale(
        self,
        raw_query: str,
        language: LanguageValue,
        normalized: NormalizedQuery,
    ) -> bool:
        if language != LanguageHint.LANGUAGE_HINT_GRC:
            return False
        text = raw_query.strip().lower()
        if not strip_accents(text).casefold().endswith(("ηος", "ηοσ")):
            return False
        expected = {
            _normalize_greek_reader_form(candidate)
            for candidate in _greek_epic_eus_candidates(text)
            if candidate
        }
        if not expected:
            return False
        actual = {
            _normalize_greek_reader_form(candidate.lemma or "")
            for candidate in normalized.candidates
        }
        return expected.isdisjoint(actual)

    def _rerank_candidates(
        self, raw_query: str, language: LanguageValue, normalized: NormalizedQuery
    ) -> NormalizedQuery:
        """
        Re-rank cached candidates with the current distance/frequency heuristic.

        Cached rows may have been stored with an older ordering; re-scoring here
        keeps omega/omicron and betacode/Unicode variants aligned to the best
        frequency match without forcing a cache clear.
        """
        if language == LanguageHint.LANGUAGE_HINT_LAT:
            return _enrich_latin_cached_candidates(raw_query, normalized)
        if language != LanguageHint.LANGUAGE_HINT_GRC:
            return normalized

        try:
            from langnet.diogenes.client import (  # noqa: PLC0415
                _levenshtein,
                _normalize_for_distance,
            )
        except Exception:
            return normalized

        candidates = list(normalized.candidates)
        if len(candidates) <= 1:
            return normalized

        target_source = raw_query
        for step in normalized.normalizations:
            if step.operation == "greek_transliterate" and step.output:
                target_source = step.output
                break
        target = _normalize_for_distance(target_source)
        target_reader_form = _final_grave_to_acute(target_source)
        target_reader_norm = _normalize_greek_reader_form(target_reader_form)
        surface_norm = _normalize_greek_reader_form(target_source)
        freqs = [_candidate_freq(c) for c in candidates]
        total = sum(freqs) or 1

        def _norm_token(cand) -> str:
            token = cand.encodings.get("betacode") or cand.lemma or ""
            normed = _normalize_for_distance(token)
            return normed or token

        def _score(item) -> tuple[int, int, float, int]:
            cand, freq = item
            normed = _norm_token(cand)
            dist = _levenshtein(normed, target)
            ratio = -(freq / total) if total else 0.0
            return (
                _greek_reader_priority(
                    cand,
                    target_source=target_source,
                    target_reader_form=target_reader_form,
                    target_reader_norm=target_reader_norm,
                    surface_norm=surface_norm,
                ),
                dist,
                ratio,
                len(normed),
            )

        ranked = sorted(zip(candidates, freqs), key=_score)
        ordered = [cand for cand, _freq in ranked]
        normalized.candidates.clear()
        normalized.candidates.extend(ordered)
        return normalized


def _enrich_latin_cached_candidates(raw_query: str, normalized: NormalizedQuery) -> NormalizedQuery:
    text = raw_query.strip().lower()
    if not text.endswith("ae") or len(text) <= LATIN_AE_SUFFIX_LEN:
        return normalized
    lemma = f"{text[:-LATIN_AE_SUFFIX_LEN]}a"
    existing = {candidate.lemma for candidate in normalized.candidates}
    if lemma in existing:
        return normalized
    normalized.candidates.append(
        CanonicalCandidate(
            lemma=lemma,
            encodings={"latin_form_rule": "ae_to_a"},
            sources=["local_form_rule"],
        )
    )
    return normalized


def _candidate_freq(candidate) -> int:
    try:
        return int(candidate.encodings.get("freq", 0))
    except Exception:
        return 0


def _greek_reader_priority(
    candidate,
    *,
    target_source: str,
    target_reader_form: str,
    target_reader_norm: str,
    surface_norm: str,
) -> int:
    lemma = candidate.lemma or ""
    lemma_norm = _normalize_greek_reader_form(lemma)
    sources = set(candidate.sources)
    if "diogenes_word_list_epic_eus" in sources:
        return 0
    if lemma == target_reader_form and lemma != target_source:
        return 0
    if _is_greek_nu_to_sigma_parse_candidate(lemma_norm, surface_norm, sources):
        return 0
    if lemma_norm == target_reader_norm and lemma != strip_accents(lemma):
        return 1
    if lemma_norm == surface_norm and lemma == strip_accents(lemma):
        return 2
    return 1


def _is_greek_nu_to_sigma_parse_candidate(
    lemma_norm: str,
    surface_norm: str,
    sources: set[str],
) -> bool:
    return (
        "diogenes_parse" in sources
        and surface_norm.endswith("ν")
        and lemma_norm.endswith("σ")
        and lemma_norm[:-1] == surface_norm[:-1]
    )


def _final_grave_to_acute(text: str) -> str:
    decomposed = list(unicodedata.normalize("NFD", text))
    for idx in range(len(decomposed) - 1, -1, -1):
        char = decomposed[idx]
        if unicodedata.combining(char) == 0:
            break
        if char == "\u0300":
            decomposed[idx] = "\u0301"
            break
    return unicodedata.normalize("NFC", "".join(decomposed))


def _normalize_greek_reader_form(text: str) -> str:
    return strip_accents(text).casefold().replace("ς", "σ")
