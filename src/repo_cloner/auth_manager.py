"""Authentication manager for Git credentials injection."""
import os
from typing import Optional
from urllib.parse import urlparse, urlunparse


class AuthManager:
    """Manages authentication credentials for Git operations."""

    def __init__(
        self, github_token: Optional[str] = None, gitlab_token: Optional[str] = None
    ):
        """
        Initialize AuthManager with API tokens.

        Args:
            github_token: GitHub personal access token
            gitlab_token: GitLab personal access token
        """
        self.github_token = github_token
        self.gitlab_token = gitlab_token

    @classmethod
    def from_environment(cls) -> "AuthManager":
        """
        Create AuthManager from environment variables.

        Returns:
            AuthManager with tokens loaded from GITHUB_TOKEN and GITLAB_TOKEN env vars
        """
        return cls(
            github_token=os.environ.get("GITHUB_TOKEN"),
            gitlab_token=os.environ.get("GITLAB_TOKEN"),
        )

    def inject_credentials(
        self, url: str, platform: Optional[str] = None
    ) -> str:
        """
        Inject authentication credentials into a Git URL.

        Args:
            url: Git URL (HTTPS or SSH)
            platform: Platform name ("github" or "gitlab"), auto-detected if not provided

        Returns:
            Authenticated URL with credentials injected

        Raises:
            ValueError: If required token is not configured
        """
        # SSH URLs pass through unchanged
        if url.startswith("git@"):
            return url

        # Auto-detect platform from URL if not specified
        if platform is None:
            platform = self._detect_platform(url)

        # Get appropriate token
        if platform == "github":
            if not self.github_token:
                raise ValueError("GitHub token not configured")
            return self._inject_github_credentials(url, self.github_token)
        elif platform == "gitlab":
            if not self.gitlab_token:
                raise ValueError("GitLab token not configured")
            return self._inject_gitlab_credentials(url, self.gitlab_token)
        else:
            raise ValueError(f"Unsupported platform: {platform}")

    def _detect_platform(self, url: str) -> str:
        """
        Auto-detect Git platform from URL.

        Args:
            url: Git URL

        Returns:
            Platform name ("github" or "gitlab")
        """
        if "github.com" in url:
            return "github"
        elif "gitlab" in url:
            return "gitlab"
        else:
            raise ValueError(f"Cannot auto-detect platform from URL: {url}")

    def _inject_github_credentials(self, url: str, token: str) -> str:
        """
        Inject GitHub token into HTTPS URL.

        GitHub format: https://TOKEN@github.com/org/repo.git

        Args:
            url: GitHub HTTPS URL
            token: GitHub personal access token

        Returns:
            Authenticated URL
        """
        parsed = urlparse(url)
        authenticated_netloc = f"{token}@{parsed.netloc}"
        return urlunparse(
            (
                parsed.scheme,
                authenticated_netloc,
                parsed.path,
                parsed.params,
                parsed.query,
                parsed.fragment,
            )
        )

    def _inject_gitlab_credentials(self, url: str, token: str) -> str:
        """
        Inject GitLab token into HTTPS URL.

        GitLab format: https://oauth2:TOKEN@gitlab.com/group/repo.git

        Args:
            url: GitLab HTTPS URL
            token: GitLab personal access token

        Returns:
            Authenticated URL
        """
        parsed = urlparse(url)
        authenticated_netloc = f"oauth2:{token}@{parsed.netloc}"
        return urlunparse(
            (
                parsed.scheme,
                authenticated_netloc,
                parsed.path,
                parsed.params,
                parsed.query,
                parsed.fragment,
            )
        )
