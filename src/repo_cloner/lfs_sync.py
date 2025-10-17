"""Git LFS sync operations for incremental updates."""

import os
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional


class LFSSync:
    """Handle Git LFS sync and incremental update operations."""

    def __init__(self):
        """Initialize LFS sync handler."""
        pass

    def sync_lfs_objects(
        self, repo_path: str, recent: bool = False, include_patterns: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Sync LFS objects for a repository, optionally fetching only recent changes.

        Args:
            repo_path: Path to local repository
            recent: If True, only fetch recent objects (last 7 days)
            include_patterns: Optional list of patterns to include (e.g., ["*.psd"])

        Returns:
            Dictionary with sync results:
            - success: bool
            - objects_fetched: int
        """
        cmd = ["git", "lfs", "fetch"]

        if recent:
            cmd.append("--recent")

        if include_patterns:
            for pattern in include_patterns:
                cmd.extend(["--include", pattern])

        # Disable LFS lock verification as not all platforms support the locking API
        env = os.environ.copy()
        env["GIT_LFS_SKIP_VERIFY"] = "1"

        result = subprocess.run(
            cmd, cwd=repo_path, capture_output=True, text=True, check=False, env=env
        )

        # Count objects fetched from output
        objects_fetched = 0
        if result.returncode == 0:
            # Count lines with "Downloading" in output
            for line in result.stdout.splitlines():
                if "Downloading" in line:
                    objects_fetched += 1

        return {"success": result.returncode == 0, "objects_fetched": objects_fetched}

    def prune_lfs_objects(self, repo_path: str) -> Dict[str, Any]:
        """
        Prune unreferenced LFS objects from local storage.

        Args:
            repo_path: Path to local repository

        Returns:
            Dictionary with prune results:
            - success: bool
        """
        # Disable LFS lock verification as not all platforms support the locking API
        env = os.environ.copy()
        env["GIT_LFS_SKIP_VERIFY"] = "1"

        result = subprocess.run(
            ["git", "lfs", "prune"], cwd=repo_path, capture_output=True, check=False, env=env
        )

        return {"success": result.returncode == 0}

    def detect_lfs_changes(
        self, old_lfs_files: List[str], new_lfs_files: List[str]
    ) -> Dict[str, List[str]]:
        """
        Detect changes between two sets of LFS files.

        Args:
            old_lfs_files: List of LFS files in old state
            new_lfs_files: List of LFS files in new state

        Returns:
            Dictionary with:
            - added: Files added
            - removed: Files removed
            - unchanged: Files that remain
        """
        old_set = set(old_lfs_files)
        new_set = set(new_lfs_files)

        added = sorted(list(new_set - old_set))
        removed = sorted(list(old_set - new_set))
        unchanged = sorted(list(old_set & new_set))

        return {"added": added, "removed": removed, "unchanged": unchanged}

    def checkout_lfs_objects(self, repo_path: str) -> Dict[str, Any]:
        """
        Check out LFS objects to working tree (replace pointers with actual files).

        Args:
            repo_path: Path to local repository

        Returns:
            Dictionary with checkout results:
            - success: bool
        """
        # Disable LFS lock verification as not all platforms support the locking API
        env = os.environ.copy()
        env["GIT_LFS_SKIP_VERIFY"] = "1"

        result = subprocess.run(
            ["git", "lfs", "checkout"], cwd=repo_path, capture_output=True, check=False, env=env
        )

        return {"success": result.returncode == 0}

    def get_lfs_storage_size(self, repo_path: str) -> int:
        """
        Get total size of LFS storage in bytes.

        Args:
            repo_path: Path to local repository

        Returns:
            Size in bytes
        """
        lfs_path = Path(repo_path) / ".git" / "lfs"

        result = subprocess.run(
            ["du", "-s", str(lfs_path)], capture_output=True, text=True, check=False
        )

        if result.returncode == 0:
            # Parse output: "524288\t.git/lfs"
            size_str = result.stdout.split("\t")[0].strip()
            return int(size_str)

        return 0
