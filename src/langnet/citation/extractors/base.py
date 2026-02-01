"""
Base citation extractor interface and common functionality.

This module provides the abstract base class for all citation extractors,
ensuring consistency across different language backends.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from ..models import Citation, CitationCollection, TextReference, CitationType


class BaseCitationExtractor(ABC):
    """Abstract base class for citation extractors."""

    def __init__(self, language: Optional[str] = None):
        """
        Initialize the extractor.

        Args:
            language: Language this extractor handles (e.g., "lat", "grk", "san")
        """
        self.language = language

    @abstractmethod
    def can_extract(self, data: Any) -> bool:
        """
        Determine if this extractor can handle the given data.

        Args:
            data: Raw data from backend response

        Returns:
            True if this extractor can handle the data
        """
        pass

    @abstractmethod
    def extract(self, data: Any) -> CitationCollection:
        """
        Extract citations from backend-specific response data.

        Args:
            data: Raw data from backend response

        Returns:
            Collection of extracted citations
        """
        pass

    def create_text_reference(
        self, citation_type: CitationType, text: str, **kwargs
    ) -> TextReference:
        """
        Create a TextReference with common defaults for this extractor.

        Args:
            citation_type: Type of citation
            text: Original citation text
            **kwargs: Additional fields for TextReference

        Returns:
            Configured TextReference
        """
        return TextReference(type=citation_type, text=text, language=self.language, **kwargs)

    def create_citation(
        self,
        references: List[TextReference],
        abbreviation: Optional[str] = None,
        full_name: Optional[str] = None,
        **kwargs,
    ) -> Citation:
        """
        Create a Citation with common defaults for this extractor.

        Args:
            references: List of text references
            abbreviation: Short form of source
            full_name: Full name of source
            **kwargs: Additional fields for Citation

        Returns:
            Configured Citation
        """
        return Citation(
            references=references,
            abbreviation=abbreviation,
            full_name=full_name,
            source_language=self.language,
            **kwargs,
        )

    def create_collection(self, query: str, source: str) -> CitationCollection:
        """
        Create a CitationCollection with common defaults.

        Args:
            query: Original query that generated these citations
            source: Which backend provided these citations

        Returns:
            Configured CitationCollection
        """
        return CitationCollection(query=query, language=self.language, source=source)


class ExtractorRegistry:
    """Registry for managing citation extractors."""

    def __init__(self):
        self._extractors: List[BaseCitationExtractor] = []

    def register(self, extractor: BaseCitationExtractor) -> None:
        """Register a citation extractor."""
        self._extractors.append(extractor)

    def get_extractor(self, data: Any) -> Optional[BaseCitationExtractor]:
        """Get the appropriate extractor for the given data."""
        for extractor in self._extractors:
            if extractor.can_extract(data):
                return extractor
        return None

    def extract_all(self, data: Any, query: str, source: str) -> CitationCollection:
        """Extract citations using all applicable extractors."""
        collection = CitationCollection(query=query, source=source)

        extractor = self.get_extractor(data)
        if extractor:
            extracted = extractor.extract(data)
            collection.citations.extend(extracted.citations)

        return collection

    def get_all_extractors(self) -> List[BaseCitationExtractor]:
        """Get all registered extractors."""
        return self._extractors.copy()


# Global registry instance
extractor_registry = ExtractorRegistry()
