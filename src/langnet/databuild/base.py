from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Generic, TypeVar

from returns.result import Result


@dataclass(frozen=True)
class BuildErrorStats:
    error: str


@dataclass(frozen=True)
class CTSStats:
    path: str
    format: str
    author_count: int | None = None
    work_count: int | None = None
    edition_count: int | None = None
    perseus_count: int | None = None
    legacy_count: int | None = None
    size_mb: float | None = None


@dataclass(frozen=True)
class CdslStats:
    dict_id: str
    path: str
    entry_count: int | None = None
    headword_count: int | None = None
    size_mb: float | None = None
    processed: int | None = None


BuildStats = CTSStats | CdslStats | BuildErrorStats
StatsType = TypeVar("StatsType", bound=BuildStats)

logger = logging.getLogger(__name__)


class BuildStatus(Enum):
    SUCCESS = "success"
    SKIPPED = "skipped"
    FAILED = "failed"


@dataclass
class BuildResult(Generic[StatsType]):
    status: BuildStatus
    output_path: Path
    stats: Result[StatsType, BuildErrorStats] | None = None
    message: str | None = None
