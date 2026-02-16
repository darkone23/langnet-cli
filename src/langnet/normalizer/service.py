from __future__ import annotations

from dataclasses import dataclass

import duckdb
from query_spec import LanguageHint

from langnet.clients import HttpToolClient
from langnet.diogenes.client import DiogenesClient
from langnet.heritage.client import HeritageHTTPClient
from langnet.storage.normalization_index import NormalizationIndex
from langnet.storage.normalization_index import apply_schema as apply_norm_schema

from .core import QueryNormalizer, normalize_with_index
from .sanskrit import HeritageClientProtocol


@dataclass
class DiogenesConfig:
    greek_client: DiogenesClient | None = None
    latin_client: DiogenesClient | None = None
    endpoint: str = "http://localhost:8888/Diogenes.cgi"


class NormalizationService:
    """
    High-level normalization entry point that wraps index lookups plus compute-and-store.
    """

    def __init__(
        self,
        conn: duckdb.DuckDBPyConnection,
        heritage_client: HeritageClientProtocol | None = None,
        diogenes_config: DiogenesConfig | None = None,
        whitaker_client=None,
    ) -> None:
        apply_norm_schema(conn)
        self.index = NormalizationIndex(conn)
        heritage: HeritageClientProtocol = heritage_client or HeritageHTTPClient()

        diogenes = diogenes_config or DiogenesConfig()

        default_diogenes = (
            DiogenesClient(HttpToolClient("diogenes"), endpoint=diogenes.endpoint)
            if diogenes.greek_client is None or diogenes.latin_client is None
            else None
        )

        dio_greek = diogenes.greek_client or default_diogenes
        dio_latin = diogenes.latin_client or default_diogenes

        self.normalizer = QueryNormalizer(
            heritage_client=heritage,
            diogenes_greek_client=dio_greek,
            diogenes_latin_client=dio_latin,
            whitaker_client=whitaker_client,
        )

    def normalize(self, raw_query: str, language: LanguageHint):
        """
        Resolve a query to canonical forms by checking the index first, then computing and storing.
        """
        return normalize_with_index(self.normalizer, raw_query, language, self.index)
