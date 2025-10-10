"""Unit tests for LocalFilesystemBackend storage backend."""

import json
import shutil
import tempfile
from pathlib import Path

import pytest

from repo_cloner.storage_backend import ArchiveMetadata, LocalFilesystemBackend


class TestLocalFilesystemBackend:
    """Test suite for LocalFilesystemBackend."""

    def test_initializes_with_absolute_path(self):
        """Test that LocalFilesystemBackend requires absolute path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            backend = LocalFilesystemBackend(Path(tmpdir))
            assert backend.base_path == Path(tmpdir)
            assert backend.base_path.is_absolute()

    def test_rejects_relative_path(self):
        """Test that LocalFilesystemBackend rejects relative paths."""
        with pytest.raises(ValueError, match="base_path must be absolute"):
            LocalFilesystemBackend(Path("relative/path"))

    def test_upload_archive_copies_file(self):
        """Test uploading (copying) an archive to local storage."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Arrange
            backend = LocalFilesystemBackend(Path(tmpdir))
            source_file = Path(tmpdir) / "source.tar.gz"
            source_file.write_text("archive content")

            # Act
            metadata = backend.upload_archive(
                local_path=source_file,
                remote_key="backups/repo-full-20251010.tar.gz",
            )

            # Assert
            dest_file = Path(tmpdir) / "backups/repo-full-20251010.tar.gz"
            assert dest_file.exists()
            assert dest_file.read_text() == "archive content"
            assert metadata.key == "backups/repo-full-20251010.tar.gz"
            assert metadata.filename == "repo-full-20251010.tar.gz"
            assert metadata.size_bytes == len("archive content")

    def test_upload_creates_parent_directories(self):
        """Test that upload creates necessary parent directories."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Arrange
            backend = LocalFilesystemBackend(Path(tmpdir))
            source_file = Path(tmpdir) / "source.tar.gz"
            source_file.write_text("content")

            # Act
            backend.upload_archive(
                local_path=source_file,
                remote_key="a/b/c/archive.tar.gz",
            )

            # Assert
            dest_file = Path(tmpdir) / "a/b/c/archive.tar.gz"
            assert dest_file.exists()
            assert dest_file.parent.exists()

    def test_upload_with_metadata_creates_sidecar(self):
        """Test that metadata is stored as JSON sidecar file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Arrange
            backend = LocalFilesystemBackend(Path(tmpdir))
            source_file = Path(tmpdir) / "source.tar.gz"
            source_file.write_text("content")
            metadata_dict = {
                "archive_type": "full",
                "repository_name": "test-repo",
                "custom_field": "custom_value",
            }

            # Act
            backend.upload_archive(
                local_path=source_file,
                remote_key="archive.tar.gz",
                metadata=metadata_dict,
            )

            # Assert
            sidecar_file = Path(tmpdir) / "archive.tar.gz.meta.json"
            assert sidecar_file.exists()
            sidecar_data = json.loads(sidecar_file.read_text())
            assert sidecar_data["archive_type"] == "full"
            assert sidecar_data["repository_name"] == "test-repo"
            assert sidecar_data["custom_field"] == "custom_value"

    def test_upload_raises_error_if_source_missing(self):
        """Test that upload raises FileNotFoundError if source doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            backend = LocalFilesystemBackend(Path(tmpdir))
            with pytest.raises(FileNotFoundError):
                backend.upload_archive(
                    local_path=Path("/nonexistent/file.tar.gz"),
                    remote_key="archive.tar.gz",
                )

    def test_download_archive_copies_file(self):
        """Test downloading (copying) an archive from local storage."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Arrange
            backend = LocalFilesystemBackend(Path(tmpdir))
            stored_file = Path(tmpdir) / "stored.tar.gz"
            stored_file.write_text("stored content")

            # Act
            dest_path = Path(tmpdir) / "downloaded.tar.gz"
            backend.download_archive(
                remote_key="stored.tar.gz",
                local_path=dest_path,
            )

            # Assert
            assert dest_path.exists()
            assert dest_path.read_text() == "stored content"

    def test_download_creates_parent_directories(self):
        """Test that download creates necessary parent directories."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Arrange
            backend = LocalFilesystemBackend(Path(tmpdir))
            stored_file = Path(tmpdir) / "stored.tar.gz"
            stored_file.write_text("content")

            # Act
            dest_path = Path(tmpdir) / "downloads/subdir/file.tar.gz"
            backend.download_archive(
                remote_key="stored.tar.gz",
                local_path=dest_path,
            )

            # Assert
            assert dest_path.exists()
            assert dest_path.parent.exists()

    def test_download_raises_error_if_source_missing(self):
        """Test that download raises KeyError if remote file doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            backend = LocalFilesystemBackend(Path(tmpdir))
            with pytest.raises(KeyError, match="Archive not found"):
                backend.download_archive(
                    remote_key="nonexistent.tar.gz",
                    local_path=Path(tmpdir) / "dest.tar.gz",
                )

    def test_list_archives_returns_all_archives(self):
        """Test listing all archives in storage."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Arrange
            backend = LocalFilesystemBackend(Path(tmpdir))
            (Path(tmpdir) / "repo1-full.tar.gz").write_text("content1")
            (Path(tmpdir) / "repo2-full.tar.gz").write_text("content2")
            (Path(tmpdir) / "repo3-inc.tar.gz").write_text("content3")

            # Act
            archives = backend.list_archives()

            # Assert
            assert len(archives) == 3
            keys = [a.key for a in archives]
            assert "repo1-full.tar.gz" in keys
            assert "repo2-full.tar.gz" in keys
            assert "repo3-inc.tar.gz" in keys

    def test_list_archives_with_prefix_filters(self):
        """Test listing archives with prefix filter."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Arrange
            backend = LocalFilesystemBackend(Path(tmpdir))
            (Path(tmpdir) / "backups").mkdir()
            (Path(tmpdir) / "backups/repo1-full.tar.gz").write_text("content1")
            (Path(tmpdir) / "backups/repo2-full.tar.gz").write_text("content2")
            (Path(tmpdir) / "other").mkdir()
            (Path(tmpdir) / "other/repo3.tar.gz").write_text("content3")

            # Act
            archives = backend.list_archives(prefix="backups/")

            # Assert
            assert len(archives) == 2
            keys = [a.key for a in archives]
            assert "backups/repo1-full.tar.gz" in keys
            assert "backups/repo2-full.tar.gz" in keys
            assert "other/repo3.tar.gz" not in keys

    def test_list_archives_includes_metadata_from_sidecar(self):
        """Test that list_archives includes metadata from sidecar files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Arrange
            backend = LocalFilesystemBackend(Path(tmpdir))
            archive_file = Path(tmpdir) / "archive.tar.gz"
            archive_file.write_text("content")

            # Create sidecar metadata
            sidecar_file = Path(tmpdir) / "archive.tar.gz.meta.json"
            sidecar_data = {
                "archive_type": "full",
                "repository_name": "test-repo",
                "checksum_sha256": "abc123",
            }
            sidecar_file.write_text(json.dumps(sidecar_data))

            # Act
            archives = backend.list_archives()

            # Assert
            assert len(archives) == 1
            metadata = archives[0]
            assert metadata.archive_type == "full"
            assert metadata.repository_name == "test-repo"
            assert metadata.checksum_sha256 == "abc123"

    def test_list_archives_handles_nested_directories(self):
        """Test listing archives in nested directory structures."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Arrange
            backend = LocalFilesystemBackend(Path(tmpdir))
            (Path(tmpdir) / "a/b/c").mkdir(parents=True)
            (Path(tmpdir) / "a/file1.tar.gz").write_text("content1")
            (Path(tmpdir) / "a/b/file2.tar.gz").write_text("content2")
            (Path(tmpdir) / "a/b/c/file3.tar.gz").write_text("content3")

            # Act
            archives = backend.list_archives()

            # Assert
            assert len(archives) == 3
            keys = [a.key for a in archives]
            assert "a/file1.tar.gz" in keys
            assert "a/b/file2.tar.gz" in keys
            assert "a/b/c/file3.tar.gz" in keys

    def test_delete_archive_removes_file(self):
        """Test deleting an archive from storage."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Arrange
            backend = LocalFilesystemBackend(Path(tmpdir))
            archive_file = Path(tmpdir) / "archive.tar.gz"
            archive_file.write_text("content")

            # Act
            backend.delete_archive("archive.tar.gz")

            # Assert
            assert not archive_file.exists()

    def test_delete_archive_removes_metadata_sidecar(self):
        """Test that deleting an archive also removes its metadata sidecar."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Arrange
            backend = LocalFilesystemBackend(Path(tmpdir))
            archive_file = Path(tmpdir) / "archive.tar.gz"
            archive_file.write_text("content")
            sidecar_file = Path(tmpdir) / "archive.tar.gz.meta.json"
            sidecar_file.write_text("{}")

            # Act
            backend.delete_archive("archive.tar.gz")

            # Assert
            assert not archive_file.exists()
            assert not sidecar_file.exists()

    def test_delete_raises_error_if_not_exists(self):
        """Test that delete raises KeyError if archive doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            backend = LocalFilesystemBackend(Path(tmpdir))
            with pytest.raises(KeyError, match="Archive not found"):
                backend.delete_archive("nonexistent.tar.gz")

    def test_archive_exists_returns_true_if_exists(self):
        """Test archive_exists returns True for existing archives."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Arrange
            backend = LocalFilesystemBackend(Path(tmpdir))
            archive_file = Path(tmpdir) / "archive.tar.gz"
            archive_file.write_text("content")

            # Act & Assert
            assert backend.archive_exists("archive.tar.gz") is True

    def test_archive_exists_returns_false_if_not_exists(self):
        """Test archive_exists returns False for non-existent archives."""
        with tempfile.TemporaryDirectory() as tmpdir:
            backend = LocalFilesystemBackend(Path(tmpdir))
            assert backend.archive_exists("nonexistent.tar.gz") is False

    def test_archive_exists_checks_nested_paths(self):
        """Test archive_exists works with nested paths."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Arrange
            backend = LocalFilesystemBackend(Path(tmpdir))
            (Path(tmpdir) / "a/b").mkdir(parents=True)
            archive_file = Path(tmpdir) / "a/b/archive.tar.gz"
            archive_file.write_text("content")

            # Act & Assert
            assert backend.archive_exists("a/b/archive.tar.gz") is True
            assert backend.archive_exists("a/b/nonexistent.tar.gz") is False
