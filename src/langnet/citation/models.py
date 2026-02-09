"""
Universal citation schema for classical language texts.

This module provides a standardized way to represent citations and references
across all language backends (Diogenes, CDSL, Heritage Platform, Whitaker's Words).
"""

from dataclasses import dataclass, field
from enum import Enum

from langnet.types import JSONMapping


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
    work: str | None = None  # Work title (e.g., "Iliad", "Aeneid")
    author: str | None = None  # Author (e.g., "Homer", "Vergil")

    # Location within text
    book: str | None = None  # Book number (e.g., "1")
    chapter: str | None = None  # Chapter number (e.g., "3")
    section: str | None = None  # Section number
    line: str | None = None  # Line number (e.g., "23")
    verse: str | None = None  # Verse number
    page: str | None = None  # Page number (e.g., "127")
    stanza: str | None = None  # Stanza number
    canto: str | None = None  # Canto number

    # Metadata
    numbering_system: NumberingSystem = NumberingSystem.STANDARD
    edition: str | None = None  # Edition identifier
    version: str | None = None  # Version/textual variant
    language: str | None = None  # Language of referenced text

    # Resolution
    url: str | None = None  # Resolvable URL
    cts_urn: str | None = None  # Canonical Text Service URN
    doi: str | None = None  # Digital Object Identifier

    # Educational value
    explanation: str | None = None  # Human-readable explanation
    context: str | None = None  # Context of reference
    significance: str | None = None  # Why this reference is important

    def to_standardized_string(self) -> str:
        """Convert to standardized string format based on type"""
        if self.type == CitationType.LINE_REFERENCE:
            if self.author and self.work and self.book and self.line:
                return f"{self.author}. {self.work} {self.book}.{self.line}"
            elif self.work and self.book and self.line:
                return f"{self.work} {self.book}.{self.line}"

        elif self.type == CitationType.DICTIONARY_ABBREVIATION and self.work and self.page:
            return f"{self.work} p. {self.page}"

        # Fallback to original text
        return self.text

    def to_dict(self) -> JSONMapping:
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
    def from_dict(cls, data: JSONMapping) -> "TextReference":
        """Create from dictionary for deserialization"""
        text_value = data.get("text")
        text = text_value if isinstance(text_value, str) else str(text_value)
        work_value = data.get("work")
        author_value = data.get("author")
        book_value = data.get("book")
        chapter_value = data.get("chapter")
        section_value = data.get("section")
        line_value = data.get("line")
        verse_value = data.get("verse")
        page_value = data.get("page")
        stanza_value = data.get("stanza")
        canto_value = data.get("canto")
        url_value = data.get("url")
        cts_value = data.get("cts_urn")
        doi_value = data.get("doi")
        explanation_value = data.get("explanation")
        context_value = data.get("context")
        significance_value = data.get("significance")

        return cls(
            type=CitationType(str(data["type"])),
            text=text,
            work=str(work_value) if work_value is not None else None,
            author=str(author_value) if author_value is not None else None,
            book=str(book_value) if book_value is not None else None,
            chapter=str(chapter_value) if chapter_value is not None else None,
            section=str(section_value) if section_value is not None else None,
            line=str(line_value) if line_value is not None else None,
            verse=str(verse_value) if verse_value is not None else None,
            page=str(page_value) if page_value is not None else None,
            stanza=str(stanza_value) if stanza_value is not None else None,
            canto=str(canto_value) if canto_value is not None else None,
            numbering_system=NumberingSystem(data.get("numbering_system", "standard")),
            edition=str(data["edition"])
            if "edition" in data and data["edition"] is not None
            else None,
            version=str(data["version"])
            if "version" in data and data["version"] is not None
            else None,
            language=str(data["language"])
            if "language" in data and data["language"] is not None
            else None,
            url=str(url_value) if url_value is not None else None,
            cts_urn=str(cts_value) if cts_value is not None else None,
            doi=str(doi_value) if doi_value is not None else None,
            explanation=str(explanation_value) if explanation_value is not None else None,
            context=str(context_value) if context_value is not None else None,
            significance=str(significance_value) if significance_value is not None else None,
        )


@dataclass
class Citation:
    """Complete citation with metadata about the source"""

    references: list[TextReference] = field(default_factory=list)

    # Source identification
    abbreviation: str | None = None  # Short form (e.g., "L&S", "GEL")
    full_name: str | None = None  # Full name (e.g., "Lewis and Short")
    short_title: str | None = None  # Short title for display

    # Source metadata
    description: str | None = None  # Description of source
    date: str | None = None  # Publication date (e.g., "1879")
    publisher: str | None = None  # Publisher
    place: str | None = None  # Place of publication
    author: str | None = None  # Author/editor of source
    editor: str | None = None  # Editor if different from author

    # Language information
    source_language: str | None = None  # Language of source
    target_language: str | None = None  # Language of translation/gloss

    # Context and relationship
    relationship: str | None = None  # "cf.", "see", "vid.", "compare"
    # confidence: float = 1.0  # Confidence score (0-1)
    importance: str | None = None  # "primary", "secondary", "cross-reference"

    # Timestamps
    # created_at: datetime = field(default_factory=datetime.now)
    # updated_at: datetime | None = None

    def add_reference(self, reference: TextReference) -> None:
        """Add a text reference to this citation"""
        self.references.append(reference)

    def get_primary_reference(self) -> TextReference | None:
        """Get the primary text reference (first one)"""
        return self.references[0] if self.references else None

    def to_dict(self) -> JSONMapping:
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
            # "confidence": self.confidence,
            "importance": self.importance,
            # "created_at": self.created_at.isoformat(),
            # "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    @classmethod
    def from_dict(cls, data: JSONMapping) -> "Citation":
        """Create from dictionary for deserialization"""
        refs_raw = data.get("references")
        references: list[TextReference] = []
        if isinstance(refs_raw, list):
            for ref in refs_raw:
                if isinstance(ref, dict):
                    references.append(TextReference.from_dict(ref))

        def _optional_str(key: str) -> str | None:
            value = data.get(key)
            return value if isinstance(value, str) else None

        # created_at_str = data.get("created_at")
        # created_at = datetime.fromisoformat(created_at_str) if created_at_str else datetime.now()

        return cls(
            references=references,
            abbreviation=_optional_str("abbreviation"),
            full_name=_optional_str("full_name"),
            short_title=_optional_str("short_title"),
            description=_optional_str("description"),
            date=_optional_str("date"),
            publisher=_optional_str("publisher"),
            place=_optional_str("place"),
            author=_optional_str("author"),
            editor=_optional_str("editor"),
            source_language=_optional_str("source_language"),
            target_language=_optional_str("target_language"),
            relationship=_optional_str("relationship"),
            # confidence=data.get("confidence", 1.0),
            importance=_optional_str("importance"),
            # created_at=created_at,
            # updated_at=updated_at,
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

    citations: list[Citation] = field(default_factory=list)
    query: str | None = None  # Original query that generated these
    language: str | None = None  # Language of query
    source: str | None = None  # Which backend provided these

    def add_citation(self, citation: Citation) -> None:
        """Add a citation to the collection"""
        self.citations.append(citation)

    def __len__(self) -> int:
        """Return number of citations in collection"""
        return len(self.citations)

    def filter_by_type(self, citation_type: CitationType) -> list[Citation]:
        """Filter citations by type of their primary reference"""
        return [
            citation
            for citation in self.citations
            if citation.references and citation.references[0].type == citation_type
        ]

    def get_dictionary_citations(self) -> list[Citation]:
        """Get all dictionary abbreviation citations"""
        return self.filter_by_type(CitationType.DICTIONARY_ABBREVIATION)

    def get_text_citations(self) -> list[Citation]:
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
