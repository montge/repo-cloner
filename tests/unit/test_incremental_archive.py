"""Unit tests for incremental archive creation and chain reconstruction."""

import subprocess
import tempfile
from pathlib import Path

import pytest

from repo_cloner.archive_manager import ArchiveManager


@pytest.mark.unit
class TestIncrementalArchive:
    """Test incremental archive creation with parent references."""

    def test_create_incremental_archive_with_parent_reference(self):
        """Test that incremental archive references parent and only includes new commits."""
        # Arrange
        manager = ArchiveManager()

        with tempfile.TemporaryDirectory() as tmpdir:
            repo_path = Path(tmpdir) / "test-repo"
            archive_dir = Path(tmpdir) / "archives"
            archive_dir.mkdir()

            # Create test repository with initial commit
            repo_path.mkdir()
            subprocess.run(["git", "init"], cwd=str(repo_path), check=True, capture_output=True)
            subprocess.run(
                ["git", "config", "user.name", "Test"],
                cwd=str(repo_path),
                check=True,
                capture_output=True,
            )
            subprocess.run(
                ["git", "config", "user.email", "test@test.com"],
                cwd=str(repo_path),
                check=True,
                capture_output=True,
            )
            (repo_path / "file1.txt").write_text("initial")
            subprocess.run(["git", "add", "."], cwd=str(repo_path), check=True, capture_output=True)
            subprocess.run(
                ["git", "commit", "-m", "Initial"],
                cwd=str(repo_path),
                check=True,
                capture_output=True,
            )

            # Create full archive (parent)
            full_result = manager.create_full_archive(str(repo_path), str(archive_dir))
            parent_archive_path = full_result["archive_path"]

            # Add new commits to repository
            (repo_path / "file2.txt").write_text("second commit")
            subprocess.run(["git", "add", "."], cwd=str(repo_path), check=True, capture_output=True)
            subprocess.run(
                ["git", "commit", "-m", "Second"],
                cwd=str(repo_path),
                check=True,
                capture_output=True,
            )

            (repo_path / "file3.txt").write_text("third commit")
            subprocess.run(["git", "add", "."], cwd=str(repo_path), check=True, capture_output=True)
            subprocess.run(
                ["git", "commit", "-m", "Third"],
                cwd=str(repo_path),
                check=True,
                capture_output=True,
            )

            # Act - Create incremental archive
            incr_result = manager.create_incremental_archive(
                str(repo_path), str(archive_dir), parent_archive_path
            )

            # Assert
            assert incr_result["success"] is True
            assert "archive_path" in incr_result
            assert "incremental" in Path(incr_result["archive_path"]).name
            assert incr_result["manifest"]["type"] == "incremental"
            assert incr_result["manifest"]["parent_archive"] == Path(parent_archive_path).name

    def test_incremental_archive_naming_includes_parent_timestamp(self):
        """Test that incremental archive filename includes parent reference."""
        # Arrange
        manager = ArchiveManager()

        with tempfile.TemporaryDirectory() as tmpdir:
            repo_path = Path(tmpdir) / "repo"
            archive_dir = Path(tmpdir) / "archives"
            archive_dir.mkdir()

            # Create repository
            repo_path.mkdir()
            subprocess.run(["git", "init"], cwd=str(repo_path), check=True, capture_output=True)
            subprocess.run(
                ["git", "config", "user.name", "Test"],
                cwd=str(repo_path),
                check=True,
                capture_output=True,
            )
            subprocess.run(
                ["git", "config", "user.email", "test@test.com"],
                cwd=str(repo_path),
                check=True,
                capture_output=True,
            )
            (repo_path / "f1.txt").write_text("1")
            subprocess.run(["git", "add", "."], cwd=str(repo_path), check=True, capture_output=True)
            subprocess.run(
                ["git", "commit", "-m", "C1"], cwd=str(repo_path), check=True, capture_output=True
            )

            # Full archive
            full_result = manager.create_full_archive(str(repo_path), str(archive_dir))
            parent_archive_path = full_result["archive_path"]

            # New commit
            (repo_path / "f2.txt").write_text("2")
            subprocess.run(["git", "add", "."], cwd=str(repo_path), check=True, capture_output=True)
            subprocess.run(
                ["git", "commit", "-m", "C2"], cwd=str(repo_path), check=True, capture_output=True
            )

            # Act
            incr_result = manager.create_incremental_archive(
                str(repo_path), str(archive_dir), parent_archive_path
            )

            # Assert - Should have "incremental" in name
            archive_name = Path(incr_result["archive_path"]).name
            assert "incremental" in archive_name
            assert archive_name.endswith(".tar.gz")

    def test_reconstruct_from_archive_chain(self):
        """Test that repository can be reconstructed from full + incremental chain."""
        # Arrange
        manager = ArchiveManager()

        with tempfile.TemporaryDirectory() as tmpdir:
            repo_path = Path(tmpdir) / "original"
            archive_dir = Path(tmpdir) / "archives"
            restore_dir = Path(tmpdir) / "restored"
            archive_dir.mkdir()
            restore_dir.mkdir()

            # Create repository with 3 commits
            repo_path.mkdir()
            subprocess.run(["git", "init"], cwd=str(repo_path), check=True, capture_output=True)
            subprocess.run(
                ["git", "config", "user.name", "Test"],
                cwd=str(repo_path),
                check=True,
                capture_output=True,
            )
            subprocess.run(
                ["git", "config", "user.email", "test@test.com"],
                cwd=str(repo_path),
                check=True,
                capture_output=True,
            )

            # Commit 1
            (repo_path / "file1.txt").write_text("commit 1")
            subprocess.run(["git", "add", "."], cwd=str(repo_path), check=True, capture_output=True)
            subprocess.run(
                ["git", "commit", "-m", "Commit 1"],
                cwd=str(repo_path),
                check=True,
                capture_output=True,
            )

            # Full archive after commit 1
            full_result = manager.create_full_archive(str(repo_path), str(archive_dir))

            # Commit 2
            (repo_path / "file2.txt").write_text("commit 2")
            subprocess.run(["git", "add", "."], cwd=str(repo_path), check=True, capture_output=True)
            subprocess.run(
                ["git", "commit", "-m", "Commit 2"],
                cwd=str(repo_path),
                check=True,
                capture_output=True,
            )

            # Incremental archive 1
            incr1_result = manager.create_incremental_archive(
                str(repo_path), str(archive_dir), full_result["archive_path"]
            )

            # Commit 3
            (repo_path / "file3.txt").write_text("commit 3")
            subprocess.run(["git", "add", "."], cwd=str(repo_path), check=True, capture_output=True)
            subprocess.run(
                ["git", "commit", "-m", "Commit 3"],
                cwd=str(repo_path),
                check=True,
                capture_output=True,
            )

            # Incremental archive 2
            incr2_result = manager.create_incremental_archive(
                str(repo_path), str(archive_dir), incr1_result["archive_path"]
            )

            # Act - Reconstruct from chain: full -> incr1 -> incr2
            restore_result = manager.restore_from_archive_chain(
                [
                    full_result["archive_path"],
                    incr1_result["archive_path"],
                    incr2_result["archive_path"],
                ],
                str(restore_dir),
            )

            # Assert - All 3 commits should be present
            assert restore_result["success"] is True
            restored_repo = Path(restore_result["repository_path"])
            assert (restored_repo / "file1.txt").exists()
            assert (restored_repo / "file2.txt").exists()
            assert (restored_repo / "file3.txt").exists()
            assert (restored_repo / "file1.txt").read_text() == "commit 1"
            assert (restored_repo / "file2.txt").read_text() == "commit 2"
            assert (restored_repo / "file3.txt").read_text() == "commit 3"

            # Verify git log has all 3 commits
            log_result = subprocess.run(
                ["git", "log", "--oneline"],
                cwd=str(restored_repo),
                check=True,
                capture_output=True,
                text=True,
            )
            log_output = log_result.stdout
            assert "Commit 1" in log_output
            assert "Commit 2" in log_output
            assert "Commit 3" in log_output

    def test_incremental_archive_manifest_includes_commit_range(self):
        """Test that incremental archive manifest includes start/end commit SHAs."""
        # Arrange
        manager = ArchiveManager()

        with tempfile.TemporaryDirectory() as tmpdir:
            repo_path = Path(tmpdir) / "repo"
            archive_dir = Path(tmpdir) / "archives"
            archive_dir.mkdir()

            # Create repository
            repo_path.mkdir()
            subprocess.run(["git", "init"], cwd=str(repo_path), check=True, capture_output=True)
            subprocess.run(
                ["git", "config", "user.name", "Test"],
                cwd=str(repo_path),
                check=True,
                capture_output=True,
            )
            subprocess.run(
                ["git", "config", "user.email", "test@test.com"],
                cwd=str(repo_path),
                check=True,
                capture_output=True,
            )
            (repo_path / "f1.txt").write_text("1")
            subprocess.run(["git", "add", "."], cwd=str(repo_path), check=True, capture_output=True)
            subprocess.run(
                ["git", "commit", "-m", "C1"], cwd=str(repo_path), check=True, capture_output=True
            )

            # Get first commit SHA
            sha1_result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=str(repo_path),
                check=True,
                capture_output=True,
                text=True,
            )
            commit1_sha = sha1_result.stdout.strip()

            # Full archive
            full_result = manager.create_full_archive(str(repo_path), str(archive_dir))

            # Add new commits
            (repo_path / "f2.txt").write_text("2")
            subprocess.run(["git", "add", "."], cwd=str(repo_path), check=True, capture_output=True)
            subprocess.run(
                ["git", "commit", "-m", "C2"], cwd=str(repo_path), check=True, capture_output=True
            )

            (repo_path / "f3.txt").write_text("3")
            subprocess.run(["git", "add", "."], cwd=str(repo_path), check=True, capture_output=True)
            subprocess.run(
                ["git", "commit", "-m", "C3"], cwd=str(repo_path), check=True, capture_output=True
            )

            # Get final commit SHA
            sha3_result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=str(repo_path),
                check=True,
                capture_output=True,
                text=True,
            )
            commit3_sha = sha3_result.stdout.strip()

            # Act
            incr_result = manager.create_incremental_archive(
                str(repo_path), str(archive_dir), full_result["archive_path"]
            )

            # Assert - Manifest should include commit range
            manifest = incr_result["manifest"]
            assert "commit_range" in manifest
            assert manifest["commit_range"]["from"] == commit1_sha
            assert manifest["commit_range"]["to"] == commit3_sha

    def test_incremental_archive_fails_without_parent(self):
        """Test that creating incremental archive without parent raises error."""
        # Arrange
        manager = ArchiveManager()

        with tempfile.TemporaryDirectory() as tmpdir:
            repo_path = Path(tmpdir) / "repo"
            archive_dir = Path(tmpdir) / "archives"
            archive_dir.mkdir()

            # Create repository
            repo_path.mkdir()
            subprocess.run(["git", "init"], cwd=str(repo_path), check=True, capture_output=True)
            subprocess.run(
                ["git", "config", "user.name", "Test"],
                cwd=str(repo_path),
                check=True,
                capture_output=True,
            )
            subprocess.run(
                ["git", "config", "user.email", "test@test.com"],
                cwd=str(repo_path),
                check=True,
                capture_output=True,
            )
            (repo_path / "f1.txt").write_text("1")
            subprocess.run(["git", "add", "."], cwd=str(repo_path), check=True, capture_output=True)
            subprocess.run(
                ["git", "commit", "-m", "C1"], cwd=str(repo_path), check=True, capture_output=True
            )

            # Act & Assert - Should fail without parent
            with pytest.raises(ValueError, match="parent_archive_path is required"):
                manager.create_incremental_archive(str(repo_path), str(archive_dir), None)

    def test_incremental_archive_fails_with_invalid_parent(self):
        """Test that creating incremental archive with non-existent parent raises error."""
        # Arrange
        manager = ArchiveManager()

        with tempfile.TemporaryDirectory() as tmpdir:
            repo_path = Path(tmpdir) / "repo"
            archive_dir = Path(tmpdir) / "archives"
            archive_dir.mkdir()

            # Create repository
            repo_path.mkdir()
            subprocess.run(["git", "init"], cwd=str(repo_path), check=True, capture_output=True)
            subprocess.run(
                ["git", "config", "user.name", "Test"],
                cwd=str(repo_path),
                check=True,
                capture_output=True,
            )
            subprocess.run(
                ["git", "config", "user.email", "test@test.com"],
                cwd=str(repo_path),
                check=True,
                capture_output=True,
            )
            (repo_path / "f1.txt").write_text("1")
            subprocess.run(["git", "add", "."], cwd=str(repo_path), check=True, capture_output=True)
            subprocess.run(
                ["git", "commit", "-m", "C1"], cwd=str(repo_path), check=True, capture_output=True
            )

            # Act & Assert - Should fail with non-existent parent
            with pytest.raises(FileNotFoundError):
                manager.create_incremental_archive(
                    str(repo_path), str(archive_dir), "/nonexistent/archive.tar.gz"
                )
