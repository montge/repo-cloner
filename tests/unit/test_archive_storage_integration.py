"""Tests for archive-storage backend integration."""

import subprocess
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from repo_cloner.archive_manager import ArchiveManager
from repo_cloner.storage_backend import LocalFilesystemBackend


class TestArchiveStorageIntegration:
    """Test suite for integrating archives with storage backends."""

    def test_upload_archive_to_local_storage(self):
        """Test uploading an archive to local filesystem backend."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create test repository
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
                ["git", "commit", "-m", "Initial"],
                cwd=str(repo_path),
                check=True,
                capture_output=True,
            )

            # Create archive
            archives_path = Path(tmpdir) / "archives"
            archives_path.mkdir()
            manager = ArchiveManager()
            result = manager.create_full_archive(
                repo_path=str(repo_path), output_path=str(archives_path)
            )
            archive_file = Path(result["archive_path"])

            # Create storage backend
            storage_path = Path(tmpdir) / "storage"
            storage_path.mkdir()
            backend = LocalFilesystemBackend(storage_path)

            # Act - upload archive to storage
            metadata = backend.upload_archive(
                local_path=archive_file,
                remote_key=f"backups/{archive_file.name}",
                metadata={
                    "archive_type": "full",
                    "repository_name": "test-repo",
                },
            )

            # Assert
            assert metadata.key == f"backups/{archive_file.name}"
            stored_file = storage_path / "backups" / archive_file.name
            assert stored_file.exists()
            assert stored_file.stat().st_size == archive_file.stat().st_size

    def test_download_archive_from_storage(self):
        """Test downloading an archive from storage backend."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create test repository and archive
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
                ["git", "commit", "-m", "Initial"],
                cwd=str(repo_path),
                check=True,
                capture_output=True,
            )

            archives_path = Path(tmpdir) / "archives"
            archives_path.mkdir()
            manager = ArchiveManager()
            result = manager.create_full_archive(
                repo_path=str(repo_path), output_path=str(archives_path)
            )
            archive_file = Path(result["archive_path"])

            # Upload to storage
            storage_path = Path(tmpdir) / "storage"
            storage_path.mkdir()
            backend = LocalFilesystemBackend(storage_path)
            backend.upload_archive(
                local_path=archive_file,
                remote_key=f"backups/{archive_file.name}",
            )

            # Act - download from storage
            download_path = Path(tmpdir) / "downloads"
            download_path.mkdir()
            download_file = download_path / archive_file.name
            backend.download_archive(
                remote_key=f"backups/{archive_file.name}",
                local_path=download_file,
            )

            # Assert
            assert download_file.exists()
            assert download_file.stat().st_size == archive_file.stat().st_size

    def test_list_archives_in_storage(self):
        """Test listing archives from storage backend."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create test repository and multiple archives
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

            archives_path = Path(tmpdir) / "archives"
            archives_path.mkdir()
            manager = ArchiveManager()

            # Create 3 archives
            import time

            archive_files = []
            for i in range(3):
                (repo_path / f"file{i}.txt").write_text(f"content{i}")
                subprocess.run(
                    ["git", "add", f"file{i}.txt"],
                    cwd=str(repo_path),
                    check=True,
                    capture_output=True,
                )
                subprocess.run(
                    ["git", "commit", "-m", f"Commit {i}"],
                    cwd=str(repo_path),
                    check=True,
                    capture_output=True,
                )
                result = manager.create_full_archive(
                    repo_path=str(repo_path), output_path=str(archives_path)
                )
                archive_files.append(Path(result["archive_path"]))
                time.sleep(1.1)  # Ensure unique timestamps (archives use seconds precision)

            # Upload to storage
            storage_path = Path(tmpdir) / "storage"
            storage_path.mkdir()
            backend = LocalFilesystemBackend(storage_path)
            for archive_file in archive_files:
                backend.upload_archive(
                    local_path=archive_file,
                    remote_key=f"backups/{archive_file.name}",
                    metadata={"archive_type": "full", "repository_name": "test-repo"},
                )

            # Act - list archives
            archives = backend.list_archives(prefix="backups/")

            # Assert
            assert len(archives) == 3
            for archive_metadata in archives:
                assert archive_metadata.key.startswith("backups/")
                assert archive_metadata.archive_type == "full"
                assert archive_metadata.repository_name == "test-repo"

    def test_download_and_restore_workflow(self):
        """Test complete workflow: download archive from storage and restore repository."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create test repository and archive
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
            (repo_path / "test.txt").write_text("important data")
            subprocess.run(
                ["git", "add", "test.txt"], cwd=str(repo_path), check=True, capture_output=True
            )
            subprocess.run(
                ["git", "commit", "-m", "Initial"],
                cwd=str(repo_path),
                check=True,
                capture_output=True,
            )

            # Create and upload archive
            archives_path = Path(tmpdir) / "archives"
            archives_path.mkdir()
            manager = ArchiveManager()
            result = manager.create_full_archive(
                repo_path=str(repo_path), output_path=str(archives_path)
            )
            archive_file = Path(result["archive_path"])

            storage_path = Path(tmpdir) / "storage"
            storage_path.mkdir()
            backend = LocalFilesystemBackend(storage_path)
            backend.upload_archive(
                local_path=archive_file,
                remote_key=f"backups/{archive_file.name}",
            )

            # Act - download and restore
            download_path = Path(tmpdir) / "downloads"
            download_path.mkdir()
            download_file = download_path / archive_file.name
            backend.download_archive(
                remote_key=f"backups/{archive_file.name}",
                local_path=download_file,
            )

            restore_path = Path(tmpdir) / "restored"
            restore_path.mkdir()
            restore_result = manager.extract_archive(
                archive_path=str(download_file),
                output_path=str(restore_path),
            )

            # Assert
            restored_repo = Path(restore_result["repository_path"])
            assert restored_repo.exists()
            assert (restored_repo / "test.txt").exists()
            assert (restored_repo / "test.txt").read_text() == "important data"

    def test_archive_exists_in_storage(self):
        """Test checking if archive exists in storage."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create archive
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

            archives_path = Path(tmpdir) / "archives"
            archives_path.mkdir()
            manager = ArchiveManager()
            result = manager.create_full_archive(
                repo_path=str(repo_path), output_path=str(archives_path)
            )
            archive_file = Path(result["archive_path"])

            # Upload to storage
            storage_path = Path(tmpdir) / "storage"
            storage_path.mkdir()
            backend = LocalFilesystemBackend(storage_path)
            backend.upload_archive(
                local_path=archive_file,
                remote_key=f"backups/{archive_file.name}",
            )

            # Act & Assert
            assert backend.archive_exists(f"backups/{archive_file.name}") is True
            assert backend.archive_exists("backups/nonexistent.tar.gz") is False

    def test_delete_archive_from_storage(self):
        """Test deleting an archive from storage."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create and upload archive
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

            archives_path = Path(tmpdir) / "archives"
            archives_path.mkdir()
            manager = ArchiveManager()
            result = manager.create_full_archive(
                repo_path=str(repo_path), output_path=str(archives_path)
            )
            archive_file = Path(result["archive_path"])

            storage_path = Path(tmpdir) / "storage"
            storage_path.mkdir()
            backend = LocalFilesystemBackend(storage_path)
            backend.upload_archive(
                local_path=archive_file,
                remote_key=f"backups/{archive_file.name}",
            )

            # Act - delete archive
            backend.delete_archive(f"backups/{archive_file.name}")

            # Assert
            assert backend.archive_exists(f"backups/{archive_file.name}") is False
            stored_file = storage_path / "backups" / archive_file.name
            assert not stored_file.exists()
