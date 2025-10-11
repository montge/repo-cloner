"""Custom exception hierarchy for repo-cloner.

This module defines a comprehensive exception hierarchy for handling
various error scenarios in repository cloning, synchronization, and
archive operations.

All exceptions inherit from RepoClonerError for easy catching and handling.
"""

from typing import Any, Optional


class RepoClonerError(Exception):
    """Base exception for all repo-cloner errors.

    All custom exceptions in repo-cloner inherit from this base class,
    allowing users to catch all tool-specific errors with a single handler.

    Attributes:
        message: Human-readable error message
        **kwargs: Additional context stored as attributes
    """

    def __init__(self, message: str, **kwargs: Any) -> None:
        """Initialize exception with message and optional context.

        Args:
            message: Human-readable error description
            **kwargs: Additional context (e.g., repository, url, exit_code)
        """
        super().__init__(message)
        self.message = message

        # Store all kwargs as instance attributes for context
        for key, value in kwargs.items():
            setattr(self, key, value)

    def __str__(self) -> str:
        """Return string representation of the error."""
        return self.message


class AuthenticationError(RepoClonerError):
    """Raised when authentication to a platform fails.

    This exception indicates that credentials are invalid, expired,
    or insufficient for the requested operation.

    Common scenarios:
    - Invalid PAT (Personal Access Token)
    - Expired credentials
    - Insufficient permissions
    - Network issues preventing auth
    """

    pass


class ConfigurationError(RepoClonerError):
    """Raised when configuration is invalid or missing.

    This exception indicates problems with YAML config files,
    environment variables, or command-line arguments.

    Common scenarios:
    - Invalid YAML syntax
    - Missing required fields
    - Incompatible configuration options
    - Failed environment variable substitution
    """

    pass


class GitOperationError(RepoClonerError):
    """Raised when a Git operation fails.

    This exception wraps errors from Git CLI or GitPython library
    operations like clone, fetch, push, or bundle.

    Common scenarios:
    - Clone failure (network, auth, disk space)
    - Push rejected (force-push protection)
    - Bundle creation failed
    - Invalid repository URL
    """

    pass


class NetworkError(RepoClonerError):
    """Raised when network operations fail.

    This exception indicates network-level failures that may be
    transient and retryable.

    Attributes:
        retryable: Whether the error should be retried

    Common scenarios:
    - Connection timeout
    - DNS resolution failure
    - Temporary service unavailability
    - Rate limiting
    """

    def __init__(self, message: str, retryable: bool = True, **kwargs: Any) -> None:
        """Initialize network error.

        Args:
            message: Error description
            retryable: Whether operation should be retried (default: True)
            **kwargs: Additional context
        """
        super().__init__(message, retryable=retryable, **kwargs)


class StorageError(RepoClonerError):
    """Raised when storage backend operations fail.

    This exception covers errors from cloud storage (S3, Azure, GCS, OCI)
    or local filesystem operations.

    Common scenarios:
    - S3 bucket not found
    - Insufficient permissions
    - Disk full
    - Network timeout during upload
    """

    pass


class ArchiveError(RepoClonerError):
    """Raised when archive operations fail.

    This exception covers archive creation, extraction, verification,
    and chain reconstruction failures.

    Common scenarios:
    - Corrupted archive file
    - Missing parent archive for incremental
    - Checksum mismatch
    - Insufficient disk space
    """

    pass


class SyncConflictError(RepoClonerError):
    """Raised when synchronization conflicts are detected.

    This exception indicates that bidirectional sync detected
    divergent changes that cannot be automatically resolved.

    Attributes:
        branch: Branch with conflict
        source_commit: Source commit SHA
        target_commit: Target commit SHA

    Common scenarios:
    - Divergent branches in bidirectional sync
    - Force-push detection
    - Conflicting commits
    """

    def __init__(
        self,
        message: str,
        branch: Optional[str] = None,
        source_commit: Optional[str] = None,
        target_commit: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        """Initialize sync conflict error.

        Args:
            message: Error description
            branch: Branch name with conflict
            source_commit: Source commit SHA
            target_commit: Target commit SHA
            **kwargs: Additional context
        """
        super().__init__(
            message,
            branch=branch,
            source_commit=source_commit,
            target_commit=target_commit,
            **kwargs,
        )
