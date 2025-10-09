"""Unit tests for GitClient class."""

from unittest.mock import MagicMock, Mock, patch

import pytest

from repo_cloner.git_client import GitClient


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
        with patch("repo_cloner.git_client.git.Repo.clone_from") as mock_clone:
            mock_repo = MagicMock()
            mock_repo.branches = [Mock(), Mock(), Mock()]  # 3 branches
            mock_clone.return_value = mock_repo

            # Act
            result = client.clone_mirror(source_url, str(local_path))

            # Assert
            assert result.success is True
            assert result.local_path == str(local_path)
            assert result.branches_count == 3
            mock_clone.assert_called_once_with(source_url, str(local_path), mirror=True)

    def test_clone_mirror_preserves_all_branches(self, tmp_path):
        """Test that clone_mirror uses mirror flag to preserve all refs."""
        # Arrange
        client = GitClient()
        source_url = "https://github.com/test/repo.git"
        local_path = tmp_path / "test-repo"

        # Mock
        with patch("repo_cloner.git_client.git.Repo.clone_from") as mock_clone:
            mock_repo = MagicMock()
            mock_repo.branches = [Mock(name=f"branch{i}") for i in range(5)]
            mock_clone.return_value = mock_repo

            # Act
            result = client.clone_mirror(source_url, str(local_path))

            # Assert - verify mirror=True was used
            _, kwargs = mock_clone.call_args
            assert kwargs.get("mirror") is True
            assert result.branches_count == 5

    def test_clone_mirror_handles_error(self, tmp_path):
        """Test that clone_mirror handles Git errors gracefully."""
        # Arrange
        client = GitClient()
        source_url = "https://github.com/test/nonexistent.git"
        local_path = tmp_path / "test-repo"

        # Mock GitPython to raise error
        with patch("repo_cloner.git_client.git.Repo.clone_from") as mock_clone:
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
        with patch("repo_cloner.git_client.git.Repo.clone_from") as mock_clone:
            # Act
            result = client.clone_mirror(source_url, str(local_path), dry_run=True)

            # Assert - clone should NOT be called in dry-run
            mock_clone.assert_not_called()
            assert result.success is True
            assert result.dry_run is True
            assert "DRY-RUN" in result.message

    def test_push_mirror_pushes_to_target(self, tmp_path):
        """Test that push_mirror pushes all refs to target repository."""
        # Arrange
        client = GitClient()
        local_path = tmp_path / "test-repo"
        target_url = "https://github.com/test/target.git"

        # Mock GitPython
        with patch("repo_cloner.git_client.git.Repo") as mock_repo_class:
            mock_repo = MagicMock()
            mock_remote = MagicMock()
            mock_repo.create_remote.return_value = mock_remote
            mock_repo_class.return_value = mock_repo

            # Act
            result = client.push_mirror(str(local_path), target_url)

            # Assert
            assert result.success is True
            assert result.target_url == target_url
            mock_repo.create_remote.assert_called_once_with("target", target_url)
            mock_remote.push.assert_called_once_with(mirror=True)

    def test_push_mirror_handles_push_error(self, tmp_path):
        """Test that push_mirror handles Git push errors gracefully."""
        # Arrange
        client = GitClient()
        local_path = tmp_path / "test-repo"
        target_url = "https://github.com/test/target.git"

        # Mock GitPython to raise error
        with patch("repo_cloner.git_client.git.Repo") as mock_repo_class:
            mock_repo_class.side_effect = Exception("Failed to push: authentication required")

            # Act
            result = client.push_mirror(str(local_path), target_url)

            # Assert
            assert result.success is False
            assert "authentication required" in result.error_message

    def test_push_mirror_with_dry_run_does_not_push(self, tmp_path):
        """Test that dry_run mode logs without actually pushing."""
        # Arrange
        client = GitClient()
        local_path = tmp_path / "test-repo"
        target_url = "https://github.com/test/target.git"

        # Mock
        with patch("repo_cloner.git_client.git.Repo") as mock_repo_class:
            # Act
            result = client.push_mirror(str(local_path), target_url, dry_run=True)

            # Assert - Repo should NOT be called in dry-run
            mock_repo_class.assert_not_called()
            assert result.success is True
            assert result.dry_run is True
            assert "DRY-RUN" in result.message

    def test_push_mirror_removes_temp_remote_after_push(self, tmp_path):
        """Test that push_mirror cleans up temporary remote after push."""
        # Arrange
        client = GitClient()
        local_path = tmp_path / "test-repo"
        target_url = "https://github.com/test/target.git"

        # Mock GitPython
        with patch("repo_cloner.git_client.git.Repo") as mock_repo_class:
            mock_repo = MagicMock()
            mock_remote = MagicMock()
            mock_repo.create_remote.return_value = mock_remote
            mock_repo_class.return_value = mock_repo

            # Act
            result = client.push_mirror(str(local_path), target_url)

            # Assert - remote should be removed after push
            assert result.success is True
            mock_repo.delete_remote.assert_called_once_with("target")
