"""
Indexer utilities and common functionality.
"""

import json
import duckdb
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict
import logging

from .core import IndexType, IndexStatus

logger = logging.getLogger(__name__)


@dataclass
class IndexStats:
    """Index statistics container."""

    index_type: IndexType
    name: str
    size_mb: float
    entry_count: int
    build_date: str
    status: IndexStatus
    last_accessed: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


class IndexManager:
    """Manager for tracking and controlling multiple indexes."""

    def __init__(self, config_dir: Path = Path.home() / ".config" / "langnet"):
        self.config_dir = config_dir
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.indexes_file = config_dir / "indexes.json"
        self._indexes: Dict[str, Dict[str, Any]] = {}
        self._load_indexes()

    def _load_indexes(self) -> None:
        """Load index configurations from disk."""
        try:
            if self.indexes_file.exists():
                with open(self.indexes_file, "r") as f:
                    self._indexes = json.load(f)
                logger.info(f"Loaded {len(self._indexes)} index configurations")
        except Exception as e:
            logger.error(f"Error loading indexes: {e}")
            self._indexes = {}

    def _save_indexes(self) -> None:
        """Save index configurations to disk."""
        try:
            with open(self.indexes_file, "w") as f:
                json.dump(self._indexes, f, indent=2)
            logger.info("Saved index configurations")
        except Exception as e:
            logger.error(f"Error saving indexes: {e}")

    def register_index(
        self, name: str, index_type: IndexType, path: Path, config: Optional[Dict[str, Any]] = None
    ) -> None:
        """Register a new index."""
        self._indexes[name] = {
            "type": index_type.value,
            "path": str(path),
            "config": config or {},
            "created_at": str(Path().cwd()),
            "last_accessed": None,
        }
        self._save_indexes()
        logger.info(f"Registered index: {name}")

    def get_index_config(self, name: str) -> Optional[Dict[str, Any]]:
        """Get index configuration."""
        if name in self._indexes:
            self._indexes[name]["last_accessed"] = str(Path().cwd())
            self._save_indexes()
            return self._indexes[name]
        return None

    def list_indexes(self) -> List[Dict[str, Any]]:
        """List all registered indexes."""
        return list(self._indexes.values())

    def get_index_stats(self, name: str) -> Optional[IndexStats]:
        """Get statistics for a specific index."""
        config = self.get_index_config(name)
        if not config:
            return None

        try:
            path = Path(config["path"])
            if not path.exists():
                return IndexStats(
                    index_type=IndexType(config["type"]),
                    name=name,
                    size_mb=0.0,
                    entry_count=0,
                    build_date="unknown",
                    status=IndexStatus.NOT_BUILT,
                )

            size_mb = path.stat().st_size / (1024 * 1024)

            entry_count = 0
            build_date = "unknown"

            if config["type"] == "cts_urn":
                try:
                    conn = duckdb.connect(str(path))
                    cursor = conn.cursor()
                    cursor.execute("SELECT value FROM indexer_config WHERE key = 'entry_count'")
                    result = cursor.fetchone()
                    entry_count = result[0] if result else 0

                    cursor.execute("SELECT value FROM indexer_config WHERE key = 'build_date'")
                    result = cursor.fetchone()
                    build_date = result[0] if result else "unknown"
                    conn.close()
                except Exception:
                    pass  # Fall back to defaults

            return IndexStats(
                index_type=IndexType(config["type"]),
                name=name,
                size_mb=size_mb,
                entry_count=entry_count,
                build_date=build_date,
                status=IndexStatus.BUILT if path.exists() else IndexStatus.NOT_BUILT,
            )

        except Exception as e:
            logger.error(f"Error getting stats for {name}: {e}")
            return None

    def remove_index(self, name: str) -> bool:
        """Remove an index registration."""
        if name in self._indexes:
            del self._indexes[name]
            self._save_indexes()
            logger.info(f"Removed index registration: {name}")
            return True
        return False


def get_index_manager() -> IndexManager:
    """Get the global index manager instance."""
    return IndexManager()
