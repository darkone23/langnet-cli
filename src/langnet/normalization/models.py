"""
Canonical Query models for normalization system.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

# Import citation models
try:
    from ..citation.models import Citation
except ImportError:
    # Fallback for when citation module is not available
    Citation: type = None  # type: ignore[assignment]


class Language(str, Enum):
    """Supported language codes"""

    SANSKRIT = "san"
    GREEK = "grc"
    LATIN = "lat"


class Encoding(str, Enum):
    """Supported encoding types"""

    ASCII = "ascii"
    DEVANAGARI = "devanagari"
    VELTHUIS = "velthuis"
    IAST = "iast"
    SLP1 = "slp1"
    HK = "hk"
    BETAcode = "betacode"
    UNICODE = "unicode"
    UNKNOWN = "unknown"


@dataclass
class CanonicalQuery:
    """
    Canonical representation of a query with normalization metadata.

    This represents a query in its canonical form along with alternate forms
    and metadata about the normalization process.
    """

    original_query: str
    language: Language

    # Canonical representations
    canonical_text: str
    alternate_forms: list[str] = field(default_factory=list)

    # Citations and references
    citations: list[Any] = field(default_factory=list)

    # Metadata
    detected_encoding: Encoding = Encoding.UNKNOWN
    normalization_notes: list[str] = field(default_factory=list)
    enrichment_metadata: dict[str, Any] | None = None

    def __post_init__(self):
        """Validate the canonical query after initialization."""
        if not isinstance(self.original_query, str):
            raise ValueError("original_query must be a string")

        if not isinstance(self.language, Language):
            raise ValueError("language must be a Language enum")

        if not isinstance(self.canonical_text, str):
            raise ValueError("canonical_text must be a string")

        if not isinstance(self.alternate_forms, list):
            raise ValueError("alternate_forms must be a list")

        if not all(isinstance(form, str) for form in self.alternate_forms):
            raise ValueError("all alternate_forms must be strings")

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "original_query": self.original_query,
            "language": self.language.value,
            "canonical_text": self.canonical_text,
            "alternate_forms": self.alternate_forms,
            "citations": [
                citation.to_dict() if hasattr(citation, "to_dict") else citation
                for citation in self.citations
            ],
            "detected_encoding": self.detected_encoding.value,
            "normalization_notes": self.normalization_notes,
            "enrichment_metadata": self.enrichment_metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CanonicalQuery":
        """Create from dictionary for deserialization."""
        return cls(
            original_query=data["original_query"],
            language=Language(data["language"]),
            canonical_text=data["canonical_text"],
            alternate_forms=data.get("alternate_forms", []),
            citations=data.get("citations", []),
            detected_encoding=Encoding(data.get("detected_encoding", "unknown")),
            normalization_notes=data.get("normalization_notes", []),
            enrichment_metadata=data.get("enrichment_metadata"),
        )

    def get_primary_form(self) -> str:
        """Get the primary canonical form."""
        return self.canonical_text

    def get_all_forms(self) -> list[str]:
        """Get all possible forms including canonical and alternates."""
        all_forms = [self.canonical_text] + self.alternate_forms
        # Remove duplicates while preserving order
        seen = set()
        return [form for form in all_forms if not (form in seen or seen.add(form))]
