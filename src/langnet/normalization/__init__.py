"""
Canonical Query Normalization

This module provides centralized query normalization for classical language queries
across multiple encoding systems and backend tools.
"""

from langnet.normalization.core import LanguageNormalizer, NormalizationPipeline
from langnet.normalization.greek import GreekNormalizer
from langnet.normalization.latin import LatinNormalizer
from langnet.normalization.models import CanonicalQuery, Encoding, Language
from langnet.normalization.sanskrit import SanskritNormalizer

__all__ = [
    "CanonicalQuery",
    "Language",
    "Encoding",
    "NormalizationPipeline",
    "LanguageNormalizer",
    "SanskritNormalizer",
    "LatinNormalizer",
    "GreekNormalizer",
]
