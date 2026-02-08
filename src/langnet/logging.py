"""Structured logging configuration for langnet-cli.

Call `setup_logging()` from entrypoints to enable structured logs with optional
correlation metadata for requests/tasks. No configuration happens at import time.
"""

from __future__ import annotations

import contextlib
import contextvars
import logging
import os
from typing import Any

import structlog


_log_context: contextvars.ContextVar[dict[str, Any]] = contextvars.ContextVar(
    "langnet_log_context", default={}
)
_configured = False
_configured_level: int | None = None


def _get_log_level_from_env() -> int:
    """Get log level from LANGNET_LOG_LEVEL env var, defaulting to WARNING."""
    level_name = os.environ.get("LANGNET_LOG_LEVEL", "WARNING").upper()
    return getattr(logging, level_name, logging.WARNING)


def _coerce_level(level: int | str | None) -> int:
    if level is None:
        return _get_log_level_from_env()
    if isinstance(level, int):
        return level
    return getattr(logging, level.upper(), logging.INFO)


def _filter_by_level(logger, method_name, event_dict):
    """Filter log events based on configured langnet log level.

    Uses method_name (e.g. 'debug', 'info') since this runs before add_log_level.
    This allows filtering before processors add more data to the event.
    """
    method_level = getattr(logging, method_name.upper(), logging.DEBUG)
    effective_level = _configured_level or logging.WARNING
    if method_level < effective_level:
        raise structlog.DropEvent
    return event_dict


def _add_context(logger, method_name, event_dict):
    """Inject contextual metadata (request/task IDs, etc.)."""
    context = _log_context.get()
    if context:
        event_dict.update(context)
    return event_dict


def setup_logging(level: int | str | None = None, force: bool = False) -> None:
    """Configure logging for langnet package.

    Configures structlog with:
    - ConsoleRenderer for colored terminal output
    - TimeStamper for ISO 8601 timestamps
    - Correlation metadata from `bind_context`

    Only affects structlog output in langnet.* loggers. Third-party libraries
    (sh, urllib3, requests, etc.) are not affected and use their own logging.
    """
    global _configured
    if _configured and not force:
        return

    resolved_level = _coerce_level(level)
    global _configured_level
    _configured_level = resolved_level
    logging.basicConfig(level=resolved_level)

    structlog.configure(
        processors=[
            _filter_by_level,
            _add_context,
            structlog.stdlib.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.dev.ConsoleRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(resolved_level),
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=False,
    )
    _configured = True


def bind_context(**kwargs: Any) -> None:
    """Bind contextual metadata (e.g., request_id, path)."""
    current = dict(_log_context.get())
    current.update({k: v for k, v in kwargs.items() if v is not None})
    _log_context.set(current)


def clear_context(*keys: str) -> None:
    """Clear selected context keys or all context if none provided."""
    if not keys:
        _log_context.set({})
        return
    current = dict(_log_context.get())
    for key in keys:
        current.pop(key, None)
    _log_context.set(current)


@contextlib.contextmanager
def scoped_context(**kwargs: Any):
    """Context manager to bind metadata for the duration of a block."""
    original = _log_context.get()
    bind_context(**kwargs)
    try:
        yield
    finally:
        _log_context.set(original)
