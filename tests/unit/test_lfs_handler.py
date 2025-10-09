"""Unit tests for LFS handling during clone and sync operations."""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from repo_cloner.lfs_handler import LFSHandler


@pytest.mark.unit
class TestLFSHandler:
    """Test LFS clone and sync functionality."""

    def test_check_lfs_installed_returns_true_when_available(self):
        """Test that LFS installation check succeeds when git-lfs is available."""
        # Arrange
        handler = LFSHandler()

        # Act & Assert - Should not raise exception
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="git-lfs/3.4.0")
            result = handler.check_lfs_installed()
            assert result is True

    def test_check_lfs_installed_returns_false_when_not_available(self):
        """Test that LFS installation check fails when git-lfs is not installed."""
        # Arrange
        handler = LFSHandler()

        # Act & Assert
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = FileNotFoundError("git-lfs not found")
            result = handler.check_lfs_installed()
            assert result is False

    def test_clone_with_lfs_uses_correct_flags(self):
        """Test that LFS clone uses GIT_LFS_SKIP_SMUDGE for faster initial clone."""
        # Arrange
        handler = LFSHandler()

        with tempfile.TemporaryDirectory() as tmpdir:
            source_url = "https://example.com/repo.git"
            target_path = Path(tmpdir) / "test-repo"

            # Act - Mock git clone to verify flags
            with patch("git.Repo.clone_from") as mock_clone, patch("subprocess.run") as mock_run:
                mock_repo = MagicMock()
                mock_clone.return_value = mock_repo
                mock_run.return_value = MagicMock(returncode=0)

                handler.clone_with_lfs(source_url, str(target_path))

                # Assert - Verify clone was called with skip smudge
                mock_clone.assert_called_once()
                call_kwargs = mock_clone.call_args[1]
                assert "env" in call_kwargs
                assert call_kwargs["env"]["GIT_LFS_SKIP_SMUDGE"] == "1"

    def test_fetch_lfs_objects_runs_lfs_pull(self):
        """Test that LFS objects are fetched after initial clone."""
        # Arrange
        handler = LFSHandler()

        with tempfile.TemporaryDirectory() as tmpdir:
            repo_path = Path(tmpdir) / "test-repo"
            repo_path.mkdir()

            # Act
            with patch("subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(returncode=0)

                handler.fetch_lfs_objects(str(repo_path))

                # Assert - Verify git lfs pull was called
                mock_run.assert_called_once()
                call_args = mock_run.call_args[0][0]
                assert "git" in call_args
                assert "lfs" in call_args
                assert "pull" in call_args

    def test_clone_with_lfs_full_workflow(self):
        """Test complete LFS clone workflow: clone with skip + fetch LFS."""
        # Arrange
        handler = LFSHandler()

        with tempfile.TemporaryDirectory() as tmpdir:
            source_url = "https://example.com/lfs-repo.git"
            target_path = Path(tmpdir) / "lfs-repo"

            # Act
            with patch("git.Repo.clone_from") as mock_clone, patch("subprocess.run") as mock_run:

                mock_repo = MagicMock()
                mock_clone.return_value = mock_repo
                mock_run.return_value = MagicMock(returncode=0)

                result = handler.clone_with_lfs(source_url, str(target_path), fetch_lfs=True)

                # Assert - Both clone and LFS pull executed
                assert mock_clone.called
                assert mock_run.called
                assert result["success"] is True
                assert result["lfs_objects_fetched"] is True

    def test_clone_with_lfs_skip_fetch_when_disabled(self):
        """Test that LFS fetch can be skipped if fetch_lfs=False."""
        # Arrange
        handler = LFSHandler()

        with tempfile.TemporaryDirectory() as tmpdir:
            source_url = "https://example.com/lfs-repo.git"
            target_path = Path(tmpdir) / "lfs-repo"

            # Act
            with patch("git.Repo.clone_from") as mock_clone, patch("subprocess.run") as mock_run:

                mock_repo = MagicMock()
                mock_clone.return_value = mock_repo

                result = handler.clone_with_lfs(
                    source_url, str(target_path), fetch_lfs=False  # Skip LFS fetch
                )

                # Assert - Clone called but NOT lfs pull
                assert mock_clone.called
                assert not mock_run.called
                assert result["success"] is True
                assert result["lfs_objects_fetched"] is False

    def test_get_lfs_info_returns_object_count(self):
        """Test that we can get information about LFS objects in a repo."""
        # Arrange
        handler = LFSHandler()

        with tempfile.TemporaryDirectory() as tmpdir:
            repo_path = Path(tmpdir)

            # Act
            with patch("subprocess.run") as mock_run:
                # Mock git lfs ls-files output
                mock_run.return_value = MagicMock(
                    returncode=0, stdout="abc123 * file1.psd\ndef456 * file2.zip\n"
                )

                info = handler.get_lfs_info(str(repo_path))

                # Assert - Should parse LFS object count
                assert info["lfs_file_count"] == 2
                assert "file1.psd" in str(info["lfs_files"])
                assert "file2.zip" in str(info["lfs_files"])
