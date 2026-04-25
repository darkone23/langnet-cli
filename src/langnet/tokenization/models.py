from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class TokenComponent:
    """Represents a component of a compound word."""

    surface: str
    normalized: str
    role: str  # "initial", "medial", "final"
    lemma: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "surface": self.surface,
            "normalized": self.normalized,
            "role": self.role,
            "lemma": self.lemma,
        }


@dataclass
class Token:
    """Represents a single token in Sanskrit text."""

    surface_form: str
    normalized_form: str
    position: int
    encoding: str
    is_compound: bool = False
    compound_type: str | None = None
    components: list[TokenComponent] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "surface": self.surface_form,
            "normalized": self.normalized_form,
            "position": self.position,
            "encoding": self.encoding,
            "is_compound": self.is_compound,
            "compound_type": self.compound_type,
            "components": [c.to_dict() for c in self.components] if self.components else None,
        }


@dataclass
class TokenizedPassage:
    """Represents a fully tokenized Sanskrit passage."""

    original_text: str
    language: str = "san"
    tokens: list[Token] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "original_text": self.original_text,
            "language": self.language,
            "tokens": [t.to_dict() for t in self.tokens],
            "metadata": self.metadata,
        }
