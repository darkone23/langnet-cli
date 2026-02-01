"""
Citation system for classical language texts.

This package provides universal citation schema and extraction utilities
for standardized citation handling across all language backends.
"""

from .models import Citation, CitationCollection, CitationType, TextReference, NumberingSystem
from .extractors.base import BaseCitationExtractor
from .extractors.diogenes import DiogenesCitationExtractor
from .extractors.cdsl import CDSLCitationExtractor
from .conversion import (
    convert_diogenes_citations_to_new_format,
    convert_cdsl_references_to_new_format,
    convert_collection_to_diogenes_format,
    convert_collection_to_cdsl_format,
    is_legacy_diogenes_citations,
    is_legacy_cdsl_references,
)

__all__ = [
    "Citation",
    "CitationCollection",
    "CitationType",
    "TextReference",
    "NumberingSystem",
    "BaseCitationExtractor",
    "DiogenesCitationExtractor",
    "CDSLCitationExtractor",
    "convert_diogenes_citations_to_new_format",
    "convert_cdsl_references_to_new_format",
    "convert_collection_to_diogenes_format",
    "convert_collection_to_cdsl_format",
    "is_legacy_diogenes_citations",
    "is_legacy_cdsl_references",
]
