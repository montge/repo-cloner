"""GitHub API client for repository operations."""

from typing import Dict, List, Optional

from github import Github, UnknownObjectException


class GitHubClient:
    """Client for GitHub API operations."""

    def __init__(
        self,
        token: str,
        base_url: str = "https://api.github.com",
        gh_instance=None,
    ):
        """
        Initialize GitHub client.

        Args:
            token: GitHub personal access token
            base_url: GitHub API base URL (default: https://api.github.com)
            gh_instance: Optional Github instance for testing (default: None)
        """
        self.token = token
        self.base_url = base_url
        self.gh = (
            gh_instance
            if gh_instance is not None
            else Github(base_url=base_url, login_or_token=token)
        )

    def repository_exists(self, repo_full_name: str) -> bool:
        """
        Check if a repository exists on GitHub.

        Args:
            repo_full_name: Repository full name (e.g., "owner/repo")

        Returns:
            True if repository exists, False if not found

        Raises:
            Exception: For API errors other than 404
        """
        try:
            self.gh.get_repo(repo_full_name)
            return True
        except UnknownObjectException:
            # Repository not found (404)
            return False
        # Let other exceptions propagate

    def create_repository(
        self,
        org_name: str,
        repo_name: str,
        description: str = "",
        private: bool = True,
        topics: Optional[List[str]] = None,
        default_branch: Optional[str] = None,
    ) -> Dict:
        """
        Create a new repository in a GitHub organization.

        Args:
            org_name: GitHub organization name
            repo_name: Repository name
            description: Repository description (default: "")
            private: Whether repository is private (default: True)
            topics: List of topics/tags (default: None)
            default_branch: Default branch name (default: None, uses GitHub default)

        Returns:
            Dictionary with repository details (name, full_name, html_url)

        Raises:
            GithubException: If repository already exists or other API error
        """
        org = self.gh.get_organization(org_name)

        # Create repository
        repo = org.create_repo(
            name=repo_name,
            description=description,
            private=private,
        )

        # Set topics if provided
        if topics:
            repo.replace_topics(topics)

        # Set default branch if provided
        if default_branch:
            repo.edit(default_branch=default_branch)

        return {
            "name": repo.name,
            "full_name": repo.full_name,
            "html_url": getattr(repo, "html_url", ""),
        }
