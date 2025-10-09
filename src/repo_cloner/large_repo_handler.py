"""Performance optimizations for large Git repositories."""

import re
import subprocess
from pathlib import Path
from typing import Any, Dict, Optional

import git


class LargeRepoHandler:
    """Handle cloning and optimization of large Git repositories."""

    def __init__(self):
        """Initialize large repository handler."""
        pass

    def shallow_clone(
        self,
        source_url: str,
        target_path: str,
        depth: int = 1,
        single_branch: bool = False,
        branch: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Perform shallow clone with limited history depth.

        Args:
            source_url: Repository URL to clone
            target_path: Local path for clone
            depth: Number of commits to fetch (default 1)
            single_branch: Only clone one branch (default False)
            branch: Specific branch to clone (default None)

        Returns:
            Dictionary with clone results:
            - success: bool
        """
        kwargs: Dict[str, Any] = {"depth": depth}

        if single_branch:
            kwargs["single_branch"] = True

        if branch:
            kwargs["branch"] = branch

        git.Repo.clone_from(source_url, target_path, **kwargs)  # type: ignore[arg-type]

        return {"success": True}

    def unshallow(self, repo_path: str) -> Dict[str, Any]:
        """
        Convert shallow clone to full clone by fetching complete history.

        Args:
            repo_path: Path to local repository

        Returns:
            Dictionary with unshallow results:
            - success: bool
        """
        result = subprocess.run(
            ["git", "fetch", "--unshallow"], cwd=repo_path, capture_output=True, check=False
        )

        return {"success": result.returncode == 0}

    def partial_clone(
        self, source_url: str, target_path: str, filter_spec: str = "blob:none"
    ) -> Dict[str, Any]:
        """
        Perform partial clone that skips certain objects initially.

        Requires Git 2.19+. Common filter specs:
        - blob:none - Skip all blobs
        - blob:limit=1m - Skip blobs larger than 1MB
        - tree:0 - Skip trees

        Args:
            source_url: Repository URL to clone
            target_path: Local path for clone
            filter_spec: Git partial clone filter specification

        Returns:
            Dictionary with clone results:
            - success: bool
        """
        result = subprocess.run(
            ["git", "clone", f"--filter={filter_spec}", source_url, target_path],
            capture_output=True,
            check=False,
        )

        return {"success": result.returncode == 0}

    def get_repo_size(self, repo_path: str) -> Dict[str, Any]:
        """
        Get repository disk usage.

        Args:
            repo_path: Path to local repository

        Returns:
            Dictionary with size information:
            - total_size_bytes: int
            - total_size_mb: float
        """
        git_dir = Path(repo_path) / ".git"

        result = subprocess.run(
            ["du", "-s", str(git_dir)], capture_output=True, text=True, check=False
        )

        if result.returncode == 0:
            # Parse output: "524288\t.git"
            size_kb = int(result.stdout.split("\t")[0].strip())
            size_bytes = size_kb * 1024
            size_mb = size_bytes / (1024 * 1024)

            return {"total_size_bytes": size_bytes, "total_size_mb": round(size_mb, 2)}

        return {"total_size_bytes": 0, "total_size_mb": 0.0}

    def estimate_clone_time(self, repo_size_mb: int, network_speed_mbps: float) -> Dict[str, Any]:
        """
        Estimate clone time based on repo size and network speed.

        Args:
            repo_size_mb: Repository size in megabytes
            network_speed_mbps: Network speed in MB/s

        Returns:
            Dictionary with time estimates:
            - estimated_seconds: float
            - estimated_minutes: float
            - estimated_human_readable: str
        """
        estimated_seconds = repo_size_mb / network_speed_mbps
        estimated_minutes = estimated_seconds / 60

        # Format human readable
        if estimated_minutes < 1:
            human_readable = f"{int(estimated_seconds)}s"
        elif estimated_minutes < 60:
            human_readable = f"{int(estimated_minutes)}m"
        else:
            hours = int(estimated_minutes / 60)
            mins = int(estimated_minutes % 60)
            human_readable = f"{hours}h {mins}m"

        return {
            "estimated_seconds": estimated_seconds,
            "estimated_minutes": estimated_minutes,
            "estimated_human_readable": human_readable,
        }

    def optimize_for_bandwidth(self, repo_path: str) -> Dict[str, Any]:
        """
        Configure Git for maximum compression to save bandwidth.

        Args:
            repo_path: Path to local repository

        Returns:
            Dictionary with optimization results:
            - success: bool
        """
        repo = git.Repo(repo_path)

        with repo.config_writer() as config:
            # Maximum compression level
            config.set_value("core", "compression", "9")
            config.set_value("pack", "compression", "9")

        return {"success": True}

    def check_partial_clone_support(self) -> Dict[str, Any]:
        """
        Check if Git version supports partial clone (requires 2.19+).

        Returns:
            Dictionary with support information:
            - supported: bool
            - version: str
        """
        result = subprocess.run(["git", "--version"], capture_output=True, text=True, check=False)

        if result.returncode == 0:
            # Parse: "git version 2.30.0"
            version_match = re.search(r"git version (\d+\.\d+\.\d+)", result.stdout)
            if version_match:
                version = version_match.group(1)
                major, minor, _ = version.split(".")

                # Partial clone support added in Git 2.19
                supported = int(major) > 2 or (int(major) == 2 and int(minor) >= 19)

                return {"supported": supported, "version": version}

        return {"supported": False, "version": "unknown"}

    def deepen(self, repo_path: str, depth: int) -> Dict[str, Any]:
        """
        Deepen a shallow clone by fetching more history.

        Args:
            repo_path: Path to local repository
            depth: Number of commits to fetch from each branch tip

        Returns:
            Dictionary with deepen results:
            - success: bool
        """
        result = subprocess.run(
            ["git", "fetch", f"--depth={depth}"], cwd=repo_path, capture_output=True, check=False
        )

        return {"success": result.returncode == 0}
