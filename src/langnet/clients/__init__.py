"""
Lightweight tool clients for Project Orion.

These clients are intentionally "dumb": they wrap transport mechanics
and emit RawResponseEffect records without parsing or derivation.
"""

from .base import RawResponseEffect, ToolClient
from .cltk import CLTKService
from .files import FileToolClient
from .http import HttpToolClient
from .subprocess import SubprocessToolClient

__all__ = [
    "RawResponseEffect",
    "ToolClient",
    "CLTKService",
    "HttpToolClient",
    "SubprocessToolClient",
    "FileToolClient",
]
