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
from typing import Any, Dict


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
