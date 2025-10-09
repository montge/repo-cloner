"""Unit tests for flatten mapping strategy."""

import pytest

from repo_cloner.group_mapper import FlattenMapper


@pytest.mark.unit
class TestFlattenMapping:
    """Test flatten mapping strategy for GitLab group hierarchy."""

    def test_flattens_simple_group_repo(self):
        """Test that simple group/repo becomes group-repo."""
        # Arrange
        mapper = FlattenMapper()
        gitlab_path = "backend/api-service"

        # Act
        github_name = mapper.map(gitlab_path)

        # Assert
        assert github_name == "backend-api-service"

    def test_flattens_nested_group_hierarchy(self):
        """Test that deeply nested groups are flattened with hyphens."""
        # Arrange
        mapper = FlattenMapper()
        gitlab_path = "infra/kubernetes/deployments/prod"

        # Act
        github_name = mapper.map(gitlab_path)

        # Assert
        assert github_name == "infra-kubernetes-deployments-prod"

    def test_preserves_single_level_repo(self):
        """Test that single-level repo name remains unchanged."""
        # Arrange
        mapper = FlattenMapper()
        gitlab_path = "monorepo"

        # Act
        github_name = mapper.map(gitlab_path)

        # Assert
        assert github_name == "monorepo"

    def test_handles_hyphens_in_original_names(self):
        """Test that existing hyphens are preserved."""
        # Arrange
        mapper = FlattenMapper()
        gitlab_path = "backend/user-service"

        # Act
        github_name = mapper.map(gitlab_path)

        # Assert
        assert github_name == "backend-user-service"

    def test_handles_underscores_in_names(self):
        """Test that underscores are preserved."""
        # Arrange
        mapper = FlattenMapper()
        gitlab_path = "backend/payment_processor"

        # Act
        github_name = mapper.map(gitlab_path)

        # Assert
        assert github_name == "backend-payment_processor"

    def test_flattens_with_custom_separator(self):
        """Test flatten with custom separator (not hyphen)."""
        # Arrange
        mapper = FlattenMapper(separator="_")
        gitlab_path = "backend/api-service"

        # Act
        github_name = mapper.map(gitlab_path)

        # Assert
        assert github_name == "backend_api-service"

    def test_reverse_mapping_from_github_to_gitlab(self):
        """Test reverse mapping from GitHub name to GitLab path."""
        # Arrange
        mapper = FlattenMapper()
        github_name = "backend-api-service"

        # Act
        gitlab_path = mapper.reverse(github_name)

        # Assert
        # Cannot uniquely reverse without context, should return as-is or raise
        assert gitlab_path == github_name

    def test_validates_empty_path(self):
        """Test that empty path raises validation error."""
        # Arrange
        mapper = FlattenMapper()

        # Act & Assert
        with pytest.raises(ValueError) as exc_info:
            mapper.map("")

        assert "empty" in str(exc_info.value).lower()

    def test_validates_none_path(self):
        """Test that None path raises validation error."""
        # Arrange
        mapper = FlattenMapper()

        # Act & Assert
        with pytest.raises((ValueError, TypeError)):
            mapper.map(None)  # type: ignore[arg-type]

    def test_handles_trailing_slashes(self):
        """Test that trailing slashes are handled correctly."""
        # Arrange
        mapper = FlattenMapper()
        gitlab_path = "backend/api-service/"

        # Act
        github_name = mapper.map(gitlab_path)

        # Assert
        assert github_name == "backend-api-service"

    def test_handles_leading_slashes(self):
        """Test that leading slashes are handled correctly."""
        # Arrange
        mapper = FlattenMapper()
        gitlab_path = "/backend/api-service"

        # Act
        github_name = mapper.map(gitlab_path)

        # Assert
        assert github_name == "backend-api-service"

    def test_handles_multiple_consecutive_slashes(self):
        """Test that multiple consecutive slashes are normalized."""
        # Arrange
        mapper = FlattenMapper()
        gitlab_path = "backend//api-service"

        # Act
        github_name = mapper.map(gitlab_path)

        # Assert
        assert github_name == "backend-api-service"

    def test_map_multiple_repos(self):
        """Test mapping multiple repositories in batch."""
        # Arrange
        mapper = FlattenMapper()
        gitlab_paths = [
            "backend/api-service",
            "backend/user-service",
            "frontend/web-app",
        ]

        # Act
        github_names = [mapper.map(path) for path in gitlab_paths]

        # Assert
        assert github_names == [
            "backend-api-service",
            "backend-user-service",
            "frontend-web-app",
        ]

    def test_preserves_case_sensitivity(self):
        """Test that case is preserved during mapping."""
        # Arrange
        mapper = FlattenMapper()
        gitlab_path = "Backend/API-Service"

        # Act
        github_name = mapper.map(gitlab_path)

        # Assert
        assert github_name == "Backend-API-Service"

    def test_handles_numeric_group_names(self):
        """Test that numeric components are handled correctly."""
        # Arrange
        mapper = FlattenMapper()
        gitlab_path = "v2/api/service"

        # Act
        github_name = mapper.map(gitlab_path)

        # Assert
        assert github_name == "v2-api-service"
