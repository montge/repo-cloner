"""Unit tests for AuthManager class."""
import pytest
import os
from unittest.mock import patch, Mock
from repo_cloner.auth_manager import AuthManager


@pytest.mark.unit
class TestAuthManager:
    """Test AuthManager credential handling."""

    def test_inject_github_token_to_url(self):
        """Test that GitHub token is correctly injected into HTTPS URL."""
        # Arrange
        auth = AuthManager(github_token="ghp_test_token_123")
        url = "https://github.com/myorg/myrepo.git"

        # Act
        authenticated_url = auth.inject_credentials(url, platform="github")

        # Assert
        assert authenticated_url == "https://ghp_test_token_123@github.com/myorg/myrepo.git"

    def test_inject_gitlab_token_to_url(self):
        """Test that GitLab token is correctly injected into HTTPS URL."""
        # Arrange
        auth = AuthManager(gitlab_token="glpat-test_token_456")
        url = "https://gitlab.com/mygroup/myrepo.git"

        # Act
        authenticated_url = auth.inject_credentials(url, platform="gitlab")

        # Assert
        assert authenticated_url == "https://oauth2:glpat-test_token_456@gitlab.com/mygroup/myrepo.git"

    def test_inject_credentials_preserves_ssh_urls(self):
        """Test that SSH URLs are not modified."""
        # Arrange
        auth = AuthManager(github_token="ghp_test_token")
        ssh_url = "git@github.com:myorg/myrepo.git"

        # Act
        result_url = auth.inject_credentials(ssh_url, platform="github")

        # Assert - SSH URLs should pass through unchanged
        assert result_url == ssh_url

    def test_load_tokens_from_environment(self):
        """Test that tokens are loaded from environment variables."""
        # Arrange
        with patch.dict(os.environ, {
            "GITHUB_TOKEN": "ghp_env_token",
            "GITLAB_TOKEN": "glpat_env_token"
        }):
            # Act
            auth = AuthManager.from_environment()

            # Assert
            assert auth.github_token == "ghp_env_token"
            assert auth.gitlab_token == "glpat_env_token"

    def test_raises_error_when_token_missing(self):
        """Test that error is raised when required token is missing."""
        # Arrange
        auth = AuthManager()  # No tokens provided

        # Act & Assert
        with pytest.raises(ValueError, match="GitHub token not configured"):
            auth.inject_credentials("https://github.com/test/repo.git", platform="github")

    def test_supports_custom_gitlab_instance(self):
        """Test authentication for custom GitLab instances."""
        # Arrange
        auth = AuthManager(gitlab_token="glpat_custom")
        custom_url = "https://gitlab.example.com/mygroup/myrepo.git"

        # Act
        authenticated_url = auth.inject_credentials(custom_url, platform="gitlab")

        # Assert
        assert authenticated_url == "https://oauth2:glpat_custom@gitlab.example.com/mygroup/myrepo.git"

    def test_auto_detects_platform_from_url(self):
        """Test that platform is auto-detected from URL."""
        # Arrange
        auth = AuthManager(github_token="ghp_auto", gitlab_token="glpat_auto")
        github_url = "https://github.com/test/repo.git"
        gitlab_url = "https://gitlab.com/test/repo.git"

        # Act
        github_result = auth.inject_credentials(github_url)  # No platform specified
        gitlab_result = auth.inject_credentials(gitlab_url)  # No platform specified

        # Assert
        assert "ghp_auto" in github_result
        assert "glpat_auto" in gitlab_result

    def test_handles_urls_without_git_suffix(self):
        """Test authentication for URLs without .git suffix."""
        # Arrange
        auth = AuthManager(github_token="ghp_test")
        url = "https://github.com/myorg/myrepo"

        # Act
        authenticated_url = auth.inject_credentials(url, platform="github")

        # Assert
        assert authenticated_url == "https://ghp_test@github.com/myorg/myrepo"
