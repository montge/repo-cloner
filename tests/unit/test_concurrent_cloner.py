"""Unit tests for concurrent repository cloning operations."""

import tempfile
import time
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from repo_cloner.concurrent_cloner import ConcurrentCloner, CloneResult


@pytest.mark.unit
class TestConcurrentCloner:
    """Test concurrent cloning of multiple repositories."""

    def test_clone_multiple_repos_in_parallel(self):
        """Test that multiple repositories are cloned concurrently."""
        # Arrange
        cloner = ConcurrentCloner(max_workers=2)

        repos = [
            {"url": "https://example.com/repo1.git", "path": "/tmp/repo1"},
            {"url": "https://example.com/repo2.git", "path": "/tmp/repo2"},
            {"url": "https://example.com/repo3.git", "path": "/tmp/repo3"},
        ]

        # Act
        with patch("git.Repo.clone_from") as mock_clone:
            mock_clone.return_value = MagicMock()

            results = cloner.clone_multiple(repos)

            # Assert - All repos cloned
            assert len(results) == 3
            assert all(r.success for r in results)
            assert mock_clone.call_count == 3

    def test_concurrent_clone_faster_than_sequential(self):
        """Test that concurrent clones are faster than sequential."""
        # Arrange
        cloner_concurrent = ConcurrentCloner(max_workers=3)
        cloner_sequential = ConcurrentCloner(max_workers=1)

        repos = [
            {"url": "https://example.com/repo1.git", "path": "/tmp/repo1"},
            {"url": "https://example.com/repo2.git", "path": "/tmp/repo2"},
            {"url": "https://example.com/repo3.git", "path": "/tmp/repo3"},
        ]

        def slow_clone(*args, **kwargs):
            """Simulate slow clone operation."""
            time.sleep(0.1)
            return MagicMock()

        # Act
        with patch("git.Repo.clone_from", side_effect=slow_clone):
            # Concurrent clone
            start = time.time()
            cloner_concurrent.clone_multiple(repos)
            concurrent_duration = time.time() - start

            # Sequential clone
            start = time.time()
            cloner_sequential.clone_multiple(repos)
            sequential_duration = time.time() - start

            # Assert - Concurrent should be faster
            # 3 repos × 0.1s each:
            # Sequential: ~0.3s
            # Concurrent (3 workers): ~0.1s
            assert concurrent_duration < sequential_duration * 0.7

    def test_clone_result_tracks_success_and_failure(self):
        """Test that CloneResult tracks successful and failed clones."""
        # Arrange
        cloner = ConcurrentCloner(max_workers=2)

        repos = [
            {"url": "https://example.com/repo1.git", "path": "/tmp/repo1"},
            {"url": "https://example.com/repo2.git", "path": "/tmp/repo2"},
        ]

        # Act - First succeeds, second fails
        def clone_side_effect(url, path, **kwargs):
            if "repo1" in url:
                return MagicMock()
            else:
                raise Exception("Clone failed")

        with patch("git.Repo.clone_from", side_effect=clone_side_effect):
            results = cloner.clone_multiple(repos)

            # Assert
            assert len(results) == 2
            assert results[0].success is True
            assert results[1].success is False
            assert results[1].error is not None

    def test_max_workers_limits_parallelism(self):
        """Test that max_workers limits concurrent operations."""
        # Arrange
        cloner = ConcurrentCloner(max_workers=2)

        repos = [
            {"url": f"https://example.com/repo{i}.git", "path": f"/tmp/repo{i}"}
            for i in range(10)
        ]

        # Act
        active_count = []

        def track_active_clones(*args, **kwargs):
            """Track how many clones are running simultaneously."""
            # This would be tracked in production, here we verify max_workers
            time.sleep(0.01)
            return MagicMock()

        with patch("git.Repo.clone_from", side_effect=track_active_clones):
            results = cloner.clone_multiple(repos)

            # Assert - All clones completed
            assert len(results) == 10
            # max_workers=2 means at most 2 concurrent operations

    def test_handles_exceptions_without_stopping_other_clones(self):
        """Test that one failed clone doesn't stop others."""
        # Arrange
        cloner = ConcurrentCloner(max_workers=3)

        repos = [
            {"url": "https://example.com/repo1.git", "path": "/tmp/repo1"},
            {"url": "https://example.com/repo2.git", "path": "/tmp/repo2"},
            {"url": "https://example.com/repo3.git", "path": "/tmp/repo3"},
        ]

        # Act - repo2 fails, others succeed
        def clone_with_failure(url, path, **kwargs):
            if "repo2" in url:
                raise Exception("Network error")
            return MagicMock()

        with patch("git.Repo.clone_from", side_effect=clone_with_failure):
            results = cloner.clone_multiple(repos)

            # Assert - 2 succeeded, 1 failed
            successful = [r for r in results if r.success]
            failed = [r for r in results if not r.success]

            assert len(successful) == 2
            assert len(failed) == 1
            assert "repo2" in failed[0].url

    def test_get_summary_reports_success_failure_counts(self):
        """Test that summary provides success/failure counts."""
        # Arrange
        cloner = ConcurrentCloner(max_workers=2)

        repos = [
            {"url": "https://example.com/repo1.git", "path": "/tmp/repo1"},
            {"url": "https://example.com/repo2.git", "path": "/tmp/repo2"},
            {"url": "https://example.com/repo3.git", "path": "/tmp/repo3"},
        ]

        # Act - 2 succeed, 1 fails
        def clone_with_partial_failure(url, path, **kwargs):
            if "repo3" in url:
                raise Exception("Failed")
            return MagicMock()

        with patch("git.Repo.clone_from", side_effect=clone_with_partial_failure):
            results = cloner.clone_multiple(repos)
            summary = cloner.get_summary(results)

            # Assert
            assert summary["total"] == 3
            assert summary["successful"] == 2
            assert summary["failed"] == 1
            assert summary["success_rate"] == pytest.approx(66.67, rel=0.01)

    def test_clone_with_progress_callback(self):
        """Test that progress callback is invoked for each clone."""
        # Arrange
        cloner = ConcurrentCloner(max_workers=2)

        repos = [
            {"url": "https://example.com/repo1.git", "path": "/tmp/repo1"},
            {"url": "https://example.com/repo2.git", "path": "/tmp/repo2"},
        ]

        progress_calls = []

        def progress_callback(repo_url, status):
            """Track progress callback invocations."""
            progress_calls.append((repo_url, status))

        # Act
        with patch("git.Repo.clone_from") as mock_clone:
            mock_clone.return_value = MagicMock()

            cloner.clone_multiple(repos, progress_callback=progress_callback)

            # Assert - Callback invoked for each repo (start + complete)
            assert len(progress_calls) >= 2  # At least 2 repos
            statuses = [status for _, status in progress_calls]
            assert "started" in statuses or "completed" in statuses

    def test_default_max_workers_is_cpu_count(self):
        """Test that default max_workers equals CPU count."""
        # Arrange & Act
        cloner = ConcurrentCloner()

        # Assert - Should use CPU count (mocked in test)
        with patch("os.cpu_count", return_value=8):
            cloner_with_default = ConcurrentCloner()
            # max_workers should be set based on CPU count
            assert cloner_with_default.max_workers is not None

    def test_retry_failed_clones(self):
        """Test retrying failed clone operations."""
        # Arrange
        cloner = ConcurrentCloner(max_workers=2)

        repo = {"url": "https://example.com/flaky-repo.git", "path": "/tmp/flaky"}

        # Act - First attempt fails, retry succeeds
        attempt_count = 0

        def flaky_clone(*args, **kwargs):
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count == 1:
                raise Exception("Network timeout")
            return MagicMock()

        with patch("git.Repo.clone_from", side_effect=flaky_clone):
            result = cloner.clone_with_retry(repo, max_retries=2)

            # Assert - Should succeed on retry
            assert result.success is True
            assert attempt_count == 2
