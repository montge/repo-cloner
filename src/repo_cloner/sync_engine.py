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

    def detect_conflicts(self, repo1_path: str, repo2_path: str) -> Dict:
        """
        Detect conflicts between two repositories.

        Args:
            repo1_path: Path to first repository
            repo2_path: Path to second repository

        Returns:
            Dictionary with conflict information:
            - has_conflicts: bool
            - conflicting_branches: list of branch names with conflicts
        """
        repo1 = git.Repo(repo1_path)
        repo2 = git.Repo(repo2_path)

        conflicting_branches = []

        # Check each branch in repo1
        for branch1 in repo1.heads:
            branch_name = branch1.name

            # Check if branch exists in repo2
            try:
                branch2 = repo2.heads[branch_name]
            except (IndexError, AttributeError):
                # Branch doesn't exist in repo2, no conflict
                continue

            # Check if commits have diverged
            commit1 = branch1.commit
            commit2 = branch2.commit

            if commit1.hexsha == commit2.hexsha:
                # Same commit, no conflict
                continue

            # Check if one is ancestor of the other (fast-forward possible)
            try:
                # Check if commit2 is ancestor of commit1 (repo1 is ahead)
                is_ancestor = repo1.is_ancestor(commit2, commit1)
                if is_ancestor:
                    # repo2 can fast-forward to repo1, no conflict
                    continue

                # Check if commit1 is ancestor of commit2 (repo2 is ahead)
                is_ancestor = repo1.is_ancestor(commit1, commit2)
                if is_ancestor:
                    # repo1 can fast-forward to repo2, no conflict
                    continue

                # Neither is ancestor of the other - diverged!
                conflicting_branches.append(branch_name)
            except git.exc.GitCommandError:
                # Error checking ancestry, assume conflict
                conflicting_branches.append(branch_name)

        return {
            "has_conflicts": len(conflicting_branches) > 0,
            "conflicting_branches": conflicting_branches,
        }

    def resolve_conflicts(
        self, source_url: str, target_url: str, strategy: str = "fail_fast"
    ) -> Dict:
        """
        Resolve conflicts between repositories.

        Args:
            source_url: Source repository URL
            target_url: Target repository URL
            strategy: Resolution strategy (source_wins, target_wins, fail_fast)

        Returns:
            Dictionary with resolution results:
            - success: bool
            - resolution_strategy: str
            - message: str
        """
        if strategy == "fail_fast":
            return {
                "success": False,
                "resolution_strategy": "fail_fast",
                "message": "Conflicts detected, failing fast as configured",
            }
        elif strategy == "source_wins":
            # Force push source to target
            try:
                with tempfile.TemporaryDirectory() as tmpdir:
                    local_path = Path(tmpdir) / "repo"
                    repo = git.Repo.clone_from(source_url, local_path)
                    remote = repo.create_remote("target", target_url)
                    remote.push(mirror=True, force=True)
                    repo.delete_remote(remote)

                return {
                    "success": True,
                    "resolution_strategy": "source_wins",
                    "message": "Source forced to target, conflicts resolved",
                }
            except Exception as e:
                return {
                    "success": False,
                    "resolution_strategy": "source_wins",
                    "message": f"Error resolving conflicts: {str(e)}",
                }
        elif strategy == "target_wins":
            # Force push target to source
            try:
                with tempfile.TemporaryDirectory() as tmpdir:
                    local_path = Path(tmpdir) / "repo"
                    repo = git.Repo.clone_from(target_url, local_path)
                    remote = repo.create_remote("source", source_url)
                    remote.push(mirror=True, force=True)
                    repo.delete_remote(remote)

                return {
                    "success": True,
                    "resolution_strategy": "target_wins",
                    "message": "Target forced to source, conflicts resolved",
                }
            except Exception as e:
                return {
                    "success": False,
                    "resolution_strategy": "target_wins",
                    "message": f"Error resolving conflicts: {str(e)}",
                }
        else:
            return {
                "success": False,
                "resolution_strategy": strategy,
                "message": f"Unknown resolution strategy: {strategy}",
            }

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
