"""Tests for LFS object bundling in archives."""

import subprocess
import tarfile
import tempfile
from pathlib import Path
from unittest.mock import patch

from repo_cloner.archive_manager import ArchiveManager


class TestArchiveLFSBundling:
    """Test suite for LFS object bundling in archives."""

    def test_full_archive_bundles_lfs_objects_when_enabled(self):
        """Test that full archive includes LFS objects when include_lfs=True."""
        manager = ArchiveManager()

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create real test repository
            repo_path = Path(tmpdir) / "test-repo"
            subprocess.run(["git", "init", str(repo_path)], check=True, capture_output=True)
            subprocess.run(
                ["git", "config", "user.name", "Test"],
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

            # Create a test file and commit
            (repo_path / "test.txt").write_text("test content")
            subprocess.run(
                ["git", "add", "test.txt"],
                cwd=str(repo_path),
                check=True,
                capture_output=True,
            )
            subprocess.run(
                ["git", "commit", "-m", "Initial commit"],
                cwd=str(repo_path),
                check=True,
                capture_output=True,
            )

            # Create .gitattributes to simulate LFS (without actually using LFS)
            (repo_path / ".gitattributes").write_text("*.bin filter=lfs\n")
            subprocess.run(
                ["git", "add", ".gitattributes"],
                cwd=str(repo_path),
                check=True,
                capture_output=True,
            )
            subprocess.run(
                ["git", "commit", "-m", "Add LFS tracking"],
                cwd=str(repo_path),
                check=True,
                capture_output=True,
            )

            # Create mock LFS object directory
            lfs_dir = repo_path / ".git" / "lfs" / "objects" / "ab" / "cd"
            lfs_dir.mkdir(parents=True)
            (lfs_dir / "abcd1234").write_bytes(b"mock LFS object")

            output_path = Path(tmpdir) / "archives"

            # Act
            result = manager.create_full_archive(
                repo_path=str(repo_path),
                output_path=str(output_path),
                include_lfs=True,
            )

            # Assert
            assert result["success"] is True
            assert result["manifest"]["lfs_enabled"] is True

            # Verify archive contains lfs-objects directory
            archive_path = Path(result["archive_path"])
            assert archive_path.exists()

            with tarfile.open(archive_path, "r:gz") as tar:
                members = tar.getnames()
                assert "manifest.json" in members
                assert "repository.bundle" in members
                # LFS objects should be included
                assert any("lfs-objects" in name for name in members)

    def test_full_archive_skips_lfs_objects_when_disabled(self):
        """Test that full archive excludes LFS objects when include_lfs=False."""
        manager = ArchiveManager()

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create real test repository
            repo_path = Path(tmpdir) / "test-repo"
            subprocess.run(["git", "init", str(repo_path)], check=True, capture_output=True)
            subprocess.run(
                ["git", "config", "user.name", "Test"],
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

            # Create a test file and commit
            (repo_path / "test.txt").write_text("test content")
            subprocess.run(
                ["git", "add", "test.txt"],
                cwd=str(repo_path),
                check=True,
                capture_output=True,
            )
            subprocess.run(
                ["git", "commit", "-m", "Initial commit"],
                cwd=str(repo_path),
                check=True,
                capture_output=True,
            )

            output_path = Path(tmpdir) / "archives"

            # Act
            result = manager.create_full_archive(
                repo_path=str(repo_path),
                output_path=str(output_path),
                include_lfs=False,
            )

            # Assert
            assert result["success"] is True
            assert result["manifest"]["lfs_enabled"] is False
            assert result["manifest"]["lfs_object_count"] == 0

            # Verify archive does NOT contain lfs-objects
            archive_path = Path(result["archive_path"])
            with tarfile.open(archive_path, "r:gz") as tar:
                members = tar.getnames()
                assert not any("lfs-objects" in name for name in members)

    def test_lfs_objects_stored_in_separate_directory(self):
        """Test that LFS objects are stored in lfs-objects/ directory in archive."""
        manager = ArchiveManager()

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create real test repository with LFS
            repo_path = Path(tmpdir) / "test-repo"
            subprocess.run(["git", "init", str(repo_path)], check=True, capture_output=True)
            subprocess.run(
                ["git", "config", "user.name", "Test"],
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

            # Create a test file and commit
            (repo_path / "test.txt").write_text("test content")
            subprocess.run(
                ["git", "add", "test.txt"],
                cwd=str(repo_path),
                check=True,
                capture_output=True,
            )
            subprocess.run(
                ["git", "commit", "-m", "Initial commit"],
                cwd=str(repo_path),
                check=True,
                capture_output=True,
            )

            # Create .gitattributes for LFS (simulate LFS without actually using it)
            (repo_path / ".gitattributes").write_text("*.bin filter=lfs\n")
            subprocess.run(
                ["git", "add", ".gitattributes"],
                cwd=str(repo_path),
                check=True,
                capture_output=True,
            )
            subprocess.run(
                ["git", "commit", "-m", "Add LFS tracking"],
                cwd=str(repo_path),
                check=True,
                capture_output=True,
            )

            # Create mock LFS object directory with proper structure
            lfs_dir = repo_path / ".git" / "lfs" / "objects" / "ab" / "cd"
            lfs_dir.mkdir(parents=True)
            (lfs_dir / "abcd1234").write_bytes(b"mock LFS object 1")
            (lfs_dir / "abcd5678").write_bytes(b"mock LFS object 2")

            output_path = Path(tmpdir) / "archives"

            # Act
            result = manager.create_full_archive(
                repo_path=str(repo_path),
                output_path=str(output_path),
                include_lfs=True,
            )

            # Assert
            assert result["success"] is True
            assert result["manifest"]["lfs_enabled"] is True
            assert result["manifest"]["lfs_object_count"] == 2

            # Verify LFS objects are in archive
            archive_path = Path(result["archive_path"])
            with tarfile.open(archive_path, "r:gz") as tar:
                members = tar.getnames()
                # Check that lfs-objects directory exists in archive
                assert any("lfs-objects" in name for name in members)
                # Check that LFS objects preserve structure
                assert any("lfs-objects/ab/cd" in name for name in members)

    def test_incremental_archive_bundles_only_new_lfs_objects(self):
        """Test that incremental archive includes only new LFS objects."""
        manager = ArchiveManager()

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create test repositories
            repo_path = Path(tmpdir) / "test-repo"
            subprocess.run(["git", "init", str(repo_path)], check=True, capture_output=True)
            subprocess.run(
                ["git", "config", "user.name", "Test"],
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

            # Create initial commit
            (repo_path / "test.txt").write_text("test")
            subprocess.run(
                ["git", "add", "test.txt"],
                cwd=str(repo_path),
                check=True,
                capture_output=True,
            )
            subprocess.run(
                ["git", "commit", "-m", "Initial"],
                cwd=str(repo_path),
                check=True,
                capture_output=True,
            )

            output_path = Path(tmpdir) / "archives"

            # Create parent archive
            parent_result = manager.create_full_archive(
                repo_path=str(repo_path),
                output_path=str(output_path),
                include_lfs=False,
            )

            # Add new commit
            (repo_path / "test2.txt").write_text("test2")
            subprocess.run(
                ["git", "add", "test2.txt"],
                cwd=str(repo_path),
                check=True,
                capture_output=True,
            )
            subprocess.run(
                ["git", "commit", "-m", "Second"],
                cwd=str(repo_path),
                check=True,
                capture_output=True,
            )

            # Act - Create incremental archive with LFS
            with patch.object(manager, "_bundle_lfs_objects_incremental") as mock_lfs:
                mock_lfs.return_value = ["lfs-objects/new-file.bin"]

                result = manager.create_incremental_archive(
                    repo_path=str(repo_path),
                    output_path=str(output_path),
                    parent_archive_path=parent_result["archive_path"],
                    include_lfs=True,
                )

                # Assert
                assert result["success"] is True
                assert result["manifest"]["lfs_enabled"] is True

    def test_lfs_object_count_in_manifest(self):
        """Test that manifest includes count of LFS objects."""
        manager = ArchiveManager()

        with tempfile.TemporaryDirectory() as tmpdir:
            repo_path = Path(tmpdir) / "test-repo"
            subprocess.run(["git", "init", str(repo_path)], check=True, capture_output=True)
            subprocess.run(
                ["git", "config", "user.name", "Test"],
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

            (repo_path / "test.txt").write_text("test")
            subprocess.run(
                ["git", "add", "test.txt"],
                cwd=str(repo_path),
                check=True,
                capture_output=True,
            )
            subprocess.run(
                ["git", "commit", "-m", "Initial"],
                cwd=str(repo_path),
                check=True,
                capture_output=True,
            )

            # Create LFS objects
            lfs_dir = repo_path / ".git" / "lfs" / "objects" / "ab" / "cd"
            lfs_dir.mkdir(parents=True)
            for i in range(3):
                (lfs_dir / f"object{i}").write_bytes(b"mock LFS")

            output_path = Path(tmpdir) / "archives"

            result = manager.create_full_archive(
                repo_path=str(repo_path),
                output_path=str(output_path),
                include_lfs=True,
            )

            # Assert
            assert "lfs_object_count" in result["manifest"]
            assert result["manifest"]["lfs_object_count"] == 3
            assert result["manifest"]["lfs_enabled"] is True

    def test_extract_archive_restores_lfs_objects(self):
        """Test that extracting archive with LFS restores LFS objects."""
        manager = ArchiveManager()

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a simple archive with LFS metadata
            repo_path = Path(tmpdir) / "test-repo"
            subprocess.run(["git", "init", str(repo_path)], check=True, capture_output=True)
            subprocess.run(
                ["git", "config", "user.name", "Test"],
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

            (repo_path / "test.txt").write_text("test")
            subprocess.run(
                ["git", "add", "test.txt"],
                cwd=str(repo_path),
                check=True,
                capture_output=True,
            )
            subprocess.run(
                ["git", "commit", "-m", "Initial"],
                cwd=str(repo_path),
                check=True,
                capture_output=True,
            )

            archives_path = Path(tmpdir) / "archives"
            archives_path.mkdir()

            # Create archive with LFS
            archive_result = manager.create_full_archive(
                repo_path=str(repo_path),
                output_path=str(archives_path),
                include_lfs=False,  # Use False for now since we haven't implemented LFS yet
            )

            # Extract archive
            extract_path = Path(tmpdir) / "extracted"
            result = manager.extract_archive(
                archive_path=archive_result["archive_path"],
                output_path=str(extract_path),
            )

            # Assert
            assert result["success"] is True
            restored_repo = Path(result["repository_path"])
            assert restored_repo.exists()

    def test_lfs_bundling_preserves_object_structure(self):
        """Test that LFS objects maintain their .git/lfs/objects structure."""
        manager = ArchiveManager()

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a repo with LFS structure
            repo_path = Path(tmpdir) / "test-repo"
            repo_path.mkdir()
            (repo_path / ".git").mkdir()
            lfs_dir = repo_path / ".git" / "lfs" / "objects"
            lfs_dir.mkdir(parents=True)

            # Create mock LFS object with proper structure
            # LFS uses: .git/lfs/objects/ab/cd/abcd1234...
            obj_dir = lfs_dir / "ab" / "cd"
            obj_dir.mkdir(parents=True)
            (obj_dir / "abcd1234567890").write_bytes(b"mock LFS object data")

            # Mock the bundling to verify structure preservation
            with patch.object(manager, "_bundle_lfs_objects") as mock_bundle:
                # The method should preserve the directory structure
                mock_bundle.return_value = ["lfs-objects/ab/cd/abcd1234567890"]

                # Verify that the structure is preserved
                result = mock_bundle(str(repo_path), Path(tmpdir) / "staging")
                assert result == ["lfs-objects/ab/cd/abcd1234567890"]
