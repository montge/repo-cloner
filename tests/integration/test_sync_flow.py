"""Integration tests for full synchronization workflows."""

import tempfile
from pathlib import Path

import git
import pytest

from repo_cloner.state_manager import StateManager
from repo_cloner.sync_engine import SyncEngine


@pytest.mark.integration
class TestSyncFlow:
    """Test end-to-end synchronization workflows."""

    def test_full_bidirectional_sync_cycle(self):
        """Test complete bidirectional sync with state tracking."""
        # Arrange - Create source and target repositories
        with tempfile.TemporaryDirectory() as tmpdir:
            source_path = Path(tmpdir) / "source"
            target_path = Path(tmpdir) / "target"
            state_file = Path(tmpdir) / "state.json"

            # Create source repository
            source_repo = git.Repo.init(source_path)
            (source_path / "readme.txt").write_text("Source repository")
            source_repo.index.add(["readme.txt"])
            initial_commit = source_repo.index.commit("Initial commit")

            # Create target repository (empty bare repo)
            target_repo = git.Repo.init(target_path, bare=True)

            # Initialize components
            engine = SyncEngine()
            state_manager = StateManager(str(state_file))

            # Act - Step 1: Initial sync (source → target)
            sync_result1 = engine.sync_repository(
                source_url=str(source_path),
                target_url=str(target_path),
                direction="source_to_target",
                strategy="mirror",
            )

            # Save state after first sync
            state_manager.save_state("test-repo", {
                "last_commit": initial_commit.hexsha,
                "branches": [ref.name for ref in source_repo.heads],
                "last_sync": "2025-10-09T12:00:00Z",
            })

            # Act - Step 2: Make changes on source
            (source_path / "file2.txt").write_text("New file on source")
            source_repo.index.add(["file2.txt"])
            new_commit = source_repo.index.commit("Add file2")

            # Detect changes
            previous_state = state_manager.load_state("test-repo")
            changes = engine.detect_changes(str(source_path), previous_state)

            # Act - Step 3: Sync changes (source → target)
            sync_result2 = engine.sync_repository(
                source_url=str(source_path),
                target_url=str(target_path),
                direction="source_to_target",
                strategy="mirror",
            )

            # Assert - Verify all syncs succeeded
            assert sync_result1["success"] is True
            assert sync_result2["success"] is True
            assert changes["has_new_commits"] is True
            assert changes["new_commit_count"] == 1

            # Verify state was tracked
            assert previous_state["last_commit"] == initial_commit.hexsha

    def test_sync_with_conflict_detection(self):
        """Test sync workflow with conflict detection and resolution."""
        # Arrange
        with tempfile.TemporaryDirectory() as tmpdir:
            source_path = Path(tmpdir) / "source"
            target_path = Path(tmpdir) / "target"

            # Create source
            source_repo = git.Repo.init(source_path)
            (source_path / "file.txt").write_text("initial")
            source_repo.index.add(["file.txt"])
            source_repo.index.commit("Base commit")

            # Clone to target (as non-bare for this test)
            target_repo = source_repo.clone(target_path)

            # Create divergent commits
            (source_path / "file.txt").write_text("source version")
            source_repo.index.add(["file.txt"])
            source_repo.index.commit("Source commit")

            (target_path / "file.txt").write_text("target version")
            target_repo.index.add(["file.txt"])
            target_repo.index.commit("Target commit")

            # Act - Detect conflicts
            engine = SyncEngine()
            conflicts = engine.detect_conflicts(str(source_path), str(target_path))

            # Assert - Conflicts detected
            assert conflicts["has_conflicts"] is True

            # Act - Resolve with source-wins
            resolution = engine.resolve_conflicts(
                source_url=str(source_path), target_url=str(target_path), strategy="source_wins"
            )

            # Assert - Resolution successful
            assert resolution["success"] is True
            assert resolution["resolution_strategy"] == "source_wins"

    def test_incremental_sync_with_state_persistence(self):
        """Test incremental sync using persisted state."""
        # Arrange
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_path = Path(tmpdir) / "repo"
            state_file = Path(tmpdir) / "state.json"

            # Create repository with multiple commits
            repo = git.Repo.init(repo_path)
            (repo_path / "file1.txt").write_text("v1")
            repo.index.add(["file1.txt"])
            commit1 = repo.index.commit("Commit 1")

            # Initialize state manager
            state_manager = StateManager(str(state_file))
            engine = SyncEngine()

            # Save initial state
            state_manager.save_state("repo1", {
                "last_commit": commit1.hexsha,
                "branches": ["master"],
            })

            # Add more commits
            (repo_path / "file2.txt").write_text("v2")
            repo.index.add(["file2.txt"])
            commit2 = repo.index.commit("Commit 2")

            (repo_path / "file3.txt").write_text("v3")
            repo.index.add(["file3.txt"])
            commit3 = repo.index.commit("Commit 3")

            # Act - Detect changes since last sync
            previous_state = state_manager.load_state("repo1")
            changes = engine.detect_changes(str(repo_path), previous_state)

            # Assert - 2 new commits detected
            assert changes["has_new_commits"] is True
            assert changes["new_commit_count"] == 2
            assert commit1.hexsha in changes["old_commits"]
            assert commit2.hexsha in changes["new_commits"]
            assert commit3.hexsha in changes["new_commits"]

            # Update state
            state_manager.save_state("repo1", {
                "last_commit": commit3.hexsha,
                "branches": [ref.name for ref in repo.heads],
            })

            # Verify state updated
            updated_state = state_manager.load_state("repo1")
            assert updated_state["last_commit"] == commit3.hexsha

    def test_sync_multiple_branches(self):
        """Test syncing repository with multiple branches."""
        # Arrange
        with tempfile.TemporaryDirectory() as tmpdir:
            source_path = Path(tmpdir) / "source"
            target_path = Path(tmpdir) / "target"

            # Create source with multiple branches
            source_repo = git.Repo.init(source_path)
            (source_path / "main.txt").write_text("main branch")
            source_repo.index.add(["main.txt"])
            source_repo.index.commit("Main commit")

            # Create feature branch
            feature_branch = source_repo.create_head("feature")
            feature_branch.checkout()
            (source_path / "feature.txt").write_text("feature branch")
            source_repo.index.add(["feature.txt"])
            source_repo.index.commit("Feature commit")

            # Switch back to main
            source_repo.heads.master.checkout()

            # Create target (bare)
            target_repo = git.Repo.init(target_path, bare=True)

            # Act - Sync with mirror strategy (all branches)
            engine = SyncEngine()
            result = engine.sync_repository(
                source_url=str(source_path),
                target_url=str(target_path),
                direction="source_to_target",
                strategy="mirror",
            )

            # Assert - All branches synced
            assert result["success"] is True
            assert result["branches_synced"] >= 2  # main/master + feature
