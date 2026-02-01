"""
Universal citation schema for classical language texts.

This module provides a standardized way to represent citations and references
across all language backends (Diogenes, CDSL, Heritage Platform, Whitaker's Words).
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from datetime import datetime


class CitationType(str, Enum):
    """Types of citations in classical language texts"""

    # Text references
    BOOK_REFERENCE = "book_reference"  # Whole book reference (e.g., "L&S")
    LINE_REFERENCE = "line_reference"  # Specific line (e.g., "Hom. Il. 1.1")
    PASSAGE_REFERENCE = "passage_reference"  # Multi-line passage (e.g., "1.1-1.10")
    VERSE_REFERENCE = "verse_reference"  # Verse in poetry (e.g., "Aen. 1.1")

    # Dictionary/source references
    DICTIONARY_ABBREVIATION = "dictionary_abbreviation"  # "cf. L&S", "see GEL", "MW"
    LEXICON_REFERENCE = "lexicon_reference"  # Reference to specific lexicon
    GRAMMAR_REFERENCE = "grammar_reference"  # Reference to grammar text

    # Cross-references
    CROSS_REFERENCE = "cross_reference"  # "→", "=>", "see also"
    SYNONYM_REFERENCE = "synonym_reference"  # Reference to synonym
    ANTONYM_REFERENCE = "antonym_reference"  # Reference to antonym

    # Edition/source material
    EDITION_REFERENCE = "edition_reference"  # Specific edition/version
    MANUSCRIPT_REFERENCE = "manuscript_reference"  # Manuscript siglum

    # Standardized formats
    CTS_URN = "cts_urn"  # Canonical Text Service URN
    PERSEUS_REFERENCE = "perseus_reference"  # Perseus-specific reference
    DOI_REFERENCE = "doi_reference"  # Digital Object Identifier

    # Other
    ETYMOLOGY_REFERENCE = "etymology_reference"  # Etymological source
    QUOTATION_REFERENCE = "quotation_reference"  # Quoted source


class NumberingSystem(str, Enum):
    """Different numbering systems for text references"""

    STANDARD = "standard"  # Book.Chapter.Section (e.g., 1.1.1)
    LINE_NUMBER = "line_number"  # Single line number
    LINE_RANGE = "line_range"  # Range of lines (e.g., "1-10")
    PAGE_NUMBER = "page_number"  # Page number (e.g., "p. 127")
    VERSE = "verse"  # Verse number (poetry)
    PARAGRAPH = "paragraph"  # Paragraph number
    SECTION = "section"  # Section number
    MANUSCRIPT_FOLIO = "manuscript_folio"  # Manuscript folio (e.g., "12r", "34v")
    STANZA = "stanza"  # Stanza number
    CANTOS = "cantos"  # Canto number (epic poetry)


@dataclass
class TextReference:
    """Structured reference to a specific text location"""

    type: CitationType
    text: str  # Original citation text

    # Hierarchical text structure
    work: Optional[str] = None  # Work title (e.g., "Iliad", "Aeneid")
    author: Optional[str] = None  # Author (e.g., "Homer", "Vergil")

    # Location within text
    book: Optional[str] = None  # Book number (e.g., "1")
    chapter: Optional[str] = None  # Chapter number (e.g., "3")
    section: Optional[str] = None  # Section number
    line: Optional[str] = None  # Line number (e.g., "23")
    verse: Optional[str] = None  # Verse number
    page: Optional[str] = None  # Page number (e.g., "127")
    stanza: Optional[str] = None  # Stanza number
    canto: Optional[str] = None  # Canto number

    # Metadata
    numbering_system: NumberingSystem = NumberingSystem.STANDARD
    edition: Optional[str] = None  # Edition identifier
    version: Optional[str] = None  # Version/textual variant
    language: Optional[str] = None  # Language of referenced text

    # Resolution
    url: Optional[str] = None  # Resolvable URL
    cts_urn: Optional[str] = None  # Canonical Text Service URN
    doi: Optional[str] = None  # Digital Object Identifier

    # Educational value
    explanation: Optional[str] = None  # Human-readable explanation
    context: Optional[str] = None  # Context of reference
    significance: Optional[str] = None  # Why this reference is important

    def to_standardized_string(self) -> str:
        """Convert to standardized string format based on type"""
        if self.type == CitationType.LINE_REFERENCE:
            if self.author and self.work and self.book and self.line:
                return f"{self.author}. {self.work} {self.book}.{self.line}"
            elif self.work and self.book and self.line:
                return f"{self.work} {self.book}.{self.line}"

        elif self.type == CitationType.DICTIONARY_ABBREVIATION:
            if self.work and self.page:
                return f"{self.work} p. {self.page}"

        # Fallback to original text
        return self.text

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "type": self.type.value,
            "text": self.text,
            "work": self.work,
            "author": self.author,
            "book": self.book,
            "chapter": self.chapter,
            "section": self.section,
            "line": self.line,
            "verse": self.verse,
            "page": self.page,
            "stanza": self.stanza,
            "canto": self.canto,
            "numbering_system": self.numbering_system.value,
            "edition": self.edition,
            "version": self.version,
            "language": self.language,
            "url": self.url,
            "cts_urn": self.cts_urn,
            "doi": self.doi,
            "explanation": self.explanation,
            "context": self.context,
            "significance": self.significance,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TextReference":
        """Create from dictionary for deserialization"""
        return cls(
            type=CitationType(data["type"]),
            text=data["text"],
            work=data.get("work"),
            author=data.get("author"),
            book=data.get("book"),
            chapter=data.get("chapter"),
            section=data.get("section"),
            line=data.get("line"),
            verse=data.get("verse"),
            page=data.get("page"),
            stanza=data.get("stanza"),
            canto=data.get("canto"),
            numbering_system=NumberingSystem(data.get("numbering_system", "standard")),
            edition=data.get("edition"),
            version=data.get("version"),
            language=data.get("language"),
            url=data.get("url"),
            cts_urn=data.get("cts_urn"),
            doi=data.get("doi"),
            explanation=data.get("explanation"),
            context=data.get("context"),
            significance=data.get("significance"),
        )


@dataclass
class Citation:
    """Complete citation with metadata about the source"""

    references: List[TextReference] = field(default_factory=list)

    # Source identification
    abbreviation: Optional[str] = None  # Short form (e.g., "L&S", "GEL")
    full_name: Optional[str] = None  # Full name (e.g., "Lewis and Short")
    short_title: Optional[str] = None  # Short title for display

    # Source metadata
    description: Optional[str] = None  # Description of source
    date: Optional[str] = None  # Publication date (e.g., "1879")
    publisher: Optional[str] = None  # Publisher
    place: Optional[str] = None  # Place of publication
    author: Optional[str] = None  # Author/editor of source
    editor: Optional[str] = None  # Editor if different from author

    # Language information
    source_language: Optional[str] = None  # Language of source
    target_language: Optional[str] = None  # Language of translation/gloss

    # Context and relationship
    relationship: Optional[str] = None  # "cf.", "see", "vid.", "compare"
    confidence: float = 1.0  # Confidence score (0-1)
    importance: Optional[str] = None  # "primary", "secondary", "cross-reference"

    # Timestamps
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: Optional[datetime] = None

    def add_reference(self, reference: TextReference) -> None:
        """Add a text reference to this citation"""
        self.references.append(reference)

    def get_primary_reference(self) -> Optional[TextReference]:
        """Get the primary text reference (first one)"""
        return self.references[0] if self.references else None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "references": [ref.to_dict() for ref in self.references],
            "abbreviation": self.abbreviation,
            "full_name": self.full_name,
            "short_title": self.short_title,
            "description": self.description,
            "date": self.date,
            "publisher": self.publisher,
            "place": self.place,
            "author": self.author,
            "editor": self.editor,
            "source_language": self.source_language,
            "target_language": self.target_language,
            "relationship": self.relationship,
            "confidence": self.confidence,
            "importance": self.importance,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Citation":
        """Create from dictionary for deserialization"""
        references = [TextReference.from_dict(ref) for ref in data.get("references", [])]

        created_at_str = data.get("created_at")
        created_at = datetime.fromisoformat(created_at_str) if created_at_str else datetime.now()

        updated_at_str = data.get("updated_at")
        updated_at = datetime.fromisoformat(updated_at_str) if updated_at_str else None

        return cls(
            references=references,
            abbreviation=data.get("abbreviation"),
            full_name=data.get("full_name"),
            short_title=data.get("short_title"),
            description=data.get("description"),
            date=data.get("date"),
            publisher=data.get("publisher"),
            place=data.get("place"),
            author=data.get("author"),
            editor=data.get("editor"),
            source_language=data.get("source_language"),
            target_language=data.get("target_language"),
            relationship=data.get("relationship"),
            confidence=data.get("confidence", 1.0),
            importance=data.get("importance"),
            created_at=created_at,
            updated_at=updated_at,
        )

    def __str__(self) -> str:
        """Human-readable string representation"""
        if self.abbreviation and self.references:
            primary_ref = self.get_primary_reference()
            if primary_ref and primary_ref.page:
                return f"{self.abbreviation} p. {primary_ref.page}"
            elif self.abbreviation:
                return self.abbreviation

        if self.references:
            primary_ref = self.get_primary_reference()
            return primary_ref.text if primary_ref else "Citation"

        return "Citation"


@dataclass
class CitationCollection:
    """Collection of citations with metadata"""

    citations: List[Citation] = field(default_factory=list)
    query: Optional[str] = None  # Original query that generated these
    language: Optional[str] = None  # Language of query
    source: Optional[str] = None  # Which backend provided these

    def add_citation(self, citation: Citation) -> None:
        """Add a citation to the collection"""
        self.citations.append(citation)

    def __len__(self) -> int:
        """Return number of citations in collection"""
        return len(self.citations)

    def filter_by_type(self, citation_type: CitationType) -> List[Citation]:
        """Filter citations by type of their primary reference"""
        return [
            citation
            for citation in self.citations
            if citation.references and citation.references[0].type == citation_type
        ]

    def get_dictionary_citations(self) -> List[Citation]:
        """Get all dictionary abbreviation citations"""
        return self.filter_by_type(CitationType.DICTIONARY_ABBREVIATION)

    def get_text_citations(self) -> List[Citation]:
        """Get all text reference citations"""
        text_types = [
            CitationType.LINE_REFERENCE,
            CitationType.BOOK_REFERENCE,
            CitationType.PASSAGE_REFERENCE,
            CitationType.VERSE_REFERENCE,
        ]
        return [
            citation
            for citation in self.citations
            if citation.references and citation.references[0].type in text_types
        ]

    def items(self):
        """Return items for backward compatibility"""
        return [(i, citation) for i, citation in enumerate(self.citations)]
