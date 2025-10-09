"""Unit tests for prefix mapping strategy."""

import pytest

from repo_cloner.group_mapper import PrefixMapper


@pytest.mark.unit
class TestPrefixMapping:
    """Test prefix mapping strategy for GitLab repositories."""

    def test_adds_prefix_to_repo_name(self):
        """Test that prefix is added to repository name."""
        # Arrange
        mapper = PrefixMapper(prefix="backend")

        # Act
        github_name = mapper.map("mygroup/api-service")

        # Assert
        assert github_name == "backend-api-service"

    def test_drops_parent_groups(self):
        """Test that parent group paths are dropped, only repo name kept."""
        # Arrange
        mapper = PrefixMapper(prefix="infra")

        # Act
        github_name = mapper.map("infra/kubernetes/monitoring/prometheus")

        # Assert - Only last component (repo name) is kept
        assert github_name == "infra-prometheus"

    def test_prefix_with_separator(self):
        """Test custom separator between prefix and repo name."""
        # Arrange
        mapper = PrefixMapper(prefix="fe", separator="_")

        # Act
        github_name = mapper.map("frontend/web-app")

        # Assert
        assert github_name == "fe_web-app"

    def test_no_prefix_returns_repo_name_only(self):
        """Test that without prefix, only repo name is returned."""
        # Arrange
        mapper = PrefixMapper(prefix="")

        # Act
        github_name = mapper.map("backend/api-service")

        # Assert
        assert github_name == "api-service"

    def test_none_prefix_returns_repo_name_only(self):
        """Test that None prefix returns only repo name."""
        # Arrange
        mapper = PrefixMapper(prefix=None)

        # Act
        github_name = mapper.map("backend/api-service")

        # Assert
        assert github_name == "api-service"

    def test_single_level_repo_with_prefix(self):
        """Test that single-level repo gets prefix added."""
        # Arrange
        mapper = PrefixMapper(prefix="legacy")

        # Act
        github_name = mapper.map("monorepo")

        # Assert
        assert github_name == "legacy-monorepo"

    def test_handles_trailing_slashes(self):
        """Test that trailing slashes are handled correctly."""
        # Arrange
        mapper = PrefixMapper(prefix="be")

        # Act
        github_name = mapper.map("backend/api-service/")

        # Assert
        assert github_name == "be-api-service"

    def test_handles_leading_slashes(self):
        """Test that leading slashes are handled correctly."""
        # Arrange
        mapper = PrefixMapper(prefix="be")

        # Act
        github_name = mapper.map("/backend/api-service")

        # Assert
        assert github_name == "be-api-service"

    def test_validates_empty_path(self):
        """Test that empty path raises validation error."""
        # Arrange
        mapper = PrefixMapper(prefix="be")

        # Act & Assert
        with pytest.raises(ValueError) as exc_info:
            mapper.map("")

        assert "empty" in str(exc_info.value).lower()

    def test_validates_none_path(self):
        """Test that None path raises validation error."""
        # Arrange
        mapper = PrefixMapper(prefix="be")

        # Act & Assert
        with pytest.raises((ValueError, TypeError)):
            mapper.map(None)  # type: ignore[arg-type]

    def test_extracts_repo_name_from_nested_path(self):
        """Test extraction of repository name from deeply nested path."""
        # Arrange
        mapper = PrefixMapper(prefix="svc")

        # Act
        github_name = mapper.map("company/division/team/project/service")

        # Assert - Only 'service' is kept
        assert github_name == "svc-service"

    def test_preserves_hyphens_in_repo_name(self):
        """Test that hyphens in original repo name are preserved."""
        # Arrange
        mapper = PrefixMapper(prefix="api")

        # Act
        github_name = mapper.map("backend/user-management-service")

        # Assert
        assert github_name == "api-user-management-service"

    def test_preserves_underscores_in_repo_name(self):
        """Test that underscores in original repo name are preserved."""
        # Arrange
        mapper = PrefixMapper(prefix="db")

        # Act
        github_name = mapper.map("backend/payment_processor")

        # Assert
        assert github_name == "db-payment_processor"

    def test_map_multiple_repos_with_same_prefix(self):
        """Test mapping multiple repositories with same prefix."""
        # Arrange
        mapper = PrefixMapper(prefix="backend")
        paths = [
            "backend/api-service",
            "backend/user-service",
            "backend/payment-service",
        ]

        # Act
        github_names = [mapper.map(path) for path in paths]

        # Assert
        assert github_names == [
            "backend-api-service",
            "backend-user-service",
            "backend-payment-service",
        ]

    def test_preserves_case_in_repo_name(self):
        """Test that case is preserved in repository name."""
        # Arrange
        mapper = PrefixMapper(prefix="Legacy")

        # Act
        github_name = mapper.map("OldProjects/ImportantService")

        # Assert
        assert github_name == "Legacy-ImportantService"

    def test_numeric_repo_names(self):
        """Test handling of numeric repository names."""
        # Arrange
        mapper = PrefixMapper(prefix="v2")

        # Act
        github_name = mapper.map("apis/v3-service")

        # Assert
        assert github_name == "v2-v3-service"

    def test_reverse_mapping_not_possible(self):
        """Test that reverse mapping returns name as-is (lossy operation)."""
        # Arrange
        mapper = PrefixMapper(prefix="be")
        github_name = "be-api-service"

        # Act
        result = mapper.reverse(github_name)

        # Assert - Cannot uniquely reverse without original path
        assert result == github_name

    def test_default_separator_is_hyphen(self):
        """Test that default separator is hyphen."""
        # Arrange
        mapper = PrefixMapper(prefix="test")

        # Act
        github_name = mapper.map("group/repo")

        # Assert
        assert github_name == "test-repo"

    def test_empty_separator_concatenates_directly(self):
        """Test that empty separator concatenates prefix and repo name."""
        # Arrange
        mapper = PrefixMapper(prefix="old", separator="")

        # Act
        github_name = mapper.map("legacy/service")

        # Assert
        assert github_name == "oldservice"

    def test_multiple_consecutive_slashes_normalized(self):
        """Test that multiple consecutive slashes are normalized."""
        # Arrange
        mapper = PrefixMapper(prefix="be")

        # Act
        github_name = mapper.map("backend//api-service")

        # Assert
        assert github_name == "be-api-service"
