"""Tests for archive retention policies."""

import tempfile
import time
from pathlib import Path

import pytest

from repo_cloner.archive_manager import ArchiveManager


class TestArchiveRetention:
    """Test suite for archive retention policies."""

    def test_apply_retention_policy_keeps_archives_within_age_limit(self):
        """Test that archives within age limit are kept."""
        manager = ArchiveManager()

        with tempfile.TemporaryDirectory() as tmpdir:
            archives_dir = Path(tmpdir) / "archives"
            archives_dir.mkdir()

            # Create recent archive (should be kept)
            archive1 = archives_dir / "repo-full-20251010.tar.gz"
            archive1.write_bytes(b"recent archive")

            # Act - retention policy: 30 days
            result = manager.apply_retention_policy(
                archives_path=str(archives_dir), max_age_days=30, dry_run=False
            )

            # Assert
            assert archive1.exists()
            assert result["deleted_count"] == 0
            assert result["kept_count"] == 1

    def test_apply_retention_policy_deletes_archives_older_than_limit(self):
        """Test that archives older than age limit are deleted."""
        manager = ArchiveManager()

        with tempfile.TemporaryDirectory() as tmpdir:
            archives_dir = Path(tmpdir) / "archives"
            archives_dir.mkdir()

            # Create old archive
            old_archive = archives_dir / "repo-full-20200101.tar.gz"
            old_archive.write_bytes(b"old archive")

            # Set modification time to 60 days ago
            old_time = time.time() - (60 * 24 * 60 * 60)  # 60 days in seconds
            Path(old_archive).touch()
            import os

            os.utime(old_archive, (old_time, old_time))

            # Act - retention policy: 30 days
            result = manager.apply_retention_policy(
                archives_path=str(archives_dir), max_age_days=30, dry_run=False
            )

            # Assert
            assert not old_archive.exists()
            assert result["deleted_count"] == 1
            assert result["kept_count"] == 0

    def test_apply_retention_policy_keeps_only_max_count_archives(self):
        """Test that only max_count most recent archives are kept."""
        manager = ArchiveManager()

        with tempfile.TemporaryDirectory() as tmpdir:
            archives_dir = Path(tmpdir) / "archives"
            archives_dir.mkdir()

            # Create 5 archives
            for i in range(5):
                archive = archives_dir / f"repo-full-2025010{i}.tar.gz"
                archive.write_bytes(b"archive content")
                # Set different modification times
                mtime = time.time() - (i * 24 * 60 * 60)  # i days ago
                import os

                os.utime(archive, (mtime, mtime))

            # Act - keep only 3 most recent
            result = manager.apply_retention_policy(
                archives_path=str(archives_dir), max_count=3, dry_run=False
            )

            # Assert
            assert result["deleted_count"] == 2
            assert result["kept_count"] == 3
            # Check that the 3 most recent exist
            assert (archives_dir / "repo-full-20250100.tar.gz").exists()
            assert (archives_dir / "repo-full-20250101.tar.gz").exists()
            assert (archives_dir / "repo-full-20250102.tar.gz").exists()
            # Check that the 2 oldest were deleted
            assert not (archives_dir / "repo-full-20250103.tar.gz").exists()
            assert not (archives_dir / "repo-full-20250104.tar.gz").exists()

    def test_apply_retention_policy_combines_age_and_count_limits(self):
        """Test that both age and count limits are applied together."""
        manager = ArchiveManager()

        with tempfile.TemporaryDirectory() as tmpdir:
            archives_dir = Path(tmpdir) / "archives"
            archives_dir.mkdir()

            # Create archives with different ages
            import os

            for i in range(5):
                archive = archives_dir / f"repo-{i}.tar.gz"
                archive.write_bytes(b"content")
                # Make some old, some new
                days_ago = i * 10  # 0, 10, 20, 30, 40 days
                mtime = time.time() - (days_ago * 24 * 60 * 60)
                os.utime(archive, (mtime, mtime))

            # Act - max_age_days=25, max_count=2
            # Should keep only 2 archives that are < 25 days old
            result = manager.apply_retention_policy(
                archives_path=str(archives_dir), max_age_days=25, max_count=2, dry_run=False
            )

            # Assert - archives older than 25 days deleted (30, 40 days)
            # Plus oldest within limit (20 days) deleted due to max_count=2
            assert result["deleted_count"] == 3
            assert result["kept_count"] == 2

    def test_apply_retention_policy_dry_run_does_not_delete(self):
        """Test that dry_run mode doesn't actually delete archives."""
        manager = ArchiveManager()

        with tempfile.TemporaryDirectory() as tmpdir:
            archives_dir = Path(tmpdir) / "archives"
            archives_dir.mkdir()

            # Create old archive
            old_archive = archives_dir / "repo-old.tar.gz"
            old_archive.write_bytes(b"old")

            import os

            old_time = time.time() - (60 * 24 * 60 * 60)  # 60 days
            os.utime(old_archive, (old_time, old_time))

            # Act - dry run
            result = manager.apply_retention_policy(
                archives_path=str(archives_dir), max_age_days=30, dry_run=True
            )

            # Assert - archive still exists but counted as would-be-deleted
            assert old_archive.exists()
            assert result["deleted_count"] == 1
            assert result["dry_run"] is True

    def test_apply_retention_policy_only_affects_tar_gz_files(self):
        """Test that retention policy only affects .tar.gz files."""
        manager = ArchiveManager()

        with tempfile.TemporaryDirectory() as tmpdir:
            archives_dir = Path(tmpdir) / "archives"
            archives_dir.mkdir()

            # Create various files
            (archives_dir / "archive.tar.gz").write_bytes(b"archive")
            (archives_dir / "readme.txt").write_text("text file")
            (archives_dir / "data.json").write_text("{}")

            import os

            old_time = time.time() - (60 * 24 * 60 * 60)
            for f in archives_dir.iterdir():
                os.utime(f, (old_time, old_time))

            # Act
            result = manager.apply_retention_policy(
                archives_path=str(archives_dir), max_age_days=30, dry_run=False
            )

            # Assert - only .tar.gz deleted
            assert not (archives_dir / "archive.tar.gz").exists()
            assert (archives_dir / "readme.txt").exists()
            assert (archives_dir / "data.json").exists()
            assert result["deleted_count"] == 1

    def test_apply_retention_policy_raises_error_if_path_not_exists(self):
        """Test that apply_retention_policy raises error for non-existent path."""
        manager = ArchiveManager()

        with pytest.raises(FileNotFoundError):
            manager.apply_retention_policy(
                archives_path="/nonexistent/path", max_age_days=30, dry_run=False
            )

    def test_apply_retention_policy_handles_empty_directory(self):
        """Test that retention policy handles empty directories gracefully."""
        manager = ArchiveManager()

        with tempfile.TemporaryDirectory() as tmpdir:
            archives_dir = Path(tmpdir) / "empty"
            archives_dir.mkdir()

            # Act
            result = manager.apply_retention_policy(
                archives_path=str(archives_dir), max_age_days=30, dry_run=False
            )

            # Assert
            assert result["deleted_count"] == 0
            assert result["kept_count"] == 0

    def test_apply_retention_policy_returns_list_of_deleted_files(self):
        """Test that retention policy returns list of deleted file paths."""
        manager = ArchiveManager()

        with tempfile.TemporaryDirectory() as tmpdir:
            archives_dir = Path(tmpdir) / "archives"
            archives_dir.mkdir()

            old1 = archives_dir / "old1.tar.gz"
            old2 = archives_dir / "old2.tar.gz"
            old1.write_bytes(b"old")
            old2.write_bytes(b"old")

            import os

            old_time = time.time() - (60 * 24 * 60 * 60)
            os.utime(old1, (old_time, old_time))
            os.utime(old2, (old_time, old_time))

            # Act
            result = manager.apply_retention_policy(
                archives_path=str(archives_dir), max_age_days=30, dry_run=False
            )

            # Assert
            assert "deleted_files" in result
            assert len(result["deleted_files"]) == 2
            assert str(old1) in result["deleted_files"]
            assert str(old2) in result["deleted_files"]

    def test_apply_retention_policy_requires_at_least_one_limit(self):
        """Test that at least one of max_age_days or max_count must be specified."""
        manager = ArchiveManager()

        with tempfile.TemporaryDirectory() as tmpdir:
            archives_dir = Path(tmpdir) / "archives"
            archives_dir.mkdir()

            # Act & Assert - no limits specified
            with pytest.raises(ValueError, match="At least one of max_age_days or max_count"):
                manager.apply_retention_policy(archives_path=str(archives_dir), dry_run=False)
