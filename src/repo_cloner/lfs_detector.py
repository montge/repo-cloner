"""LFS detection for Git repositories."""

import re
from pathlib import Path
from typing import List


class LFSDetector:
    """Detect Git LFS usage in repositories."""

    def __init__(self):
        """Initialize LFS detector."""
        self.lfs_pattern = re.compile(r"filter=lfs")

    def is_lfs_enabled(self, repo_path: str) -> bool:
        """
        Check if a repository has Git LFS enabled.

        Args:
            repo_path: Path to repository root

        Returns:
            True if LFS is detected, False otherwise
        """
        gitattributes_path = Path(repo_path) / ".gitattributes"

        if not gitattributes_path.exists():
            return False

        content = gitattributes_path.read_text()
        return self.lfs_pattern.search(content) is not None

    def get_lfs_patterns(self, repo_path: str) -> List[str]:
        """
        Extract LFS file patterns from .gitattributes.

        Args:
            repo_path: Path to repository root

        Returns:
            List of file patterns tracked by LFS (e.g., ["*.psd", "*.zip"])
        """
        gitattributes_path = Path(repo_path) / ".gitattributes"

        if not gitattributes_path.exists():
            return []

        patterns = []
        content = gitattributes_path.read_text()

        # Parse .gitattributes for LFS patterns
        # Format: <pattern> filter=lfs diff=lfs merge=lfs -text
        for line in content.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue

            if "filter=lfs" in line:
                # Extract the pattern (first word before filter=lfs)
                parts = line.split()
                if parts:
                    pattern = parts[0]
                    patterns.append(pattern)

        return patterns
