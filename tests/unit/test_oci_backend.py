"""Unit tests for OCIBackend storage backend using unittest.mock."""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from repo_cloner.storage_backend import OCIBackend


class TestOCIBackend:
    """Test suite for OCIBackend using mocks."""

    def test_initializes_with_bucket_namespace_region(self):
        """Test that OCIBackend initializes with bucket, namespace, and region."""
        with patch("oci.config.from_file"), patch("oci.object_storage.ObjectStorageClient"):
            backend = OCIBackend(
                bucket="test-bucket",
                namespace="test-namespace",
                region="us-ashburn-1",
            )
            assert backend.bucket == "test-bucket"
            assert backend.namespace == "test-namespace"
            assert backend.region == "us-ashburn-1"

    def test_initializes_with_config_file(self):
        """Test that OCIBackend supports custom config file path."""
        with patch("oci.config.from_file"), patch("oci.object_storage.ObjectStorageClient"):
            backend = OCIBackend(
                bucket="test-bucket",
                namespace="test-namespace",
                region="us-ashburn-1",
                config_file="~/.oci/custom_config",
            )
            assert backend.config_file == "~/.oci/custom_config"

    def test_initializes_with_custom_prefix(self):
        """Test that OCIBackend supports custom object prefix."""
        with patch("oci.config.from_file"), patch("oci.object_storage.ObjectStorageClient"):
            backend = OCIBackend(
                bucket="test-bucket",
                namespace="test-namespace",
                region="us-ashburn-1",
                prefix="backups/",
            )
            assert backend.prefix == "backups/"

    def test_upload_archive_to_oci(self):
        """Test uploading an archive to Oracle Cloud Object Storage."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Arrange
            source_file = Path(tmpdir) / "archive.tar.gz"
            source_file.write_text("test content")

            # Mock OCI SDK
            mock_object_storage_client = MagicMock()
            mock_response = Mock()
            mock_response.data = Mock()
            mock_response.data.content_length = len("test content")
            mock_object_storage_client.get_object.return_value = mock_response

            with patch("oci.config.from_file"), patch(
                "oci.object_storage.ObjectStorageClient"
            ) as mock_client:
                mock_client.return_value = mock_object_storage_client

                backend = OCIBackend(
                    bucket="test-bucket",
                    namespace="test-namespace",
                    region="us-ashburn-1",
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
                mock_object_storage_client.put_object.assert_called_once()

    def test_upload_with_prefix(self):
        """Test uploading an archive with object prefix."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Arrange
            source_file = Path(tmpdir) / "archive.tar.gz"
            source_file.write_text("content")

            mock_object_storage_client = MagicMock()
            mock_response = Mock()
            mock_response.data = Mock()
            mock_response.data.content_length = len("content")
            mock_object_storage_client.get_object.return_value = mock_response

            with patch("oci.config.from_file"), patch(
                "oci.object_storage.ObjectStorageClient"
            ) as mock_client:
                mock_client.return_value = mock_object_storage_client

                backend = OCIBackend(
                    bucket="test-bucket",
                    namespace="test-namespace",
                    region="us-ashburn-1",
                    prefix="backups/",
                )

                # Act
                metadata = backend.upload_archive(
                    local_path=source_file,
                    remote_key="repo.tar.gz",
                )

                # Assert
                assert metadata.key == "backups/repo.tar.gz"

                # Verify full object name used
                call_args = mock_object_storage_client.put_object.call_args
                assert call_args[1]["object_name"] == "backups/repo.tar.gz"

    def test_upload_with_metadata_tags(self):
        """Test that metadata is stored as OCI object metadata."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Arrange
            source_file = Path(tmpdir) / "archive.tar.gz"
            source_file.write_text("content")

            mock_object_storage_client = MagicMock()
            mock_response = Mock()
            mock_response.data = Mock()
            mock_response.data.content_length = len("content")
            mock_object_storage_client.get_object.return_value = mock_response

            metadata_dict = {
                "archive_type": "full",
                "repository_name": "test-repo",
            }

            with patch("oci.config.from_file"), patch(
                "oci.object_storage.ObjectStorageClient"
            ) as mock_client:
                mock_client.return_value = mock_object_storage_client

                backend = OCIBackend(
                    bucket="test-bucket",
                    namespace="test-namespace",
                    region="us-ashburn-1",
                )

                # Act
                backend.upload_archive(
                    local_path=source_file,
                    remote_key="archive.tar.gz",
                    metadata=metadata_dict,
                )

                # Assert - Check metadata was passed to put_object
                call_args = mock_object_storage_client.put_object.call_args
                assert call_args[1]["metadata"]["archive_type"] == "full"
                assert call_args[1]["metadata"]["repository_name"] == "test-repo"

    def test_upload_raises_error_if_source_missing(self):
        """Test that upload raises FileNotFoundError if source doesn't exist."""
        with patch("oci.config.from_file"), patch("oci.object_storage.ObjectStorageClient"):
            backend = OCIBackend(
                bucket="test-bucket",
                namespace="test-namespace",
                region="us-ashburn-1",
            )

            with pytest.raises(FileNotFoundError):
                backend.upload_archive(
                    local_path=Path("/nonexistent/file.tar.gz"),
                    remote_key="archive.tar.gz",
                )

    def test_download_archive_from_oci(self):
        """Test downloading an archive from Oracle Cloud Object Storage."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Arrange
            dest_path = Path(tmpdir) / "downloaded.tar.gz"

            mock_object_storage_client = MagicMock()
            mock_response = Mock()
            mock_response.data = Mock()
            mock_response.data.content = b"stored content"
            mock_object_storage_client.get_object.return_value = mock_response

            with patch("oci.config.from_file"), patch(
                "oci.object_storage.ObjectStorageClient"
            ) as mock_client:
                mock_client.return_value = mock_object_storage_client

                backend = OCIBackend(
                    bucket="test-bucket",
                    namespace="test-namespace",
                    region="us-ashburn-1",
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
        """Test downloading an archive with object prefix."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Arrange
            dest_path = Path(tmpdir) / "downloaded.tar.gz"

            mock_object_storage_client = MagicMock()
            mock_response = Mock()
            mock_response.data = Mock()
            mock_response.data.content = b"content"
            mock_object_storage_client.get_object.return_value = mock_response

            with patch("oci.config.from_file"), patch(
                "oci.object_storage.ObjectStorageClient"
            ) as mock_client:
                mock_client.return_value = mock_object_storage_client

                backend = OCIBackend(
                    bucket="test-bucket",
                    namespace="test-namespace",
                    region="us-ashburn-1",
                    prefix="backups/",
                )

                # Act
                backend.download_archive(
                    remote_key="repo.tar.gz",
                    local_path=dest_path,
                )

                # Assert
                assert dest_path.read_text() == "content"

                # Verify full object name used
                call_args = mock_object_storage_client.get_object.call_args
                assert call_args[1]["object_name"] == "backups/repo.tar.gz"

    def test_download_raises_error_if_not_exists(self):
        """Test that download raises KeyError if object doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Arrange
            dest_path = Path(tmpdir) / "downloaded.tar.gz"

            mock_object_storage_client = MagicMock()
            # Simulate object not found
            from oci.exceptions import ServiceError

            mock_object_storage_client.get_object.side_effect = ServiceError(
                status=404, code="ObjectNotFound", headers={}, message="Not found"
            )

            with patch("oci.config.from_file"), patch(
                "oci.object_storage.ObjectStorageClient"
            ) as mock_client:
                mock_client.return_value = mock_object_storage_client

                backend = OCIBackend(
                    bucket="test-bucket",
                    namespace="test-namespace",
                    region="us-ashburn-1",
                )

                # Act & Assert
                with pytest.raises(KeyError, match="Archive not found"):
                    backend.download_archive(
                        remote_key="nonexistent.tar.gz",
                        local_path=dest_path,
                    )

    def test_list_archives_returns_all_objects(self):
        """Test listing all archives in OCI bucket."""
        # Arrange
        mock_object_storage_client = MagicMock()
        mock_response = Mock()

        # Mock object list
        mock_obj1 = Mock()
        mock_obj1.name = "repo1-full.tar.gz"
        mock_obj1.size = 100
        mock_obj1.time_created = "2025-01-09T12:00:00Z"
        mock_obj1.metadata = {}

        mock_obj2 = Mock()
        mock_obj2.name = "repo2-full.tar.gz"
        mock_obj2.size = 200
        mock_obj2.time_created = "2025-01-09T13:00:00Z"
        mock_obj2.metadata = {}

        mock_response.data = Mock()
        mock_response.data.objects = [mock_obj1, mock_obj2]
        mock_object_storage_client.list_objects.return_value = mock_response

        with patch("oci.config.from_file"), patch(
            "oci.object_storage.ObjectStorageClient"
        ) as mock_client:
            mock_client.return_value = mock_object_storage_client

            backend = OCIBackend(
                bucket="test-bucket",
                namespace="test-namespace",
                region="us-ashburn-1",
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
        mock_object_storage_client = MagicMock()
        mock_response = Mock()

        # Mock filtered object list
        mock_obj1 = Mock()
        mock_obj1.name = "backups/repo1.tar.gz"
        mock_obj1.size = 100
        mock_obj1.time_created = "2025-01-09T12:00:00Z"
        mock_obj1.metadata = {}

        mock_obj2 = Mock()
        mock_obj2.name = "backups/repo2.tar.gz"
        mock_obj2.size = 200
        mock_obj2.time_created = "2025-01-09T13:00:00Z"
        mock_obj2.metadata = {}

        mock_response.data = Mock()
        mock_response.data.objects = [mock_obj1, mock_obj2]
        mock_object_storage_client.list_objects.return_value = mock_response

        with patch("oci.config.from_file"), patch(
            "oci.object_storage.ObjectStorageClient"
        ) as mock_client:
            mock_client.return_value = mock_object_storage_client

            backend = OCIBackend(
                bucket="test-bucket",
                namespace="test-namespace",
                region="us-ashburn-1",
            )

            # Act
            archives = backend.list_archives(prefix="backups/")

            # Assert
            assert len(archives) == 2
            keys = [a.key for a in archives]
            assert "backups/repo1.tar.gz" in keys
            assert "backups/repo2.tar.gz" in keys

            # Verify prefix was used in list call
            call_args = mock_object_storage_client.list_objects.call_args
            assert call_args[1]["prefix"] == "backups/"

    def test_list_archives_includes_metadata_from_object_metadata(self):
        """Test that list_archives includes metadata from OCI object metadata."""
        # Arrange
        mock_object_storage_client = MagicMock()
        mock_response = Mock()

        # Mock object with metadata
        mock_obj = Mock()
        mock_obj.name = "archive.tar.gz"
        mock_obj.size = 100
        mock_obj.time_created = "2025-01-09T12:00:00Z"
        mock_obj.metadata = {
            "archive_type": "full",
            "repository_name": "test-repo",
            "checksum_sha256": "abc123",
        }

        mock_response.data = Mock()
        mock_response.data.objects = [mock_obj]
        mock_object_storage_client.list_objects.return_value = mock_response

        with patch("oci.config.from_file"), patch(
            "oci.object_storage.ObjectStorageClient"
        ) as mock_client:
            mock_client.return_value = mock_object_storage_client

            backend = OCIBackend(
                bucket="test-bucket",
                namespace="test-namespace",
                region="us-ashburn-1",
            )

            # Act
            archives = backend.list_archives()

            # Assert
            assert len(archives) == 1
            metadata = archives[0]
            assert metadata.archive_type == "full"
            assert metadata.repository_name == "test-repo"
            assert metadata.checksum_sha256 == "abc123"

    def test_delete_archive_removes_object(self):
        """Test deleting an archive from Oracle Cloud Object Storage."""
        # Arrange
        mock_object_storage_client = MagicMock()

        with patch("oci.config.from_file"), patch(
            "oci.object_storage.ObjectStorageClient"
        ) as mock_client:
            mock_client.return_value = mock_object_storage_client

            backend = OCIBackend(
                bucket="test-bucket",
                namespace="test-namespace",
                region="us-ashburn-1",
            )

            # Act
            backend.delete_archive("archive.tar.gz")

            # Assert
            mock_object_storage_client.delete_object.assert_called_once()

    def test_delete_raises_error_if_not_exists(self):
        """Test that delete raises KeyError if object doesn't exist."""
        # Arrange
        mock_object_storage_client = MagicMock()

        # Simulate object not found
        from oci.exceptions import ServiceError

        mock_object_storage_client.delete_object.side_effect = ServiceError(
            status=404, code="ObjectNotFound", headers={}, message="Not found"
        )

        with patch("oci.config.from_file"), patch(
            "oci.object_storage.ObjectStorageClient"
        ) as mock_client:
            mock_client.return_value = mock_object_storage_client

            backend = OCIBackend(
                bucket="test-bucket",
                namespace="test-namespace",
                region="us-ashburn-1",
            )

            # Act & Assert
            with pytest.raises(KeyError, match="Archive not found"):
                backend.delete_archive("nonexistent.tar.gz")

    def test_archive_exists_returns_true_if_exists(self):
        """Test archive_exists returns True for existing objects."""
        # Arrange
        mock_object_storage_client = MagicMock()
        mock_response = Mock()
        mock_response.data = Mock()
        mock_object_storage_client.head_object.return_value = mock_response

        with patch("oci.config.from_file"), patch(
            "oci.object_storage.ObjectStorageClient"
        ) as mock_client:
            mock_client.return_value = mock_object_storage_client

            backend = OCIBackend(
                bucket="test-bucket",
                namespace="test-namespace",
                region="us-ashburn-1",
            )

            # Act & Assert
            assert backend.archive_exists("archive.tar.gz") is True

    def test_archive_exists_returns_false_if_not_exists(self):
        """Test archive_exists returns False for non-existent objects."""
        # Arrange
        mock_object_storage_client = MagicMock()

        # Simulate object not found
        from oci.exceptions import ServiceError

        mock_object_storage_client.head_object.side_effect = ServiceError(
            status=404, code="ObjectNotFound", headers={}, message="Not found"
        )

        with patch("oci.config.from_file"), patch(
            "oci.object_storage.ObjectStorageClient"
        ) as mock_client:
            mock_client.return_value = mock_object_storage_client

            backend = OCIBackend(
                bucket="test-bucket",
                namespace="test-namespace",
                region="us-ashburn-1",
            )

            # Act & Assert
            assert backend.archive_exists("nonexistent.tar.gz") is False

    def test_get_archive_url_generates_preauthenticated_request(self):
        """Test generating a pre-authenticated request URL for an OCI object."""
        # Arrange
        mock_object_storage_client = MagicMock()
        mock_response = Mock()
        mock_response.data = Mock()
        mock_response.data.access_uri = "/p/abc123/n/namespace/b/bucket/o/archive.tar.gz"
        mock_object_storage_client.create_preauthenticated_request.return_value = mock_response

        with patch("oci.config.from_file"), patch(
            "oci.object_storage.ObjectStorageClient"
        ) as mock_client:
            mock_client.return_value = mock_object_storage_client

            backend = OCIBackend(
                bucket="test-bucket",
                namespace="test-namespace",
                region="us-ashburn-1",
            )

            # Act
            url = backend.get_archive_url("archive.tar.gz")

            # Assert
            assert url is not None
            assert "objectstorage.us-ashburn-1.oraclecloud.com" in url
            assert "/p/abc123/" in url

    def test_initializes_with_explicit_config_file(self):
        """Test that OCIBackend accepts explicit config file path."""
        with patch("oci.config.from_file"), patch("oci.object_storage.ObjectStorageClient"):
            backend = OCIBackend(
                bucket="test-bucket",
                namespace="test-namespace",
                region="us-ashburn-1",
                config_file="~/.oci/config",
            )
            assert backend.bucket == "test-bucket"
            assert backend.namespace == "test-namespace"
            assert backend.region == "us-ashburn-1"
            assert backend.config_file == "~/.oci/config"
