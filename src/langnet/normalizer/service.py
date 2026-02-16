from __future__ import annotations

import os
from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol

import duckdb

from langnet.storage.effects_index import RawResponseIndex
from langnet.storage.normalization_index import NormalizationIndex
from langnet.storage.normalization_index import ensure_schema as ensure_norm_schema
from query_spec import LanguageHint

from .core import NormalizationResult, QueryNormalizer, _hash_query, normalize_with_index

if TYPE_CHECKING:
    from langnet.diogenes.client import DiogenesClient

    from .sanskrit import HeritageClientProtocol
else:
    HeritageClientProtocol = object  # type: ignore[misc,assignment]


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
    ) -> None:
        ensure_norm_schema(conn)
        self.index = NormalizationIndex(conn)
        self._effects_index = effects_index
        self._heritage_client = heritage_client
        self._diogenes_config = diogenes_config or DiogenesConfig()
        self._whitaker_client = whitaker_client
        self.normalizer: QueryNormalizer | None = None
        env_nocache = os.getenv("LANGNET_NOCACHE", "").lower()
        self.use_cache = (
            use_cache if use_cache is not None else env_nocache not in ("1", "true", "yes")
        )

    def _ensure_normalizer(self) -> None:
        if self.normalizer is not None:
            return
        # Lazy imports to avoid heavy modules when cache hits
        from langnet.clients import HttpToolClient  # noqa: PLC0415
        from langnet.clients.capturing import wrap_client_if_index  # noqa: PLC0415
        from langnet.diogenes.client import DiogenesClient  # noqa: PLC0415
        from langnet.heritage.client import HeritageHTTPClient  # noqa: PLC0415

        heritage = (
            self._heritage_client() if callable(self._heritage_client) else self._heritage_client
        ) or HeritageHTTPClient()

        dio_cfg = self._diogenes_config
        # Wrap HTTP client with capturing behavior if effects index is configured
        http_client = wrap_client_if_index(HttpToolClient("diogenes"), self._effects_index)
        default_diogenes = (
            DiogenesClient(http_client, endpoint=dio_cfg.endpoint)
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

    def normalize(self, raw_query: str, language: LanguageHint):
        """
        Resolve a query to canonical forms by checking the index first, then computing and storing.
        """
        query_hash = _hash_query(raw_query, language)
        if self.use_cache:
            cached = self.index.get(query_hash)
            if cached is not None:
                return NormalizationResult(query_hash=query_hash, normalized=cached)

        self._ensure_normalizer()
        assert self.normalizer is not None
        result = normalize_with_index(
            self.normalizer, raw_query, language, self.index, use_cache=self.use_cache
        )
        return result
