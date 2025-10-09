"""GitLab API client for repository discovery and operations."""

from dataclasses import dataclass
from typing import Dict, List

import gitlab


@dataclass
class ProjectDetails:
    """Details of a GitLab project."""

    id: int
    name: str
    path_with_namespace: str
    description: str
    topics: List[str]
    visibility: str
    default_branch: str
    http_url_to_repo: str


class GitLabClient:
    """Client for GitLab API operations."""

    def __init__(self, url: str, token: str, gl_instance=None):
        """
        Initialize GitLab client.

        Args:
            url: GitLab instance URL (e.g., https://gitlab.com)
            token: GitLab personal access token
            gl_instance: Optional GitLab instance for testing (default: None)
        """
        self.url = url
        self.token = token
        self.gl = (
            gl_instance if gl_instance is not None else gitlab.Gitlab(url, private_token=token)
        )

    def list_projects(self, group_path: str) -> List[Dict]:
        """
        List all projects in a GitLab group.

        Args:
            group_path: Path to the GitLab group (e.g., "mygroup" or "mygroup/subgroup")

        Returns:
            List of project dictionaries with basic info

        Raises:
            Exception: If group not found or API error occurs
        """
        group = self.gl.groups.get(group_path)
        projects = []

        # Handle pagination - get all projects
        page = 1
        while True:
            page_projects = group.projects.list(page=page, per_page=20)
            if not page_projects:
                break

            for project in page_projects:
                projects.append(
                    {
                        "id": project.id,
                        "name": project.name,
                        "path_with_namespace": project.path_with_namespace,
                        "web_url": getattr(project, "web_url", ""),
                    }
                )

            page += 1

        return projects

    def get_project_details(self, project_id: int) -> ProjectDetails:
        """
        Get detailed information about a specific project.

        Args:
            project_id: GitLab project ID

        Returns:
            ProjectDetails with metadata including description, topics, visibility

        Raises:
            Exception: If project not found or API error occurs
        """
        project = self.gl.projects.get(project_id)

        return ProjectDetails(
            id=project.id,
            name=project.name,
            path_with_namespace=project.path_with_namespace,
            description=project.description or "",
            topics=getattr(project, "topics", []) or [],
            visibility=getattr(project, "visibility", "private"),
            default_branch=getattr(project, "default_branch", "main"),
            http_url_to_repo=getattr(project, "http_url_to_repo", ""),
        )
