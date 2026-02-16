"""
Lightweight tool clients for Project Orion.

These clients are intentionally "dumb": they wrap transport mechanics
and emit RawResponseEffect records without parsing or derivation.
"""

from __future__ import annotations

__all__ = [
    "RawResponseEffect",
    "ToolClient",
    "CLTKService",
    "HttpToolClient",
    "SubprocessToolClient",
    "FileToolClient",
    "CapturingToolClient",
    "wrap_client_if_index",
]

# Lazy loading to avoid importing heavy modules on package load
_imported = {}


# ruff: noqa: PLC0415
# Imports inside __getattr__ are intentional for lazy loading


def __getattr__(name: str):  # noqa: PLR0911
    """Lazy load modules only when their exports are accessed."""
    if name in _imported:
        return _imported[name]

    if name in ("RawResponseEffect", "ToolClient"):
        from .base import RawResponseEffect, ToolClient

        _imported["RawResponseEffect"] = RawResponseEffect
        _imported["ToolClient"] = ToolClient
        return _imported[name]

    if name in ("CapturingToolClient", "wrap_client_if_index"):
        from .capturing import CapturingToolClient, wrap_client_if_index

        _imported["CapturingToolClient"] = CapturingToolClient
        _imported["wrap_client_if_index"] = wrap_client_if_index
        return _imported[name]

    if name == "CLTKService":
        from .cltk import CLTKService

        _imported["CLTKService"] = CLTKService
        return CLTKService

    if name == "FileToolClient":
        from .files import FileToolClient

        _imported["FileToolClient"] = FileToolClient
        return FileToolClient

    if name == "HttpToolClient":
        from .http import HttpToolClient

        _imported["HttpToolClient"] = HttpToolClient
        return HttpToolClient

    if name == "SubprocessToolClient":
        from .subprocess import SubprocessToolClient

        _imported["SubprocessToolClient"] = SubprocessToolClient
        return SubprocessToolClient

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
