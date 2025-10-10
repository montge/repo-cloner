"""Unit tests for S3Backend storage backend using moto."""

import tempfile
from pathlib import Path

import boto3
import pytest
from moto import mock_aws

from repo_cloner.storage_backend import S3Backend


@mock_aws
class TestS3Backend:
    """Test suite for S3Backend using moto S3 mocking."""

    def test_initializes_with_bucket_and_region(self):
        """Test that S3Backend initializes with bucket and region."""
        backend = S3Backend(
            bucket="test-bucket",
            region="us-east-1",
        )
        assert backend.bucket == "test-bucket"
        assert backend.region == "us-east-1"

    def test_initializes_with_custom_prefix(self):
        """Test that S3Backend supports custom key prefix."""
        backend = S3Backend(
            bucket="test-bucket",
            region="us-east-1",
            prefix="backups/",
        )
        assert backend.prefix == "backups/"

    def test_upload_archive_to_s3(self):
        """Test uploading an archive to S3."""
        # Arrange - Create S3 bucket
        s3_client = boto3.client("s3", region_name="us-east-1")
        s3_client.create_bucket(Bucket="test-bucket")

        backend = S3Backend(bucket="test-bucket", region="us-east-1")

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
            assert metadata.size_bytes == len("test content")

            # Verify file exists in S3
            response = s3_client.head_object(Bucket="test-bucket", Key="test-archive.tar.gz")
            assert response["ContentLength"] == len("test content")

    def test_upload_with_prefix(self):
        """Test uploading an archive with key prefix."""
        # Arrange
        s3_client = boto3.client("s3", region_name="us-west-2")
        s3_client.create_bucket(
            Bucket="test-bucket",
            CreateBucketConfiguration={"LocationConstraint": "us-west-2"},
        )

        backend = S3Backend(
            bucket="test-bucket",
            region="us-west-2",
            prefix="backups/",
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
            assert metadata.key == "backups/repo.tar.gz"

            # Verify full key in S3
            response = s3_client.head_object(Bucket="test-bucket", Key="backups/repo.tar.gz")
            assert response["ContentLength"] == len("content")

    def test_upload_with_metadata_tags(self):
        """Test that metadata is stored as S3 object tags."""
        # Arrange
        s3_client = boto3.client("s3", region_name="us-east-1")
        s3_client.create_bucket(Bucket="test-bucket")

        backend = S3Backend(bucket="test-bucket", region="us-east-1")

        with tempfile.TemporaryDirectory() as tmpdir:
            source_file = Path(tmpdir) / "archive.tar.gz"
            source_file.write_text("content")

            metadata_dict = {
                "archive_type": "full",
                "repository_name": "test-repo",
            }

            # Act
            backend.upload_archive(
                local_path=source_file,
                remote_key="archive.tar.gz",
                metadata=metadata_dict,
            )

            # Assert - Check tags
            response = s3_client.get_object_tagging(Bucket="test-bucket", Key="archive.tar.gz")
            tags = {tag["Key"]: tag["Value"] for tag in response["TagSet"]}
            assert tags["archive_type"] == "full"
            assert tags["repository_name"] == "test-repo"

    def test_upload_raises_error_if_source_missing(self):
        """Test that upload raises FileNotFoundError if source doesn't exist."""
        s3_client = boto3.client("s3", region_name="us-east-1")
        s3_client.create_bucket(Bucket="test-bucket")

        backend = S3Backend(bucket="test-bucket", region="us-east-1")

        with pytest.raises(FileNotFoundError):
            backend.upload_archive(
                local_path=Path("/nonexistent/file.tar.gz"),
                remote_key="archive.tar.gz",
            )

    def test_download_archive_from_s3(self):
        """Test downloading an archive from S3."""
        # Arrange
        s3_client = boto3.client("s3", region_name="us-east-1")
        s3_client.create_bucket(Bucket="test-bucket")
        s3_client.put_object(Bucket="test-bucket", Key="archive.tar.gz", Body=b"stored content")

        backend = S3Backend(bucket="test-bucket", region="us-east-1")

        with tempfile.TemporaryDirectory() as tmpdir:
            dest_path = Path(tmpdir) / "downloaded.tar.gz"

            # Act
            backend.download_archive(
                remote_key="archive.tar.gz",
                local_path=dest_path,
            )

            # Assert
            assert dest_path.exists()
            assert dest_path.read_text() == "stored content"

    def test_download_with_prefix(self):
        """Test downloading an archive with key prefix."""
        # Arrange
        s3_client = boto3.client("s3", region_name="us-east-1")
        s3_client.create_bucket(Bucket="test-bucket")
        s3_client.put_object(Bucket="test-bucket", Key="backups/repo.tar.gz", Body=b"content")

        backend = S3Backend(
            bucket="test-bucket",
            region="us-east-1",
            prefix="backups/",
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            dest_path = Path(tmpdir) / "downloaded.tar.gz"

            # Act
            backend.download_archive(
                remote_key="repo.tar.gz",
                local_path=dest_path,
            )

            # Assert
            assert dest_path.read_text() == "content"

    def test_download_raises_error_if_not_exists(self):
        """Test that download raises KeyError if object doesn't exist."""
        s3_client = boto3.client("s3", region_name="us-east-1")
        s3_client.create_bucket(Bucket="test-bucket")

        backend = S3Backend(bucket="test-bucket", region="us-east-1")

        with tempfile.TemporaryDirectory() as tmpdir:
            dest_path = Path(tmpdir) / "downloaded.tar.gz"

            with pytest.raises(KeyError, match="Archive not found"):
                backend.download_archive(
                    remote_key="nonexistent.tar.gz",
                    local_path=dest_path,
                )

    def test_list_archives_returns_all_objects(self):
        """Test listing all archives in S3 bucket."""
        # Arrange
        s3_client = boto3.client("s3", region_name="us-east-1")
        s3_client.create_bucket(Bucket="test-bucket")
        s3_client.put_object(Bucket="test-bucket", Key="repo1-full.tar.gz", Body=b"content1")
        s3_client.put_object(Bucket="test-bucket", Key="repo2-full.tar.gz", Body=b"content2")
        s3_client.put_object(Bucket="test-bucket", Key="repo3-inc.tar.gz", Body=b"content3")

        backend = S3Backend(bucket="test-bucket", region="us-east-1")

        # Act
        archives = backend.list_archives()

        # Assert
        assert len(archives) == 3
        keys = [a.key for a in archives]
        assert "repo1-full.tar.gz" in keys
        assert "repo2-full.tar.gz" in keys
        assert "repo3-inc.tar.gz" in keys

    def test_list_archives_with_prefix_filter(self):
        """Test listing archives with prefix filter."""
        # Arrange
        s3_client = boto3.client("s3", region_name="us-east-1")
        s3_client.create_bucket(Bucket="test-bucket")
        s3_client.put_object(Bucket="test-bucket", Key="backups/repo1.tar.gz", Body=b"content1")
        s3_client.put_object(Bucket="test-bucket", Key="backups/repo2.tar.gz", Body=b"content2")
        s3_client.put_object(Bucket="test-bucket", Key="other/repo3.tar.gz", Body=b"content3")

        backend = S3Backend(bucket="test-bucket", region="us-east-1")

        # Act
        archives = backend.list_archives(prefix="backups/")

        # Assert
        assert len(archives) == 2
        keys = [a.key for a in archives]
        assert "backups/repo1.tar.gz" in keys
        assert "backups/repo2.tar.gz" in keys
        assert "other/repo3.tar.gz" not in keys

    def test_list_archives_includes_metadata_from_tags(self):
        """Test that list_archives includes metadata from S3 tags."""
        # Arrange
        s3_client = boto3.client("s3", region_name="us-east-1")
        s3_client.create_bucket(Bucket="test-bucket")
        s3_client.put_object(Bucket="test-bucket", Key="archive.tar.gz", Body=b"content")

        # Add tags
        s3_client.put_object_tagging(
            Bucket="test-bucket",
            Key="archive.tar.gz",
            Tagging={
                "TagSet": [
                    {"Key": "archive_type", "Value": "full"},
                    {"Key": "repository_name", "Value": "test-repo"},
                ]
            },
        )

        backend = S3Backend(bucket="test-bucket", region="us-east-1")

        # Act
        archives = backend.list_archives()

        # Assert
        assert len(archives) == 1
        metadata = archives[0]
        assert metadata.archive_type == "full"
        assert metadata.repository_name == "test-repo"

    def test_delete_archive_removes_object(self):
        """Test deleting an archive from S3."""
        # Arrange
        s3_client = boto3.client("s3", region_name="us-east-1")
        s3_client.create_bucket(Bucket="test-bucket")
        s3_client.put_object(Bucket="test-bucket", Key="archive.tar.gz", Body=b"content")

        backend = S3Backend(bucket="test-bucket", region="us-east-1")

        # Act
        backend.delete_archive("archive.tar.gz")

        # Assert
        with pytest.raises(Exception):  # ClientError from boto3
            s3_client.head_object(Bucket="test-bucket", Key="archive.tar.gz")

    def test_delete_raises_error_if_not_exists(self):
        """Test that delete raises KeyError if object doesn't exist."""
        s3_client = boto3.client("s3", region_name="us-east-1")
        s3_client.create_bucket(Bucket="test-bucket")

        backend = S3Backend(bucket="test-bucket", region="us-east-1")

        with pytest.raises(KeyError, match="Archive not found"):
            backend.delete_archive("nonexistent.tar.gz")

    def test_archive_exists_returns_true_if_exists(self):
        """Test archive_exists returns True for existing objects."""
        # Arrange
        s3_client = boto3.client("s3", region_name="us-east-1")
        s3_client.create_bucket(Bucket="test-bucket")
        s3_client.put_object(Bucket="test-bucket", Key="archive.tar.gz", Body=b"content")

        backend = S3Backend(bucket="test-bucket", region="us-east-1")

        # Act & Assert
        assert backend.archive_exists("archive.tar.gz") is True

    def test_archive_exists_returns_false_if_not_exists(self):
        """Test archive_exists returns False for non-existent objects."""
        s3_client = boto3.client("s3", region_name="us-east-1")
        s3_client.create_bucket(Bucket="test-bucket")

        backend = S3Backend(bucket="test-bucket", region="us-east-1")

        assert backend.archive_exists("nonexistent.tar.gz") is False

    def test_get_archive_url_generates_presigned_url(self):
        """Test generating a pre-signed URL for an S3 object."""
        # Arrange
        s3_client = boto3.client("s3", region_name="us-east-1")
        s3_client.create_bucket(Bucket="test-bucket")
        s3_client.put_object(Bucket="test-bucket", Key="archive.tar.gz", Body=b"content")

        backend = S3Backend(bucket="test-bucket", region="us-east-1")

        # Act
        url = backend.get_archive_url("archive.tar.gz")

        # Assert
        assert url is not None
        assert "test-bucket" in url
        assert "archive.tar.gz" in url
        # Check for either signature format (X-Amz-Algorithm or AWSAccessKeyId)
        assert "X-Amz-Algorithm" in url or "AWSAccessKeyId" in url

    def test_initializes_with_credentials(self):
        """Test that S3Backend accepts explicit credentials."""
        backend = S3Backend(
            bucket="test-bucket",
            region="us-east-1",
            access_key="AKIAIOSFODNN7EXAMPLE",
            secret_key="wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
        )
        assert backend.access_key == "AKIAIOSFODNN7EXAMPLE"
        assert backend.secret_key == "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
