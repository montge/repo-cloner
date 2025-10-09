"""Unit tests for GitHubClient class."""

from unittest.mock import Mock

import pytest

from repo_cloner.github_client import GitHubClient


@pytest.mark.unit
class TestGitHubClient:
    """Test GitHubClient API operations."""

    def test_repository_exists_returns_true_for_existing_repo(self):
        """Test that repository_exists returns True for existing repository."""
        # Arrange
        mock_gh = Mock()
        mock_repo = Mock()
        mock_gh.get_repo.return_value = mock_repo

        client = GitHubClient(token="test-token", gh_instance=mock_gh)

        # Act
        exists = client.repository_exists("org/repo")

        # Assert
        assert exists is True
        mock_gh.get_repo.assert_called_once_with("org/repo")

    def test_repository_exists_returns_false_for_nonexistent_repo(self):
        """Test that repository_exists returns False when repo not found."""
        # Arrange
        mock_gh = Mock()
        # Simulate 404 error from PyGithub
        from github import UnknownObjectException

        mock_gh.get_repo.side_effect = UnknownObjectException(
            status=404, data={"message": "Not Found"}, headers={}
        )

        client = GitHubClient(token="test-token", gh_instance=mock_gh)

        # Act
        exists = client.repository_exists("org/nonexistent")

        # Assert
        assert exists is False
        mock_gh.get_repo.assert_called_once_with("org/nonexistent")

    def test_repository_exists_handles_other_exceptions(self):
        """Test that repository_exists re-raises non-404 exceptions."""
        # Arrange
        mock_gh = Mock()
        mock_gh.get_repo.side_effect = Exception("API rate limit exceeded")

        client = GitHubClient(token="test-token", gh_instance=mock_gh)

        # Act & Assert
        with pytest.raises(Exception, match="API rate limit exceeded"):
            client.repository_exists("org/repo")

    def test_create_repository_creates_new_repo_in_org(self):
        """Test that create_repository creates a new repository in organization."""
        # Arrange
        mock_gh = Mock()
        mock_org = Mock()
        mock_repo = Mock()
        mock_repo.name = "new-repo"
        mock_repo.full_name = "org/new-repo"
        mock_repo.html_url = "https://github.com/org/new-repo"

        mock_org.create_repo.return_value = mock_repo
        mock_gh.get_organization.return_value = mock_org

        client = GitHubClient(token="test-token", gh_instance=mock_gh)

        # Act
        result = client.create_repository(
            org_name="org",
            repo_name="new-repo",
            description="Test repository",
            private=True,
        )

        # Assert
        assert result["name"] == "new-repo"
        assert result["full_name"] == "org/new-repo"
        assert result["html_url"] == "https://github.com/org/new-repo"
        mock_gh.get_organization.assert_called_once_with("org")
        mock_org.create_repo.assert_called_once_with(
            name="new-repo", description="Test repository", private=True
        )

    def test_create_repository_with_topics(self):
        """Test that create_repository sets topics on new repository."""
        # Arrange
        mock_gh = Mock()
        mock_org = Mock()
        mock_repo = Mock()
        mock_repo.name = "tagged-repo"
        mock_repo.full_name = "org/tagged-repo"

        mock_org.create_repo.return_value = mock_repo
        mock_gh.get_organization.return_value = mock_org

        client = GitHubClient(token="test-token", gh_instance=mock_gh)

        # Act
        client.create_repository(
            org_name="org",
            repo_name="tagged-repo",
            description="Repo with topics",
            private=False,
            topics=["python", "testing"],
        )

        # Assert
        mock_org.create_repo.assert_called_once()
        # Verify topics were set on the created repo
        mock_repo.replace_topics.assert_called_once_with(["python", "testing"])

    def test_create_repository_handles_already_exists_error(self):
        """Test that create_repository handles repository already exists error."""
        # Arrange
        mock_gh = Mock()
        mock_org = Mock()
        from github import GithubException

        mock_org.create_repo.side_effect = GithubException(
            status=422,
            data={"message": "Repository already exists"},
            headers={},
        )
        mock_gh.get_organization.return_value = mock_org

        client = GitHubClient(token="test-token", gh_instance=mock_gh)

        # Act & Assert
        with pytest.raises(GithubException, match="Repository already exists"):
            client.create_repository(org_name="org", repo_name="existing-repo")

    def test_create_repository_sets_default_branch(self):
        """Test that create_repository can set custom default branch."""
        # Arrange
        mock_gh = Mock()
        mock_org = Mock()
        mock_repo = Mock()
        mock_repo.name = "main-branch-repo"
        mock_repo.default_branch = "master"  # GitHub default

        mock_org.create_repo.return_value = mock_repo
        mock_gh.get_organization.return_value = mock_org

        client = GitHubClient(token="test-token", gh_instance=mock_gh)

        # Act
        client.create_repository(
            org_name="org",
            repo_name="main-branch-repo",
            default_branch="main",
        )

        # Assert
        # Verify default_branch was set after creation
        mock_repo.edit.assert_called_once_with(default_branch="main")

    def test_supports_github_enterprise(self):
        """Test that client works with GitHub Enterprise instances."""
        # Arrange
        mock_gh = Mock()
        mock_repo = Mock()
        mock_gh.get_repo.return_value = mock_repo

        # GitHub Enterprise uses custom base_url
        client = GitHubClient(
            token="enterprise-token",
            base_url="https://github.example.com/api/v3",
            gh_instance=mock_gh,
        )

        # Act
        exists = client.repository_exists("enterprise-org/repo")

        # Assert
        assert exists is True
        mock_gh.get_repo.assert_called_once_with("enterprise-org/repo")

    def test_create_repository_without_description(self):
        """Test that create_repository works without description."""
        # Arrange
        mock_gh = Mock()
        mock_org = Mock()
        mock_repo = Mock()
        mock_repo.name = "minimal-repo"
        mock_repo.full_name = "org/minimal-repo"

        mock_org.create_repo.return_value = mock_repo
        mock_gh.get_organization.return_value = mock_org

        client = GitHubClient(token="test-token", gh_instance=mock_gh)

        # Act
        result = client.create_repository(org_name="org", repo_name="minimal-repo")

        # Assert
        assert result["name"] == "minimal-repo"
        # Verify description wasn't passed (or was empty string)
        call_kwargs = mock_org.create_repo.call_args.kwargs
        assert call_kwargs.get("description", "") == ""
