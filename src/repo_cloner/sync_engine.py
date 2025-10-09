"""Synchronization engine for repository mirroring and updates."""

from typing import Dict, List, Optional

import git


class SyncEngine:
    """Engine for synchronizing repositories with change detection."""

    def __init__(self):
        """Initialize SyncEngine."""
        pass

    def detect_changes(self, repo_path: str, previous_state: Dict) -> Dict:
        """
        Detect changes in repository since previous state.

        Args:
            repo_path: Path to local repository
            previous_state: Previous sync state with last_commit SHA

        Returns:
            Dictionary with change detection results:
            - has_new_commits: bool
            - new_commit_count: int
            - old_commits: list of previous commit SHAs
            - new_commits: list of new commit SHAs
        """
        repo = git.Repo(repo_path)
        current_sha = repo.head.commit.hexsha
        previous_sha = previous_state.get("last_commit")

        if not previous_sha:
            # First sync, no previous state
            return {
                "has_new_commits": True,
                "new_commit_count": 1,
                "old_commits": [],
                "new_commits": [current_sha],
            }

        if current_sha == previous_sha:
            # No changes
            return {
                "has_new_commits": False,
                "new_commit_count": 0,
                "old_commits": [previous_sha],
                "new_commits": [],
            }

        # Find commits between previous and current
        commits = list(repo.iter_commits(f"{previous_sha}..{current_sha}"))
        new_commit_shas = [commit.hexsha for commit in commits]

        return {
            "has_new_commits": True,
            "new_commit_count": len(new_commit_shas),
            "old_commits": [previous_sha],
            "new_commits": new_commit_shas,
        }
