"""Unit tests for GCSBackend storage backend using unittest.mock."""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch
from urllib.parse import urlparse

import pytest

from repo_cloner.storage_backend import GCSBackend


class TestGCSBackend:
    """Test suite for GCSBackend using mocks."""

    def test_initializes_with_bucket_and_project(self):
        """Test that GCSBackend initializes with bucket and project."""
        with patch("google.cloud.storage.Client"):
            backend = GCSBackend(
                bucket="test-bucket",
                project_id="test-project",
            )
            assert backend.bucket_name == "test-bucket"
            assert backend.project_id == "test-project"

    def test_initializes_with_service_account_json(self):
        """Test that GCSBackend supports service account JSON authentication."""
        with patch("google.cloud.storage.Client"):
            backend = GCSBackend(
                bucket="test-bucket",
                project_id="test-project",
                service_account_json="/path/to/credentials.json",
            )
            assert backend.service_account_json == "/path/to/credentials.json"

    def test_initializes_with_custom_prefix(self):
        """Test that GCSBackend supports custom blob prefix."""
        with patch("google.cloud.storage.Client"):
            backend = GCSBackend(
                bucket="test-bucket",
                project_id="test-project",
                prefix="backups/",
            )
            assert backend.prefix == "backups/"

    def test_upload_archive_to_gcs(self):
        """Test uploading an archive to Google Cloud Storage."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Arrange
            source_file = Path(tmpdir) / "archive.tar.gz"
            source_file.write_text("test content")

            # Mock GCS SDK
            mock_storage_client = MagicMock()
            mock_bucket = MagicMock()
            mock_blob = MagicMock()
            mock_storage_client.bucket.return_value = mock_bucket
            mock_bucket.blob.return_value = mock_blob

            # Mock blob properties after upload
            mock_blob.size = len("test content")

            with patch("google.cloud.storage.Client") as mock_client:
                mock_client.return_value = mock_storage_client

                backend = GCSBackend(
                    bucket="test-bucket",
                    project_id="test-project",
                )

                # Act
                metadata = backend.upload_archive(
                    local_path=source_file,
                    remote_key="test-archive.tar.gz",
                )

                # Assert
                assert metadata.key == "test-archive.tar.gz"
                assert metadata.filename == "test-archive.tar.gz"
                assert metadata.size_bytes == len("test content")

                # Verify upload was called
                mock_blob.upload_from_filename.assert_called_once()

    def test_upload_with_prefix(self):
        """Test uploading an archive with blob prefix."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Arrange
            source_file = Path(tmpdir) / "archive.tar.gz"
            source_file.write_text("content")

            mock_storage_client = MagicMock()
            mock_bucket = MagicMock()
            mock_blob = MagicMock()
            mock_storage_client.bucket.return_value = mock_bucket
            mock_bucket.blob.return_value = mock_blob
            mock_blob.size = len("content")

            with patch("google.cloud.storage.Client") as mock_client:
                mock_client.return_value = mock_storage_client

                backend = GCSBackend(
                    bucket="test-bucket",
                    project_id="test-project",
                    prefix="backups/",
                )

                # Act
                metadata = backend.upload_archive(
                    local_path=source_file,
                    remote_key="repo.tar.gz",
                )

                # Assert
                assert metadata.key == "backups/repo.tar.gz"

                # Verify full blob name used
                mock_bucket.blob.assert_called_with("backups/repo.tar.gz")

    def test_upload_with_metadata_tags(self):
        """Test that metadata is stored as GCS blob metadata."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Arrange
            source_file = Path(tmpdir) / "archive.tar.gz"
            source_file.write_text("content")

            mock_storage_client = MagicMock()
            mock_bucket = MagicMock()
            mock_blob = MagicMock()
            mock_storage_client.bucket.return_value = mock_bucket
            mock_bucket.blob.return_value = mock_blob
            mock_blob.size = len("content")

            metadata_dict = {
                "archive_type": "full",
                "repository_name": "test-repo",
            }

            with patch("google.cloud.storage.Client") as mock_client:
                mock_client.return_value = mock_storage_client

                backend = GCSBackend(
                    bucket="test-bucket",
                    project_id="test-project",
                )

                # Act
                backend.upload_archive(
                    local_path=source_file,
                    remote_key="archive.tar.gz",
                    metadata=metadata_dict,
                )

                # Assert - Check metadata was set on blob
                assert mock_blob.metadata == metadata_dict
                mock_blob.patch.assert_called_once()

    def test_upload_raises_error_if_source_missing(self):
        """Test that upload raises FileNotFoundError if source doesn't exist."""
        with patch("google.cloud.storage.Client"):
            backend = GCSBackend(
                bucket="test-bucket",
                project_id="test-project",
            )

            with pytest.raises(FileNotFoundError):
                backend.upload_archive(
                    local_path=Path("/nonexistent/file.tar.gz"),
                    remote_key="archive.tar.gz",
                )

    def test_download_archive_from_gcs(self):
        """Test downloading an archive from Google Cloud Storage."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Arrange
            dest_path = Path(tmpdir) / "downloaded.tar.gz"

            mock_storage_client = MagicMock()
            mock_bucket = MagicMock()
            mock_blob = MagicMock()
            mock_storage_client.bucket.return_value = mock_bucket
            mock_bucket.blob.return_value = mock_blob

            # Mock blob exists
            mock_blob.exists.return_value = True

            with patch("google.cloud.storage.Client") as mock_client:
                mock_client.return_value = mock_storage_client

                backend = GCSBackend(
                    bucket="test-bucket",
                    project_id="test-project",
                )

                # Act
                backend.download_archive(
                    remote_key="archive.tar.gz",
                    local_path=dest_path,
                )

                # Assert
                mock_blob.download_to_filename.assert_called_once_with(str(dest_path))

    def test_download_with_prefix(self):
        """Test downloading an archive with blob prefix."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Arrange
            dest_path = Path(tmpdir) / "downloaded.tar.gz"

            mock_storage_client = MagicMock()
            mock_bucket = MagicMock()
            mock_blob = MagicMock()
            mock_storage_client.bucket.return_value = mock_bucket
            mock_bucket.blob.return_value = mock_blob
            mock_blob.exists.return_value = True

            with patch("google.cloud.storage.Client") as mock_client:
                mock_client.return_value = mock_storage_client

                backend = GCSBackend(
                    bucket="test-bucket",
                    project_id="test-project",
                    prefix="backups/",
                )

                # Act
                backend.download_archive(
                    remote_key="repo.tar.gz",
                    local_path=dest_path,
                )

                # Assert
                # Verify full blob name used
                mock_bucket.blob.assert_called_with("backups/repo.tar.gz")

    def test_download_raises_error_if_not_exists(self):
        """Test that download raises KeyError if blob doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Arrange
            dest_path = Path(tmpdir) / "downloaded.tar.gz"

            mock_storage_client = MagicMock()
            mock_bucket = MagicMock()
            mock_blob = MagicMock()
            mock_storage_client.bucket.return_value = mock_bucket
            mock_bucket.blob.return_value = mock_blob

            # Simulate blob not found
            mock_blob.exists.return_value = False

            with patch("google.cloud.storage.Client") as mock_client:
                mock_client.return_value = mock_storage_client

                backend = GCSBackend(
                    bucket="test-bucket",
                    project_id="test-project",
                )

                # Act & Assert
                with pytest.raises(KeyError, match="Archive not found"):
                    backend.download_archive(
                        remote_key="nonexistent.tar.gz",
                        local_path=dest_path,
                    )

    def test_list_archives_returns_all_blobs(self):
        """Test listing all archives in GCS bucket."""
        # Arrange
        mock_storage_client = MagicMock()
        mock_bucket = MagicMock()
        mock_storage_client.bucket.return_value = mock_bucket

        # Mock blob list
        mock_blob1 = Mock()
        mock_blob1.name = "repo1-full.tar.gz"
        mock_blob1.size = 100
        mock_blob1.time_created.isoformat.return_value = "2025-01-09T12:00:00Z"
        mock_blob1.metadata = {}

        mock_blob2 = Mock()
        mock_blob2.name = "repo2-full.tar.gz"
        mock_blob2.size = 200
        mock_blob2.time_created.isoformat.return_value = "2025-01-09T13:00:00Z"
        mock_blob2.metadata = {}

        mock_bucket.list_blobs.return_value = [mock_blob1, mock_blob2]

        with patch("google.cloud.storage.Client") as mock_client:
            mock_client.return_value = mock_storage_client

            backend = GCSBackend(
                bucket="test-bucket",
                project_id="test-project",
            )

            # Act
            archives = backend.list_archives()

            # Assert
            assert len(archives) == 2
            keys = [a.key for a in archives]
            assert "repo1-full.tar.gz" in keys
            assert "repo2-full.tar.gz" in keys

    def test_list_archives_with_prefix_filter(self):
        """Test listing archives with prefix filter."""
        # Arrange
        mock_storage_client = MagicMock()
        mock_bucket = MagicMock()
        mock_storage_client.bucket.return_value = mock_bucket

        # Mock filtered blob list
        mock_blob1 = Mock()
        mock_blob1.name = "backups/repo1.tar.gz"
        mock_blob1.size = 100
        mock_blob1.time_created.isoformat.return_value = "2025-01-09T12:00:00Z"
        mock_blob1.metadata = {}

        mock_blob2 = Mock()
        mock_blob2.name = "backups/repo2.tar.gz"
        mock_blob2.size = 200
        mock_blob2.time_created.isoformat.return_value = "2025-01-09T13:00:00Z"
        mock_blob2.metadata = {}

        mock_bucket.list_blobs.return_value = [mock_blob1, mock_blob2]

        with patch("google.cloud.storage.Client") as mock_client:
            mock_client.return_value = mock_storage_client

            backend = GCSBackend(
                bucket="test-bucket",
                project_id="test-project",
            )

            # Act
            archives = backend.list_archives(prefix="backups/")

            # Assert
            assert len(archives) == 2
            keys = [a.key for a in archives]
            assert "backups/repo1.tar.gz" in keys
            assert "backups/repo2.tar.gz" in keys

            # Verify prefix was used in list call
            mock_bucket.list_blobs.assert_called_with(prefix="backups/")

    def test_list_archives_includes_metadata_from_blob_metadata(self):
        """Test that list_archives includes metadata from GCS blob metadata."""
        # Arrange
        mock_storage_client = MagicMock()
        mock_bucket = MagicMock()
        mock_storage_client.bucket.return_value = mock_bucket

        # Mock blob with metadata
        mock_blob = Mock()
        mock_blob.name = "archive.tar.gz"
        mock_blob.size = 100
        mock_blob.time_created.isoformat.return_value = "2025-01-09T12:00:00Z"
        mock_blob.metadata = {
            "archive_type": "full",
            "repository_name": "test-repo",
            "checksum_sha256": "abc123",
        }

        mock_bucket.list_blobs.return_value = [mock_blob]

        with patch("google.cloud.storage.Client") as mock_client:
            mock_client.return_value = mock_storage_client

            backend = GCSBackend(
                bucket="test-bucket",
                project_id="test-project",
            )

            # Act
            archives = backend.list_archives()

            # Assert
            assert len(archives) == 1
            metadata = archives[0]
            assert metadata.archive_type == "full"
            assert metadata.repository_name == "test-repo"
            assert metadata.checksum_sha256 == "abc123"

    def test_delete_archive_removes_blob(self):
        """Test deleting an archive from Google Cloud Storage."""
        # Arrange
        mock_storage_client = MagicMock()
        mock_bucket = MagicMock()
        mock_blob = MagicMock()
        mock_storage_client.bucket.return_value = mock_bucket
        mock_bucket.blob.return_value = mock_blob

        # Mock blob exists
        mock_blob.exists.return_value = True

        with patch("google.cloud.storage.Client") as mock_client:
            mock_client.return_value = mock_storage_client

            backend = GCSBackend(
                bucket="test-bucket",
                project_id="test-project",
            )

            # Act
            backend.delete_archive("archive.tar.gz")

            # Assert
            mock_blob.delete.assert_called_once()

    def test_delete_raises_error_if_not_exists(self):
        """Test that delete raises KeyError if blob doesn't exist."""
        # Arrange
        mock_storage_client = MagicMock()
        mock_bucket = MagicMock()
        mock_blob = MagicMock()
        mock_storage_client.bucket.return_value = mock_bucket
        mock_bucket.blob.return_value = mock_blob

        # Simulate blob not found
        mock_blob.exists.return_value = False

        with patch("google.cloud.storage.Client") as mock_client:
            mock_client.return_value = mock_storage_client

            backend = GCSBackend(
                bucket="test-bucket",
                project_id="test-project",
            )

            # Act & Assert
            with pytest.raises(KeyError, match="Archive not found"):
                backend.delete_archive("nonexistent.tar.gz")

    def test_archive_exists_returns_true_if_exists(self):
        """Test archive_exists returns True for existing blobs."""
        # Arrange
        mock_storage_client = MagicMock()
        mock_bucket = MagicMock()
        mock_blob = MagicMock()
        mock_storage_client.bucket.return_value = mock_bucket
        mock_bucket.blob.return_value = mock_blob

        # Mock blob exists
        mock_blob.exists.return_value = True

        with patch("google.cloud.storage.Client") as mock_client:
            mock_client.return_value = mock_storage_client

            backend = GCSBackend(
                bucket="test-bucket",
                project_id="test-project",
            )

            # Act & Assert
            assert backend.archive_exists("archive.tar.gz") is True

    def test_archive_exists_returns_false_if_not_exists(self):
        """Test archive_exists returns False for non-existent blobs."""
        # Arrange
        mock_storage_client = MagicMock()
        mock_bucket = MagicMock()
        mock_blob = MagicMock()
        mock_storage_client.bucket.return_value = mock_bucket
        mock_bucket.blob.return_value = mock_blob

        # Mock blob doesn't exist
        mock_blob.exists.return_value = False

        with patch("google.cloud.storage.Client") as mock_client:
            mock_client.return_value = mock_storage_client

            backend = GCSBackend(
                bucket="test-bucket",
                project_id="test-project",
            )

            # Act & Assert
            assert backend.archive_exists("nonexistent.tar.gz") is False

    def test_get_archive_url_generates_signed_url(self):
        """Test generating a signed URL for a GCS blob."""
        # Arrange
        mock_storage_client = MagicMock()
        mock_bucket = MagicMock()
        mock_blob = MagicMock()
        mock_storage_client.bucket.return_value = mock_bucket
        mock_bucket.blob.return_value = mock_blob

        # Mock signed URL generation
        mock_blob.generate_signed_url.return_value = (
            "https://storage.googleapis.com/test-bucket/archive.tar.gz?X-Goog-Signature=..."
        )

        with patch("google.cloud.storage.Client") as mock_client:
            mock_client.return_value = mock_storage_client

            backend = GCSBackend(
                bucket="test-bucket",
                project_id="test-project",
            )

            # Act
            url = backend.get_archive_url("archive.tar.gz")

            # Assert
            assert url is not None
            parsed = urlparse(url)
            assert parsed.netloc == "storage.googleapis.com"
            assert "archive.tar.gz" in parsed.path
            assert "X-Goog-Signature" in parsed.query

    def test_initializes_with_explicit_credentials(self):
        """Test that GCSBackend accepts explicit service account JSON path."""
        with patch("google.cloud.storage.Client"):
            backend = GCSBackend(
                bucket="test-bucket",
                project_id="test-project",
                service_account_json="/path/to/sa.json",
            )
            assert backend.bucket_name == "test-bucket"
            assert backend.project_id == "test-project"
            assert backend.service_account_json == "/path/to/sa.json"
