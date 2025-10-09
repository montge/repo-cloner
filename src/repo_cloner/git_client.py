"""Git client for repository cloning and synchronization operations."""
from dataclasses import dataclass
from pathlib import Path
from typing import Optional
import git


@dataclass
class CloneResult:
    """Result of a clone operation."""

    success: bool
    local_path: str
    branches_count: int
    error_message: str = ""
    dry_run: bool = False
    message: str = ""


@dataclass
class PushResult:
    """Result of a push operation."""

    success: bool
    target_url: str
    error_message: str = ""
    dry_run: bool = False
    message: str = ""


class GitClient:
    """Client for Git operations using GitPython."""

    def clone_mirror(
        self, source_url: str, local_path: str, dry_run: bool = False
    ) -> CloneResult:
        """
        Clone a Git repository as a mirror (all refs, branches, tags).

        Args:
            source_url: URL of the source repository
            local_path: Local path for the cloned repository
            dry_run: If True, log operation without executing

        Returns:
            CloneResult with success status and metadata
        """
        if dry_run:
            return CloneResult(
                success=True,
                local_path=local_path,
                branches_count=0,
                dry_run=True,
                message=f"DRY-RUN: Would clone {source_url} to {local_path} with mirror=True",
            )

        try:
            # Create parent directory if needed
            Path(local_path).parent.mkdir(parents=True, exist_ok=True)

            # Clone repository with mirror flag
            repo = git.Repo.clone_from(source_url, local_path, mirror=True)

            # Count branches
            branches = list(repo.branches)

            return CloneResult(
                success=True, local_path=local_path, branches_count=len(branches)
            )
        except Exception as e:
            return CloneResult(
                success=False,
                local_path=local_path,
                branches_count=0,
                error_message=str(e),
            )

    def push_mirror(
        self, local_path: str, target_url: str, dry_run: bool = False
    ) -> PushResult:
        """
        Push a Git repository as a mirror (all refs, branches, tags) to target.

        Args:
            local_path: Local path of the repository to push
            target_url: URL of the target repository
            dry_run: If True, log operation without executing

        Returns:
            PushResult with success status and metadata
        """
        if dry_run:
            return PushResult(
                success=True,
                target_url=target_url,
                dry_run=True,
                message=f"DRY-RUN: Would push {local_path} to {target_url} with mirror=True",
            )

        try:
            # Open existing repository
            repo = git.Repo(local_path)

            # Create temporary remote
            remote = repo.create_remote("target", target_url)

            # Push with mirror flag (all refs)
            remote.push(mirror=True)

            # Clean up temporary remote
            repo.delete_remote("target")

            return PushResult(success=True, target_url=target_url)
        except Exception as e:
            return PushResult(
                success=False, target_url=target_url, error_message=str(e)
            )
