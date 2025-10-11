"""Tests for custom exception hierarchy."""

import pytest

from repo_cloner.exceptions import (
    ArchiveError,
    AuthenticationError,
    ConfigurationError,
    GitOperationError,
    NetworkError,
    RepoClonerError,
    StorageError,
    SyncConflictError,
)


class TestExceptionHierarchy:
    """Test suite for custom exception hierarchy."""

    def test_base_exception_is_repo_cloner_error(self):
        """Test that base exception is RepoClonerError."""
        error = RepoClonerError("Test error")
        assert isinstance(error, Exception)
        assert str(error) == "Test error"

    def test_authentication_error_inherits_from_base(self):
        """Test that AuthenticationError inherits from base."""
        error = AuthenticationError("Auth failed")
        assert isinstance(error, RepoClonerError)
        assert str(error) == "Auth failed"

    def test_configuration_error_inherits_from_base(self):
        """Test that ConfigurationError inherits from base."""
        error = ConfigurationError("Invalid config")
        assert isinstance(error, RepoClonerError)
        assert str(error) == "Invalid config"

    def test_git_operation_error_inherits_from_base(self):
        """Test that GitOperationError inherits from base."""
        error = GitOperationError("Git clone failed")
        assert isinstance(error, RepoClonerError)
        assert str(error) == "Git clone failed"

    def test_network_error_inherits_from_base(self):
        """Test that NetworkError inherits from base."""
        error = NetworkError("Connection timeout")
        assert isinstance(error, RepoClonerError)
        assert str(error) == "Connection timeout"

    def test_storage_error_inherits_from_base(self):
        """Test that StorageError inherits from base."""
        error = StorageError("S3 upload failed")
        assert isinstance(error, RepoClonerError)
        assert str(error) == "S3 upload failed"

    def test_archive_error_inherits_from_base(self):
        """Test that ArchiveError inherits from base."""
        error = ArchiveError("Archive extraction failed")
        assert isinstance(error, RepoClonerError)
        assert str(error) == "Archive extraction failed"

    def test_sync_conflict_error_inherits_from_base(self):
        """Test that SyncConflictError inherits from base."""
        error = SyncConflictError("Merge conflict detected")
        assert isinstance(error, RepoClonerError)
        assert str(error) == "Merge conflict detected"

    def test_exceptions_can_store_context(self):
        """Test that exceptions can store additional context."""
        error = GitOperationError(
            "Clone failed",
            repository="https://gitlab.com/org/repo",
            exit_code=128,
        )
        assert error.repository == "https://gitlab.com/org/repo"
        assert error.exit_code == 128

    def test_exceptions_have_user_friendly_messages(self):
        """Test that exceptions provide user-friendly messages."""
        error = AuthenticationError(
            "Authentication failed for GitLab",
            platform="gitlab",
            url="https://gitlab.example.com",
        )
        assert "Authentication failed" in str(error)
        assert hasattr(error, "platform")
        assert hasattr(error, "url")

    def test_network_error_stores_retryable_flag(self):
        """Test that NetworkError can indicate if retryable."""
        error = NetworkError("Timeout", retryable=True)
        assert error.retryable is True

        error2 = NetworkError("DNS failure", retryable=False)
        assert error2.retryable is False

    def test_sync_conflict_error_stores_conflict_details(self):
        """Test that SyncConflictError stores conflict details."""
        error = SyncConflictError(
            "Divergent branches",
            branch="main",
            source_commit="abc123",
            target_commit="def456",
        )
        assert error.branch == "main"
        assert error.source_commit == "abc123"
        assert error.target_commit == "def456"

    def test_can_catch_all_errors_with_base_exception(self):
        """Test that base exception catches all custom errors."""
        errors = [
            AuthenticationError("auth"),
            ConfigurationError("config"),
            GitOperationError("git"),
            NetworkError("network"),
            StorageError("storage"),
            ArchiveError("archive"),
            SyncConflictError("conflict"),
        ]

        for error in errors:
            try:
                raise error
            except RepoClonerError as e:
                assert isinstance(e, RepoClonerError)
            else:
                pytest.fail(f"Failed to catch {type(error).__name__}")
