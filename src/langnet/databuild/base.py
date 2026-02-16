from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class BuildStatus(Enum):
    SUCCESS = "success"
    SKIPPED = "skipped"
    FAILED = "failed"


@dataclass
class BuildResult:
    status: BuildStatus
    output_path: Path
    stats: dict[str, Any] = field(default_factory=dict)
    message: str | None = None
