"""
Core indexer classes and interfaces.
"""

import logging
from abc import ABC, abstractmethod
from enum import Enum
from pathlib import Path

import duckdb
from langnet.types import JSONMapping

logger = logging.getLogger(__name__)


class IndexType(Enum):
    """Supported indexer types."""

    CTS_URN = "cts_urn"
    CDSL = "cdsl"
    CACHE = "cache"


class IndexStatus(Enum):
    """Index build status."""

    NOT_BUILT = "not_built"
    BUILDING = "building"
    BUILT = "built"
    ERROR = "error"
    OUTDATED = "outdated"


class IndexerBase(ABC):
    """Base class for all indexers."""

    def __init__(self, output_path: Path, config: JSONMapping | None = None):
        self.output_path = Path(output_path)
        self.config = config or {}
        self.status = IndexStatus.NOT_BUILT
        self._stats: JSONMapping = {}

    @abstractmethod
    def build(self) -> bool:
        """Build the index. Returns True on success."""
        pass

    @abstractmethod
    def validate(self) -> bool:
        """Validate the index integrity. Returns True if valid."""
        pass

    @abstractmethod
    def get_stats(self) -> JSONMapping:
        """Get index statistics."""
        pass

    @abstractmethod
    def cleanup(self) -> None:
        """Clean up temporary files and resources."""
        pass

    def is_built(self) -> bool:
        """Check if the index is built."""
        if self.status == IndexStatus.BUILT and self.output_path.exists():
            return True
        if self.output_path.exists():
            return self._check_db_built()
        return False

    def _check_db_built(self) -> bool:
        """Check if the database file has valid content."""
        if not self.output_path.exists():
            return False
        try:
            conn = duckdb.connect(str(self.output_path))
            result = conn.execute("SELECT COUNT(*) FROM author_index").fetchone()
            conn.close()
            count = result[0] if result else 0
            has_data = count > 0
            if has_data:
                self.status = IndexStatus.BUILT
            return has_data
        except Exception:
            return False

    def get_size_mb(self) -> float:
        """Get index size in megabytes."""
        if not self.output_path.exists():
            return 0.0
        return self.output_path.stat().st_size / (1024 * 1024)

    def update_status(self, status: IndexStatus) -> None:
        """Update indexer status."""
        logger.info(f"Indexer {self.__class__.__name__} status: {status.value}")
        self.status = status
