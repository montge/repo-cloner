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

            # Assert
            assert changes["has_new_commits"] is True
            assert changes["new_commit_count"] == 1
            assert initial_sha in changes["old_commits"]
            assert new_sha in changes["new_commits"]
