"""Git LFS handling for clone and sync operations."""

import os
import subprocess
from pathlib import Path
from typing import Any, Dict, List

import git


class LFSHandler:
    """Handle Git LFS operations for cloning and syncing repositories."""

    def __init__(self):
        """Initialize LFS handler."""
        pass

    def check_lfs_installed(self) -> bool:
        """
        Check if git-lfs is installed and available.

        Returns:
            True if git-lfs is installed, False otherwise
        """
        try:
            result = subprocess.run(
                ["git", "lfs", "version"],
                capture_output=True,
                text=True,
                check=False
            )
            return result.returncode == 0
        except FileNotFoundError:
            return False

    def clone_with_lfs(
        self,
        source_url: str,
        target_path: str,
        fetch_lfs: bool = True
    ) -> Dict[str, Any]:
        """
        Clone a repository with LFS support.

        Uses GIT_LFS_SKIP_SMUDGE=1 for faster initial clone,
        then optionally fetches LFS objects.

        Args:
            source_url: Repository URL to clone
            target_path: Local path for clone
            fetch_lfs: Whether to fetch LFS objects after clone (default True)

        Returns:
            Dictionary with clone results:
            - success: bool
            - lfs_objects_fetched: bool
        """
        # Clone with LFS skip smudge for faster clone
        env = os.environ.copy()
        env["GIT_LFS_SKIP_SMUDGE"] = "1"

        # Perform clone
        git.Repo.clone_from(
            source_url,
            target_path,
            env=env
        )

        lfs_fetched = False
        if fetch_lfs:
            # Fetch LFS objects after clone
            self.fetch_lfs_objects(target_path)
            lfs_fetched = True

        return {
            "success": True,
            "lfs_objects_fetched": lfs_fetched
        }

    def fetch_lfs_objects(self, repo_path: str) -> None:
        """
        Fetch LFS objects for a repository.

        Args:
            repo_path: Path to local repository
        """
        subprocess.run(
            ["git", "lfs", "pull"],
            cwd=repo_path,
            check=True,
            capture_output=True
        )

    def get_lfs_info(self, repo_path: str) -> Dict[str, Any]:
        """
        Get information about LFS objects in a repository.

        Args:
            repo_path: Path to local repository

        Returns:
            Dictionary with LFS information:
            - lfs_file_count: int
            - lfs_files: List[str]
        """
        result = subprocess.run(
            ["git", "lfs", "ls-files"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            check=False
        )

        if result.returncode != 0:
            return {
                "lfs_file_count": 0,
                "lfs_files": []
            }

        # Parse output: each line is like "abc123 * filename.ext"
        lfs_files: List[str] = []
        for line in result.stdout.splitlines():
            if line.strip():
                parts = line.split()
                if len(parts) >= 3:
                    filename = " ".join(parts[2:])  # Handle filenames with spaces
                    lfs_files.append(filename)

        return {
            "lfs_file_count": len(lfs_files),
            "lfs_files": lfs_files
        }
