from __future__ import annotations

import os
from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol

import duckdb
from query_spec import LanguageHint

from langnet.storage.effects_index import RawResponseIndex
from langnet.storage.normalization_index import NormalizationIndex
from langnet.storage.normalization_index import ensure_schema as ensure_norm_schema

from .core import NormalizationResult, QueryNormalizer, _hash_query
from .sanskrit import HeritageClientProtocol

LanguageValue = LanguageHint.ValueType

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
    ) -> None:
        ensure_norm_schema(conn)
        self.index = NormalizationIndex(conn)
        self._effects_index = effects_index
        self._heritage_client = heritage_client
        self._diogenes_config = diogenes_config or DiogenesConfig()
        self._whitaker_client = whitaker_client
        self.normalizer: QueryNormalizer | None = None
        self._capturing_clients: list = []
        env_nocache = os.getenv("LANGNET_NOCACHE", "").lower()
        self.use_cache = (
            use_cache if use_cache is not None else env_nocache not in ("1", "true", "yes")
        )

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
        if self.use_cache:
            cached = self.index.get(query_hash)
            if cached is not None:
                return NormalizationResult(query_hash=query_hash, normalized=cached)

        self._ensure_normalizer()
        assert self.normalizer is not None

        # Clear any previously captured response IDs
        self._clear_captured_response_ids()

        # Perform normalization
        result = self.normalizer.normalize(raw_query, language)

        # Collect captured response IDs
        source_response_ids = self._get_captured_response_ids()

        # Store in index with provenance (always store, but only check cache if use_cache=True)
        self.index.upsert(
            query_hash=result.query_hash,
            raw_query=raw_query,
            language=str(language).lower(),
            normalized=result.normalized,
            source_response_ids=source_response_ids if source_response_ids else None,
        )

        return result
