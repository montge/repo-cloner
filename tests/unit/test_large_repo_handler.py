"""Unit tests for large repository handling and performance optimizations."""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from repo_cloner.large_repo_handler import LargeRepoHandler


@pytest.mark.unit
class TestLargeRepoHandler:
    """Test performance optimizations for large repositories."""

    def test_shallow_clone_with_depth(self):
        """Test that shallow clone only fetches recent history."""
        # Arrange
        handler = LargeRepoHandler()

        with tempfile.TemporaryDirectory() as tmpdir:
            source_url = "https://example.com/large-repo.git"
            target_path = Path(tmpdir) / "shallow-repo"

            # Act - Clone with depth=1 (only latest commit)
            with patch("git.Repo.clone_from") as mock_clone:
                mock_repo = MagicMock()
                mock_clone.return_value = mock_repo

                handler.shallow_clone(source_url, str(target_path), depth=1)

                # Assert - Should pass depth parameter
                mock_clone.assert_called_once()
                call_kwargs = mock_clone.call_args[1]
                assert call_kwargs["depth"] == 1

    def test_shallow_clone_with_single_branch(self):
        """Test that shallow clone can fetch only one branch."""
        # Arrange
        handler = LargeRepoHandler()

        with tempfile.TemporaryDirectory() as tmpdir:
            source_url = "https://example.com/large-repo.git"
            target_path = Path(tmpdir) / "single-branch-repo"

            # Act - Clone only main branch
            with patch("git.Repo.clone_from") as mock_clone:
                mock_repo = MagicMock()
                mock_clone.return_value = mock_repo

                handler.shallow_clone(
                    source_url, str(target_path), depth=1, single_branch=True, branch="main"
                )

                # Assert - Should pass single-branch flag
                call_kwargs = mock_clone.call_args[1]
                assert call_kwargs["single_branch"] is True
                assert call_kwargs["branch"] == "main"

    def test_unshallow_converts_shallow_to_full(self):
        """Test that we can convert a shallow clone to full history."""
        # Arrange
        handler = LargeRepoHandler()

        with tempfile.TemporaryDirectory() as tmpdir:
            repo_path = Path(tmpdir)

            # Act
            with patch("subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(returncode=0)

                handler.unshallow(str(repo_path))

                # Assert - Should run git fetch --unshallow
                call_args = mock_run.call_args[0][0]
                assert "git" in call_args
                assert "fetch" in call_args
                assert "--unshallow" in call_args

    def test_partial_clone_with_blob_filter(self):
        """Test partial clone that skips large blobs initially."""
        # Arrange
        handler = LargeRepoHandler()

        with tempfile.TemporaryDirectory() as tmpdir:
            source_url = "https://example.com/large-repo.git"
            target_path = Path(tmpdir) / "partial-repo"

            # Act - Partial clone without blobs
            with patch("subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(returncode=0)

                result = handler.partial_clone(
                    source_url, str(target_path), filter_spec="blob:none"
                )

                # Assert - Should use --filter flag
                call_args = mock_run.call_args[0][0]
                assert "git" in call_args
                assert "clone" in call_args
                assert "--filter=blob:none" in call_args
                assert result["success"] is True

    def test_partial_clone_with_blob_size_limit(self):
        """Test partial clone with blob size filter."""
        # Arrange
        handler = LargeRepoHandler()

        with tempfile.TemporaryDirectory() as tmpdir:
            source_url = "https://example.com/large-repo.git"
            target_path = Path(tmpdir) / "partial-repo"

            # Act - Only clone blobs smaller than 1MB
            with patch("subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(returncode=0)

                handler.partial_clone(source_url, str(target_path), filter_spec="blob:limit=1m")

                # Assert - Should use blob size filter
                call_args = mock_run.call_args[0][0]
                assert "--filter=blob:limit=1m" in call_args

    def test_get_repo_size_estimates_disk_usage(self):
        """Test getting repository disk usage."""
        # Arrange
        handler = LargeRepoHandler()

        with tempfile.TemporaryDirectory() as tmpdir:
            repo_path = Path(tmpdir)

            # Act
            with patch("subprocess.run") as mock_run:
                # Mock du output: "524288\t.git"  (512 KB)
                mock_run.return_value = MagicMock(returncode=0, stdout="524288\t.git")

                size_info = handler.get_repo_size(str(repo_path))

                # Assert - Should return size in bytes
                assert size_info["total_size_bytes"] > 0
                assert size_info["total_size_mb"] > 0
                assert isinstance(size_info["total_size_bytes"], int)

    def test_estimate_clone_time_predicts_duration(self):
        """Test estimation of clone time based on repo size."""
        # Arrange
        handler = LargeRepoHandler()

        # Act - Estimate for 1GB repo at 10MB/s
        estimate = handler.estimate_clone_time(repo_size_mb=1024, network_speed_mbps=10)

        # Assert - Should calculate reasonable estimate
        assert estimate["estimated_seconds"] > 0
        assert estimate["estimated_minutes"] > 0
        assert "estimated_human_readable" in estimate

    def test_optimize_for_bandwidth_enables_compression(self):
        """Test that bandwidth optimization enables Git compression."""
        # Arrange
        handler = LargeRepoHandler()

        with tempfile.TemporaryDirectory() as tmpdir:
            repo_path = Path(tmpdir)

            # Act
            with patch("git.Repo") as mock_repo_class:
                mock_repo = MagicMock()
                mock_config = MagicMock()
                mock_repo.config_writer.return_value.__enter__.return_value = mock_config
                mock_repo_class.return_value = mock_repo

                handler.optimize_for_bandwidth(str(repo_path))

                # Assert - Should configure compression
                mock_config.set_value.assert_any_call("core", "compression", "9")
                mock_config.set_value.assert_any_call("pack", "compression", "9")

    def test_check_git_version_supports_partial_clone(self):
        """Test checking if Git version supports partial clone."""
        # Arrange
        handler = LargeRepoHandler()

        # Act
        with patch("subprocess.run") as mock_run:
            # Mock git version 2.19+ (supports partial clone)
            mock_run.return_value = MagicMock(returncode=0, stdout="git version 2.30.0")

            result = handler.check_partial_clone_support()

            # Assert - Should detect support
            assert result["supported"] is True
            assert result["version"] >= "2.19.0"

    def test_deepen_shallow_clone_fetches_more_history(self):
        """Test deepening a shallow clone to fetch more commits."""
        # Arrange
        handler = LargeRepoHandler()

        with tempfile.TemporaryDirectory() as tmpdir:
            repo_path = Path(tmpdir)

            # Act - Deepen by 50 commits
            with patch("subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(returncode=0)

                handler.deepen(str(repo_path), depth=50)

                # Assert - Should run git fetch --depth
                call_args = mock_run.call_args[0][0]
                assert "git" in call_args
                assert "fetch" in call_args
                assert "--depth=50" in call_args
