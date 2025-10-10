"""Unit tests for S3CompatibleBackend storage backend.

Since S3CompatibleBackend uses custom endpoint URLs that moto can't mock properly,
we use unittest.mock to mock the boto3 S3 client directly.
"""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from repo_cloner.storage_backend import S3CompatibleBackend


class TestS3CompatibleBackend:
    """Test suite for S3CompatibleBackend using unittest.mock."""

    def test_initializes_with_endpoint_bucket_credentials(self):
        """Test that S3CompatibleBackend initializes with endpoint, bucket, and credentials."""
        with patch("boto3.client"):
            backend = S3CompatibleBackend(
                endpoint_url="https://minio.example.com:9000",
                bucket="test-bucket",
                access_key="minioadmin",
                secret_key="minioadmin",
            )
            assert backend.endpoint_url == "https://minio.example.com:9000"
            assert backend.bucket == "test-bucket"
            assert backend.access_key == "minioadmin"
            assert backend.secret_key == "minioadmin"

    def test_initializes_with_region_parameter(self):
        """Test that S3CompatibleBackend supports region parameter."""
        with patch("boto3.client"):
            backend = S3CompatibleBackend(
                endpoint_url="https://nyc3.digitaloceanspaces.com",
                bucket="test-bucket",
                access_key="DO_ACCESS_KEY",
                secret_key="DO_SECRET_KEY",
                region="nyc3",
            )
            assert backend.region == "nyc3"

    def test_initializes_with_custom_prefix(self):
        """Test that S3CompatibleBackend supports custom key prefix."""
        with patch("boto3.client"):
            backend = S3CompatibleBackend(
                endpoint_url="https://s3.wasabisys.com",
                bucket="test-bucket",
                access_key="WASABI_KEY",
                secret_key="WASABI_SECRET",
                prefix="backups/",
            )
            assert backend.prefix == "backups/"

    def test_upload_archive_to_s3_compatible(self):
        """Test uploading an archive to S3-compatible storage."""
        # Mock S3 client
        mock_s3_client = MagicMock()
        mock_s3_client.head_object.return_value = {"ContentLength": 12}

        with patch("boto3.client") as mock_client:
            mock_client.return_value = mock_s3_client

            backend = S3CompatibleBackend(
                endpoint_url="https://minio.local:9000",
                bucket="test-bucket",
                access_key="minioadmin",
                secret_key="minioadmin",
            )

            with tempfile.TemporaryDirectory() as tmpdir:
                source_file = Path(tmpdir) / "archive.tar.gz"
                source_file.write_text("test content")

                # Act
                metadata = backend.upload_archive(
                    local_path=source_file,
                    remote_key="test-archive.tar.gz",
                )

                # Assert
                assert metadata.key == "test-archive.tar.gz"
                assert metadata.filename == "test-archive.tar.gz"
                assert metadata.size_bytes == 12
                mock_s3_client.upload_file.assert_called_once()

    def test_upload_with_prefix(self):
        """Test uploading an archive with key prefix."""
        mock_s3_client = MagicMock()
        mock_s3_client.head_object.return_value = {"ContentLength": 7}

        with patch("boto3.client") as mock_client:
            mock_client.return_value = mock_s3_client

            backend = S3CompatibleBackend(
                endpoint_url="https://ceph.example.com",
                bucket="test-bucket",
                access_key="ceph_key",
                secret_key="ceph_secret",
                prefix="repos/",
            )

            with tempfile.TemporaryDirectory() as tmpdir:
                source_file = Path(tmpdir) / "archive.tar.gz"
                source_file.write_text("content")

                # Act
                metadata = backend.upload_archive(
                    local_path=source_file,
                    remote_key="repo.tar.gz",
                )

                # Assert
                assert metadata.key == "repos/repo.tar.gz"
                # Verify upload_file was called with the full key including prefix
                call_args = mock_s3_client.upload_file.call_args
                assert call_args[0][2] == "repos/repo.tar.gz"  # Third argument is the key

    def test_upload_with_metadata_tags(self):
        """Test that metadata is stored as S3 object tags."""
        mock_s3_client = MagicMock()
        mock_s3_client.head_object.return_value = {"ContentLength": 7}

        with patch("boto3.client") as mock_client:
            mock_client.return_value = mock_s3_client

            backend = S3CompatibleBackend(
                endpoint_url="https://minio.local:9000",
                bucket="test-bucket",
                access_key="minioadmin",
                secret_key="minioadmin",
            )

            with tempfile.TemporaryDirectory() as tmpdir:
                source_file = Path(tmpdir) / "archive.tar.gz"
                source_file.write_text("content")

                metadata_dict = {
                    "archive_type": "incremental",
                    "repository_name": "test-repo",
                }

                # Act
                backend.upload_archive(
                    local_path=source_file,
                    remote_key="archive.tar.gz",
                    metadata=metadata_dict,
                )

                # Assert - Check put_object_tagging was called
                mock_s3_client.put_object_tagging.assert_called_once()
                call_kwargs = mock_s3_client.put_object_tagging.call_args[1]
                assert call_kwargs["Bucket"] == "test-bucket"
                assert call_kwargs["Key"] == "archive.tar.gz"

    def test_upload_raises_error_if_source_missing(self):
        """Test that upload raises FileNotFoundError if source doesn't exist."""
        with patch("boto3.client"):
            backend = S3CompatibleBackend(
                endpoint_url="https://minio.local:9000",
                bucket="test-bucket",
                access_key="admin",
                secret_key="password",
            )

            with pytest.raises(FileNotFoundError):
                backend.upload_archive(
                    local_path=Path("/nonexistent/file.tar.gz"),
                    remote_key="archive.tar.gz",
                )

    def test_download_archive_from_s3_compatible(self):
        """Test downloading an archive from S3-compatible storage."""
        mock_s3_client = MagicMock()

        with patch("boto3.client") as mock_client:
            mock_client.return_value = mock_s3_client

            backend = S3CompatibleBackend(
                endpoint_url="https://wasabi.example.com",
                bucket="test-bucket",
                access_key="WASABI_KEY",
                secret_key="WASABI_SECRET",
            )

            with tempfile.TemporaryDirectory() as tmpdir:
                dest_path = Path(tmpdir) / "downloaded.tar.gz"

                # Act
                backend.download_archive(
                    remote_key="archive.tar.gz",
                    local_path=dest_path,
                )

                # Assert - Check download_file was called
                mock_s3_client.head_object.assert_called_once()
                mock_s3_client.download_file.assert_called_once()

    def test_download_with_prefix(self):
        """Test downloading an archive with key prefix."""
        mock_s3_client = MagicMock()

        with patch("boto3.client") as mock_client:
            mock_client.return_value = mock_s3_client

            backend = S3CompatibleBackend(
                endpoint_url="https://spaces.digitalocean.com",
                bucket="test-bucket",
                access_key="DO_KEY",
                secret_key="DO_SECRET",
                prefix="backups/",
            )

            with tempfile.TemporaryDirectory() as tmpdir:
                dest_path = Path(tmpdir) / "downloaded.tar.gz"

                # Act
                backend.download_archive(
                    remote_key="repo.tar.gz",
                    local_path=dest_path,
                )

                # Assert - Check head_object was called with full key including prefix
                call_kwargs = mock_s3_client.head_object.call_args[1]
                assert call_kwargs["Key"] == "backups/repo.tar.gz"

    def test_download_raises_error_if_not_exists(self):
        """Test that download raises KeyError if object doesn't exist."""
        from botocore.exceptions import ClientError

        mock_s3_client = MagicMock()
        # Simulate 404 error
        error_response = {"Error": {"Code": "404"}}
        mock_s3_client.head_object.side_effect = ClientError(error_response, "HeadObject")

        with patch("boto3.client") as mock_client:
            mock_client.return_value = mock_s3_client

            backend = S3CompatibleBackend(
                endpoint_url="https://minio.local:9000",
                bucket="test-bucket",
                access_key="minioadmin",
                secret_key="minioadmin",
            )

            with tempfile.TemporaryDirectory() as tmpdir:
                dest_path = Path(tmpdir) / "downloaded.tar.gz"

                with pytest.raises(KeyError, match="Archive not found"):
                    backend.download_archive(
                        remote_key="nonexistent.tar.gz",
                        local_path=dest_path,
                    )

    def test_list_archives_returns_all_objects(self):
        """Test listing all archives in S3-compatible bucket."""
        from datetime import datetime, timezone

        mock_s3_client = MagicMock()
        mock_paginator = MagicMock()
        mock_s3_client.get_paginator.return_value = mock_paginator

        # Simulate list_objects_v2 response
        mock_paginator.paginate.return_value = [
            {
                "Contents": [
                    {
                        "Key": "repo1-full.tar.gz",
                        "Size": 100,
                        "LastModified": datetime(2025, 10, 10, 12, 0, 0, tzinfo=timezone.utc),
                    },
                    {
                        "Key": "repo2-full.tar.gz",
                        "Size": 200,
                        "LastModified": datetime(2025, 10, 10, 13, 0, 0, tzinfo=timezone.utc),
                    },
                ]
            }
        ]

        with patch("boto3.client") as mock_client:
            mock_client.return_value = mock_s3_client

            backend = S3CompatibleBackend(
                endpoint_url="https://ceph.storage.local",
                bucket="test-bucket",
                access_key="ceph_admin",
                secret_key="ceph_password",
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
        from datetime import datetime, timezone

        mock_s3_client = MagicMock()
        mock_paginator = MagicMock()
        mock_s3_client.get_paginator.return_value = mock_paginator

        mock_paginator.paginate.return_value = [
            {
                "Contents": [
                    {
                        "Key": "production/repo1.tar.gz",
                        "Size": 100,
                        "LastModified": datetime(2025, 10, 10, 12, 0, 0, tzinfo=timezone.utc),
                    },
                    {
                        "Key": "production/repo2.tar.gz",
                        "Size": 200,
                        "LastModified": datetime(2025, 10, 10, 13, 0, 0, tzinfo=timezone.utc),
                    },
                ]
            }
        ]

        with patch("boto3.client") as mock_client:
            mock_client.return_value = mock_s3_client

            backend = S3CompatibleBackend(
                endpoint_url="https://minio.example.com:9000",
                bucket="test-bucket",
                access_key="minioadmin",
                secret_key="minioadmin",
            )

            # Act
            archives = backend.list_archives(prefix="production/")

            # Assert
            assert len(archives) == 2
            # Verify paginate was called with the correct prefix
            call_kwargs = mock_paginator.paginate.call_args[1]
            assert call_kwargs["Prefix"] == "production/"

    def test_list_archives_includes_metadata_from_tags(self):
        """Test that list_archives includes metadata from S3 tags."""
        from datetime import datetime, timezone

        mock_s3_client = MagicMock()
        mock_paginator = MagicMock()
        mock_s3_client.get_paginator.return_value = mock_paginator

        mock_paginator.paginate.return_value = [
            {
                "Contents": [
                    {
                        "Key": "archive.tar.gz",
                        "Size": 100,
                        "LastModified": datetime(2025, 10, 10, 12, 0, 0, tzinfo=timezone.utc),
                    },
                ]
            }
        ]

        # Mock get_object_tagging response
        mock_s3_client.get_object_tagging.return_value = {
            "TagSet": [
                {"Key": "archive_type", "Value": "full"},
                {"Key": "repository_name", "Value": "test-repo"},
            ]
        }

        with patch("boto3.client") as mock_client:
            mock_client.return_value = mock_s3_client

            backend = S3CompatibleBackend(
                endpoint_url="https://wasabi.local",
                bucket="test-bucket",
                access_key="wasabi_key",
                secret_key="wasabi_secret",
            )

            # Act
            archives = backend.list_archives()

            # Assert
            assert len(archives) == 1
            metadata = archives[0]
            assert metadata.archive_type == "full"
            assert metadata.repository_name == "test-repo"

    def test_delete_archive_removes_object(self):
        """Test deleting an archive from S3-compatible storage."""
        mock_s3_client = MagicMock()

        with patch("boto3.client") as mock_client:
            mock_client.return_value = mock_s3_client

            backend = S3CompatibleBackend(
                endpoint_url="https://ceph.local:7480",
                bucket="test-bucket",
                access_key="ceph_key",
                secret_key="ceph_secret",
            )

            # Act
            backend.delete_archive("archive.tar.gz")

            # Assert
            mock_s3_client.head_object.assert_called_once()
            mock_s3_client.delete_object.assert_called_once_with(
                Bucket="test-bucket", Key="archive.tar.gz"
            )

    def test_delete_raises_error_if_not_exists(self):
        """Test that delete raises KeyError if object doesn't exist."""
        from botocore.exceptions import ClientError

        mock_s3_client = MagicMock()
        error_response = {"Error": {"Code": "404"}}
        mock_s3_client.head_object.side_effect = ClientError(error_response, "HeadObject")

        with patch("boto3.client") as mock_client:
            mock_client.return_value = mock_s3_client

            backend = S3CompatibleBackend(
                endpoint_url="https://minio.local:9000",
                bucket="test-bucket",
                access_key="minioadmin",
                secret_key="minioadmin",
            )

            with pytest.raises(KeyError, match="Archive not found"):
                backend.delete_archive("nonexistent.tar.gz")

    def test_archive_exists_returns_true_if_exists(self):
        """Test archive_exists returns True for existing objects."""
        mock_s3_client = MagicMock()

        with patch("boto3.client") as mock_client:
            mock_client.return_value = mock_s3_client

            backend = S3CompatibleBackend(
                endpoint_url="https://spaces.digitalocean.com",
                bucket="test-bucket",
                access_key="DO_KEY",
                secret_key="DO_SECRET",
            )

            # Act & Assert
            assert backend.archive_exists("archive.tar.gz") is True
            mock_s3_client.head_object.assert_called_once()

    def test_archive_exists_returns_false_if_not_exists(self):
        """Test archive_exists returns False for non-existent objects."""
        from botocore.exceptions import ClientError

        mock_s3_client = MagicMock()
        error_response = {"Error": {"Code": "404"}}
        mock_s3_client.head_object.side_effect = ClientError(error_response, "HeadObject")

        with patch("boto3.client") as mock_client:
            mock_client.return_value = mock_s3_client

            backend = S3CompatibleBackend(
                endpoint_url="https://wasabi.local",
                bucket="test-bucket",
                access_key="WASABI_KEY",
                secret_key="WASABI_SECRET",
            )

            assert backend.archive_exists("nonexistent.tar.gz") is False

    def test_get_archive_url_generates_presigned_url(self):
        """Test generating a pre-signed URL for an S3-compatible object."""
        mock_s3_client = MagicMock()
        mock_s3_client.generate_presigned_url.return_value = (
            "https://minio.local:9000/test-bucket/archive.tar.gz?X-Amz-Algorithm=..."
        )

        with patch("boto3.client") as mock_client:
            mock_client.return_value = mock_s3_client

            backend = S3CompatibleBackend(
                endpoint_url="https://minio.local:9000",
                bucket="test-bucket",
                access_key="minioadmin",
                secret_key="minioadmin",
            )

            # Act
            url = backend.get_archive_url("archive.tar.gz")

            # Assert
            assert url is not None
            assert "test-bucket" in url
            assert "archive.tar.gz" in url
            mock_s3_client.generate_presigned_url.assert_called_once()
