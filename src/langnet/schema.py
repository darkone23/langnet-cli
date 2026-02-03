"""
Universal Schema for Language Data

This module defines the core dataclasses that all backends must conform to.
All language backends (Heritage, CDSL, Whitaker's, etc.) should return data
in this format for consistent API responses.
"""

from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class Citation:
    """Source reference for a dictionary entry or sense."""

    url: Optional[str] = None
    title: Optional[str] = None
    author: Optional[str] = None
    page: Optional[str] = None
    excerpt: Optional[str] = None


@dataclass
class Sense:
    """A specific meaning of a word."""

    pos: str  # Part of speech
    definition: str  # Definition text
    examples: list[str] = field(default_factory=list)  # Example sentences
    citations: list[Citation] = field(default_factory=list)  # Source references
    metadata: dict[str, Any] = field(default_factory=dict)  # Additional backend-specific data


@dataclass
class MorphologyInfo:
    """Morphological parsing results."""

    lemma: str
    pos: str
    features: dict[str, str]  # Morphological features (case, tense, etc.)
    confidence: float = 1.0


@dataclass
class DictionaryEntry:
    """Top-level container for a queried term."""

    word: str  # The queried word
    language: str  # Language identifier ('la', 'grc', 'san', etc.)
    senses: list[Sense] = field(default_factory=list)  # Meanings and citations
    morphology: Optional[MorphologyInfo] = None
    source: str = ""  # Backend name ('heritage', 'cdsl', 'whitakers', etc.)
    metadata: dict[str, Any] = field(default_factory=dict)
