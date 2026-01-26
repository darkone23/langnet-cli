"""Structured logging configuration for langnet-cli.

Uses structlog for structured logging with:
- ISO timestamps
- Colored console output
- Level filtering via LANGNET_LOG_LEVEL env var (default: WARNING)
- Only affects langnet.* loggers, not third-party libraries

Example usage:
    import structlog
    logger = structlog.get_logger(__name__)

    logger.debug("processing_item", item_id=123)
    logger.info("task_completed", task="import")
    logger.warning("rate_limited", retries=3)
    logger.error("connection_failed", host="localhost")

Environment variables:
    LANGNET_LOG_LEVEL: DEBUG, INFO, WARNING, ERROR, CRITICAL (default: WARNING)
"""

import logging
import os
import structlog

_log_level = logging.WARNING


def _get_log_level_from_env() -> int:
    """Get log level from LANGNET_LOG_LEVEL env var, defaulting to WARNING."""
    level_name = os.environ.get("LANGNET_LOG_LEVEL", "WARNING").upper()
    return getattr(logging, level_name, logging.WARNING)


def _filter_by_level(logger, method_name, event_dict):
    """Filter log events based on configured langnet log level.

    Uses method_name (e.g. 'debug', 'info') since this runs before add_log_level.
    This allows filtering before processors add more data to the event.
    """
    method_level = getattr(logging, method_name.upper(), logging.DEBUG)
    if method_level < _log_level:
        raise structlog.DropEvent
    return event_dict


def setup_logging(level: int | None = None) -> None:
    """Configure logging for langnet package.

    Configures structlog with:
    - ConsoleRenderer for colored terminal output
    - TimeStamper for ISO 8601 timestamps
    - Level filtering that respects LANGNET_LOG_LEVEL

    Only affects structlog output in langnet.* loggers. Third-party libraries
    (sh, urllib3, requests, etc.) are not affected and use their own logging.

    Args:
        level: Log level as int (e.g. logging.INFO). If None, reads from
               LANGNET_LOG_LEVEL env var, defaulting to WARNING.

    Example:
        >>> from langnet.logging import setup_logging
        >>> setup_logging(logging.DEBUG)  # enable debug output
    """
    global _log_level
    if level is None:
        level = _get_log_level_from_env()

    _log_level = level

    structlog.configure(
        processors=[
            _filter_by_level,
            structlog.stdlib.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.dev.ConsoleRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(_log_level),
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=False,
    )


setup_logging()
