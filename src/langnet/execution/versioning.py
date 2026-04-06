"""Handler versioning for cache invalidation.

This module provides a decorator for marking handler functions with version strings,
enabling detection of stale cached effects when handler implementations improve.

Design Principles:
- Versions are EXPLICIT - handlers must declare their version
- Versions are SEMANTIC - use semver-style strings (v1.0, v2.1, etc.)
- Versions enable INVALIDATION - executor can detect handler version mismatches
- Versions are IMMUTABLE - changing a handler requires version bump

References:
- docs/plans/active/tool-fact-indexing.md (Task 6)
- docs/technical/tool-response-pipeline.md
"""

from __future__ import annotations

from collections.abc import Callable
from functools import wraps
from typing import Any, TypeVar

F = TypeVar("F", bound=Callable[..., Any])


def versioned(version: str) -> Callable[[F], F]:
    """Decorator to mark handler functions with version strings.

    Args:
        version: Version string (e.g., "v1", "v1.0", "v2.1")

    Returns:
        Decorator that attaches __handler_version__ attribute

    Example:
        >>> @versioned("v1")
        ... def extract_html(call, response):
        ...     return ExtractionEffect(...)
        ...
        >>> extract_html.__handler_version__
        'v1'

    Usage Pattern:
        1. Initial implementation: @versioned("v1")
        2. Bug fix (no schema change): @versioned("v1.1")
        3. Breaking change (new fields): @versioned("v2")

    Integration:
        The executor reads __handler_version__ and stores it in effect metadata,
        enabling cache invalidation when handler versions don't match.
    """

    def decorator(func: F) -> F:
        func.__handler_version__ = version  # type: ignore[attr-defined]
        return func

    return decorator


def get_handler_version(func: Callable[..., Any]) -> str | None:
    """Extract version from handler function.

    Args:
        func: Handler function (possibly decorated with @versioned)

    Returns:
        Version string if decorated, None otherwise

    Example:
        >>> @versioned("v2.1")
        ... def my_handler():
        ...     pass
        ...
        >>> get_handler_version(my_handler)
        'v2.1'
        >>> get_handler_version(lambda: None)
        None
    """
    return getattr(func, "__handler_version__", None)


def versioned_with_fallback(version: str) -> Callable[[F], F]:
    """Decorator that preserves function behavior while adding version.

    This is a safer variant that wraps the handler function, ensuring
    that the version attribute is always accessible even if the function
    is further decorated.

    Args:
        version: Version string

    Returns:
        Decorator that wraps function and attaches version

    Example:
        >>> @versioned_with_fallback("v1")
        ... def extract_html(call, response):
        ...     return ExtractionEffect(...)
    """

    def decorator(func: F) -> F:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            return func(*args, **kwargs)

        wrapper.__handler_version__ = version  # type: ignore[attr-defined]
        return wrapper  # type: ignore[return-value]

    return decorator
