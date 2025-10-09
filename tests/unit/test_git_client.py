"""Unit tests for GitClient class."""
import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from repo_cloner.git_client import GitClient, CloneResult


@pytest.mark.unit
class TestGitClient:
    """Test GitClient Git operations."""

    def test_clone_mirror_creates_local_repo(self, tmp_path):
        """Test that clone_mirror creates a local repository."""
        # Arrange
        client = GitClient()
        source_url = "https://github.com/test/repo.git"
        local_path = tmp_path / "test-repo"

        # Mock GitPython
        with patch('repo_cloner.git_client.git.Repo.clone_from') as mock_clone:
            mock_repo = MagicMock()
            mock_repo.branches = [Mock(), Mock(), Mock()]  # 3 branches
            mock_clone.return_value = mock_repo

            # Act
            result = client.clone_mirror(source_url, str(local_path))

            # Assert
            assert result.success is True
            assert result.local_path == str(local_path)
            assert result.branches_count == 3
            mock_clone.assert_called_once_with(
                source_url, str(local_path), mirror=True
            )

    def test_clone_mirror_preserves_all_branches(self, tmp_path):
        """Test that clone_mirror uses mirror flag to preserve all refs."""
        # Arrange
        client = GitClient()
        source_url = "https://github.com/test/repo.git"
        local_path = tmp_path / "test-repo"

        # Mock
        with patch('repo_cloner.git_client.git.Repo.clone_from') as mock_clone:
            mock_repo = MagicMock()
            mock_repo.branches = [Mock(name=f"branch{i}") for i in range(5)]
            mock_clone.return_value = mock_repo

            # Act
            result = client.clone_mirror(source_url, str(local_path))

            # Assert - verify mirror=True was used
            _, kwargs = mock_clone.call_args
            assert kwargs.get('mirror') is True
            assert result.branches_count == 5

    def test_clone_mirror_handles_error(self, tmp_path):
        """Test that clone_mirror handles Git errors gracefully."""
        # Arrange
        client = GitClient()
        source_url = "https://github.com/test/nonexistent.git"
        local_path = tmp_path / "test-repo"

        # Mock GitPython to raise error
        with patch('repo_cloner.git_client.git.Repo.clone_from') as mock_clone:
            mock_clone.side_effect = Exception("Repository not found")

            # Act
            result = client.clone_mirror(source_url, str(local_path))

            # Assert
            assert result.success is False
            assert result.branches_count == 0
            assert "Repository not found" in result.error_message

    def test_clone_mirror_with_dry_run_does_not_clone(self, tmp_path):
        """Test that dry_run mode logs without actually cloning."""
        # Arrange
        client = GitClient()
        source_url = "https://github.com/test/repo.git"
        local_path = tmp_path / "test-repo"

        # Mock
        with patch('repo_cloner.git_client.git.Repo.clone_from') as mock_clone:
            # Act
            result = client.clone_mirror(source_url, str(local_path), dry_run=True)

            # Assert - clone should NOT be called in dry-run
            mock_clone.assert_not_called()
            assert result.success is True
            assert result.dry_run is True
            assert "DRY-RUN" in result.message
