"""Unit tests for StateManager class."""

import json
import tempfile
from pathlib import Path

import pytest

from repo_cloner.state_manager import StateManager


@pytest.mark.unit
class TestStateManager:
    """Test StateManager for sync state persistence."""

    def test_save_and_load_state(self):
        """Test that state can be saved and loaded."""
        # Arrange
        with tempfile.TemporaryDirectory() as tmpdir:
            state_file = Path(tmpdir) / "sync-state.json"
            manager = StateManager(str(state_file))

            state_data = {
                "repo_url": "https://gitlab.com/org/repo.git",
                "last_sync": "2025-10-09T12:00:00Z",
                "last_commit": "abc123",
                "branches": ["main", "develop"],
            }

            # Act - Save state
            manager.save_state("gitlab-org-repo", state_data)

            # Act - Load state
            loaded_state = manager.load_state("gitlab-org-repo")

            # Assert
            assert loaded_state == state_data
            assert loaded_state["last_commit"] == "abc123"
            assert "main" in loaded_state["branches"]

    def test_load_state_returns_empty_for_new_repo(self):
        """Test that loading state for non-existent repo returns empty dict."""
        # Arrange
        with tempfile.TemporaryDirectory() as tmpdir:
            state_file = Path(tmpdir) / "sync-state.json"
            manager = StateManager(str(state_file))

            # Act
            state = manager.load_state("nonexistent-repo")

            # Assert
            assert state == {}

    def test_save_state_creates_file_if_not_exists(self):
        """Test that save_state creates state file if it doesn't exist."""
        # Arrange
        with tempfile.TemporaryDirectory() as tmpdir:
            state_file = Path(tmpdir) / "new-state.json"
            manager = StateManager(str(state_file))

            state_data = {"last_commit": "def456"}

            # Act
            manager.save_state("test-repo", state_data)

            # Assert - File should be created
            assert state_file.exists()

            # Verify content
            with open(state_file, "r") as f:
                data = json.load(f)
            assert "test-repo" in data
            assert data["test-repo"]["last_commit"] == "def456"

    def test_save_state_preserves_other_repos(self):
        """Test that saving state for one repo doesn't affect others."""
        # Arrange
        with tempfile.TemporaryDirectory() as tmpdir:
            state_file = Path(tmpdir) / "state.json"
            manager = StateManager(str(state_file))

            # Save state for repo1
            manager.save_state("repo1", {"last_commit": "aaa"})

            # Save state for repo2
            manager.save_state("repo2", {"last_commit": "bbb"})

            # Act - Load both
            state1 = manager.load_state("repo1")
            state2 = manager.load_state("repo2")

            # Assert - Both should exist
            assert state1["last_commit"] == "aaa"
            assert state2["last_commit"] == "bbb"

    def test_update_state_modifies_existing(self):
        """Test that updating state modifies existing entry."""
        # Arrange
        with tempfile.TemporaryDirectory() as tmpdir:
            state_file = Path(tmpdir) / "state.json"
            manager = StateManager(str(state_file))

            # Initial state
            manager.save_state("repo1", {"last_commit": "old123"})

            # Act - Update state
            manager.save_state("repo1", {"last_commit": "new456"})

            # Assert
            state = manager.load_state("repo1")
            assert state["last_commit"] == "new456"

    def test_get_all_repos(self):
        """Test that get_all_repos returns all tracked repositories."""
        # Arrange
        with tempfile.TemporaryDirectory() as tmpdir:
            state_file = Path(tmpdir) / "state.json"
            manager = StateManager(str(state_file))

            manager.save_state("repo1", {"last_commit": "aaa"})
            manager.save_state("repo2", {"last_commit": "bbb"})
            manager.save_state("repo3", {"last_commit": "ccc"})

            # Act
            all_repos = manager.get_all_repos()

            # Assert
            assert len(all_repos) == 3
            assert "repo1" in all_repos
            assert "repo2" in all_repos
            assert "repo3" in all_repos
