"""Storage backend abstraction for archive management.

Provides pluggable storage backends for uploading/downloading archives
to various cloud providers and local filesystem.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class ArchiveMetadata:
    """Metadata for an archive stored in a backend."""

    key: str  # Unique identifier/path in storage
    filename: str  # Original filename
    size_bytes: int
    timestamp: str  # ISO 8601 format
    checksum_sha256: Optional[str] = None
    archive_type: Optional[str] = None  # 'full' or 'incremental'
    repository_name: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None  # Additional backend-specific metadata


class StorageBackend(ABC):
    """Abstract base class for storage backends.

    All storage backends must implement these methods to support
    archive upload, download, listing, and deletion operations.
    """

    @abstractmethod
    def upload_archive(
        self,
        local_path: Path,
        remote_key: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ArchiveMetadata:
        """Upload an archive file to the storage backend.

        Args:
            local_path: Path to the local archive file
            remote_key: Key/path in the storage backend (e.g., "backups/repo-full-20251010.tar.gz")
            metadata: Optional metadata to store with the archive

        Returns:
            ArchiveMetadata object with upload details

        Raises:
            FileNotFoundError: If local_path does not exist
            PermissionError: If authentication/authorization fails
            IOError: If upload fails
        """
        pass

    @abstractmethod
    def download_archive(self, remote_key: str, local_path: Path) -> None:
        """Download an archive file from the storage backend.

        Args:
            remote_key: Key/path in the storage backend
            local_path: Destination path for downloaded file

        Raises:
            KeyError: If remote_key does not exist
            PermissionError: If authentication/authorization fails
            IOError: If download fails
        """
        pass

    @abstractmethod
    def list_archives(self, prefix: Optional[str] = None) -> List[ArchiveMetadata]:
        """List all archives in the storage backend.

        Args:
            prefix: Optional prefix filter (e.g., "backups/myrepo-")

        Returns:
            List of ArchiveMetadata objects

        Raises:
            PermissionError: If authentication/authorization fails
            IOError: If listing fails
        """
        pass

    @abstractmethod
    def delete_archive(self, remote_key: str) -> None:
        """Delete an archive from the storage backend.

        Args:
            remote_key: Key/path in the storage backend

        Raises:
            KeyError: If remote_key does not exist
            PermissionError: If authentication/authorization fails
            IOError: If deletion fails
        """
        pass

    @abstractmethod
    def archive_exists(self, remote_key: str) -> bool:
        """Check if an archive exists in the storage backend.

        Args:
            remote_key: Key/path in the storage backend

        Returns:
            True if archive exists, False otherwise

        Raises:
            PermissionError: If authentication/authorization fails
            IOError: If check fails
        """
        pass

    def get_archive_url(self, remote_key: str) -> Optional[str]:
        """Get a public or pre-signed URL for an archive (optional).

        Not all backends support this. Returns None if unsupported.

        Args:
            remote_key: Key/path in the storage backend

        Returns:
            URL string or None if unsupported

        Raises:
            KeyError: If remote_key does not exist
            PermissionError: If authentication/authorization fails
        """
        return None  # Default: not supported


class LocalFilesystemBackend(StorageBackend):
    """Storage backend for local filesystem (including NFS/SMB mounts).

    Supports any locally-accessible path, including network mounts.
    """

    def __init__(self, base_path: Path):
        """Initialize local filesystem backend.

        Args:
            base_path: Base directory for storing archives

        Raises:
            ValueError: If base_path is not a valid directory path
        """
        self.base_path = Path(base_path)
        if not self.base_path.is_absolute():
            raise ValueError(f"base_path must be absolute: {base_path}")

    def upload_archive(
        self,
        local_path: Path,
        remote_key: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ArchiveMetadata:
        """Copy archive to local filesystem storage.

        Args:
            local_path: Source archive file
            remote_key: Relative path within base_path
            metadata: Optional metadata (stored as JSON sidecar file)

        Returns:
            ArchiveMetadata with upload details
        """
        import hashlib
        import shutil
        from datetime import datetime, timezone

        # Validate source exists
        local_path = Path(local_path)
        if not local_path.exists():
            raise FileNotFoundError(f"Source file not found: {local_path}")

        # Determine destination path
        dest_path = self.base_path / remote_key
        dest_path.parent.mkdir(parents=True, exist_ok=True)

        # Copy file
        shutil.copy2(local_path, dest_path)

        # Calculate checksum
        sha256_hash = hashlib.sha256()
        with open(dest_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                sha256_hash.update(chunk)
        checksum = sha256_hash.hexdigest()

        # Get file size and timestamp
        size_bytes = dest_path.stat().st_size
        timestamp = datetime.now(timezone.utc).isoformat()

        # Store metadata sidecar if provided
        if metadata:
            import json

            sidecar_path = Path(str(dest_path) + ".meta.json")
            with open(sidecar_path, "w") as f:
                json.dump(metadata, f, indent=2)

        # Build and return metadata
        return ArchiveMetadata(
            key=remote_key,
            filename=Path(remote_key).name,
            size_bytes=size_bytes,
            timestamp=timestamp,
            checksum_sha256=checksum,
            archive_type=metadata.get("archive_type") if metadata else None,
            repository_name=metadata.get("repository_name") if metadata else None,
            metadata=metadata,
        )

    def download_archive(self, remote_key: str, local_path: Path) -> None:
        """Copy archive from local filesystem storage.

        Args:
            remote_key: Relative path within base_path
            local_path: Destination file path
        """
        import shutil

        # Check source exists
        source_path = self.base_path / remote_key
        if not source_path.exists():
            raise KeyError(f"Archive not found: {remote_key}")

        # Create parent directories for destination
        local_path = Path(local_path)
        local_path.parent.mkdir(parents=True, exist_ok=True)

        # Copy file
        shutil.copy2(source_path, local_path)

    def list_archives(self, prefix: Optional[str] = None) -> List[ArchiveMetadata]:
        """List archives in local filesystem storage.

        Args:
            prefix: Optional path prefix filter

        Returns:
            List of ArchiveMetadata for matching files
        """
        import json
        from datetime import datetime, timezone

        archives = []
        search_path = self.base_path / (prefix if prefix else "")

        # Handle case where search path doesn't exist
        if not search_path.exists():
            return []

        # Recursively find all .tar.gz files
        pattern = "**/*.tar.gz" if search_path.is_dir() else "*.tar.gz"
        for archive_file in search_path.glob(pattern):
            # Skip metadata sidecar files
            if archive_file.name.endswith(".meta.json"):
                continue

            # Calculate relative key
            relative_key = str(archive_file.relative_to(self.base_path))

            # Read metadata from sidecar if exists
            sidecar_path = Path(str(archive_file) + ".meta.json")
            meta_dict = None
            archive_type = None
            repository_name = None
            checksum_sha256 = None

            if sidecar_path.exists():
                with open(sidecar_path, "r") as f:
                    meta_dict = json.load(f)
                    archive_type = meta_dict.get("archive_type")
                    repository_name = meta_dict.get("repository_name")
                    checksum_sha256 = meta_dict.get("checksum_sha256")

            # Get file stats
            stat = archive_file.stat()
            size_bytes = stat.st_size
            timestamp = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat()

            # Create metadata object
            archives.append(
                ArchiveMetadata(
                    key=relative_key,
                    filename=archive_file.name,
                    size_bytes=size_bytes,
                    timestamp=timestamp,
                    checksum_sha256=checksum_sha256,
                    archive_type=archive_type,
                    repository_name=repository_name,
                    metadata=meta_dict,
                )
            )

        return archives

    def delete_archive(self, remote_key: str) -> None:
        """Delete archive from local filesystem storage.

        Args:
            remote_key: Relative path within base_path
        """
        # Check archive exists
        archive_path = self.base_path / remote_key
        if not archive_path.exists():
            raise KeyError(f"Archive not found: {remote_key}")

        # Delete archive file
        archive_path.unlink()

        # Delete metadata sidecar if exists
        sidecar_path = Path(str(archive_path) + ".meta.json")
        if sidecar_path.exists():
            sidecar_path.unlink()

    def archive_exists(self, remote_key: str) -> bool:
        """Check if archive exists in local filesystem storage.

        Args:
            remote_key: Relative path within base_path

        Returns:
            True if file exists, False otherwise
        """
        archive_path = self.base_path / remote_key
        return archive_path.exists()


# Placeholder classes for future backends
# These will be implemented in subsequent phases


class S3Backend(StorageBackend):
    """AWS S3 storage backend with region selection.

    Uses boto3 for S3 operations.
    """

    def __init__(
        self,
        bucket: str,
        region: str,
        prefix: str = "",
        access_key: Optional[str] = None,
        secret_key: Optional[str] = None,
    ):
        """Initialize S3 backend.

        Args:
            bucket: S3 bucket name
            region: AWS region (e.g., 'us-east-1')
            prefix: Optional key prefix for all operations
            access_key: AWS access key ID (optional, uses default credentials if not provided)
            secret_key: AWS secret access key (optional)
        """
        import boto3

        self.bucket = bucket
        self.region = region
        self.prefix = prefix
        self.access_key = access_key
        self.secret_key = secret_key

        # Create S3 client
        if access_key and secret_key:
            self.s3_client = boto3.client(
                "s3",
                region_name=region,
                aws_access_key_id=access_key,
                aws_secret_access_key=secret_key,
            )
        else:
            # Use default credentials from environment/IAM role
            self.s3_client = boto3.client("s3", region_name=region)

    def _full_key(self, remote_key: str) -> str:
        """Prepend prefix to remote key if configured."""
        if self.prefix:
            return f"{self.prefix}{remote_key}"
        return remote_key

    def upload_archive(
        self, local_path: Path, remote_key: str, metadata: Optional[Dict[str, Any]] = None
    ) -> ArchiveMetadata:
        """Upload archive to S3.

        Args:
            local_path: Local file to upload
            remote_key: S3 object key (will be prefixed if prefix configured)
            metadata: Optional metadata (stored as S3 tags)

        Returns:
            ArchiveMetadata with upload details
        """
        import hashlib
        from datetime import datetime, timezone

        from botocore.exceptions import ClientError

        # Validate source exists
        local_path = Path(local_path)
        if not local_path.exists():
            raise FileNotFoundError(f"Source file not found: {local_path}")

        # Calculate full S3 key
        full_key = self._full_key(remote_key)

        # Calculate checksum
        sha256_hash = hashlib.sha256()
        with open(local_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                sha256_hash.update(chunk)
        checksum = sha256_hash.hexdigest()

        # Upload to S3
        self.s3_client.upload_file(str(local_path), self.bucket, full_key)

        # Add tags if metadata provided
        if metadata:
            tag_set = [{"Key": k, "Value": str(v)} for k, v in metadata.items()]
            self.s3_client.put_object_tagging(
                Bucket=self.bucket, Key=full_key, Tagging={"TagSet": tag_set}
            )

        # Get object metadata
        response = self.s3_client.head_object(Bucket=self.bucket, Key=full_key)
        size_bytes = response["ContentLength"]
        timestamp = datetime.now(timezone.utc).isoformat()

        return ArchiveMetadata(
            key=full_key,
            filename=Path(remote_key).name,
            size_bytes=size_bytes,
            timestamp=timestamp,
            checksum_sha256=checksum,
            archive_type=metadata.get("archive_type") if metadata else None,
            repository_name=metadata.get("repository_name") if metadata else None,
            metadata=metadata,
        )

    def download_archive(self, remote_key: str, local_path: Path) -> None:
        """Download archive from S3.

        Args:
            remote_key: S3 object key (will be prefixed if prefix configured)
            local_path: Destination file path
        """
        from botocore.exceptions import ClientError

        full_key = self._full_key(remote_key)

        # Check if object exists
        try:
            self.s3_client.head_object(Bucket=self.bucket, Key=full_key)
        except ClientError as e:
            if e.response["Error"]["Code"] == "404":
                raise KeyError(f"Archive not found: {remote_key}")
            raise

        # Create parent directories
        local_path = Path(local_path)
        local_path.parent.mkdir(parents=True, exist_ok=True)

        # Download file
        self.s3_client.download_file(self.bucket, full_key, str(local_path))

    def list_archives(self, prefix: Optional[str] = None) -> List[ArchiveMetadata]:
        """List archives in S3 bucket.

        Args:
            prefix: Optional prefix filter (in addition to configured prefix)

        Returns:
            List of ArchiveMetadata objects
        """
        from datetime import datetime, timezone

        archives = []

        # Combine configured prefix with filter prefix
        list_prefix = self.prefix if self.prefix else ""
        if prefix:
            list_prefix = f"{list_prefix}{prefix}"

        # List objects
        paginator = self.s3_client.get_paginator("list_objects_v2")
        pages = paginator.paginate(Bucket=self.bucket, Prefix=list_prefix)

        for page in pages:
            if "Contents" not in page:
                continue

            for obj in page["Contents"]:
                key = obj["Key"]

                # Skip if not a .tar.gz file
                if not key.endswith(".tar.gz"):
                    continue

                # Get tags for metadata
                try:
                    tag_response = self.s3_client.get_object_tagging(Bucket=self.bucket, Key=key)
                    tags = {tag["Key"]: tag["Value"] for tag in tag_response["TagSet"]}
                    archive_type = tags.get("archive_type")
                    repository_name = tags.get("repository_name")
                    meta_dict = tags
                except Exception:
                    archive_type = None
                    repository_name = None
                    meta_dict = None

                # Create metadata object
                archives.append(
                    ArchiveMetadata(
                        key=key,
                        filename=Path(key).name,
                        size_bytes=obj["Size"],
                        timestamp=obj["LastModified"].astimezone(timezone.utc).isoformat(),
                        checksum_sha256=None,  # Not stored in object metadata by default
                        archive_type=archive_type,
                        repository_name=repository_name,
                        metadata=meta_dict,
                    )
                )

        return archives

    def delete_archive(self, remote_key: str) -> None:
        """Delete archive from S3.

        Args:
            remote_key: S3 object key (will be prefixed if prefix configured)
        """
        from botocore.exceptions import ClientError

        full_key = self._full_key(remote_key)

        # Check if object exists
        try:
            self.s3_client.head_object(Bucket=self.bucket, Key=full_key)
        except ClientError as e:
            if e.response["Error"]["Code"] == "404":
                raise KeyError(f"Archive not found: {remote_key}")
            raise

        # Delete object
        self.s3_client.delete_object(Bucket=self.bucket, Key=full_key)

    def archive_exists(self, remote_key: str) -> bool:
        """Check if archive exists in S3.

        Args:
            remote_key: S3 object key (will be prefixed if prefix configured)

        Returns:
            True if object exists, False otherwise
        """
        from botocore.exceptions import ClientError

        full_key = self._full_key(remote_key)

        try:
            self.s3_client.head_object(Bucket=self.bucket, Key=full_key)
            return True
        except ClientError as e:
            if e.response["Error"]["Code"] == "404":
                return False
            raise

    def get_archive_url(self, remote_key: str) -> Optional[str]:
        """Generate pre-signed URL for S3 object.

        Args:
            remote_key: S3 object key (will be prefixed if prefix configured)

        Returns:
            Pre-signed URL valid for 1 hour
        """
        full_key = self._full_key(remote_key)

        url = self.s3_client.generate_presigned_url(
            "get_object",
            Params={"Bucket": self.bucket, "Key": full_key},
            ExpiresIn=3600,  # 1 hour
        )
        return url


class AzureBlobBackend(StorageBackend):
    """Azure Blob Storage backend with region selection."""

    def __init__(
        self,
        container: str,
        account_name: str,
        region: str,
        connection_string: Optional[str] = None,
        account_key: Optional[str] = None,
    ):
        raise NotImplementedError("AzureBlobBackend to be implemented in Phase 2")

    def upload_archive(
        self, local_path: Path, remote_key: str, metadata: Optional[Dict[str, Any]] = None
    ) -> ArchiveMetadata:
        raise NotImplementedError()

    def download_archive(self, remote_key: str, local_path: Path) -> None:
        raise NotImplementedError()

    def list_archives(self, prefix: Optional[str] = None) -> List[ArchiveMetadata]:
        raise NotImplementedError()

    def delete_archive(self, remote_key: str) -> None:
        raise NotImplementedError()

    def archive_exists(self, remote_key: str) -> bool:
        raise NotImplementedError()


class GCSBackend(StorageBackend):
    """Google Cloud Storage backend with location selection."""

    def __init__(
        self,
        bucket: str,
        location: str,
        service_account_json: Optional[str] = None,
        project_id: Optional[str] = None,
    ):
        raise NotImplementedError("GCSBackend to be implemented in Phase 2")

    def upload_archive(
        self, local_path: Path, remote_key: str, metadata: Optional[Dict[str, Any]] = None
    ) -> ArchiveMetadata:
        raise NotImplementedError()

    def download_archive(self, remote_key: str, local_path: Path) -> None:
        raise NotImplementedError()

    def list_archives(self, prefix: Optional[str] = None) -> List[ArchiveMetadata]:
        raise NotImplementedError()

    def delete_archive(self, remote_key: str) -> None:
        raise NotImplementedError()

    def archive_exists(self, remote_key: str) -> bool:
        raise NotImplementedError()


class OCIBackend(StorageBackend):
    """Oracle Cloud Infrastructure Object Storage backend."""

    def __init__(
        self,
        bucket: str,
        namespace: str,
        region: str,
        config_file: Optional[str] = None,
    ):
        raise NotImplementedError("OCIBackend to be implemented in Phase 2")

    def upload_archive(
        self, local_path: Path, remote_key: str, metadata: Optional[Dict[str, Any]] = None
    ) -> ArchiveMetadata:
        raise NotImplementedError()

    def download_archive(self, remote_key: str, local_path: Path) -> None:
        raise NotImplementedError()

    def list_archives(self, prefix: Optional[str] = None) -> List[ArchiveMetadata]:
        raise NotImplementedError()

    def delete_archive(self, remote_key: str) -> None:
        raise NotImplementedError()

    def archive_exists(self, remote_key: str) -> bool:
        raise NotImplementedError()


class S3CompatibleBackend(StorageBackend):
    """S3-compatible storage backend (MinIO, Ceph, DigitalOcean, Wasabi, etc.)."""

    def __init__(
        self,
        bucket: str,
        endpoint_url: str,
        access_key: str,
        secret_key: str,
        region: Optional[str] = None,
    ):
        raise NotImplementedError("S3CompatibleBackend to be implemented in Phase 2")

    def upload_archive(
        self, local_path: Path, remote_key: str, metadata: Optional[Dict[str, Any]] = None
    ) -> ArchiveMetadata:
        raise NotImplementedError()

    def download_archive(self, remote_key: str, local_path: Path) -> None:
        raise NotImplementedError()

    def list_archives(self, prefix: Optional[str] = None) -> List[ArchiveMetadata]:
        raise NotImplementedError()

    def delete_archive(self, remote_key: str) -> None:
        raise NotImplementedError()

    def archive_exists(self, remote_key: str) -> bool:
        raise NotImplementedError()
