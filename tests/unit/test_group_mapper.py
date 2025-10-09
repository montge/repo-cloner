"""Unit tests for GroupMapper class."""

import pytest

from repo_cloner.group_mapper import GroupMapper


@pytest.mark.unit
class TestGroupMapper:
    """Test GroupMapper for GitLab group to GitHub organization mapping."""

    def test_maps_simple_group_to_org(self):
        """Test that simple GitLab group maps to GitHub organization."""
        # Arrange
        mapper = GroupMapper(mapping={"mygroup": "myorg"})

        # Act
        org_name = mapper.get_github_org("mygroup")

        # Assert
        assert org_name == "myorg"

    def test_maps_nested_group_to_org(self):
        """Test that nested GitLab group maps to GitHub organization."""
        # Arrange
        mapper = GroupMapper(mapping={"mygroup/subgroup": "myorg"})

        # Act
        org_name = mapper.get_github_org("mygroup/subgroup")

        # Assert
        assert org_name == "myorg"

    def test_maps_multiple_groups_to_same_org(self):
        """Test that multiple GitLab groups can map to same GitHub org."""
        # Arrange
        mapper = GroupMapper(
            mapping={
                "team-a": "company-org",
                "team-b": "company-org",
                "team-c": "company-org",
            }
        )

        # Act & Assert
        assert mapper.get_github_org("team-a") == "company-org"
        assert mapper.get_github_org("team-b") == "company-org"
        assert mapper.get_github_org("team-c") == "company-org"

    def test_maps_groups_to_different_orgs(self):
        """Test that different GitLab groups map to different GitHub orgs."""
        # Arrange
        mapper = GroupMapper(
            mapping={
                "frontend": "frontend-org",
                "backend": "backend-org",
                "devops": "infrastructure-org",
            }
        )

        # Act & Assert
        assert mapper.get_github_org("frontend") == "frontend-org"
        assert mapper.get_github_org("backend") == "backend-org"
        assert mapper.get_github_org("devops") == "infrastructure-org"

    def test_raises_error_for_unmapped_group(self):
        """Test that unmapped group raises ValueError."""
        # Arrange
        mapper = GroupMapper(mapping={"mapped-group": "mapped-org"})

        # Act & Assert
        with pytest.raises(ValueError, match="No GitHub organization mapping found"):
            mapper.get_github_org("unmapped-group")

    def test_extracts_org_from_path_with_namespace(self):
        """Test that organization can be extracted from full path."""
        # Arrange
        mapper = GroupMapper(mapping={"mygroup": "myorg"})

        # Act - Pass full path like "mygroup/repo-name"
        org_name = mapper.get_github_org_for_project("mygroup/repo-name")

        # Assert
        assert org_name == "myorg"

    def test_extracts_org_from_nested_path(self):
        """Test organization extraction from nested group path."""
        # Arrange
        mapper = GroupMapper(mapping={"parent/child": "target-org"})

        # Act - Pass full path like "parent/child/repo-name"
        org_name = mapper.get_github_org_for_project("parent/child/repo-name")

        # Assert
        assert org_name == "target-org"

    def test_handles_deep_nesting(self):
        """Test handling of deeply nested GitLab group structures."""
        # Arrange
        mapper = GroupMapper(mapping={"company/division/team": "team-org"})

        # Act
        org_name = mapper.get_github_org_for_project("company/division/team/my-repo")

        # Assert
        assert org_name == "team-org"

    def test_supports_default_org_fallback(self):
        """Test that default_org is used when no mapping found."""
        # Arrange
        mapper = GroupMapper(mapping={"specific-group": "specific-org"}, default_org="default-org")

        # Act
        org_name = mapper.get_github_org("unmapped-group")

        # Assert
        assert org_name == "default-org"

    def test_prefers_explicit_mapping_over_default(self):
        """Test that explicit mapping takes precedence over default_org."""
        # Arrange
        mapper = GroupMapper(mapping={"mapped-group": "mapped-org"}, default_org="default-org")

        # Act
        org_name = mapper.get_github_org("mapped-group")

        # Assert
        assert org_name == "mapped-org"

    def test_handles_empty_mapping_with_default(self):
        """Test that empty mapping dict works with default_org."""
        # Arrange
        mapper = GroupMapper(mapping={}, default_org="catch-all-org")

        # Act
        org_name = mapper.get_github_org("any-group")

        # Assert
        assert org_name == "catch-all-org"

    def test_raises_error_when_no_mapping_and_no_default(self):
        """Test that error is raised when no mapping and no default_org."""
        # Arrange
        mapper = GroupMapper(mapping={})

        # Act & Assert
        with pytest.raises(ValueError, match="No GitHub organization mapping found"):
            mapper.get_github_org("unmapped-group")
