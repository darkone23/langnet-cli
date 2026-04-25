from __future__ import annotations

from pathlib import Path

from langnet.databuild.paths import cache_dir, data_dir, ensure_data_dir


def normalization_db_path() -> Path:
    """
    Default on-disk DuckDB for primary langnet cache.
    """
    return cache_dir() / "langnet.duckdb"


def main_db_path() -> Path:
    """
    Path to the main langnet.duckdb (cross-tool indexes).

    This is the primary storage for:
    - Raw response cache
    - Extraction/derivation indexes
    - Claims
    - Plan response cache

    Currently aliases to normalization_db_path() for backward compatibility.
    """
    return normalization_db_path()


def tool_db_path(tool: str) -> Path:
    """
    Path to a tool-specific database.

    Args:
        tool: Tool name (e.g., "diogenes", "whitakers", "cdsl")

    Returns:
        Path to the tool's dedicated database file

    Note: Currently stores in cache/tools/ subdirectory.
          Tool-specific databases are optional and not yet used.
    """
    tools_dir = cache_dir() / "tools"
    tools_dir.mkdir(parents=True, exist_ok=True)
    return tools_dir / f"{tool}.duckdb"


def all_db_paths() -> dict[str, Path]:
    """
    Return all database paths used by langnet.

    Returns:
        Dictionary mapping database names to their paths.
        Format: {"main": Path, "tool:diogenes": Path, ...}

    Useful for:
    - Inspecting cache status
    - Clearing specific tool caches
    - Computing total storage usage
    """
    paths = {"main": main_db_path()}

    # Known tools that may have dedicated databases
    tools = ["diogenes", "whitakers", "cltk", "spacy", "heritage", "cdsl", "cts_index"]
    for tool in tools:
        paths[f"tool:{tool}"] = tool_db_path(tool)

    return paths


__all__ = [
    "data_dir",
    "ensure_data_dir",
    "normalization_db_path",
    "main_db_path",
    "tool_db_path",
    "all_db_paths",
]
