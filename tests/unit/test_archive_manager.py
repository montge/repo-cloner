"""Unit tests for archive creation and management."""

import subprocess
import tempfile
from pathlib import Path

import pytest

from repo_cloner.archive_manager import ArchiveManager


@pytest.mark.unit
class TestArchiveManager:
    """Test archive creation, extraction, and management."""

    def test_create_full_archive_from_repo(self):
        """Test that full archive creates tar.gz with git bundle."""
        # Arrange
        manager = ArchiveManager()

        with tempfile.TemporaryDirectory() as tmpdir:
            repo_path = Path(tmpdir) / "test-repo"
            output_path = Path(tmpdir) / "archives"
            output_path.mkdir()

            # Create a test git repository
            repo_path.mkdir()
            subprocess.run(["git", "init"], cwd=str(repo_path), check=True, capture_output=True)
            subprocess.run(
                ["git", "config", "user.name", "Test User"],
                cwd=str(repo_path),
                check=True,
                capture_output=True,
            )
            subprocess.run(
                ["git", "config", "user.email", "test@example.com"],
                cwd=str(repo_path),
                check=True,
                capture_output=True,
            )

            # Add a test file and commit
            test_file = repo_path / "README.md"
            test_file.write_text("# Test Repository\n")
            subprocess.run(
                ["git", "add", "README.md"], cwd=str(repo_path), check=True, capture_output=True
            )
            subprocess.run(
                ["git", "commit", "-m", "Initial commit"],
                cwd=str(repo_path),
                check=True,
                capture_output=True,
            )

            # Act
            result = manager.create_full_archive(str(repo_path), str(output_path))

            # Assert
            assert result["success"] is True
            assert "archive_path" in result
            archive_file = Path(result["archive_path"])
            assert archive_file.exists()
            assert archive_file.suffix == ".gz"
            assert "full" in archive_file.name

    def test_full_archive_includes_manifest(self):
        """Test that full archive includes a manifest file with metadata."""
        # Arrange
        manager = ArchiveManager()

        with tempfile.TemporaryDirectory() as tmpdir:
            repo_path = Path(tmpdir) / "test-repo"
            output_path = Path(tmpdir) / "archives"
            output_path.mkdir()

            # Create test repository
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
            (repo_path / "file.txt").write_text("test")
            subprocess.run(["git", "add", "."], cwd=str(repo_path), check=True, capture_output=True)
            subprocess.run(
                ["git", "commit", "-m", "Test"], cwd=str(repo_path), check=True, capture_output=True
            )

            # Act
            result = manager.create_full_archive(str(repo_path), str(output_path))

            # Assert - Manifest should be included
            assert result["success"] is True
            assert "manifest" in result
            manifest = result["manifest"]
            assert manifest["type"] == "full"
            assert "timestamp" in manifest
            assert "repository" in manifest

    def test_archive_naming_convention(self):
        """Test that archive follows naming convention: repo-name-full-timestamp.tar.gz"""
        # Arrange
        manager = ArchiveManager()

        with tempfile.TemporaryDirectory() as tmpdir:
            repo_path = Path(tmpdir) / "my-test-repo"
            output_path = Path(tmpdir) / "archives"
            output_path.mkdir()

            # Create test repository
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
            (repo_path / "file.txt").write_text("test")
            subprocess.run(["git", "add", "."], cwd=str(repo_path), check=True, capture_output=True)
            subprocess.run(
                ["git", "commit", "-m", "Test"], cwd=str(repo_path), check=True, capture_output=True
            )

            # Act
            result = manager.create_full_archive(str(repo_path), str(output_path))

            # Assert
            archive_file = Path(result["archive_path"])
            assert "my-test-repo" in archive_file.name
            assert "full" in archive_file.name
            assert archive_file.name.endswith(".tar.gz")

    def test_extract_archive_restores_repo(self):
        """Test that extracting an archive restores the repository."""
        # Arrange
        manager = ArchiveManager()

        with tempfile.TemporaryDirectory() as tmpdir:
            repo_path = Path(tmpdir) / "original-repo"
            archive_path_dir = Path(tmpdir) / "archives"
            extract_path = Path(tmpdir) / "extracted"
            archive_path_dir.mkdir()
            extract_path.mkdir()

            # Create and archive a test repository
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
            (repo_path / "README.md").write_text("# Original Repo\n")
            subprocess.run(["git", "add", "."], cwd=str(repo_path), check=True, capture_output=True)
            subprocess.run(
                ["git", "commit", "-m", "Initial"],
                cwd=str(repo_path),
                check=True,
                capture_output=True,
            )

            archive_result = manager.create_full_archive(str(repo_path), str(archive_path_dir))
            archive_file = archive_result["archive_path"]

            # Act
            extract_result = manager.extract_archive(archive_file, str(extract_path))

            # Assert
            assert extract_result["success"] is True
            extracted_repo = extract_path / "repository"
            assert extracted_repo.exists()
            assert (extracted_repo / "README.md").exists()
            assert (extracted_repo / "README.md").read_text() == "# Original Repo\n"

    def test_validates_repository_path_exists(self):
        """Test that create_full_archive validates repository path exists."""
        # Arrange
        manager = ArchiveManager()

        # Act & Assert
        with pytest.raises(FileNotFoundError):
            manager.create_full_archive("/nonexistent/repo", "/output")

    def test_creates_output_directory_if_missing(self):
        """Test that output directory is created if it doesn't exist."""
        # Arrange
        manager = ArchiveManager()

        with tempfile.TemporaryDirectory() as tmpdir:
            repo_path = Path(tmpdir) / "test-repo"
            output_path = Path(tmpdir) / "new-archives" / "subfolder"

            # Create test repository
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
            (repo_path / "file.txt").write_text("test")
            subprocess.run(["git", "add", "."], cwd=str(repo_path), check=True, capture_output=True)
            subprocess.run(
                ["git", "commit", "-m", "Test"], cwd=str(repo_path), check=True, capture_output=True
            )

            # Act
            result = manager.create_full_archive(str(repo_path), str(output_path))

            # Assert
            assert result["success"] is True
            assert output_path.exists()
            archive_file = Path(result["archive_path"])
            assert archive_file.parent == output_path
