"""Unit tests for LFS sync operations."""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from repo_cloner.lfs_sync import LFSSync


@pytest.mark.unit
class TestLFSSync:
    """Test LFS sync and incremental update functionality."""

    def test_sync_lfs_fetches_only_new_objects(self):
        """Test that LFS sync only fetches new/changed objects."""
        # Arrange
        sync = LFSSync()

        with tempfile.TemporaryDirectory() as tmpdir:
            repo_path = Path(tmpdir)

            # Act
            with patch("subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(
                    returncode=0,
                    stdout="Downloading file1.psd (5 MB)\nDownloading file2.zip (10 MB)\n",
                )

                result = sync.sync_lfs_objects(str(repo_path))

                # Assert - git lfs fetch called
                assert mock_run.called
                call_args = mock_run.call_args[0][0]
                assert "git" in call_args
                assert "lfs" in call_args
                assert "fetch" in call_args
                assert result["success"] is True
                assert result["objects_fetched"] > 0

    def test_sync_lfs_uses_recent_flag_for_incremental(self):
        """Test that LFS sync can fetch only recent objects."""
        # Arrange
        sync = LFSSync()

        with tempfile.TemporaryDirectory() as tmpdir:
            repo_path = Path(tmpdir)

            # Act - Sync with recent flag (last 7 days)
            with patch("subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(returncode=0, stdout="")

                sync.sync_lfs_objects(str(repo_path), recent=True)

                # Assert - Should use --recent flag
                call_args = mock_run.call_args[0][0]
                assert "--recent" in call_args

    def test_sync_lfs_prunes_old_objects(self):
        """Test that LFS sync can prune unreferenced objects."""
        # Arrange
        sync = LFSSync()

        with tempfile.TemporaryDirectory() as tmpdir:
            repo_path = Path(tmpdir)

            # Act
            with patch("subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(returncode=0)

                result = sync.prune_lfs_objects(str(repo_path))

                # Assert - git lfs prune called
                call_args = mock_run.call_args[0][0]
                assert "git" in call_args
                assert "lfs" in call_args
                assert "prune" in call_args
                assert result["success"] is True

    def test_sync_lfs_detects_changed_objects(self):
        """Test detection of LFS objects that have changed."""
        # Arrange
        sync = LFSSync()

        # Mock two different states
        old_lfs_files = ["file1.psd", "file2.zip"]
        new_lfs_files = ["file1.psd", "file2.zip", "file3.bin"]

        # Act
        changes = sync.detect_lfs_changes(old_lfs_files, new_lfs_files)

        # Assert - Should detect new file
        assert changes["added"] == ["file3.bin"]
        assert changes["removed"] == []
        assert changes["unchanged"] == ["file1.psd", "file2.zip"]

    def test_sync_lfs_detects_removed_objects(self):
        """Test detection of LFS objects that were removed."""
        # Arrange
        sync = LFSSync()

        old_lfs_files = ["file1.psd", "file2.zip", "file3.bin"]
        new_lfs_files = ["file1.psd", "file2.zip"]

        # Act
        changes = sync.detect_lfs_changes(old_lfs_files, new_lfs_files)

        # Assert - Should detect removed file
        assert changes["added"] == []
        assert changes["removed"] == ["file3.bin"]
        assert changes["unchanged"] == ["file1.psd", "file2.zip"]

    def test_sync_lfs_checkout_updates_working_tree(self):
        """Test that LFS checkout updates working tree with LFS objects."""
        # Arrange
        sync = LFSSync()

        with tempfile.TemporaryDirectory() as tmpdir:
            repo_path = Path(tmpdir)

            # Act
            with patch("subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(returncode=0)

                result = sync.checkout_lfs_objects(str(repo_path))

                # Assert - git lfs checkout called
                call_args = mock_run.call_args[0][0]
                assert "git" in call_args
                assert "lfs" in call_args
                assert "checkout" in call_args
                assert result["success"] is True

    def test_get_lfs_storage_size(self):
        """Test getting total size of LFS storage."""
        # Arrange
        sync = LFSSync()

        with tempfile.TemporaryDirectory() as tmpdir:
            repo_path = Path(tmpdir)

            # Act
            with patch("subprocess.run") as mock_run:
                # Mock du output for .git/lfs directory
                mock_run.return_value = MagicMock(
                    returncode=0, stdout="524288\t.git/lfs"  # 512 KB in bytes
                )

                size = sync.get_lfs_storage_size(str(repo_path))

                # Assert - Should return size in bytes
                assert size > 0
                assert isinstance(size, int)

    def test_sync_lfs_with_filter_includes_only_patterns(self):
        """Test that LFS sync can filter by file patterns."""
        # Arrange
        sync = LFSSync()

        with tempfile.TemporaryDirectory() as tmpdir:
            repo_path = Path(tmpdir)

            # Act - Sync only .psd files
            with patch("subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(returncode=0, stdout="")

                sync.sync_lfs_objects(str(repo_path), include_patterns=["*.psd"])

                # Assert - Should use --include flag
                call_args = mock_run.call_args[0][0]
                assert "--include" in call_args
                assert "*.psd" in call_args
