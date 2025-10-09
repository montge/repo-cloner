"""Integration tests for repository discovery flow."""

from unittest.mock import Mock

import pytest
from github import UnknownObjectException

from repo_cloner.github_client import GitHubClient
from repo_cloner.gitlab_client import GitLabClient, ProjectDetails
from repo_cloner.group_mapper import GroupMapper
from repo_cloner.metadata_mapper import MetadataMapper


@pytest.mark.integration
class TestDiscoveryFlow:
    """Test end-to-end repository discovery and mapping flow."""

    def test_full_discovery_flow_single_repository(self):
        """Test complete flow: discover GitLab project → map → create GitHub repo."""
        # Arrange - Mock GitLab client
        mock_gitlab = Mock()
        mock_group = Mock()

        # GitLab has one project
        mock_project = Mock()
        mock_project.id = 123
        mock_project.name = "awesome-project"
        mock_project.path_with_namespace = "myteam/awesome-project"
        mock_project.description = "An awesome project"
        mock_project.topics = ["python", "cli"]
        mock_project.visibility = "private"
        mock_project.default_branch = "main"
        mock_project.http_url_to_repo = "https://gitlab.com/myteam/awesome-project.git"

        mock_group.projects.list.side_effect = [[mock_project], []]
        mock_gitlab.groups.get.return_value = mock_group
        mock_gitlab.projects.get.return_value = mock_project

        gitlab_client = GitLabClient(
            url="https://gitlab.com", token="gitlab-token", gl_instance=mock_gitlab
        )

        # Arrange - Mock GitHub client
        mock_github = Mock()
        mock_org = Mock()
        mock_created_repo = Mock()
        mock_created_repo.name = "awesome-project"
        mock_created_repo.full_name = "github-org/awesome-project"
        mock_created_repo.html_url = "https://github.com/github-org/awesome-project"

        mock_org.create_repo.return_value = mock_created_repo
        mock_github.get_organization.return_value = mock_org
        mock_github.get_repo.side_effect = UnknownObjectException(
            status=404, data={"message": "Not Found"}, headers={}
        )  # Repo doesn't exist

        github_client = GitHubClient(token="github-token", gh_instance=mock_github)

        # Arrange - Mappers
        group_mapper = GroupMapper(mapping={"myteam": "github-org"})
        metadata_mapper = MetadataMapper()

        # Act - Step 1: Discover GitLab projects
        projects = gitlab_client.list_projects("myteam")
        assert len(projects) == 1
        project_info = projects[0]

        # Act - Step 2: Get detailed metadata
        project_details = gitlab_client.get_project_details(project_info["id"])

        # Act - Step 3: Map group to GitHub org
        github_org = group_mapper.get_github_org_for_project(project_details.path_with_namespace)
        assert github_org == "github-org"

        # Act - Step 4: Map metadata
        github_settings = metadata_mapper.map_gitlab_to_github(project_details)
        assert github_settings["name"] == "awesome-project"
        assert github_settings["description"] == "An awesome project"
        assert github_settings["topics"] == ["python", "cli"]
        assert github_settings["private"] is True
        assert github_settings["default_branch"] == "main"

        # Act - Step 5: Check if repo exists on GitHub
        repo_exists = github_client.repository_exists(f"{github_org}/awesome-project")
        assert repo_exists is False

        # Act - Step 6: Create GitHub repository
        created_repo = github_client.create_repository(
            org_name=github_org,
            repo_name=github_settings["name"],
            description=github_settings["description"],
            private=github_settings["private"],
            topics=github_settings["topics"],
            default_branch=github_settings["default_branch"],
        )

        # Assert
        assert created_repo["name"] == "awesome-project"
        assert created_repo["full_name"] == "github-org/awesome-project"
        mock_org.create_repo.assert_called_once_with(
            name="awesome-project",
            description="An awesome project",
            private=True,
        )
        mock_created_repo.replace_topics.assert_called_once_with(["python", "cli"])
        mock_created_repo.edit.assert_called_once_with(default_branch="main")

    def test_discovery_flow_with_multiple_repositories(self):
        """Test discovery flow with multiple projects in a group."""
        # Arrange - Mock GitLab with 3 projects
        mock_gitlab = Mock()
        mock_group = Mock()

        projects_data = [
            {
                "id": 1,
                "name": "project-1",
                "path": "team/project-1",
                "desc": "First project",
                "topics": ["python"],
            },
            {
                "id": 2,
                "name": "project-2",
                "path": "team/project-2",
                "desc": "Second project",
                "topics": ["nodejs"],
            },
            {
                "id": 3,
                "name": "project-3",
                "path": "team/project-3",
                "desc": "Third project",
                "topics": ["rust"],
            },
        ]

        mock_projects = []
        for data in projects_data:
            mp = Mock()
            mp.id = data["id"]
            mp.name = data["name"]
            mp.path_with_namespace = data["path"]
            mp.description = data["desc"]
            mp.topics = data["topics"]
            mp.visibility = "public"
            mp.default_branch = "main"
            mp.http_url_to_repo = f"https://gitlab.com/{data['path']}.git"
            mock_projects.append(mp)

        mock_group.projects.list.side_effect = [mock_projects, []]
        mock_gitlab.groups.get.return_value = mock_group

        # Mock get_project_details to return the project
        def mock_get_project(proj_id):
            for mp in mock_projects:
                if mp.id == proj_id:
                    return mp
            raise Exception(f"Project {proj_id} not found")

        mock_gitlab.projects.get.side_effect = mock_get_project

        gitlab_client = GitLabClient(
            url="https://gitlab.com", token="gitlab-token", gl_instance=mock_gitlab
        )

        # Arrange - Mappers
        group_mapper = GroupMapper(mapping={"team": "company-org"})
        metadata_mapper = MetadataMapper()

        # Act - Discover all projects
        projects = gitlab_client.list_projects("team")
        assert len(projects) == 3

        # Act - Process each project
        mapped_repos = []
        for project in projects:
            details = gitlab_client.get_project_details(project["id"])
            org = group_mapper.get_github_org_for_project(details.path_with_namespace)
            settings = metadata_mapper.map_gitlab_to_github(details)
            mapped_repos.append({"org": org, "settings": settings})

        # Assert
        assert len(mapped_repos) == 3
        assert all(repo["org"] == "company-org" for repo in mapped_repos)
        assert mapped_repos[0]["settings"]["name"] == "project-1"
        assert mapped_repos[1]["settings"]["name"] == "project-2"
        assert mapped_repos[2]["settings"]["name"] == "project-3"
        assert mapped_repos[0]["settings"]["topics"] == ["python"]
        assert mapped_repos[1]["settings"]["topics"] == ["nodejs"]
        assert mapped_repos[2]["settings"]["topics"] == ["rust"]

    def test_discovery_flow_with_nested_groups(self):
        """Test discovery flow with nested GitLab groups."""
        # Arrange
        mock_gitlab = Mock()
        mock_group = Mock()

        mock_project = Mock()
        mock_project.id = 456
        mock_project.name = "nested-repo"
        mock_project.path_with_namespace = "company/division/team/nested-repo"
        mock_project.description = "Nested group project"
        mock_project.topics = []
        mock_project.visibility = "internal"
        mock_project.default_branch = "develop"

        mock_group.projects.list.side_effect = [[mock_project], []]
        mock_gitlab.groups.get.return_value = mock_group
        mock_gitlab.projects.get.return_value = mock_project

        gitlab_client = GitLabClient(
            url="https://gitlab.com", token="token", gl_instance=mock_gitlab
        )

        # Arrange - Mapper with nested group
        group_mapper = GroupMapper(mapping={"company/division/team": "team-github-org"})
        metadata_mapper = MetadataMapper()

        # Act
        projects = gitlab_client.list_projects("company/division/team")
        project_details = gitlab_client.get_project_details(projects[0]["id"])
        github_org = group_mapper.get_github_org_for_project(project_details.path_with_namespace)
        github_settings = metadata_mapper.map_gitlab_to_github(project_details)

        # Assert
        assert github_org == "team-github-org"
        assert github_settings["name"] == "nested-repo"
        assert github_settings["private"] is True  # internal → private
        assert github_settings["default_branch"] == "develop"

    def test_discovery_flow_with_default_org_fallback(self):
        """Test discovery flow using default_org for unmapped group."""
        # Arrange
        mock_gitlab = Mock()
        mock_group = Mock()

        mock_project = Mock()
        mock_project.id = 789
        mock_project.name = "unmapped-project"
        mock_project.path_with_namespace = "random-group/unmapped-project"
        mock_project.description = "Project in unmapped group"
        mock_project.topics = []
        mock_project.visibility = "public"
        mock_project.default_branch = "main"

        mock_group.projects.list.side_effect = [[mock_project], []]
        mock_gitlab.groups.get.return_value = mock_group
        mock_gitlab.projects.get.return_value = mock_project

        gitlab_client = GitLabClient(
            url="https://gitlab.com", token="token", gl_instance=mock_gitlab
        )

        # Arrange - Mapper with default_org
        group_mapper = GroupMapper(
            mapping={"specific-group": "specific-org"}, default_org="catch-all-org"
        )
        metadata_mapper = MetadataMapper()

        # Act
        projects = gitlab_client.list_projects("random-group")
        project_details = gitlab_client.get_project_details(projects[0]["id"])
        github_org = group_mapper.get_github_org_for_project(project_details.path_with_namespace)

        # Assert - Should use default_org
        assert github_org == "catch-all-org"
