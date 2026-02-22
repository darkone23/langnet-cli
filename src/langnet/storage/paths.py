from __future__ import annotations

from pathlib import Path

from langnet.databuild.paths import cache_dir, data_dir, ensure_data_dir


def normalization_db_path() -> Path:
    """
    Default on-disk DuckDB for primary langnet cache.
    """
    return cache_dir() / "langnet.duckdb"


__all__ = ["data_dir", "ensure_data_dir", "normalization_db_path"]
