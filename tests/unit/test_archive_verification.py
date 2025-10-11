"""Tests for archive verification and integrity checks."""

import json
import subprocess
import tarfile
import tempfile
from pathlib import Path

import pytest

from repo_cloner.archive_manager import ArchiveManager


class TestArchiveVerification:
    """Test suite for archive verification and integrity checks."""

    def test_verify_archive_returns_true_for_valid_archive(self):
        """Test that verify_archive returns True for a valid archive."""
        manager = ArchiveManager()

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a valid repository
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
            (repo_path / "test.txt").write_text("test content")
            subprocess.run(
                ["git", "add", "test.txt"], cwd=str(repo_path), check=True, capture_output=True
            )
            subprocess.run(
                ["git", "commit", "-m", "Initial commit"],
                cwd=str(repo_path),
                check=True,
                capture_output=True,
            )

            # Create archive
            output_path = Path(tmpdir) / "archives"
            result = manager.create_full_archive(
                repo_path=str(repo_path), output_path=str(output_path), include_lfs=False
            )

            # Act
            verification_result = manager.verify_archive(result["archive_path"])

            # Assert
            assert verification_result["valid"] is True
            assert verification_result["errors"] == []

    def test_verify_archive_detects_missing_manifest(self):
        """Test that verify_archive detects missing manifest.json."""
        manager = ArchiveManager()

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create an archive without manifest
            archive_path = Path(tmpdir) / "invalid.tar.gz"
            with tarfile.open(archive_path, "w:gz") as tar:
                # Add only bundle, no manifest
                bundle_file = Path(tmpdir) / "repository.bundle"
                bundle_file.write_bytes(b"fake bundle content")
                tar.add(bundle_file, arcname="repository.bundle")

            # Act
            result = manager.verify_archive(str(archive_path))

            # Assert
            assert result["valid"] is False
            assert any("manifest.json not found" in err for err in result["errors"])

    def test_verify_archive_detects_missing_bundle(self):
        """Test that verify_archive detects missing repository.bundle."""
        manager = ArchiveManager()

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create an archive without bundle
            archive_path = Path(tmpdir) / "invalid.tar.gz"
            with tarfile.open(archive_path, "w:gz") as tar:
                # Add only manifest, no bundle
                manifest_file = Path(tmpdir) / "manifest.json"
                manifest_file.write_text(
                    json.dumps(
                        {
                            "type": "full",
                            "timestamp": "20251010-120000",
                            "repository": {"name": "test"},
                        }
                    )
                )
                tar.add(manifest_file, arcname="manifest.json")

            # Act
            result = manager.verify_archive(str(archive_path))

            # Assert
            assert result["valid"] is False
            assert any("repository.bundle not found" in err for err in result["errors"])

    def test_verify_archive_detects_corrupted_manifest(self):
        """Test that verify_archive detects corrupted manifest.json."""
        manager = ArchiveManager()

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create an archive with corrupted manifest
            archive_path = Path(tmpdir) / "invalid.tar.gz"
            with tarfile.open(archive_path, "w:gz") as tar:
                manifest_file = Path(tmpdir) / "manifest.json"
                manifest_file.write_text("{ invalid json")
                tar.add(manifest_file, arcname="manifest.json")

                bundle_file = Path(tmpdir) / "repository.bundle"
                bundle_file.write_bytes(b"fake bundle")
                tar.add(bundle_file, arcname="repository.bundle")

            # Act
            result = manager.verify_archive(str(archive_path))

            # Assert
            assert result["valid"] is False
            assert any("manifest.json is corrupted" in err for err in result["errors"])

    def test_verify_archive_validates_git_bundle(self):
        """Test that verify_archive validates git bundle integrity."""
        manager = ArchiveManager()

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a valid repository and archive
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
            (repo_path / "test.txt").write_text("test content")
            subprocess.run(
                ["git", "add", "test.txt"], cwd=str(repo_path), check=True, capture_output=True
            )
            subprocess.run(
                ["git", "commit", "-m", "Initial commit"],
                cwd=str(repo_path),
                check=True,
                capture_output=True,
            )

            output_path = Path(tmpdir) / "archives"
            result = manager.create_full_archive(
                repo_path=str(repo_path), output_path=str(output_path)
            )

            # Act - verify the valid bundle
            verification = manager.verify_archive(result["archive_path"])

            # Assert
            assert verification["valid"] is True
            assert verification["bundle_valid"] is True

    def test_verify_archive_detects_invalid_git_bundle(self):
        """Test that verify_archive detects invalid git bundle."""
        manager = ArchiveManager()

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create archive with invalid bundle
            archive_path = Path(tmpdir) / "invalid.tar.gz"
            with tarfile.open(archive_path, "w:gz") as tar:
                manifest = {
                    "type": "full",
                    "timestamp": "20251010-120000",
                    "repository": {"name": "test", "head_sha": "abc123"},
                }
                manifest_file = Path(tmpdir) / "manifest.json"
                manifest_file.write_text(json.dumps(manifest))
                tar.add(manifest_file, arcname="manifest.json")

                # Invalid bundle (not a git bundle)
                bundle_file = Path(tmpdir) / "repository.bundle"
                bundle_file.write_bytes(b"this is not a valid git bundle")
                tar.add(bundle_file, arcname="repository.bundle")

            # Act
            result = manager.verify_archive(str(archive_path))

            # Assert
            assert result["valid"] is False
            assert result["bundle_valid"] is False
            assert any("bundle is invalid" in err.lower() for err in result["errors"])

    def test_verify_archive_checks_lfs_objects_when_enabled(self):
        """Test that verify_archive checks LFS objects when lfs_enabled is True."""
        manager = ArchiveManager()

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create repo with LFS
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
                ["git", "add", "test.txt"], cwd=str(repo_path), check=True, capture_output=True
            )
            subprocess.run(
                ["git", "commit", "-m", "Initial"],
                cwd=str(repo_path),
                check=True,
                capture_output=True,
            )

            # Create mock LFS objects
            lfs_dir = repo_path / ".git" / "lfs" / "objects" / "ab" / "cd"
            lfs_dir.mkdir(parents=True)
            (lfs_dir / "abcd1234").write_bytes(b"mock LFS object")

            # Create archive with LFS
            output_path = Path(tmpdir) / "archives"
            result = manager.create_full_archive(
                repo_path=str(repo_path), output_path=str(output_path), include_lfs=True
            )

            # Act
            verification = manager.verify_archive(result["archive_path"])

            # Assert
            assert verification["valid"] is True
            assert verification["lfs_objects_verified"] is True
            assert verification["lfs_object_count"] == 1

    def test_verify_archive_detects_lfs_count_mismatch(self):
        """Test that verify_archive detects LFS object count mismatch."""
        manager = ArchiveManager()

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create archive with LFS
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
                ["git", "add", "test.txt"], cwd=str(repo_path), check=True, capture_output=True
            )
            subprocess.run(
                ["git", "commit", "-m", "Initial"],
                cwd=str(repo_path),
                check=True,
                capture_output=True,
            )

            lfs_dir = repo_path / ".git" / "lfs" / "objects" / "ab" / "cd"
            lfs_dir.mkdir(parents=True)
            (lfs_dir / "obj1").write_bytes(b"mock LFS 1")
            (lfs_dir / "obj2").write_bytes(b"mock LFS 2")

            output_path = Path(tmpdir) / "archives"
            result = manager.create_full_archive(
                repo_path=str(repo_path), output_path=str(output_path), include_lfs=True
            )

            # Manually corrupt the manifest to show wrong count
            archive_path = Path(result["archive_path"])
            with tempfile.TemporaryDirectory() as extract_dir:
                with tarfile.open(archive_path, "r:gz") as tar:
                    tar.extractall(extract_dir)

                # Modify manifest to show wrong LFS count
                manifest_path = Path(extract_dir) / "manifest.json"
                with open(manifest_path, "r") as f:
                    manifest = json.load(f)
                manifest["lfs_object_count"] = 5  # Wrong count
                with open(manifest_path, "w") as f:
                    json.dump(manifest, f)

                # Recreate archive with corrupted manifest
                corrupted_archive = Path(tmpdir) / "corrupted.tar.gz"
                with tarfile.open(corrupted_archive, "w:gz") as tar:
                    tar.add(Path(extract_dir) / "manifest.json", arcname="manifest.json")
                    tar.add(Path(extract_dir) / "repository.bundle", arcname="repository.bundle")
                    tar.add(Path(extract_dir) / "lfs-objects", arcname="lfs-objects")

                # Act
                verification = manager.verify_archive(str(corrupted_archive))

                # Assert
                assert verification["valid"] is False
                assert any("LFS object count mismatch" in err for err in verification["errors"])

    def test_verify_archive_raises_error_if_archive_not_found(self):
        """Test that verify_archive raises FileNotFoundError for missing archive."""
        manager = ArchiveManager()

        with pytest.raises(FileNotFoundError):
            manager.verify_archive("/nonexistent/archive.tar.gz")

    def test_verify_archive_returns_detailed_report(self):
        """Test that verify_archive returns a detailed verification report."""
        manager = ArchiveManager()

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create valid archive
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
                ["git", "add", "test.txt"], cwd=str(repo_path), check=True, capture_output=True
            )
            subprocess.run(
                ["git", "commit", "-m", "Initial"],
                cwd=str(repo_path),
                check=True,
                capture_output=True,
            )

            output_path = Path(tmpdir) / "archives"
            result = manager.create_full_archive(
                repo_path=str(repo_path), output_path=str(output_path)
            )

            # Act
            verification = manager.verify_archive(result["archive_path"])

            # Assert - verify report structure
            assert "valid" in verification
            assert "errors" in verification
            assert "manifest_valid" in verification
            assert "bundle_valid" in verification
            assert "archive_path" in verification
            assert verification["archive_path"] == result["archive_path"]
