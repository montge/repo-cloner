"""Unit tests for MetadataMapper class."""

import pytest

from repo_cloner.gitlab_client import ProjectDetails
from repo_cloner.metadata_mapper import MetadataMapper


@pytest.mark.unit
class TestMetadataMapper:
    """Test MetadataMapper for GitLab to GitHub metadata conversion."""

    def test_maps_description_from_gitlab_to_github(self):
        """Test that GitLab description is mapped to GitHub description."""
        # Arrange
        gitlab_project = ProjectDetails(
            id=123,
            name="test-repo",
            path_with_namespace="group/test-repo",
            description="An awesome test repository",
            topics=["python"],
            visibility="private",
            default_branch="main",
            http_url_to_repo="https://gitlab.com/group/test-repo.git",
        )
        mapper = MetadataMapper()

        # Act
        github_settings = mapper.map_gitlab_to_github(gitlab_project)

        # Assert
        assert github_settings["description"] == "An awesome test repository"

    def test_maps_topics_from_gitlab_to_github(self):
        """Test that GitLab topics are mapped to GitHub topics."""
        # Arrange
        gitlab_project = ProjectDetails(
            id=456,
            name="tagged-repo",
            path_with_namespace="org/tagged-repo",
            description="Repo with tags",
            topics=["python", "testing", "ci-cd", "automation"],
            visibility="public",
            default_branch="main",
            http_url_to_repo="https://gitlab.com/org/tagged-repo.git",
        )
        mapper = MetadataMapper()

        # Act
        github_settings = mapper.map_gitlab_to_github(gitlab_project)

        # Assert
        assert github_settings["topics"] == ["python", "testing", "ci-cd", "automation"]

    def test_maps_visibility_private_to_github(self):
        """Test that GitLab private visibility maps to GitHub private=True."""
        # Arrange
        gitlab_project = ProjectDetails(
            id=789,
            name="private-repo",
            path_with_namespace="org/private-repo",
            description="Private repository",
            topics=[],
            visibility="private",
            default_branch="main",
            http_url_to_repo="https://gitlab.com/org/private-repo.git",
        )
        mapper = MetadataMapper()

        # Act
        github_settings = mapper.map_gitlab_to_github(gitlab_project)

        # Assert
        assert github_settings["private"] is True

    def test_maps_visibility_public_to_github(self):
        """Test that GitLab public visibility maps to GitHub private=False."""
        # Arrange
        gitlab_project = ProjectDetails(
            id=101,
            name="public-repo",
            path_with_namespace="org/public-repo",
            description="Public repository",
            topics=[],
            visibility="public",
            default_branch="main",
            http_url_to_repo="https://gitlab.com/org/public-repo.git",
        )
        mapper = MetadataMapper()

        # Act
        github_settings = mapper.map_gitlab_to_github(gitlab_project)

        # Assert
        assert github_settings["private"] is False

    def test_maps_visibility_internal_to_github_private(self):
        """Test that GitLab internal visibility maps to GitHub private=True."""
        # Arrange
        gitlab_project = ProjectDetails(
            id=202,
            name="internal-repo",
            path_with_namespace="org/internal-repo",
            description="Internal repository",
            topics=[],
            visibility="internal",
            default_branch="main",
            http_url_to_repo="https://gitlab.com/org/internal-repo.git",
        )
        mapper = MetadataMapper()

        # Act
        github_settings = mapper.map_gitlab_to_github(gitlab_project)

        # Assert
        # GitLab internal → GitHub private (no internal visibility on GitHub)
        assert github_settings["private"] is True

    def test_maps_default_branch(self):
        """Test that default branch is mapped correctly."""
        # Arrange
        gitlab_project = ProjectDetails(
            id=303,
            name="develop-repo",
            path_with_namespace="org/develop-repo",
            description="Repo with develop branch",
            topics=[],
            visibility="public",
            default_branch="develop",
            http_url_to_repo="https://gitlab.com/org/develop-repo.git",
        )
        mapper = MetadataMapper()

        # Act
        github_settings = mapper.map_gitlab_to_github(gitlab_project)

        # Assert
        assert github_settings["default_branch"] == "develop"

    def test_maps_repository_name_from_path(self):
        """Test that repository name is extracted from path_with_namespace."""
        # Arrange
        gitlab_project = ProjectDetails(
            id=404,
            name="should-not-use-this",
            path_with_namespace="group/subgroup/actual-repo-name",
            description="Test",
            topics=[],
            visibility="public",
            default_branch="main",
            http_url_to_repo="https://gitlab.com/group/subgroup/actual-repo-name.git",
        )
        mapper = MetadataMapper()

        # Act
        github_settings = mapper.map_gitlab_to_github(gitlab_project)

        # Assert
        # Should use last part of path_with_namespace, not the name field
        assert github_settings["name"] == "actual-repo-name"

    def test_handles_empty_description(self):
        """Test that empty description is handled gracefully."""
        # Arrange
        gitlab_project = ProjectDetails(
            id=505,
            name="no-desc-repo",
            path_with_namespace="org/no-desc-repo",
            description="",
            topics=[],
            visibility="public",
            default_branch="main",
            http_url_to_repo="https://gitlab.com/org/no-desc-repo.git",
        )
        mapper = MetadataMapper()

        # Act
        github_settings = mapper.map_gitlab_to_github(gitlab_project)

        # Assert
        assert github_settings["description"] == ""

    def test_handles_empty_topics_list(self):
        """Test that empty topics list is handled gracefully."""
        # Arrange
        gitlab_project = ProjectDetails(
            id=606,
            name="no-topics-repo",
            path_with_namespace="org/no-topics-repo",
            description="No tags",
            topics=[],
            visibility="public",
            default_branch="main",
            http_url_to_repo="https://gitlab.com/org/no-topics-repo.git",
        )
        mapper = MetadataMapper()

        # Act
        github_settings = mapper.map_gitlab_to_github(gitlab_project)

        # Assert
        assert github_settings["topics"] == []

    def test_maps_all_fields_together(self):
        """Test that all fields are mapped correctly in one operation."""
        # Arrange
        gitlab_project = ProjectDetails(
            id=707,
            name="complete-repo",
            path_with_namespace="myorg/complete-repo",
            description="Complete repository with all metadata",
            topics=["python", "gitlab", "migration"],
            visibility="private",
            default_branch="main",
            http_url_to_repo="https://gitlab.com/myorg/complete-repo.git",
        )
        mapper = MetadataMapper()

        # Act
        github_settings = mapper.map_gitlab_to_github(gitlab_project)

        # Assert
        assert github_settings == {
            "name": "complete-repo",
            "description": "Complete repository with all metadata",
            "topics": ["python", "gitlab", "migration"],
            "private": True,
            "default_branch": "main",
        }
