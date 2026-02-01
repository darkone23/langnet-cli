"""
Citation extractors package.

This package provides backend-specific citation extractors for converting
raw backend responses into standardized Citation objects.
"""

from .base import BaseCitationExtractor, ExtractorRegistry, extractor_registry

__all__ = ["BaseCitationExtractor", "ExtractorRegistry", "extractor_registry"]
