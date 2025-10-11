"""Retry logic with exponential backoff for handling transient failures.

This module provides retry mechanisms for operations that may fail due to
transient network or service issues. It implements exponential backoff with
optional jitter to avoid thundering herd problems.

Key Features:
- Configurable retry attempts, delays, and backoff factors
- Exponential backoff with optional jitter
- Selective retry based on exception type and attributes
- Decorator and function call interfaces
- Respects NetworkError.retryable flag
"""

import functools
import logging
import random
import time
from dataclasses import dataclass
from typing import Any, Callable, Optional, TypeVar

from repo_cloner.exceptions import NetworkError

logger = logging.getLogger(__name__)

# Type variable for generic function return type
T = TypeVar("T")


@dataclass
class RetryConfig:
    """Configuration for retry behavior with exponential backoff.

    Attributes:
        max_retries: Maximum number of retry attempts (default: 3)
        initial_delay: Initial delay in seconds before first retry (default: 1.0)
        max_delay: Maximum delay in seconds between retries (default: 60.0)
        backoff_factor: Multiplier for exponential backoff (default: 2.0)
        jitter: Whether to add random jitter to delays (default: True)
    """

    max_retries: int = 3
    initial_delay: float = 1.0
    max_delay: float = 60.0
    backoff_factor: float = 2.0
    jitter: bool = True

    def __post_init__(self) -> None:
        """Validate configuration parameters."""
        if self.max_retries < 0:
            raise ValueError("max_retries must be >= 0")
        if self.initial_delay <= 0:
            raise ValueError("initial_delay must be > 0")
        if self.max_delay <= 0:
            raise ValueError("max_delay must be > 0")
        if self.backoff_factor < 1.0:
            raise ValueError("backoff_factor must be >= 1")

    def calculate_delay(self, attempt: int) -> float:
        """Calculate delay for given retry attempt with exponential backoff.

        Args:
            attempt: Current retry attempt number (0-indexed)

        Returns:
            Delay in seconds before next retry
        """
        # Calculate exponential delay
        delay = self.initial_delay * (self.backoff_factor**attempt)

        # Cap at max_delay
        delay = min(delay, self.max_delay)

        # Add jitter if enabled (random factor between 0.5 and 1.0)
        if self.jitter:
            delay *= 0.5 + random.random() * 0.5

        return delay


def should_retry_exception(exception: Exception) -> bool:
    """Determine if an exception should trigger a retry.

    Only NetworkError with retryable=True should be retried by default.
    All other exceptions fail immediately.

    Args:
        exception: Exception to evaluate

    Returns:
        True if operation should be retried, False otherwise
    """
    if isinstance(exception, NetworkError):
        # Check if NetworkError has retryable attribute set to True
        return getattr(exception, "retryable", False)

    # All other exceptions (including other RepoClonerError types) are not retried
    return False


def retry_with_backoff(
    func: Callable[..., T],
    *args: Any,
    config: Optional[RetryConfig] = None,
    **kwargs: Any,
) -> T:
    """Execute a function with retry logic and exponential backoff.

    This function wraps any callable and retries it on transient failures
    with exponential backoff delays.

    Args:
        func: Function to execute
        *args: Positional arguments to pass to func
        config: Retry configuration (uses defaults if not provided)
        **kwargs: Keyword arguments to pass to func

    Returns:
        Result from successful function execution

    Raises:
        Exception: Re-raises the last exception if all retries exhausted
                  or if exception is not retryable

    Example:
        >>> result = retry_with_backoff(api_client.fetch_data, repo_id=123)
        >>> # Custom config
        >>> config = RetryConfig(max_retries=5, initial_delay=2.0)
        >>> result = retry_with_backoff(api_client.fetch, config=config)
    """
    if config is None:
        config = RetryConfig()

    attempt = 0
    last_exception: Optional[Exception] = None

    while attempt <= config.max_retries:
        try:
            # Attempt to execute the function
            return func(*args, **kwargs)

        except Exception as e:
            last_exception = e

            # Check if we should retry this exception
            if not should_retry_exception(e):
                logger.debug(f"Exception {type(e).__name__} is not retryable, failing immediately")
                raise

            # Check if we've exhausted retries
            if attempt >= config.max_retries:
                func_name = getattr(func, "__name__", repr(func))
                logger.warning(
                    f"Max retries ({config.max_retries}) exhausted for {func_name}, "
                    f"last error: {e}"
                )
                raise

            # Calculate delay and wait before retry
            delay = config.calculate_delay(attempt)
            func_name = getattr(func, "__name__", repr(func))
            logger.info(
                f"Attempt {attempt + 1}/{config.max_retries} failed for {func_name}: {e}. "
                f"Retrying in {delay:.2f}s..."
            )

            time.sleep(delay)
            attempt += 1

    # This should never be reached, but satisfy type checker
    if last_exception:
        raise last_exception
    raise RuntimeError("Retry loop exited unexpectedly")


def retry(
    max_retries: int = 3,
    initial_delay: float = 1.0,
    max_delay: float = 60.0,
    backoff_factor: float = 2.0,
    jitter: bool = True,
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Decorator to add retry logic with exponential backoff to functions.

    This decorator wraps a function to automatically retry on transient failures.

    Args:
        max_retries: Maximum number of retry attempts
        initial_delay: Initial delay in seconds
        max_delay: Maximum delay in seconds
        backoff_factor: Exponential backoff multiplier
        jitter: Whether to add random jitter

    Returns:
        Decorated function with retry logic

    Example:
        >>> @retry(max_retries=5, initial_delay=2.0)
        >>> def fetch_repository(url: str) -> dict:
        >>>     return api_client.get(url)
        >>>
        >>> @retry()  # Use defaults
        >>> def clone_repo(source: str, target: str) -> None:
        >>>     git.clone(source, target)
    """
    config = RetryConfig(
        max_retries=max_retries,
        initial_delay=initial_delay,
        max_delay=max_delay,
        backoff_factor=backoff_factor,
        jitter=jitter,
    )

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            return retry_with_backoff(func, *args, config=config, **kwargs)

        return wrapper

    return decorator
