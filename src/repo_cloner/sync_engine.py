"""Synchronization engine for repository mirroring and updates."""

import tempfile
from pathlib import Path
from typing import Dict, List, Optional

import git


class SyncEngine:
    """Engine for synchronizing repositories with change detection."""

    def __init__(self):
        """Initialize SyncEngine."""
        pass

    def sync_repository(
        self,
        source_url: str,
        target_url: str,
        direction: str = "source_to_target",
        strategy: str = "mirror",
    ) -> Dict:
        """
        Synchronize repository from source to target.

        Args:
            source_url: Source repository URL or path
            target_url: Target repository URL or path
            direction: Sync direction (source_to_target, target_to_source, bidirectional)
            strategy: Sync strategy (mirror, incremental)

        Returns:
            Dictionary with sync results:
            - success: bool
            - direction: str
            - commits_synced: int
            - branches_synced: int
        """
        if direction == "source_to_target":
            return self._sync_unidirectional(source_url, target_url, strategy)
        elif direction == "target_to_source":
            return self._sync_unidirectional(target_url, source_url, strategy)
        elif direction == "bidirectional":
            # For now, simplified bidirectional (will add conflict detection later)
            result1 = self._sync_unidirectional(source_url, target_url, strategy)
            result2 = self._sync_unidirectional(target_url, source_url, strategy)
            return {
                "success": result1["success"] and result2["success"],
                "direction": "bidirectional",
                "commits_synced": result1["commits_synced"] + result2["commits_synced"],
                "branches_synced": result1["branches_synced"] + result2["branches_synced"],
            }
        else:
            raise ValueError(f"Unknown direction: {direction}")

    def _sync_unidirectional(self, source_url: str, target_url: str, strategy: str) -> Dict:
        """
        Perform unidirectional sync from source to target.

        Args:
            source_url: Source repository
            target_url: Target repository
            strategy: mirror or incremental

        Returns:
            Sync result dictionary
        """
        # Clone source to temp directory
        with tempfile.TemporaryDirectory() as tmpdir:
            local_path = Path(tmpdir) / "repo"
            repo = git.Repo.clone_from(source_url, local_path, mirror=True)

            # Push to target
            if strategy == "mirror":
                # Mirror push (all refs)
                try:
                    remote = repo.create_remote("target", target_url)
                    remote.push(mirror=True)
                    repo.delete_remote(remote)

                    # Count commits and branches
                    commits_count = sum(1 for _ in repo.iter_commits("--all"))
                    branches_count = len(list(repo.heads))

                    return {
                        "success": True,
                        "direction": "source_to_target",
                        "commits_synced": commits_count,
                        "branches_synced": branches_count,
                    }
                except Exception as e:
                    return {
                        "success": False,
                        "direction": "source_to_target",
                        "commits_synced": 0,
                        "branches_synced": 0,
                        "error": str(e),
                    }
            else:
                # Incremental strategy (for future implementation)
                raise NotImplementedError("Incremental strategy not yet implemented")

    def detect_changes(self, repo_path: str, previous_state: Dict) -> Dict:
        """
        Detect changes in repository since previous state.

        Args:
            repo_path: Path to local repository
            previous_state: Previous sync state with last_commit SHA and branches

        Returns:
            Dictionary with change detection results:
            - has_new_commits: bool
            - new_commit_count: int
            - old_commits: list of previous commit SHAs
            - new_commits: list of new commit SHAs
            - has_new_branches: bool
            - new_branches: list of new branch names
            - new_branch_count: int
            - has_deleted_branches: bool
            - deleted_branches: list of deleted branch names
            - deleted_branch_count: int
        """
        repo = git.Repo(repo_path)

        # Detect commit changes
        current_sha = repo.head.commit.hexsha
        previous_sha = previous_state.get("last_commit")

        result = {}

        if not previous_sha:
            # First sync, no previous state
            result.update({
                "has_new_commits": True,
                "new_commit_count": 1,
                "old_commits": [],
                "new_commits": [current_sha],
            })
        elif current_sha == previous_sha:
            # No commit changes
            result.update({
                "has_new_commits": False,
                "new_commit_count": 0,
                "old_commits": [previous_sha],
                "new_commits": [],
            })
        else:
            # Find commits between previous and current
            commits = list(repo.iter_commits(f"{previous_sha}..{current_sha}"))
            new_commit_shas = [commit.hexsha for commit in commits]

            result.update({
                "has_new_commits": True,
                "new_commit_count": len(new_commit_shas),
                "old_commits": [previous_sha],
                "new_commits": new_commit_shas,
            })

        # Detect branch changes
        current_branches = set(ref.name for ref in repo.heads)
        previous_branches = set(previous_state.get("branches", []))

        new_branches = current_branches - previous_branches
        deleted_branches = previous_branches - current_branches

        result.update({
            "has_new_branches": len(new_branches) > 0,
            "new_branches": list(new_branches),
            "new_branch_count": len(new_branches),
            "has_deleted_branches": len(deleted_branches) > 0,
            "deleted_branches": list(deleted_branches),
            "deleted_branch_count": len(deleted_branches),
        })

        return result
