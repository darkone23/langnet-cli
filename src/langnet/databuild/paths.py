from __future__ import annotations

import os
from pathlib import Path


def project_root() -> Path:
    """
    Return the repository root inferred from this file location.
    """
    return Path(__file__).resolve().parents[3]


def data_dir() -> Path:
    """
    Default data directory for generated DuckDB files.
    Respects LANGNET_DATA_DIR override, otherwise uses repo-local data/.
    """
    override = os.getenv("LANGNET_DATA_DIR")
    if override:
        return Path(override).expanduser()
    return project_root() / "data"


def ensure_data_dir() -> Path:
    """
    Ensure the data directory exists and return it.
    """
    path = data_dir()
    path.mkdir(parents=True, exist_ok=True)
    return path


def default_cts_path() -> Path:
    """
    Default output path for CTS index.
    """
    return ensure_data_dir() / "cts_urn.duckdb"


def default_cdsl_path(dict_id: str) -> Path:
    """
    Default output path for a CDSL dictionary index.
    """
    return ensure_data_dir() / f"cdsl_{dict_id.lower()}.duckdb"
