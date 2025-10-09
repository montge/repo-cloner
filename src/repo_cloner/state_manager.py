"""State management for repository synchronization."""

import json
from pathlib import Path
from typing import Dict, List


class StateManager:
    """Manages persistent state for repository synchronization."""

    def __init__(self, state_file: str):
        """
        Initialize StateManager.

        Args:
            state_file: Path to JSON file for storing state
        """
        self.state_file = Path(state_file)

    def save_state(self, repo_id: str, state_data: Dict) -> None:
        """
        Save state for a repository.

        Args:
            repo_id: Unique identifier for repository
            state_data: State data to save (dict with last_commit, branches, etc.)
        """
        # Load existing state
        all_state = self._load_all_state()

        # Update state for this repo
        all_state[repo_id] = state_data

        # Save back to file
        self._save_all_state(all_state)

    def load_state(self, repo_id: str) -> Dict:
        """
        Load state for a repository.

        Args:
            repo_id: Unique identifier for repository

        Returns:
            State data dict, or empty dict if no state exists
        """
        all_state = self._load_all_state()
        return all_state.get(repo_id, {})

    def get_all_repos(self) -> List[str]:
        """
        Get list of all tracked repository IDs.

        Returns:
            List of repository IDs with saved state
        """
        all_state = self._load_all_state()
        return list(all_state.keys())

    def _load_all_state(self) -> Dict:
        """Load all state from file."""
        if not self.state_file.exists():
            return {}

        with open(self.state_file, "r") as f:
            return json.load(f)

    def _save_all_state(self, all_state: Dict) -> None:
        """Save all state to file."""
        # Create parent directory if it doesn't exist
        self.state_file.parent.mkdir(parents=True, exist_ok=True)

        with open(self.state_file, "w") as f:
            json.dump(all_state, f, indent=2)
