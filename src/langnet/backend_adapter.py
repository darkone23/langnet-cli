"""Compatibility shim for legacy adapter imports.

New code should import from `langnet.adapters` and `langnet.adapters.registry`.
"""

from langnet.adapters import (  # noqa: F401
    CDSLBackendAdapter,
    CLTKBackendAdapter,
    DiogenesBackendAdapter,
    HeritageBackendAdapter,
    WhitakersBackendAdapter,
)
from langnet.adapters.registry import CompositeAdapter, LanguageAdapterRegistry  # noqa: F401

