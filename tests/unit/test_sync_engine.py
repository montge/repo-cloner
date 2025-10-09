"""Unit tests for SyncEngine class."""

import tempfile
from pathlib import Path
from unittest.mock import Mock

import git
import pytest

from repo_cloner.sync_engine import SyncEngine


@pytest.mark.unit
class TestSyncEngine:
    """Test SyncEngine for repository synchronization."""

    def test_detect_changes_finds_new_commits(self):
        """Test that detect_changes identifies new commits in source."""
        # Arrange - Create a test repository with commits
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_path = Path(tmpdir) / "test-repo"
            repo = git.Repo.init(repo_path)

            # Initial commit
            (repo_path / "file1.txt").write_text("initial content")
            repo.index.add(["file1.txt"])
            repo.index.commit("Initial commit")
            initial_sha = repo.head.commit.hexsha

            # Create SyncEngine and record initial state
            engine = SyncEngine()
            initial_state = {
                "last_commit": initial_sha,
                "branches": [ref.name for ref in repo.heads],
            }

            # Add new commit
            (repo_path / "file2.txt").write_text("new content")
            repo.index.add(["file2.txt"])
            new_commit = repo.index.commit("Second commit")
            new_sha = new_commit.hexsha

            # Act - Detect changes
            changes = engine.detect_changes(str(repo_path), initial_state)

            # Assert - Check commit changes
            assert changes["has_new_commits"] is True
            assert changes["new_commit_count"] == 1
            assert initial_sha in changes["old_commits"]
            assert new_sha in changes["new_commits"]
            # Check branch changes (no branch changes in this test)
            assert changes["has_new_branches"] is False
            assert changes["has_deleted_branches"] is False

    def test_detect_changes_finds_new_branches(self):
        """Test that detect_changes identifies new branches."""
        # Arrange - Create repository with multiple branches
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_path = Path(tmpdir) / "test-repo"
            repo = git.Repo.init(repo_path)

            # Initial commit on main
            (repo_path / "file1.txt").write_text("initial")
            repo.index.add(["file1.txt"])
            repo.index.commit("Initial commit")

            # Record initial state (only main branch)
            initial_branches = [ref.name for ref in repo.heads]

            # Create new branch
            repo.create_head("feature-branch")

            # Create SyncEngine
            engine = SyncEngine()
            previous_state = {"branches": initial_branches}

            # Act - Detect changes
            changes = engine.detect_changes(str(repo_path), previous_state)

            # Assert
            assert changes["has_new_branches"] is True
            assert "feature-branch" in changes["new_branches"]
            assert changes["new_branch_count"] == 1

    def test_detect_changes_finds_deleted_branches(self):
        """Test that detect_changes identifies deleted branches."""
        # Arrange - Create repository with multiple branches
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_path = Path(tmpdir) / "test-repo"
            repo = git.Repo.init(repo_path)

            # Initial commit
            (repo_path / "file1.txt").write_text("initial")
            repo.index.add(["file1.txt"])
            repo.index.commit("Initial commit")

            # Create feature branch
            feature_branch = repo.create_head("feature-branch")

            # Record state with both branches
            initial_branches = [ref.name for ref in repo.heads]

            # Delete feature branch
            repo.delete_head(feature_branch)

            # Create SyncEngine
            engine = SyncEngine()
            previous_state = {"branches": initial_branches}

            # Act - Detect changes
            changes = engine.detect_changes(str(repo_path), previous_state)

            # Assert
            assert changes["has_deleted_branches"] is True
            assert "feature-branch" in changes["deleted_branches"]
            assert changes["deleted_branch_count"] == 1

    def test_sync_repository_unidirectional_source_to_target(self):
        """Test sync_repository in unidirectional mode (source → target)."""
        # Arrange
        with tempfile.TemporaryDirectory() as tmpdir:
            source_path = Path(tmpdir) / "source"
            target_path = Path(tmpdir) / "target"

            # Create source repository
            source_repo = git.Repo.init(source_path)
            (source_path / "file1.txt").write_text("content")
            source_repo.index.add(["file1.txt"])
            source_repo.index.commit("Initial commit")

            # Create target repository (empty)
            target_repo = git.Repo.init(target_path, bare=True)

            # Create SyncEngine
            engine = SyncEngine()

            # Act - Sync source to target
            result = engine.sync_repository(
                source_url=str(source_path),
                target_url=str(target_path),
                direction="source_to_target",
                strategy="mirror",
            )

            # Assert
            assert result["success"] is True
            assert result["direction"] == "source_to_target"
            assert result["commits_synced"] > 0

    def test_sync_repository_detects_no_changes(self):
        """Test that sync_repository handles no changes efficiently."""
        # Arrange
        with tempfile.TemporaryDirectory() as tmpdir:
            source_path = Path(tmpdir) / "source"

            # Create source repository
            source_repo = git.Repo.init(source_path)
            (source_path / "file1.txt").write_text("content")
            source_repo.index.add(["file1.txt"])
            commit = source_repo.index.commit("Initial commit")

            engine = SyncEngine()

            # Mock state with current commit (simulating already synced)
            mock_state = {
                "last_commit": commit.hexsha,
                "branches": [ref.name for ref in source_repo.heads],
            }

            # Act - Detect changes (should be none)
            changes = engine.detect_changes(str(source_path), mock_state)

            # Assert - No changes
            assert changes["has_new_commits"] is False
            assert changes["has_new_branches"] is False
            assert changes["has_deleted_branches"] is False

    def test_detect_conflicts_finds_divergent_commits(self):
        """Test that detect_conflicts identifies divergent commits on same branch."""
        # Arrange - Create two repos with divergent commits
        with tempfile.TemporaryDirectory() as tmpdir:
            repo1_path = Path(tmpdir) / "repo1"
            repo2_path = Path(tmpdir) / "repo2"

            # Create repo1 with initial commit
            repo1 = git.Repo.init(repo1_path)
            (repo1_path / "file.txt").write_text("initial")
            repo1.index.add(["file.txt"])
            base_commit = repo1.index.commit("Base commit")

            # Clone to repo2
            repo2 = repo1.clone(repo2_path)

            # Make divergent commits on main branch
            # Repo1: add commit A
            (repo1_path / "file.txt").write_text("version A")
            repo1.index.add(["file.txt"])
            commit_a = repo1.index.commit("Commit A on repo1")

            # Repo2: add commit B (different content)
            (repo2_path / "file.txt").write_text("version B")
            repo2.index.add(["file.txt"])
            commit_b = repo2.index.commit("Commit B on repo2")

            # Act - Detect conflicts
            engine = SyncEngine()
            conflicts = engine.detect_conflicts(str(repo1_path), str(repo2_path))

            # Assert
            assert conflicts["has_conflicts"] is True
            assert len(conflicts["conflicting_branches"]) > 0
            assert (
                "master" in conflicts["conflicting_branches"]
                or "main" in conflicts["conflicting_branches"]
            )

    def test_detect_conflicts_no_conflicts_when_fast_forward(self):
        """Test that detect_conflicts returns no conflicts for fast-forward merges."""
        # Arrange
        with tempfile.TemporaryDirectory() as tmpdir:
            repo1_path = Path(tmpdir) / "repo1"
            repo2_path = Path(tmpdir) / "repo2"

            # Create repo1
            repo1 = git.Repo.init(repo1_path)
            (repo1_path / "file.txt").write_text("initial")
            repo1.index.add(["file.txt"])
            repo1.index.commit("Initial commit")

            # Clone to repo2
            repo2 = repo1.clone(repo2_path)

            # Add commit only to repo1 (repo2 can fast-forward)
            (repo1_path / "file2.txt").write_text("new file")
            repo1.index.add(["file2.txt"])
            repo1.index.commit("New commit on repo1")

            # Act
            engine = SyncEngine()
            conflicts = engine.detect_conflicts(str(repo1_path), str(repo2_path))

            # Assert - No conflicts, repo2 can fast-forward
            assert conflicts["has_conflicts"] is False

    def test_resolve_conflicts_with_source_wins_strategy(self):
        """Test conflict resolution with source-wins strategy."""
        # Arrange - Create conflicting repos
        with tempfile.TemporaryDirectory() as tmpdir:
            source_path = Path(tmpdir) / "source"
            target_path = Path(tmpdir) / "target"

            # Create source with commit A
            source_repo = git.Repo.init(source_path)
            (source_path / "file.txt").write_text("initial")
            source_repo.index.add(["file.txt"])
            source_repo.index.commit("Base")

            # Clone to target
            target_repo = source_repo.clone(target_path)

            # Divergent commits
            (source_path / "file.txt").write_text("source version")
            source_repo.index.add(["file.txt"])
            source_repo.index.commit("Source commit")

            (target_path / "file.txt").write_text("target version")
            target_repo.index.add(["file.txt"])
            target_repo.index.commit("Target commit")

            # Act - Resolve with source-wins
            engine = SyncEngine()
            result = engine.resolve_conflicts(
                source_url=str(source_path),
                target_url=str(target_path),
                strategy="source_wins"
            )

            # Assert
            assert result["success"] is True
            assert result["resolution_strategy"] == "source_wins"
