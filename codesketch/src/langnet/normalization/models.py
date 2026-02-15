"""
Canonical Query models for normalization system.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, cast

from langnet.types import JSONMapping

if TYPE_CHECKING:
    from ..citation.models import Citation
else:  # pragma: no cover - optional at runtime
    try:
        from ..citation.models import Citation  # type: ignore[misc,assignment]
    except ImportError:
        Citation = object  # type: ignore[misc,assignment]

CitationLike = Citation | JSONMapping | str


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
    citations: list[CitationLike] = field(default_factory=list)

    # Metadata
    detected_encoding: Encoding = Encoding.UNKNOWN
    normalization_notes: list[str] = field(default_factory=list)
    enrichment_metadata: JSONMapping | None = None

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

    def to_dict(self) -> JSONMapping:
        """Convert to dictionary for serialization."""
        converted_citations: list[JSONMapping | str] = []
        for citation in self.citations:
            if hasattr(citation, "to_dict"):
                to_dict_fn = getattr(citation, "to_dict")
                if callable(to_dict_fn):
                    converted_citations.append(to_dict_fn())  # type: ignore[call-arg]
                    continue
            if isinstance(citation, dict):
                converted_citations.append(cast(JSONMapping, citation))
            elif isinstance(citation, str):
                converted_citations.append(citation)
            else:
                converted_citations.append(str(citation))

        return {
            "original_query": self.original_query,
            "language": self.language.value,
            "canonical_text": self.canonical_text,
            "alternate_forms": self.alternate_forms,
            "citations": converted_citations,
            "detected_encoding": self.detected_encoding.value,
            "normalization_notes": self.normalization_notes,
            "enrichment_metadata": self.enrichment_metadata,
        }

    @classmethod
    def from_dict(cls, data: JSONMapping) -> "CanonicalQuery":
        """Create from dictionary for deserialization."""
        alternate_raw = data.get("alternate_forms", [])
        alternate_forms = (
            [str(form) for form in alternate_raw] if isinstance(alternate_raw, list) else []
        )

        citations_raw = data.get("citations", [])
        citations: list[CitationLike] = (
            [citation for citation in citations_raw] if isinstance(citations_raw, list) else []
        )

        normalization_notes_raw = data.get("normalization_notes", [])
        normalization_notes = (
            [str(note) for note in normalization_notes_raw]
            if isinstance(normalization_notes_raw, list)
            else []
        )

        enrichment_meta = data.get("enrichment_metadata")
        enrichment_metadata = enrichment_meta if isinstance(enrichment_meta, dict) else None

        return cls(
            original_query=str(data.get("original_query", "")),
            language=Language(str(data.get("language"))),
            canonical_text=str(data.get("canonical_text", "")),
            alternate_forms=alternate_forms,
            citations=citations,
            detected_encoding=Encoding(str(data.get("detected_encoding", "unknown"))),
            normalization_notes=normalization_notes,
            enrichment_metadata=enrichment_metadata,
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
