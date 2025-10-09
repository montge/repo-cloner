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
