"""Unit tests for GitLabClient class."""

from unittest.mock import Mock

import pytest

from repo_cloner.gitlab_client import GitLabClient


@pytest.mark.unit
class TestGitLabClient:
    """Test GitLabClient API operations."""

    def test_list_projects_returns_projects_from_group(self):
        """Test that list_projects retrieves all projects in a group."""
        # Arrange
        mock_gl = Mock()
        mock_group = Mock()
        mock_project1 = Mock()
        mock_project1.id = 1
        mock_project1.name = "repo1"
        mock_project1.path_with_namespace = "group/repo1"
        mock_project1.web_url = "https://gitlab.com/group/repo1"

        mock_project2 = Mock()
        mock_project2.id = 2
        mock_project2.name = "repo2"
        mock_project2.path_with_namespace = "group/repo2"
        mock_project2.web_url = "https://gitlab.com/group/repo2"

        # Use side_effect to return projects on first call, empty list on second call
        mock_group.projects.list.side_effect = [[mock_project1, mock_project2], []]
        mock_gl.groups.get.return_value = mock_group

        client = GitLabClient(url="https://gitlab.com", token="test-token", gl_instance=mock_gl)

        # Act
        projects = client.list_projects("group")

        # Assert
        assert len(projects) == 2
        assert projects[0]["name"] == "repo1"
        assert projects[0]["path_with_namespace"] == "group/repo1"
        assert projects[1]["name"] == "repo2"
        mock_gl.groups.get.assert_called_once_with("group")

    def test_list_projects_handles_pagination(self):
        """Test that list_projects handles paginated results."""
        # Arrange
        mock_gl = Mock()
        mock_group = Mock()

        # Create 3 pages of results
        page1 = [
            Mock(id=i, name=f"repo{i}", path_with_namespace=f"g/repo{i}") for i in range(1, 21)
        ]
        page2 = [
            Mock(id=i, name=f"repo{i}", path_with_namespace=f"g/repo{i}") for i in range(21, 41)
        ]
        page3 = [
            Mock(id=i, name=f"repo{i}", path_with_namespace=f"g/repo{i}") for i in range(41, 45)
        ]

        mock_group.projects.list.side_effect = [page1, page2, page3, []]
        mock_gl.groups.get.return_value = mock_group

        client = GitLabClient(url="https://gitlab.com", token="test-token", gl_instance=mock_gl)

        # Act
        projects = client.list_projects("group")

        # Assert
        assert len(projects) == 44
        assert mock_group.projects.list.call_count >= 3

    def test_get_project_details_returns_metadata(self):
        """Test that get_project_details includes description and tags."""
        # Arrange
        mock_gl = Mock()
        mock_project = Mock()
        mock_project.id = 123
        mock_project.name = "awesome-repo"
        mock_project.path_with_namespace = "group/awesome-repo"
        mock_project.description = "An awesome repository for testing"
        mock_project.topics = ["python", "testing", "ci-cd"]
        mock_project.visibility = "private"
        mock_project.web_url = "https://gitlab.com/group/awesome-repo"
        mock_project.default_branch = "main"

        mock_gl.projects.get.return_value = mock_project

        client = GitLabClient(url="https://gitlab.com", token="test-token", gl_instance=mock_gl)

        # Act
        details = client.get_project_details(123)

        # Assert
        assert details.name == "awesome-repo"
        assert details.description == "An awesome repository for testing"
        assert details.topics == ["python", "testing", "ci-cd"]
        assert details.visibility == "private"
        assert details.default_branch == "main"
        mock_gl.projects.get.assert_called_once_with(123)

    def test_get_project_details_handles_missing_description(self):
        """Test that get_project_details handles projects without descriptions."""
        # Arrange
        mock_gl = Mock()
        mock_project = Mock()
        mock_project.id = 456
        mock_project.name = "minimal-repo"
        mock_project.path_with_namespace = "group/minimal-repo"
        mock_project.description = None
        mock_project.topics = []
        mock_project.visibility = "public"
        mock_project.default_branch = "master"

        mock_gl.projects.get.return_value = mock_project

        client = GitLabClient(url="https://gitlab.com", token="test-token", gl_instance=mock_gl)

        # Act
        details = client.get_project_details(456)

        # Assert
        assert details.name == "minimal-repo"
        assert details.description == ""
        assert details.topics == []
        assert details.visibility == "public"

    def test_list_projects_handles_api_error(self):
        """Test that list_projects handles GitLab API errors gracefully."""
        # Arrange
        mock_gl = Mock()
        mock_gl.groups.get.side_effect = Exception("Group not found")

        client = GitLabClient(url="https://gitlab.com", token="test-token", gl_instance=mock_gl)

        # Act & Assert
        with pytest.raises(Exception, match="Group not found"):
            client.list_projects("nonexistent-group")

    def test_supports_self_hosted_gitlab(self):
        """Test that client works with self-hosted GitLab instances."""
        # Arrange
        mock_gl = Mock()
        mock_group = Mock()
        mock_group.projects.list.return_value = []
        mock_gl.groups.get.return_value = mock_group

        client = GitLabClient(
            url="https://gitlab.example.com", token="custom-token", gl_instance=mock_gl
        )

        # Act
        projects = client.list_projects("test-group")

        # Assert
        assert projects == []
        mock_gl.groups.get.assert_called_once_with("test-group")

    def test_get_project_details_includes_clone_url(self):
        """Test that project details include HTTP clone URL."""
        # Arrange
        mock_gl = Mock()
        mock_project = Mock()
        mock_project.id = 789
        mock_project.name = "clone-test"
        mock_project.path_with_namespace = "org/clone-test"
        mock_project.http_url_to_repo = "https://gitlab.com/org/clone-test.git"
        mock_project.description = "Test"
        mock_project.topics = []
        mock_project.visibility = "public"
        mock_project.default_branch = "main"

        mock_gl.projects.get.return_value = mock_project

        client = GitLabClient(url="https://gitlab.com", token="test-token", gl_instance=mock_gl)

        # Act
        details = client.get_project_details(789)

        # Assert
        assert details.http_url_to_repo == "https://gitlab.com/org/clone-test.git"

    def test_list_projects_includes_subgroups_by_default(self):
        """Test that list_projects includes nested subgroup projects by default."""
        # Arrange
        mock_gl = Mock()
        mock_group = Mock()

        # Create mock projects from different subgroup levels
        # company/ (no direct projects)
        # company/backend/auth-service (project)
        # company/backend/api/rest-api (project)
        # company/frontend/web-app (project)
        mock_project1 = Mock()
        mock_project1.id = 1
        mock_project1.name = "auth-service"
        mock_project1.path_with_namespace = "company/backend/auth-service"
        mock_project1.web_url = "https://gitlab.com/company/backend/auth-service"

        mock_project2 = Mock()
        mock_project2.id = 2
        mock_project2.name = "rest-api"
        mock_project2.path_with_namespace = "company/backend/api/rest-api"
        mock_project2.web_url = "https://gitlab.com/company/backend/api/rest-api"

        mock_project3 = Mock()
        mock_project3.id = 3
        mock_project3.name = "web-app"
        mock_project3.path_with_namespace = "company/frontend/web-app"
        mock_project3.web_url = "https://gitlab.com/company/frontend/web-app"

        # Mock projects.list with include_subgroups=True returning all nested projects
        mock_group.projects.list.side_effect = [
            [mock_project1, mock_project2, mock_project3],
            [],
        ]
        mock_gl.groups.get.return_value = mock_group

        client = GitLabClient(url="https://gitlab.com", token="test-token", gl_instance=mock_gl)

        # Act
        projects = client.list_projects("company")

        # Assert
        assert len(projects) == 3
        assert projects[0]["path_with_namespace"] == "company/backend/auth-service"
        assert projects[1]["path_with_namespace"] == "company/backend/api/rest-api"
        assert projects[2]["path_with_namespace"] == "company/frontend/web-app"

        # Verify include_subgroups=True was passed in the first call
        assert mock_group.projects.list.call_count >= 1
        first_call = mock_group.projects.list.call_args_list[0]
        assert first_call[1]["include_subgroups"] is True

    def test_list_projects_can_exclude_subgroups(self):
        """Test that list_projects can list only direct projects when include_subgroups=False."""
        # Arrange
        mock_gl = Mock()
        mock_group = Mock()

        # Only direct projects in the group (no nested subgroup projects)
        mock_project = Mock()
        mock_project.id = 1
        mock_project.name = "direct-project"
        mock_project.path_with_namespace = "company/direct-project"
        mock_project.web_url = "https://gitlab.com/company/direct-project"

        mock_group.projects.list.side_effect = [[mock_project], []]
        mock_gl.groups.get.return_value = mock_group

        client = GitLabClient(url="https://gitlab.com", token="test-token", gl_instance=mock_gl)

        # Act
        projects = client.list_projects("company", include_subgroups=False)

        # Assert
        assert len(projects) == 1
        assert projects[0]["name"] == "direct-project"

        # Verify include_subgroups=False was passed in the first call
        assert mock_group.projects.list.call_count >= 1
        first_call = mock_group.projects.list.call_args_list[0]
        assert first_call[1]["include_subgroups"] is False
