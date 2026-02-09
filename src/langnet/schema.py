"""
Universal Schema for Language Data

This module defines the core dataclasses that all backends must conform to.
All language backends (Heritage, CDSL, Whitaker's, etc.) should return data
in this format for consistent API responses.
"""

from dataclasses import dataclass, field
from typing import TypeAlias

from langnet.types import JSONMapping


@dataclass
class Citation:
    """Source reference for a dictionary entry or sense."""

    url: str | None = None
    title: str | None = None
    author: str | None = None
    page: str | None = None
    excerpt: str | None = None


@dataclass
class DictionaryDefinition:
    """A concrete dictionary entry or definition."""

    definition: str  # The dictionary definition text
    pos: str  # Part of speech (noun, verb, adjective, etc.)
    gender: str | None = None  # Gender for nouns/adjectives (m., f., n., c.)
    etymology: str | None = None  # Etymology information (√root, from X, etc.)
    examples: list[str] = field(default_factory=list)  # Example usages
    citations: list[Citation] = field(default_factory=list)  # Source references
    metadata: JSONMapping = field(default_factory=dict)  # Backend-specific raw data


@dataclass
class DictionaryBlock:
    """A raw dictionary entry block from Diogenes."""

    entry: str  # The dictionary text ("lupus, i, m. kindred with...")
    entryid: str  # Hierarchical ID ("00", "00:00", etc.)
    citations: dict[str, str] = field(default_factory=dict)  # CTS URN -> citation text
    original_citations: dict[str, str] = field(
        default_factory=dict
    )  # Raw citation ids/text prior to normalization
    citation_details: dict[str, dict[str, str]] = field(
        default_factory=dict
    )  # Metadata (author/work/display)
    metadata: JSONMapping = field(default_factory=dict)  # POS/foster and other enrichment data


MorphFeature: TypeAlias = (
    str | list[str] | list[dict[str, str | list[str] | None]] | dict[str, str | list[str]]
)
MorphFeatures: TypeAlias = dict[str, MorphFeature]


@dataclass
class MorphologyInfo:
    """Morphological parsing results."""

    lemma: str
    pos: str
    features: MorphFeatures  # Morphological features (case, tense, etc.)
    foster_codes: list[str] | dict[str, str] | None = None  # Foster functional grammar codes
    declension: str | None = None  # Noun/adjective declension (1st, 2nd, 3rd, etc.)
    conjugation: str | None = None  # Verb conjugation (1st, 2nd, 3rd, 4th, etc.)
    stem_type: str | None = None  # Type of stem (thematic/athematic, strong/weak, etc.)
    # Verb-specific morphology
    tense: str | None = None  # Present, imperfect, perfect, future, etc.
    mood: str | None = None  # Indicative, subjunctive, imperative, optative, etc.
    voice: str | None = None  # Active, passive, middle, medio-passive
    person: str | None = None  # 1st, 2nd, 3rd person
    number: str | None = None  # Singular, plural, dual
    # Noun/adjective-specific morphology
    case: str | None = None  # Nominative, accusative, genitive, dative, etc.
    gender: str | None = None  # Masculine, feminine, neuter


@dataclass
class DictionaryEntry:
    """Top-level container for a queried term."""

    word: str  # The queried word
    language: str  # Language identifier ('la', 'grc', 'san', etc.)
    definitions: list[DictionaryDefinition] = field(default_factory=list)  # Dictionary definitions
    morphology: MorphologyInfo | None = None
    source: str = ""  # Backend name ('heritage', 'cdsl', 'whitakers', etc.)
    metadata: JSONMapping = field(default_factory=dict)
    dictionary_blocks: list[DictionaryBlock] = field(default_factory=list)  # Raw dictionary blocks
