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
            initial_state = {"last_commit": initial_sha}

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
