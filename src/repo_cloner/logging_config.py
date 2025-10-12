"""Structured logging configuration for repo-cloner.

This module provides JSON-formatted logging with contextual information,
making it easy to parse logs programmatically and integrate with log
aggregation systems (ELK, Splunk, CloudWatch, etc.).

Key Features:
- JSON-formatted logs for structured data
- Contextual logging with log_context() manager
- Support for extra fields in log records
- Exception logging with full tracebacks
- Configurable log levels and output destinations
- Thread-safe context management
"""

import json
import logging
import sys
import threading
from contextlib import contextmanager
from datetime import datetime
from typing import Any, Dict, Optional, Union

# Thread-local storage for log context
_log_context = threading.local()


def _get_context() -> Dict[str, Any]:
    """Get the current log context for this thread.

    Returns:
        Dictionary of context fields for the current thread
    """
    if not hasattr(_log_context, "data"):
        _log_context.data = {}
    data: Dict[str, Any] = _log_context.data
    return data


class JSONFormatter(logging.Formatter):
    """Custom formatter that outputs logs as JSON.

    This formatter converts log records to JSON format with the following fields:
    - timestamp: ISO 8601 formatted timestamp
    - level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    - logger: Logger name
    - message: Log message
    - filename: Source file name
    - lineno: Source line number
    - exception: Full exception traceback (if present)
    - Any extra fields passed via extra= or context manager

    Example output:
        {
            "timestamp": "2025-10-11T22:10:00.123456",
            "level": "INFO",
            "logger": "repo_cloner.sync",
            "message": "Starting sync",
            "filename": "sync_engine.py",
            "lineno": 42,
            "repository": "https://gitlab.com/org/repo",
            "operation": "clone"
        }
    """

    # Fields that are part of the standard log record
    RESERVED_FIELDS = {
        "name",
        "msg",
        "args",
        "created",
        "filename",
        "funcName",
        "levelname",
        "levelno",
        "lineno",
        "module",
        "msecs",
        "message",
        "pathname",
        "process",
        "processName",
        "relativeCreated",
        "thread",
        "threadName",
        "exc_info",
        "exc_text",
        "stack_info",
        "getMessage",
    }

    def format(self, record: logging.LogRecord) -> str:
        """Format a log record as JSON.

        Args:
            record: Log record to format

        Returns:
            JSON-formatted log string
        """
        # Build base log data
        log_data: Dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "filename": record.filename,
            "lineno": record.lineno,
        }

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        # Add extra fields (anything not in RESERVED_FIELDS)
        for key, value in record.__dict__.items():
            if key not in self.RESERVED_FIELDS and not key.startswith("_"):
                # Try to serialize the value, fall back to string representation
                try:
                    json.dumps(value)  # Test if serializable
                    log_data[key] = value
                except (TypeError, ValueError):
                    log_data[key] = str(value)

        # Return JSON string
        return json.dumps(log_data)


class ContextFilter(logging.Filter):
    """Logging filter that adds contextual fields to log records.

    This filter injects fields from the current thread's log context
    into every log record, allowing context to be set once and applied
    to all subsequent logs.

    Args:
        context: Dictionary of context fields to add to log records

    Example:
        filter = ContextFilter({"request_id": "abc123", "user": "admin"})
        handler.addFilter(filter)
    """

    def __init__(self, context: Optional[Dict[str, Any]] = None) -> None:
        """Initialize context filter.

        Args:
            context: Optional dictionary of context fields
        """
        super().__init__()
        self.context = context or {}

    def filter(self, record: logging.LogRecord) -> bool:
        """Add context fields to the log record.

        Args:
            record: Log record to modify

        Returns:
            Always True (doesn't filter any records)
        """
        # Add global context
        for key, value in self.context.items():
            setattr(record, key, value)

        # Add thread-local context
        for key, value in _get_context().items():
            setattr(record, key, value)

        return True


@contextmanager
def log_context(**kwargs: Any) -> Any:
    """Context manager for adding fields to all logs within a scope.

    This allows you to set contextual information once and have it
    automatically included in all log messages within the context.

    Context is thread-safe and supports nesting (inner contexts inherit
    from outer contexts).

    Args:
        **kwargs: Key-value pairs to add to log context

    Example:
        with log_context(request_id="abc123", user="admin"):
            logger.info("Starting operation")  # Includes request_id and user
            with log_context(operation="clone"):
                logger.info("Cloning repo")  # Includes all three fields

    Yields:
        None
    """
    context = _get_context()
    old_context = context.copy()

    try:
        # Add new context fields
        context.update(kwargs)
        yield
    finally:
        # Restore previous context
        context.clear()
        context.update(old_context)


def configure_logging(
    level: str = "INFO",
    json_format: bool = True,
    log_file: Optional[str] = None,
) -> logging.Logger:
    """Configure the repo-cloner logging system.

    This sets up the root logger for repo-cloner with appropriate
    handlers, formatters, and filters.

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        json_format: Whether to use JSON formatting (True) or plain text (False)
        log_file: Optional file path to write logs to (in addition to stdout)

    Returns:
        Configured root logger for repo-cloner

    Example:
        # JSON logs to stdout
        logger = configure_logging(level="INFO", json_format=True)

        # Plain text logs to file
        logger = configure_logging(
            level="DEBUG",
            json_format=False,
            log_file="/var/log/repo-cloner.log"
        )
    """
    # Get root logger for repo-cloner
    logger = logging.getLogger("repo_cloner")
    logger.setLevel(getattr(logging, level.upper()))

    # Remove existing handlers to avoid duplicates
    for handler in logger.handlers[:]:
        handler.close()
        logger.removeHandler(handler)

    # Choose formatter
    formatter: Union[JSONFormatter, logging.Formatter]
    if json_format:
        formatter = JSONFormatter()
    else:
        formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")

    # Add console handler (stdout)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.addFilter(ContextFilter())
    logger.addHandler(console_handler)

    # Add file handler if specified
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        file_handler.addFilter(ContextFilter())
        logger.addHandler(file_handler)

    # Don't propagate to root logger (avoid duplicate logs)
    logger.propagate = False

    return logger


def get_logger(name: str) -> logging.Logger:
    """Get a logger for a specific module within repo-cloner.

    This returns a child logger that inherits configuration from
    the root repo-cloner logger.

    Args:
        name: Module name (without 'repo_cloner.' prefix)

    Returns:
        Logger instance for the module

    Example:
        # In sync_engine.py
        logger = get_logger("sync_engine")
        logger.info("Starting sync")  # Logs as "repo_cloner.sync_engine"

        # In git_client.py
        logger = get_logger("git_client")
        logger.debug("Cloning repository", extra={"url": "..."})
    """
    return logging.getLogger(f"repo_cloner.{name}")
