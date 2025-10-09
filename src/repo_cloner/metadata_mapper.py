"""Mapper for converting GitLab project metadata to GitHub repository settings."""

from typing import Dict

from repo_cloner.gitlab_client import ProjectDetails


class MetadataMapper:
    """Maps GitLab project metadata to GitHub repository settings."""

    def map_gitlab_to_github(self, gitlab_project: ProjectDetails) -> Dict:
        """
        Map GitLab project metadata to GitHub repository settings.

        Args:
            gitlab_project: GitLab ProjectDetails object

        Returns:
            Dictionary with GitHub repository settings:
            - name: Repository name (extracted from path_with_namespace)
            - description: Repository description
            - topics: List of topics/tags
            - private: Boolean (True for private/internal, False for public)
            - default_branch: Default branch name
        """
        # Extract repository name from path (last part of path_with_namespace)
        repo_name = gitlab_project.path_with_namespace.split("/")[-1]

        # Map visibility: GitLab has public/internal/private, GitHub has public/private
        # GitLab internal → GitHub private (GitHub doesn't have internal visibility)
        private = gitlab_project.visibility in ["private", "internal"]

        return {
            "name": repo_name,
            "description": gitlab_project.description,
            "topics": gitlab_project.topics,
            "private": private,
            "default_branch": gitlab_project.default_branch,
        }
