"""
Core normalization pipeline and abstract interfaces.
"""

import logging
from abc import ABC, abstractmethod

from .models import CanonicalQuery, Encoding, Language

logger = logging.getLogger(__name__)


class LanguageNormalizer(ABC):
    """
    Abstract base class for language-specific normalizers.
    """

    @abstractmethod
    def detect_encoding(self, text: str) -> str:
        """Detect the encoding of the input text."""
        pass

    @abstractmethod
    def to_canonical(self, text: str, source_encoding: str) -> str:
        """Convert text to canonical form."""
        pass

    @abstractmethod
    def generate_alternates(self, canonical_text: str) -> list[str]:
        """Generate alternate forms for different tools."""
        pass

    @abstractmethod
    def fuzzy_match_candidates(self, text: str) -> list[str]:
        """Generate possible forms for fuzzy matching."""
        pass

    def normalize(self, query: str) -> CanonicalQuery:
        """Main normalization method - to be implemented by subclasses."""
        raise NotImplementedError("Subclasses must implement normalize method")


class NormalizationPipeline:
    """
    Centralized query normalization service.
    """

    def __init__(self):
        self.language_handlers: dict[Language, LanguageNormalizer] = {}
        self._initialized = False

    def register_handler(self, language: Language, handler: LanguageNormalizer) -> None:
        """Register a language-specific handler."""
        self.language_handlers[language] = handler
        logger.info(f"Registered handler for {language.value}")

    def initialize(self) -> None:
        """Initialize the pipeline with language handlers."""
        # This will be called by the main application
        self._initialized = True
        logger.info("Normalization pipeline initialized")

    def normalize_query(self, language: str, query: str) -> CanonicalQuery:
        """
        Main entry point - normalize any query to canonical form.

        Args:
            language: Language code ("san", "grc", "lat")
            query: The query string to normalize

        Returns:
            CanonicalQuery object with normalized form and metadata

        Raises:
            ValueError: If language is not supported
        """
        if not self._initialized:
            raise RuntimeError("Normalization pipeline not initialized")

        # Handle empty strings gracefully at pipeline level
        if not query:
            try:
                lang_enum = Language(language)
            except ValueError:
                lang_enum = Language.SANSKRIT
            return CanonicalQuery(
                original_query="",
                language=lang_enum,
                canonical_text="",
                alternate_forms=[],
                detected_encoding=Encoding.UNKNOWN,
                confidence=0.0,
                normalization_notes=["Empty query received"],
            )

        try:
            lang_enum = Language(language)
        except ValueError:
            logger.warning(f"Unsupported language: {language}")
            return self._default_normalization(language, query)

        handler = self.language_handlers.get(lang_enum)
        if not handler:
            logger.warning(f"No handler registered for {language}")
            return self._default_normalization(language, query)

        try:
            canonical_query = handler.normalize(query)
            logger.debug(f"Normalized query: {query} -> {canonical_query.canonical_text}")
            return canonical_query
        except Exception as e:
            logger.error(f"Normalization failed for {query}: {e}")
            return self._default_normalization(language, query)

    def _default_normalization(self, language: str, query: str) -> CanonicalQuery:
        """Fallback normalization when no handler is available."""
        try:
            lang_enum = Language(language)
        except ValueError:
            lang_enum = Language.SANSKRIT  # Default fallback

        # Handle empty strings - validate at pipeline level to preserve original
        if not query:
            return CanonicalQuery(
                original_query="",
                language=lang_enum,
                canonical_text="",
                alternate_forms=[],
                detected_encoding=Encoding.UNKNOWN,
                confidence=0.0,
                normalization_notes=["Empty query received - no normalization applied"],
            )

        # For non-empty queries, use unknown as canonical if needed
        canonical_text = query if query else "unknown"

        return CanonicalQuery(
            original_query=query,
            language=lang_enum,
            canonical_text=canonical_text,
            alternate_forms=[],
            detected_encoding=Encoding.UNKNOWN,
            confidence=0.0,
            normalization_notes=["No normalization handler available - using original query"],
        )

    def get_supported_languages(self) -> list[str]:
        """Get list of supported language codes."""
        return [lang.value for lang in self.language_handlers]

    def is_language_supported(self, language: str) -> bool:
        """Check if a language is supported."""
        try:
            lang_enum = Language(language)
            return lang_enum in self.language_handlers
        except ValueError:
            return False
