"""Unit tests for AzureBlobBackend storage backend using unittest.mock."""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from repo_cloner.storage_backend import AzureBlobBackend


class TestAzureBlobBackend:
    """Test suite for AzureBlobBackend using mocks."""

    def test_initializes_with_container_and_account(self):
        """Test that AzureBlobBackend initializes with container and account."""
        with patch("azure.storage.blob.BlobServiceClient"):
            backend = AzureBlobBackend(
                container="test-container",
                account_name="teststorage",
                account_key="test-key",
            )
            assert backend.container == "test-container"
            assert backend.account_name == "teststorage"
            assert backend.account_key == "test-key"

    def test_initializes_with_connection_string(self):
        """Test that AzureBlobBackend supports connection string authentication."""
        with patch("azure.storage.blob.BlobServiceClient"):
            backend = AzureBlobBackend(
                container="test-container",
                connection_string="DefaultEndpointsProtocol=https;AccountName=teststorage",
            )
            assert backend.container == "test-container"
            assert backend.connection_string is not None

    def test_initializes_with_custom_prefix(self):
        """Test that AzureBlobBackend supports custom blob prefix."""
        with patch("azure.storage.blob.BlobServiceClient"):
            backend = AzureBlobBackend(
                container="test-container",
                account_name="teststorage",
                account_key="test-key",
                prefix="backups/",
            )
            assert backend.prefix == "backups/"

    def test_upload_archive_to_azure_blob(self):
        """Test uploading an archive to Azure Blob Storage."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Arrange
            source_file = Path(tmpdir) / "archive.tar.gz"
            source_file.write_text("test content")

            # Mock Azure SDK
            mock_blob_service = MagicMock()
            mock_blob_client = MagicMock()
            mock_blob_service.get_blob_client.return_value = mock_blob_client

            # Mock blob properties
            mock_properties = Mock()
            mock_properties.size = len("test content")
            mock_blob_client.get_blob_properties.return_value = mock_properties

            with patch("azure.storage.blob.BlobServiceClient") as mock_bsc:
                mock_bsc.return_value = mock_blob_service

                backend = AzureBlobBackend(
                    container="test-container",
                    account_name="teststorage",
                    account_key="test-key",
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
                mock_blob_client.upload_blob.assert_called_once()

    def test_upload_with_prefix(self):
        """Test uploading an archive with blob prefix."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Arrange
            source_file = Path(tmpdir) / "archive.tar.gz"
            source_file.write_text("content")

            mock_blob_service = MagicMock()
            mock_blob_client = MagicMock()
            mock_blob_service.get_blob_client.return_value = mock_blob_client

            mock_properties = Mock()
            mock_properties.size = len("content")
            mock_blob_client.get_blob_properties.return_value = mock_properties

            with patch("azure.storage.blob.BlobServiceClient") as mock_bsc:
                mock_bsc.return_value = mock_blob_service

                backend = AzureBlobBackend(
                    container="test-container",
                    account_name="teststorage",
                    account_key="test-key",
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
                mock_blob_service.get_blob_client.assert_called_with(
                    container="test-container",
                    blob="backups/repo.tar.gz",
                )

    def test_upload_with_metadata_tags(self):
        """Test that metadata is stored as Azure blob metadata."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Arrange
            source_file = Path(tmpdir) / "archive.tar.gz"
            source_file.write_text("content")

            mock_blob_service = MagicMock()
            mock_blob_client = MagicMock()
            mock_blob_service.get_blob_client.return_value = mock_blob_client

            mock_properties = Mock()
            mock_properties.size = len("content")
            mock_blob_client.get_blob_properties.return_value = mock_properties

            metadata_dict = {
                "archive_type": "full",
                "repository_name": "test-repo",
            }

            with patch("azure.storage.blob.BlobServiceClient") as mock_bsc:
                mock_bsc.return_value = mock_blob_service

                backend = AzureBlobBackend(
                    container="test-container",
                    account_name="teststorage",
                    account_key="test-key",
                )

                # Act
                backend.upload_archive(
                    local_path=source_file,
                    remote_key="archive.tar.gz",
                    metadata=metadata_dict,
                )

                # Assert - Check metadata was passed to set_blob_metadata
                mock_blob_client.set_blob_metadata.assert_called_once()
                call_args = mock_blob_client.set_blob_metadata.call_args
                assert call_args[1]["metadata"]["archive_type"] == "full"
                assert call_args[1]["metadata"]["repository_name"] == "test-repo"

    def test_upload_raises_error_if_source_missing(self):
        """Test that upload raises FileNotFoundError if source doesn't exist."""
        with patch("azure.storage.blob.BlobServiceClient"):
            backend = AzureBlobBackend(
                container="test-container",
                account_name="teststorage",
                account_key="test-key",
            )

            with pytest.raises(FileNotFoundError):
                backend.upload_archive(
                    local_path=Path("/nonexistent/file.tar.gz"),
                    remote_key="archive.tar.gz",
                )

    def test_download_archive_from_azure_blob(self):
        """Test downloading an archive from Azure Blob Storage."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Arrange
            dest_path = Path(tmpdir) / "downloaded.tar.gz"

            mock_blob_service = MagicMock()
            mock_blob_client = MagicMock()
            mock_blob_service.get_blob_client.return_value = mock_blob_client

            # Mock download_blob to write content
            mock_downloader = MagicMock()
            mock_downloader.readall.return_value = b"stored content"
            mock_blob_client.download_blob.return_value = mock_downloader

            with patch("azure.storage.blob.BlobServiceClient") as mock_bsc:
                mock_bsc.return_value = mock_blob_service

                backend = AzureBlobBackend(
                    container="test-container",
                    account_name="teststorage",
                    account_key="test-key",
                )

                # Act
                backend.download_archive(
                    remote_key="archive.tar.gz",
                    local_path=dest_path,
                )

                # Assert
                assert dest_path.exists()
                assert dest_path.read_text() == "stored content"

    def test_download_with_prefix(self):
        """Test downloading an archive with blob prefix."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Arrange
            dest_path = Path(tmpdir) / "downloaded.tar.gz"

            mock_blob_service = MagicMock()
            mock_blob_client = MagicMock()
            mock_blob_service.get_blob_client.return_value = mock_blob_client

            mock_downloader = MagicMock()
            mock_downloader.readall.return_value = b"content"
            mock_blob_client.download_blob.return_value = mock_downloader

            with patch("azure.storage.blob.BlobServiceClient") as mock_bsc:
                mock_bsc.return_value = mock_blob_service

                backend = AzureBlobBackend(
                    container="test-container",
                    account_name="teststorage",
                    account_key="test-key",
                    prefix="backups/",
                )

                # Act
                backend.download_archive(
                    remote_key="repo.tar.gz",
                    local_path=dest_path,
                )

                # Assert
                assert dest_path.read_text() == "content"

                # Verify full blob name used
                mock_blob_service.get_blob_client.assert_called_with(
                    container="test-container",
                    blob="backups/repo.tar.gz",
                )

    def test_download_raises_error_if_not_exists(self):
        """Test that download raises KeyError if blob doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Arrange
            dest_path = Path(tmpdir) / "downloaded.tar.gz"

            mock_blob_service = MagicMock()
            mock_blob_client = MagicMock()
            mock_blob_service.get_blob_client.return_value = mock_blob_client

            # Simulate blob not found
            from azure.core.exceptions import ResourceNotFoundError
            mock_blob_client.download_blob.side_effect = ResourceNotFoundError("Blob not found")

            with patch("azure.storage.blob.BlobServiceClient") as mock_bsc:
                mock_bsc.return_value = mock_blob_service

                backend = AzureBlobBackend(
                    container="test-container",
                    account_name="teststorage",
                    account_key="test-key",
                )

                # Act & Assert
                with pytest.raises(KeyError, match="Archive not found"):
                    backend.download_archive(
                        remote_key="nonexistent.tar.gz",
                        local_path=dest_path,
                    )

    def test_list_archives_returns_all_blobs(self):
        """Test listing all archives in Azure Blob container."""
        # Arrange
        mock_blob_service = MagicMock()
        mock_container_client = MagicMock()
        mock_blob_service.get_container_client.return_value = mock_container_client

        # Mock blob list
        mock_blob1 = Mock()
        mock_blob1.name = "repo1-full.tar.gz"
        mock_blob1.size = 100
        mock_blob1.last_modified.isoformat.return_value = "2025-01-09T12:00:00Z"
        mock_blob1.metadata = {}

        mock_blob2 = Mock()
        mock_blob2.name = "repo2-full.tar.gz"
        mock_blob2.size = 200
        mock_blob2.last_modified.isoformat.return_value = "2025-01-09T13:00:00Z"
        mock_blob2.metadata = {}

        mock_container_client.list_blobs.return_value = [mock_blob1, mock_blob2]

        with patch("azure.storage.blob.BlobServiceClient") as mock_bsc:
            mock_bsc.return_value = mock_blob_service

            backend = AzureBlobBackend(
                container="test-container",
                account_name="teststorage",
                account_key="test-key",
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
        mock_blob_service = MagicMock()
        mock_container_client = MagicMock()
        mock_blob_service.get_container_client.return_value = mock_container_client

        # Mock filtered blob list
        mock_blob1 = Mock()
        mock_blob1.name = "backups/repo1.tar.gz"
        mock_blob1.size = 100
        mock_blob1.last_modified.isoformat.return_value = "2025-01-09T12:00:00Z"
        mock_blob1.metadata = {}

        mock_blob2 = Mock()
        mock_blob2.name = "backups/repo2.tar.gz"
        mock_blob2.size = 200
        mock_blob2.last_modified.isoformat.return_value = "2025-01-09T13:00:00Z"
        mock_blob2.metadata = {}

        mock_container_client.list_blobs.return_value = [mock_blob1, mock_blob2]

        with patch("azure.storage.blob.BlobServiceClient") as mock_bsc:
            mock_bsc.return_value = mock_blob_service

            backend = AzureBlobBackend(
                container="test-container",
                account_name="teststorage",
                account_key="test-key",
            )

            # Act
            archives = backend.list_archives(prefix="backups/")

            # Assert
            assert len(archives) == 2
            keys = [a.key for a in archives]
            assert "backups/repo1.tar.gz" in keys
            assert "backups/repo2.tar.gz" in keys

            # Verify prefix was used in list call
            mock_container_client.list_blobs.assert_called_with(name_starts_with="backups/")

    def test_list_archives_includes_metadata_from_blob_metadata(self):
        """Test that list_archives includes metadata from Azure blob metadata."""
        # Arrange
        mock_blob_service = MagicMock()
        mock_container_client = MagicMock()
        mock_blob_service.get_container_client.return_value = mock_container_client

        # Mock blob with metadata
        mock_blob = Mock()
        mock_blob.name = "archive.tar.gz"
        mock_blob.size = 100
        mock_blob.last_modified.isoformat.return_value = "2025-01-09T12:00:00Z"
        mock_blob.metadata = {
            "archive_type": "full",
            "repository_name": "test-repo",
            "checksum_sha256": "abc123",
        }

        mock_container_client.list_blobs.return_value = [mock_blob]

        with patch("azure.storage.blob.BlobServiceClient") as mock_bsc:
            mock_bsc.return_value = mock_blob_service

            backend = AzureBlobBackend(
                container="test-container",
                account_name="teststorage",
                account_key="test-key",
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
        """Test deleting an archive from Azure Blob Storage."""
        # Arrange
        mock_blob_service = MagicMock()
        mock_blob_client = MagicMock()
        mock_blob_service.get_blob_client.return_value = mock_blob_client

        with patch("azure.storage.blob.BlobServiceClient") as mock_bsc:
            mock_bsc.return_value = mock_blob_service

            backend = AzureBlobBackend(
                container="test-container",
                account_name="teststorage",
                account_key="test-key",
            )

            # Act
            backend.delete_archive("archive.tar.gz")

            # Assert
            mock_blob_client.delete_blob.assert_called_once()

    def test_delete_raises_error_if_not_exists(self):
        """Test that delete raises KeyError if blob doesn't exist."""
        # Arrange
        mock_blob_service = MagicMock()
        mock_blob_client = MagicMock()
        mock_blob_service.get_blob_client.return_value = mock_blob_client

        # Simulate blob not found
        from azure.core.exceptions import ResourceNotFoundError
        mock_blob_client.delete_blob.side_effect = ResourceNotFoundError("Blob not found")

        with patch("azure.storage.blob.BlobServiceClient") as mock_bsc:
            mock_bsc.return_value = mock_blob_service

            backend = AzureBlobBackend(
                container="test-container",
                account_name="teststorage",
                account_key="test-key",
            )

            # Act & Assert
            with pytest.raises(KeyError, match="Archive not found"):
                backend.delete_archive("nonexistent.tar.gz")

    def test_archive_exists_returns_true_if_exists(self):
        """Test archive_exists returns True for existing blobs."""
        # Arrange
        mock_blob_service = MagicMock()
        mock_blob_client = MagicMock()
        mock_blob_service.get_blob_client.return_value = mock_blob_client

        # Mock blob exists
        mock_blob_client.exists.return_value = True

        with patch("azure.storage.blob.BlobServiceClient") as mock_bsc:
            mock_bsc.return_value = mock_blob_service

            backend = AzureBlobBackend(
                container="test-container",
                account_name="teststorage",
                account_key="test-key",
            )

            # Act & Assert
            assert backend.archive_exists("archive.tar.gz") is True

    def test_archive_exists_returns_false_if_not_exists(self):
        """Test archive_exists returns False for non-existent blobs."""
        # Arrange
        mock_blob_service = MagicMock()
        mock_blob_client = MagicMock()
        mock_blob_service.get_blob_client.return_value = mock_blob_client

        # Mock blob doesn't exist
        mock_blob_client.exists.return_value = False

        with patch("azure.storage.blob.BlobServiceClient") as mock_bsc:
            mock_bsc.return_value = mock_blob_service

            backend = AzureBlobBackend(
                container="test-container",
                account_name="teststorage",
                account_key="test-key",
            )

            # Act & Assert
            assert backend.archive_exists("nonexistent.tar.gz") is False

    def test_get_archive_url_generates_sas_url(self):
        """Test generating a SAS URL for an Azure blob."""
        # Arrange
        mock_blob_service = MagicMock()
        mock_blob_client = MagicMock()
        mock_blob_service.get_blob_client.return_value = mock_blob_client

        # Mock SAS URL generation
        mock_blob_client.url = "https://teststorage.blob.core.windows.net/test-container/archive.tar.gz"

        with patch("azure.storage.blob.BlobServiceClient") as mock_bsc:
            mock_bsc.return_value = mock_blob_service

            with patch("azure.storage.blob.generate_blob_sas") as mock_sas:
                mock_sas.return_value = "sv=2022-11-02&sig=..."

                backend = AzureBlobBackend(
                    container="test-container",
                    account_name="teststorage",
                    account_key="test-key",
                )

                # Act
                url = backend.get_archive_url("archive.tar.gz")

                # Assert
                assert url is not None
                assert "teststorage.blob.core.windows.net" in url
                assert "archive.tar.gz" in url
                assert "sv=" in url  # SAS token present

    def test_initializes_with_explicit_credentials(self):
        """Test that AzureBlobBackend accepts explicit credentials."""
        with patch("azure.storage.blob.BlobServiceClient"):
            backend = AzureBlobBackend(
                container="test-container",
                account_name="teststorage",
                account_key="test-key-abc123",
            )
            assert backend.account_name == "teststorage"
            assert backend.account_key == "test-key-abc123"
