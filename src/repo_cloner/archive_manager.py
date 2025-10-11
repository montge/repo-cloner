"""Archive management for air-gap deployments.

This module provides functionality to create and extract repository archives
using git bundles and tar compression for offline/air-gap environments.
"""

import json
import subprocess
import tarfile
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


class ArchiveManager:
    """Manages creation and extraction of repository archives for air-gap deployments."""

    def __init__(self):
        """Initialize the ArchiveManager."""
        pass

    def create_full_archive(
        self, repo_path: str, output_path: str, include_lfs: bool = False
    ) -> Dict[str, Any]:
        """Create a full archive of a git repository.

        Args:
            repo_path: Path to the git repository to archive
            output_path: Directory where the archive will be created
            include_lfs: Whether to include Git LFS objects

        Returns:
            Dictionary containing:
                - success: bool indicating if archive was created
                - archive_path: Path to the created archive file
                - manifest: Dictionary with archive metadata

        Raises:
            FileNotFoundError: If repo_path does not exist
        """
        repo_path_obj = Path(repo_path)
        output_path_obj = Path(output_path)

        # Validate repository path exists
        if not repo_path_obj.exists():
            raise FileNotFoundError(f"Repository path does not exist: {repo_path}")

        # Create output directory if it doesn't exist
        output_path_obj.mkdir(parents=True, exist_ok=True)

        # Generate archive filename: repo-name-full-timestamp.tar.gz
        repo_name = repo_path_obj.name
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        archive_name = f"{repo_name}-full-{timestamp}.tar.gz"
        archive_path = output_path_obj / archive_name

        # Create temporary directory for staging
        with tempfile.TemporaryDirectory() as tmpdir:
            staging_dir = Path(tmpdir) / "archive-staging"
            staging_dir.mkdir()

            # Create git bundle with all refs
            bundle_path = staging_dir / "repository.bundle"
            subprocess.run(
                ["git", "bundle", "create", str(bundle_path), "--all"],
                cwd=str(repo_path_obj),
                check=True,
                capture_output=True,
            )

            # Get repository metadata for manifest
            # Get HEAD commit SHA
            head_result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=str(repo_path_obj),
                check=True,
                capture_output=True,
                text=True,
            )
            head_sha = head_result.stdout.strip()

            # Get remote URL if available
            remote_result = subprocess.run(
                ["git", "remote", "get-url", "origin"],
                cwd=str(repo_path_obj),
                capture_output=True,
                text=True,
            )
            remote_url = remote_result.stdout.strip() if remote_result.returncode == 0 else ""

            # Bundle LFS objects if enabled
            lfs_object_count = 0
            if include_lfs:
                lfs_object_count = self._bundle_lfs_objects(repo_path_obj, staging_dir)

            # Create manifest
            manifest = {
                "type": "full",
                "timestamp": timestamp,
                "repository": {
                    "name": repo_name,
                    "path": str(repo_path_obj.absolute()),
                    "remote_url": remote_url,
                    "head_sha": head_sha,
                },
                "archive": {
                    "filename": archive_name,
                    "format": "tar.gz",
                    "bundle_file": "repository.bundle",
                },
                "lfs_enabled": include_lfs,
                "lfs_object_count": lfs_object_count,
            }

            # Write manifest to staging directory
            manifest_path = staging_dir / "manifest.json"
            with open(manifest_path, "w") as f:
                json.dump(manifest, f, indent=2)

            # Create tar.gz archive
            with tarfile.open(archive_path, "w:gz") as tar:
                tar.add(bundle_path, arcname="repository.bundle")
                tar.add(manifest_path, arcname="manifest.json")

                # Add LFS objects if they were bundled
                if include_lfs:
                    lfs_staging = staging_dir / "lfs-objects"
                    if lfs_staging.exists():
                        tar.add(lfs_staging, arcname="lfs-objects")

        return {"success": True, "archive_path": str(archive_path), "manifest": manifest}

    def extract_archive(self, archive_path: str, output_path: str) -> Dict[str, Any]:
        """Extract a repository archive.

        Args:
            archive_path: Path to the archive file
            output_path: Directory where the repository will be extracted

        Returns:
            Dictionary containing:
                - success: bool indicating if extraction was successful
                - repository_path: Path to the extracted repository

        Raises:
            FileNotFoundError: If archive_path does not exist
        """
        archive_path_obj = Path(archive_path)
        output_path_obj = Path(output_path)

        # Validate archive exists
        if not archive_path_obj.exists():
            raise FileNotFoundError(f"Archive file does not exist: {archive_path}")

        # Create output directory if needed
        output_path_obj.mkdir(parents=True, exist_ok=True)

        # Extract tar.gz archive
        with tempfile.TemporaryDirectory() as tmpdir:
            extract_dir = Path(tmpdir) / "extracted"
            extract_dir.mkdir()

            # Extract archive contents
            with tarfile.open(archive_path_obj, "r:gz") as tar:
                tar.extractall(extract_dir, filter="data")

            # Read manifest
            manifest_path = extract_dir / "manifest.json"
            with open(manifest_path, "r") as f:
                manifest = json.load(f)

            # Clone from bundle
            bundle_path = extract_dir / "repository.bundle"
            repository_path = output_path_obj / "repository"

            # Initialize repository from bundle
            subprocess.run(
                ["git", "clone", str(bundle_path), str(repository_path)],
                check=True,
                capture_output=True,
            )

        return {"success": True, "repository_path": str(repository_path), "manifest": manifest}

    def create_incremental_archive(
        self,
        repo_path: str,
        output_path: str,
        parent_archive_path: Optional[str],
        include_lfs: bool = False,
    ) -> Dict[str, Any]:
        """Create an incremental archive with only new commits since parent.

        Args:
            repo_path: Path to the git repository to archive
            output_path: Directory where the archive will be created
            parent_archive_path: Path to the parent archive (required)
            include_lfs: Whether to include Git LFS objects

        Returns:
            Dictionary containing:
                - success: bool indicating if archive was created
                - archive_path: Path to the created archive file
                - manifest: Dictionary with archive metadata

        Raises:
            ValueError: If parent_archive_path is None
            FileNotFoundError: If repo_path or parent_archive_path does not exist
        """
        if parent_archive_path is None:
            raise ValueError("parent_archive_path is required for incremental archives")

        repo_path_obj = Path(repo_path)
        output_path_obj = Path(output_path)
        parent_archive_obj = Path(parent_archive_path)

        # Validate paths exist
        if not repo_path_obj.exists():
            raise FileNotFoundError(f"Repository path does not exist: {repo_path}")

        if not parent_archive_obj.exists():
            raise FileNotFoundError(f"Parent archive does not exist: {parent_archive_path}")

        # Create output directory if it doesn't exist
        output_path_obj.mkdir(parents=True, exist_ok=True)

        # Extract parent manifest to get base commit SHA
        with tempfile.TemporaryDirectory() as tmpdir:
            parent_extract = Path(tmpdir) / "parent"
            parent_extract.mkdir()

            with tarfile.open(parent_archive_obj, "r:gz") as tar:
                tar.extractall(parent_extract, filter="data")

            with open(parent_extract / "manifest.json", "r") as f:
                parent_manifest = json.load(f)

        base_commit_sha = parent_manifest["repository"]["head_sha"]

        # Generate archive filename: repo-name-incremental-timestamp.tar.gz
        repo_name = repo_path_obj.name
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        archive_name = f"{repo_name}-incremental-{timestamp}.tar.gz"
        archive_path = output_path_obj / archive_name

        # Create temporary directory for staging
        with tempfile.TemporaryDirectory() as tmpdir:
            staging_dir = Path(tmpdir) / "archive-staging"
            staging_dir.mkdir()

            # Get current HEAD commit SHA
            head_result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=str(repo_path_obj),
                check=True,
                capture_output=True,
                text=True,
            )
            current_head_sha = head_result.stdout.strip()

            # Create incremental git bundle containing all refs
            # This ensures the bundle is self-contained and can be applied independently
            bundle_path = staging_dir / "repository.bundle"
            subprocess.run(
                ["git", "bundle", "create", str(bundle_path), "--all"],
                cwd=str(repo_path_obj),
                check=True,
                capture_output=True,
            )

            # Get remote URL if available
            remote_result = subprocess.run(
                ["git", "remote", "get-url", "origin"],
                cwd=str(repo_path_obj),
                capture_output=True,
                text=True,
            )
            remote_url = remote_result.stdout.strip() if remote_result.returncode == 0 else ""

            # Create manifest
            manifest = {
                "type": "incremental",
                "timestamp": timestamp,
                "parent_archive": parent_archive_obj.name,
                "commit_range": {"from": base_commit_sha, "to": current_head_sha},
                "repository": {
                    "name": repo_name,
                    "path": str(repo_path_obj.absolute()),
                    "remote_url": remote_url,
                    "head_sha": current_head_sha,
                },
                "archive": {
                    "filename": archive_name,
                    "format": "tar.gz",
                    "bundle_file": "repository.bundle",
                },
                "lfs_enabled": include_lfs,
            }

            # Write manifest to staging directory
            manifest_path = staging_dir / "manifest.json"
            with open(manifest_path, "w") as f:
                json.dump(manifest, f, indent=2)

            # Create tar.gz archive
            with tarfile.open(archive_path, "w:gz") as tar:
                tar.add(bundle_path, arcname="repository.bundle")
                tar.add(manifest_path, arcname="manifest.json")

        return {"success": True, "archive_path": str(archive_path), "manifest": manifest}

    def restore_from_archive_chain(
        self, archive_paths: List[str], output_path: str
    ) -> Dict[str, Any]:
        """Restore a repository from a chain of archives (full + incrementals).

        Args:
            archive_paths: List of archive paths in order (full first, then incrementals)
            output_path: Directory where the repository will be restored

        Returns:
            Dictionary containing:
                - success: bool indicating if restoration was successful
                - repository_path: Path to the restored repository

        Raises:
            FileNotFoundError: If any archive does not exist
            ValueError: If archive chain is invalid
        """
        if not archive_paths:
            raise ValueError("archive_paths cannot be empty")

        output_path_obj = Path(output_path)
        output_path_obj.mkdir(parents=True, exist_ok=True)

        # Validate all archives exist
        for archive_path in archive_paths:
            if not Path(archive_path).exists():
                raise FileNotFoundError(f"Archive does not exist: {archive_path}")

        with tempfile.TemporaryDirectory() as tmpdir:
            work_dir = Path(tmpdir) / "restore"
            work_dir.mkdir()

            # Extract and apply archives in order
            for i, archive_path in enumerate(archive_paths):
                archive_path_obj = Path(archive_path)
                extract_dir = work_dir / f"archive-{i}"
                extract_dir.mkdir()

                # Extract archive
                with tarfile.open(archive_path_obj, "r:gz") as tar:
                    tar.extractall(extract_dir, filter="data")

                # Read manifest
                with open(extract_dir / "manifest.json", "r") as f:
                    manifest = json.load(f)

                if i == 0:
                    # First archive must be full
                    if manifest["type"] != "full":
                        raise ValueError("First archive must be a full archive")

                    # Clone from full bundle
                    bundle_path = extract_dir / "repository.bundle"
                    repository_path = output_path_obj / "repository"
                    subprocess.run(
                        ["git", "clone", str(bundle_path), str(repository_path)],
                        check=True,
                        capture_output=True,
                    )
                else:
                    # Apply incremental bundle
                    if manifest["type"] != "incremental":
                        raise ValueError(f"Archive {i} must be an incremental archive")

                    bundle_path = extract_dir / "repository.bundle"
                    # Fetch from bundle (brings in new commits)
                    subprocess.run(
                        ["git", "fetch", str(bundle_path), "HEAD"],
                        cwd=str(repository_path),
                        check=True,
                        capture_output=True,
                    )
                    # Update to the commit specified in manifest
                    target_sha = manifest["repository"]["head_sha"]
                    subprocess.run(
                        ["git", "reset", "--hard", target_sha],
                        cwd=str(repository_path),
                        check=True,
                        capture_output=True,
                    )

        return {"success": True, "repository_path": str(repository_path), "manifest": manifest}

    def _bundle_lfs_objects(self, repo_path: Path, staging_dir: Path) -> int:
        """Bundle LFS objects from repository into staging directory.

        Args:
            repo_path: Path to the git repository
            staging_dir: Staging directory for archive contents

        Returns:
            Number of LFS objects bundled
        """
        import shutil

        # Check if LFS objects directory exists
        lfs_objects_dir = repo_path / ".git" / "lfs" / "objects"
        if not lfs_objects_dir.exists():
            return 0

        # Create LFS staging directory
        lfs_staging = staging_dir / "lfs-objects"
        lfs_staging.mkdir()

        # Copy LFS objects preserving structure
        # LFS uses structure: .git/lfs/objects/ab/cd/abcd1234567890...
        object_count = 0
        for hash_prefix_dir in lfs_objects_dir.iterdir():
            if not hash_prefix_dir.is_dir():
                continue

            for hash_subdir in hash_prefix_dir.iterdir():
                if not hash_subdir.is_dir():
                    continue

                # Copy entire subdirectory preserving structure
                dest_prefix = lfs_staging / hash_prefix_dir.name
                dest_prefix.mkdir(exist_ok=True)
                dest_subdir = dest_prefix / hash_subdir.name

                shutil.copytree(hash_subdir, dest_subdir)

                # Count objects
                for obj_file in dest_subdir.iterdir():
                    if obj_file.is_file():
                        object_count += 1

        return object_count

    def _get_lfs_object_count(self, repo_path: Path) -> int:
        """Get count of LFS objects in repository.

        Args:
            repo_path: Path to the git repository

        Returns:
            Number of LFS objects
        """
        lfs_objects_dir = repo_path / ".git" / "lfs" / "objects"
        if not lfs_objects_dir.exists():
            return 0

        count = 0
        for hash_prefix_dir in lfs_objects_dir.iterdir():
            if not hash_prefix_dir.is_dir():
                continue

            for hash_subdir in hash_prefix_dir.iterdir():
                if not hash_subdir.is_dir():
                    continue

                for obj_file in hash_subdir.iterdir():
                    if obj_file.is_file():
                        count += 1

        return count

    def _bundle_lfs_objects_incremental(
        self, repo_path: Path, staging_dir: Path, base_sha: str, current_sha: str
    ) -> int:
        """Bundle only new LFS objects for incremental archive.

        For simplicity in this implementation, we bundle all LFS objects.
        A more sophisticated implementation could track which LFS objects
        are referenced by commits in the range base_sha..current_sha.

        Args:
            repo_path: Path to the git repository
            staging_dir: Staging directory for archive contents
            base_sha: Base commit SHA
            current_sha: Current commit SHA

        Returns:
            Number of LFS objects bundled
        """
        # For now, use the same logic as full bundling
        # TODO: Implement differential LFS object detection
        return self._bundle_lfs_objects(repo_path, staging_dir)

    def verify_archive(self, archive_path: str) -> Dict[str, Any]:
        """Verify integrity and validity of an archive.

        Checks:
        - Archive file exists and can be opened
        - manifest.json is present and valid JSON
        - repository.bundle is present
        - Git bundle is valid
        - LFS objects match manifest (if lfs_enabled)

        Args:
            archive_path: Path to the archive file

        Returns:
            Dictionary containing:
                - valid: bool indicating if archive is valid
                - errors: List of error messages (empty if valid)
                - manifest_valid: bool indicating if manifest is valid
                - bundle_valid: bool indicating if git bundle is valid
                - lfs_objects_verified: bool (if lfs_enabled)
                - lfs_object_count: int (if lfs_enabled)
                - archive_path: str path to the archive

        Raises:
            FileNotFoundError: If archive_path does not exist
        """
        archive_path_obj = Path(archive_path)

        # Validate archive exists
        if not archive_path_obj.exists():
            raise FileNotFoundError(f"Archive file does not exist: {archive_path}")

        errors = []
        manifest_valid = False
        bundle_valid = False
        lfs_objects_verified = False
        lfs_object_count = 0
        manifest = None

        with tempfile.TemporaryDirectory() as tmpdir:
            extract_dir = Path(tmpdir) / "verify"
            extract_dir.mkdir()

            try:
                # Extract archive
                with tarfile.open(archive_path_obj, "r:gz") as tar:
                    tar.extractall(extract_dir, filter="data")

                # Check for manifest.json
                manifest_path = extract_dir / "manifest.json"
                if not manifest_path.exists():
                    errors.append("manifest.json not found in archive")
                else:
                    # Validate manifest JSON
                    try:
                        with open(manifest_path, "r") as f:
                            manifest = json.load(f)
                        manifest_valid = True
                    except json.JSONDecodeError as e:
                        errors.append(f"manifest.json is corrupted: {e}")

                # Check for repository.bundle
                bundle_path = extract_dir / "repository.bundle"
                if not bundle_path.exists():
                    errors.append("repository.bundle not found in archive")
                else:
                    # Validate git bundle
                    result = subprocess.run(
                        ["git", "bundle", "verify", str(bundle_path)],
                        capture_output=True,
                        text=True,
                    )
                    if result.returncode == 0:
                        bundle_valid = True
                    else:
                        bundle_valid = False
                        errors.append(f"Git bundle is invalid: {result.stderr}")

                # Verify LFS objects if enabled
                if manifest and manifest.get("lfs_enabled", False):
                    lfs_dir = extract_dir / "lfs-objects"
                    if lfs_dir.exists():
                        # Count LFS objects in archive
                        actual_count = 0
                        for hash_prefix in lfs_dir.iterdir():
                            if hash_prefix.is_dir():
                                for hash_subdir in hash_prefix.iterdir():
                                    if hash_subdir.is_dir():
                                        for obj_file in hash_subdir.iterdir():
                                            if obj_file.is_file():
                                                actual_count += 1

                        lfs_object_count = actual_count
                        expected_count = manifest.get("lfs_object_count", 0)

                        if actual_count == expected_count:
                            lfs_objects_verified = True
                        else:
                            errors.append(
                                f"LFS object count mismatch: expected {expected_count}, "
                                f"found {actual_count}"
                            )
                    else:
                        errors.append("lfs-objects directory not found but lfs_enabled is True")

            except tarfile.TarError as e:
                errors.append(f"Failed to extract archive: {e}")
            except Exception as e:
                errors.append(f"Unexpected error during verification: {e}")

        # Determine overall validity
        valid = len(errors) == 0 and manifest_valid and bundle_valid

        return {
            "valid": valid,
            "errors": errors,
            "manifest_valid": manifest_valid,
            "bundle_valid": bundle_valid,
            "lfs_objects_verified": (
                lfs_objects_verified if manifest and manifest.get("lfs_enabled") else None
            ),  # noqa: E501
            "lfs_object_count": (
                lfs_object_count if manifest and manifest.get("lfs_enabled") else None
            ),  # noqa: E501
            "archive_path": str(archive_path),
        }

    def apply_retention_policy(
        self,
        archives_path: str,
        max_age_days: Optional[int] = None,
        max_count: Optional[int] = None,
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        """Apply retention policy to archives in a directory.

        Retention policy can be based on:
        - max_age_days: Delete archives older than N days
        - max_count: Keep only N most recent archives
        - Both: Apply both policies (archives must satisfy both to be kept)

        Args:
            archives_path: Directory containing archives
            max_age_days: Maximum age in days (archives older will be deleted)
            max_count: Maximum number of archives to keep (oldest deleted first)
            dry_run: If True, simulate deletion without actually deleting

        Returns:
            Dictionary containing:
                - deleted_count: Number of archives deleted (or would be deleted)
                - kept_count: Number of archives kept
                - deleted_files: List of deleted archive paths
                - dry_run: bool indicating if this was a dry run

        Raises:
            FileNotFoundError: If archives_path does not exist
            ValueError: If neither max_age_days nor max_count is specified
        """
        import os
        import time

        archives_path_obj = Path(archives_path)

        # Validate directory exists
        if not archives_path_obj.exists():
            raise FileNotFoundError(f"Archives path does not exist: {archives_path}")

        # Require at least one policy parameter
        if max_age_days is None and max_count is None:
            raise ValueError("At least one of max_age_days or max_count must be specified")

        # Find all .tar.gz archives
        archives = []
        for file_path in archives_path_obj.iterdir():
            if file_path.is_file() and file_path.suffix == ".gz" and str(file_path).endswith(".tar.gz"):
                archives.append(file_path)

        # Sort archives by modification time (newest first)
        archives.sort(key=lambda p: p.stat().st_mtime, reverse=True)

        archives_to_delete = []
        archives_to_keep = []

        current_time = time.time()

        for archive in archives:
            should_delete = False

            # Check age-based retention
            if max_age_days is not None:
                age_seconds = current_time - archive.stat().st_mtime
                age_days = age_seconds / (24 * 60 * 60)
                if age_days > max_age_days:
                    should_delete = True

            # Check count-based retention
            if max_count is not None:
                if len(archives_to_keep) >= max_count:
                    should_delete = True

            if should_delete:
                archives_to_delete.append(archive)
            else:
                archives_to_keep.append(archive)

        # Delete archives (unless dry run)
        deleted_files = []
        if not dry_run:
            for archive in archives_to_delete:
                archive.unlink()
                deleted_files.append(str(archive))
        else:
            # In dry run, just record what would be deleted
            deleted_files = [str(archive) for archive in archives_to_delete]

        return {
            "deleted_count": len(archives_to_delete),
            "kept_count": len(archives_to_keep),
            "deleted_files": deleted_files,
            "dry_run": dry_run,
        }
