"""Unit tests for LFS detection."""

import tempfile
from pathlib import Path

import pytest

from repo_cloner.lfs_detector import LFSDetector


@pytest.mark.unit
class TestLFSDetector:
    """Test LFS detection functionality."""

    def test_detects_lfs_enabled_repo(self):
        """Test that LFS detector identifies repos with LFS enabled."""
        # Arrange - Create a test repository with .gitattributes
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_path = Path(tmpdir)
            gitattributes = repo_path / ".gitattributes"

            # Write .gitattributes with LFS patterns
            gitattributes.write_text(
                "*.psd filter=lfs diff=lfs merge=lfs -text\n"
                "*.zip filter=lfs diff=lfs merge=lfs -text\n"
                "*.bin filter=lfs diff=lfs merge=lfs -text\n"
            )

            # Create LFS detector
            detector = LFSDetector()

            # Act - Check if LFS is enabled
            result = detector.is_lfs_enabled(str(repo_path))

            # Assert - LFS should be detected
            assert result is True

    def test_detects_no_lfs_in_regular_repo(self):
        """Test that detector returns False for repos without LFS."""
        # Arrange - Create repo without .gitattributes
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_path = Path(tmpdir)

            # Just create a regular file
            (repo_path / "README.md").write_text("# Test Repo")

            detector = LFSDetector()

            # Act
            result = detector.is_lfs_enabled(str(repo_path))

            # Assert - No LFS detected
            assert result is False

    def test_detects_no_lfs_when_gitattributes_has_no_lfs_patterns(self):
        """Test that detector returns False when .gitattributes exists but has no LFS."""
        # Arrange
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_path = Path(tmpdir)
            gitattributes = repo_path / ".gitattributes"

            # Write .gitattributes WITHOUT LFS patterns
            gitattributes.write_text(
                "* text=auto\n"
                "*.py text\n"
                "*.sh text eol=lf\n"
            )

            detector = LFSDetector()

            # Act
            result = detector.is_lfs_enabled(str(repo_path))

            # Assert - No LFS detected
            assert result is False

    def test_get_lfs_patterns_returns_tracked_extensions(self):
        """Test that detector extracts LFS file patterns from .gitattributes."""
        # Arrange
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_path = Path(tmpdir)
            gitattributes = repo_path / ".gitattributes"

            gitattributes.write_text(
                "*.psd filter=lfs diff=lfs merge=lfs -text\n"
                "*.ai filter=lfs diff=lfs merge=lfs -text\n"
                "data/*.csv filter=lfs diff=lfs merge=lfs -text\n"
            )

            detector = LFSDetector()

            # Act - Get LFS patterns
            patterns = detector.get_lfs_patterns(str(repo_path))

            # Assert - Should extract all LFS patterns
            assert "*.psd" in patterns
            assert "*.ai" in patterns
            assert "data/*.csv" in patterns
            assert len(patterns) == 3

    def test_get_lfs_patterns_returns_empty_for_non_lfs_repo(self):
        """Test that get_lfs_patterns returns empty list for non-LFS repos."""
        # Arrange
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_path = Path(tmpdir)
            (repo_path / "README.md").write_text("Test")

            detector = LFSDetector()

            # Act
            patterns = detector.get_lfs_patterns(str(repo_path))

            # Assert - No patterns
            assert patterns == []
