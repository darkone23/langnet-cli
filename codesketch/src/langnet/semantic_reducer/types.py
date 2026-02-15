"""
Witness Sense Unit types for semantic reduction pipeline.

WSUs are the smallest semantic evidence units extracted from sources.
Each WSU represents a single sense from a dictionary entry with
stable source tracking for evidence inspection.
"""

from dataclasses import dataclass, field
from enum import Enum


class Mode(str, Enum):
    OPEN = "open"
    SKEPTIC = "skeptic"


class Source(str, Enum):
    MW = "mw"
    AP90 = "ap90"
    HERITAGE = "heritage"
    WHITAKERS = "whitakers"
    DIOGENES = "diogenes"
    LSJ = "lsj"
    LEWIS_SHORT = "lewis_short"
    CLTK = "cltk"
    CDSL = "cdsl"


SOURCE_PRIORITY: dict[Source, int] = {
    Source.MW: 1,
    Source.AP90: 2,
    Source.HERITAGE: 3,
    Source.LSJ: 4,
    Source.LEWIS_SHORT: 5,
    Source.WHITAKERS: 6,
    Source.DIOGENES: 7,
    Source.CLTK: 8,
    Source.CDSL: 9,
}


@dataclass
class WitnessSenseUnit:
    source: str
    sense_ref: str
    gloss_raw: str
    gloss_normalized: str
    domains: list[str] = field(default_factory=list)
    register: list[str] = field(default_factory=list)
    confidence: float | None = None
    ordering: int = 0

    def __hash__(self) -> int:
        return hash(self.sense_ref)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, WitnessSenseUnit):
            return NotImplemented
        return self.sense_ref == other.sense_ref


@dataclass
class SenseBucket:
    sense_id: str
    semantic_constant: str | None
    display_gloss: str
    confidence: float
    witnesses: list[WitnessSenseUnit] = field(default_factory=list)
    domains: list[str] = field(default_factory=list)
    register: list[str] = field(default_factory=list)


MODE_THRESHOLDS: dict[Mode, float] = {
    Mode.OPEN: 0.15,
    Mode.SKEPTIC: 0.25,
}
