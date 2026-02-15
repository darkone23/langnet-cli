"""Adapter package for backend-specific conversions."""

from .cdsl import CDSLBackendAdapter
from .cltk import CLTKBackendAdapter
from .diogenes import DiogenesBackendAdapter
from .heritage import HeritageBackendAdapter
from .whitakers import WhitakersBackendAdapter

__all__ = [
    "CDSLBackendAdapter",
    "CLTKBackendAdapter",
    "DiogenesBackendAdapter",
    "HeritageBackendAdapter",
    "WhitakersBackendAdapter",
]
