from __future__ import annotations

from pathlib import Path

from langnet.normalizer.service import NormalizationService
from langnet.storage.db import connect_duckdb
from langnet.storage.effects_index import RawResponseIndex, apply_schema
from langnet.storage.extraction_index import ExtractionIndex


class Wiring:
    """
    Lightweight test wiring to share connections and services.
    """

    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self.conn = None
        self.raw_index: RawResponseIndex | None = None
        self.extraction_index: ExtractionIndex | None = None
        self.norm_service: NormalizationService | None = None

    def __enter__(self):
        self._ctx = connect_duckdb(self.db_path)
        self.conn = self._ctx.__enter__()
        apply_schema(self.conn)
        self.raw_index = RawResponseIndex(self.conn)
        self.extraction_index = ExtractionIndex(self.conn)
        self.norm_service = NormalizationService(self.conn)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if hasattr(self, "_ctx"):
            self._ctx.__exit__(exc_type, exc_val, exc_tb)
