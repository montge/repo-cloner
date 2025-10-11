"""Tests for retry logic with exponential backoff."""

import time
from unittest.mock import Mock, patch

import pytest

from repo_cloner.exceptions import GitOperationError, NetworkError, StorageError
from repo_cloner.retry import (
    RetryConfig,
    retry_with_backoff,
    should_retry_exception,
)


class TestRetryConfig:
    """Test suite for retry configuration."""

    def test_default_config_values(self):
        """Test that default configuration has sensible values."""
        config = RetryConfig()
        assert config.max_retries == 3
        assert config.initial_delay == 1.0
        assert config.max_delay == 60.0
        assert config.backoff_factor == 2.0
        assert config.jitter is True

    def test_custom_config_values(self):
        """Test that custom configuration values are respected."""
        config = RetryConfig(
            max_retries=5,
            initial_delay=2.0,
            max_delay=120.0,
            backoff_factor=3.0,
            jitter=False,
        )
        assert config.max_retries == 5
        assert config.initial_delay == 2.0
        assert config.max_delay == 120.0
        assert config.backoff_factor == 3.0
        assert config.jitter is False

    def test_config_validates_max_retries(self):
        """Test that max_retries must be non-negative."""
        with pytest.raises(ValueError, match="max_retries must be >= 0"):
            RetryConfig(max_retries=-1)

    def test_config_validates_delays(self):
        """Test that delays must be positive."""
        with pytest.raises(ValueError, match="initial_delay must be > 0"):
            RetryConfig(initial_delay=0)

        with pytest.raises(ValueError, match="max_delay must be > 0"):
            RetryConfig(max_delay=0)

    def test_config_validates_backoff_factor(self):
        """Test that backoff_factor must be >= 1."""
        with pytest.raises(ValueError, match="backoff_factor must be >= 1"):
            RetryConfig(backoff_factor=0.5)


class TestRetryLogic:
    """Test suite for retry logic."""

    def test_retry_succeeds_on_first_attempt(self):
        """Test that successful operations don't retry."""
        mock_func = Mock(return_value="success")

        result = retry_with_backoff(mock_func)

        assert result == "success"
        assert mock_func.call_count == 1

    def test_retry_succeeds_after_transient_failure(self):
        """Test that transient failures are retried and succeed."""
        mock_func = Mock(
            side_effect=[
                NetworkError("Timeout", retryable=True),
                NetworkError("Connection reset", retryable=True),
                "success",
            ]
        )

        result = retry_with_backoff(mock_func)

        assert result == "success"
        assert mock_func.call_count == 3

    def test_retry_respects_max_retries(self):
        """Test that retry stops after max_retries attempts."""
        config = RetryConfig(max_retries=2)
        mock_func = Mock(side_effect=NetworkError("Persistent failure", retryable=True))

        with pytest.raises(NetworkError, match="Persistent failure"):
            retry_with_backoff(mock_func, config=config)

        # Initial attempt + 2 retries = 3 total attempts
        assert mock_func.call_count == 3

    def test_retry_does_not_retry_non_retryable_errors(self):
        """Test that non-retryable errors fail immediately."""
        mock_func = Mock(side_effect=NetworkError("DNS failure", retryable=False))

        with pytest.raises(NetworkError, match="DNS failure"):
            retry_with_backoff(mock_func)

        # Should fail immediately without retries
        assert mock_func.call_count == 1

    def test_retry_does_not_retry_non_network_errors(self):
        """Test that non-network errors are not retried by default."""
        mock_func = Mock(side_effect=ValueError("Invalid argument"))

        with pytest.raises(ValueError, match="Invalid argument"):
            retry_with_backoff(mock_func)

        # Should fail immediately
        assert mock_func.call_count == 1

    def test_retry_exponential_backoff_timing(self):
        """Test that delays follow exponential backoff pattern."""
        config = RetryConfig(
            max_retries=3,
            initial_delay=0.1,
            backoff_factor=2.0,
            jitter=False,  # Disable jitter for predictable timing
        )

        mock_func = Mock(
            side_effect=[
                NetworkError("Timeout 1", retryable=True),
                NetworkError("Timeout 2", retryable=True),
                NetworkError("Timeout 3", retryable=True),
                "success",
            ]
        )

        start_time = time.time()
        result = retry_with_backoff(mock_func, config=config)
        elapsed_time = time.time() - start_time

        assert result == "success"
        assert mock_func.call_count == 4

        # Expected delays: 0.1s, 0.2s, 0.4s = 0.7s total
        # Allow some tolerance for execution time
        assert 0.6 <= elapsed_time <= 1.0

    def test_retry_respects_max_delay(self):
        """Test that delay caps at max_delay."""
        config = RetryConfig(
            max_retries=5,
            initial_delay=10.0,
            max_delay=15.0,
            backoff_factor=2.0,
            jitter=False,
        )

        delays = []
        original_sleep = time.sleep

        def mock_sleep(seconds):
            delays.append(seconds)
            # Use minimal actual sleep for testing
            original_sleep(0.001)

        with patch("time.sleep", side_effect=mock_sleep):
            mock_func = Mock(
                side_effect=[
                    NetworkError("Timeout 1", retryable=True),
                    NetworkError("Timeout 2", retryable=True),
                    NetworkError("Timeout 3", retryable=True),
                    "success",
                ]
            )

            retry_with_backoff(mock_func, config=config)

        # Expected delays: 10.0, 15.0 (capped), 15.0 (capped)
        assert delays[0] == 10.0
        assert delays[1] == 15.0
        assert delays[2] == 15.0

    def test_retry_with_jitter_adds_randomness(self):
        """Test that jitter adds randomness to delays."""
        config = RetryConfig(
            max_retries=10,
            initial_delay=1.0,
            backoff_factor=2.0,
            jitter=True,
        )

        delays = []
        original_sleep = time.sleep

        def mock_sleep(seconds):
            delays.append(seconds)
            original_sleep(0.001)

        with patch("time.sleep", side_effect=mock_sleep):
            mock_func = Mock(
                side_effect=[NetworkError("Timeout", retryable=True) for _ in range(10)]
                + ["success"]
            )

            retry_with_backoff(mock_func, config=config)

        # With jitter, delays should not be exactly exponential
        # Check that we have variation
        expected_without_jitter = [1.0, 2.0, 4.0, 8.0, 16.0, 32.0, 60.0, 60.0, 60.0, 60.0]

        # At least some delays should differ due to jitter
        differences = [
            abs(actual - expected) for actual, expected in zip(delays, expected_without_jitter)
        ]
        assert any(diff > 0.1 for diff in differences), "Jitter should add randomness"


class TestShouldRetryException:
    """Test suite for exception retry decision logic."""

    def test_network_error_with_retryable_true(self):
        """Test that retryable NetworkError should retry."""
        error = NetworkError("Timeout", retryable=True)
        assert should_retry_exception(error) is True

    def test_network_error_with_retryable_false(self):
        """Test that non-retryable NetworkError should not retry."""
        error = NetworkError("DNS failure", retryable=False)
        assert should_retry_exception(error) is False

    def test_git_operation_error_is_not_retried_by_default(self):
        """Test that GitOperationError is not retried by default."""
        error = GitOperationError("Clone failed")
        assert should_retry_exception(error) is False

    def test_storage_error_is_not_retried_by_default(self):
        """Test that StorageError is not retried by default."""
        error = StorageError("S3 bucket not found")
        assert should_retry_exception(error) is False

    def test_non_repo_cloner_error_is_not_retried(self):
        """Test that standard Python exceptions are not retried."""
        assert should_retry_exception(ValueError("Invalid")) is False
        assert should_retry_exception(RuntimeError("Error")) is False
        assert should_retry_exception(Exception("Generic")) is False


class TestRetryDecorator:
    """Test suite for @retry decorator functionality."""

    def test_decorator_works_on_function(self):
        """Test that retry decorator can be applied to functions."""
        from repo_cloner.retry import retry

        call_count = 0

        @retry(max_retries=2)
        def flaky_function():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise NetworkError("Transient error", retryable=True)
            return "success"

        result = flaky_function()

        assert result == "success"
        assert call_count == 3

    def test_decorator_works_on_method(self):
        """Test that retry decorator works on class methods."""
        from repo_cloner.retry import retry

        class MyClient:
            def __init__(self):
                self.call_count = 0

            @retry(max_retries=2)
            def fetch_data(self):
                self.call_count += 1
                if self.call_count < 2:
                    raise NetworkError("Connection timeout", retryable=True)
                return "data"

        client = MyClient()
        result = client.fetch_data()

        assert result == "data"
        assert client.call_count == 2

    def test_decorator_preserves_function_metadata(self):
        """Test that decorator preserves function name and docstring."""
        from repo_cloner.retry import retry

        @retry()
        def my_function():
            """My docstring."""
            pass

        assert my_function.__name__ == "my_function"
        assert my_function.__doc__ == "My docstring."
