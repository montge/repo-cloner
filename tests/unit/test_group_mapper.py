"""Unit tests for GroupMapper (group hierarchy mapping)."""

from repo_cloner.group_mapper import (
    GroupMapper,
    MappingConfig,
    MappingStrategy,
)


class TestFlattenStrategy:
    """Tests for FLATTEN mapping strategy."""

    def test_flatten_basic(self):
        """Test basic flatten strategy with default separator."""
        config = MappingConfig(strategy=MappingStrategy.FLATTEN)
        mapper = GroupMapper(config)

        result = mapper.map_repository_name("company/backend/services/auth")
        assert result == "company-backend-services-auth"

    def test_flatten_custom_separator(self):
        """Test flatten with underscore separator."""
        config = MappingConfig(strategy=MappingStrategy.FLATTEN, separator="_")
        mapper = GroupMapper(config)

        result = mapper.map_repository_name("company/backend/auth")
        assert result == "company_backend_auth"

    def test_flatten_strip_parent_group(self):
        """Test flatten with strip_parent_group enabled."""
        config = MappingConfig(
            strategy=MappingStrategy.FLATTEN,
            strip_parent_group=True,
        )
        mapper = GroupMapper(config)

        result = mapper.map_repository_name("company/backend/services/auth")
        assert result == "backend-services-auth"

    def test_flatten_keep_last_n_levels(self):
        """Test flatten with keep_last_n_levels."""
        config = MappingConfig(
            strategy=MappingStrategy.FLATTEN,
            keep_last_n_levels=2,
        )
        mapper = GroupMapper(config)

        result = mapper.map_repository_name("company/backend/services/auth")
        assert result == "services-auth"

    def test_flatten_strip_parent_and_keep_last_n(self):
        """Test flatten with both strip_parent_group and keep_last_n_levels."""
        config = MappingConfig(
            strategy=MappingStrategy.FLATTEN,
            strip_parent_group=True,
            keep_last_n_levels=2,
        )
        mapper = GroupMapper(config)

        result = mapper.map_repository_name("company/backend/services/auth")
        assert result == "services-auth"

    def test_flatten_single_level(self):
        """Test flatten with single-level path (no groups)."""
        config = MappingConfig(strategy=MappingStrategy.FLATTEN)
        mapper = GroupMapper(config)

        result = mapper.map_repository_name("standalone-repo")
        assert result == "standalone-repo"

    def test_flatten_deep_nesting(self):
        """Test flatten with deeply nested groups."""
        config = MappingConfig(strategy=MappingStrategy.FLATTEN)
        mapper = GroupMapper(config)

        result = mapper.map_repository_name("org/dept/team/project/service/repo")
        assert result == "org-dept-team-project-service-repo"


class TestPrefixStrategy:
    """Tests for PREFIX mapping strategy."""

    def test_prefix_repo_name_only(self):
        """Test prefix strategy with just repository name (default)."""
        config = MappingConfig(strategy=MappingStrategy.PREFIX)
        mapper = GroupMapper(config)

        result = mapper.map_repository_name("company/backend/services/auth")
        assert result == "auth"

    def test_prefix_keep_last_n_levels_1(self):
        """Test prefix with keep_last_n_levels=1."""
        config = MappingConfig(
            strategy=MappingStrategy.PREFIX,
            keep_last_n_levels=1,
        )
        mapper = GroupMapper(config)

        result = mapper.map_repository_name("company/backend/services/auth")
        assert result == "auth"

    def test_prefix_keep_last_n_levels_2(self):
        """Test prefix with keep_last_n_levels=2."""
        config = MappingConfig(
            strategy=MappingStrategy.PREFIX,
            keep_last_n_levels=2,
        )
        mapper = GroupMapper(config)

        result = mapper.map_repository_name("company/backend/services/auth")
        assert result == "services-auth"

    def test_prefix_keep_last_n_levels_3(self):
        """Test prefix with keep_last_n_levels=3."""
        config = MappingConfig(
            strategy=MappingStrategy.PREFIX,
            keep_last_n_levels=3,
        )
        mapper = GroupMapper(config)

        result = mapper.map_repository_name("company/backend/services/auth")
        assert result == "backend-services-auth"

    def test_prefix_custom_separator(self):
        """Test prefix with underscore separator."""
        config = MappingConfig(
            strategy=MappingStrategy.PREFIX,
            keep_last_n_levels=2,
            separator="_",
        )
        mapper = GroupMapper(config)

        result = mapper.map_repository_name("company/backend/auth")
        assert result == "backend_auth"

    def test_prefix_single_level(self):
        """Test prefix with single-level path."""
        config = MappingConfig(strategy=MappingStrategy.PREFIX)
        mapper = GroupMapper(config)

        result = mapper.map_repository_name("standalone-repo")
        assert result == "standalone-repo"


class TestFullPathStrategy:
    """Tests for FULL_PATH mapping strategy."""

    def test_full_path_default_separator(self):
        """Test full_path with default hyphen separator."""
        config = MappingConfig(strategy=MappingStrategy.FULL_PATH)
        mapper = GroupMapper(config)

        result = mapper.map_repository_name("company/backend/services/auth")
        assert result == "company-backend-services-auth"

    def test_full_path_underscore_separator(self):
        """Test full_path with underscore separator."""
        config = MappingConfig(
            strategy=MappingStrategy.FULL_PATH,
            separator="_",
        )
        mapper = GroupMapper(config)

        result = mapper.map_repository_name("company/backend/auth")
        assert result == "company_backend_auth"

    def test_full_path_single_level(self):
        """Test full_path with single-level path."""
        config = MappingConfig(strategy=MappingStrategy.FULL_PATH)
        mapper = GroupMapper(config)

        result = mapper.map_repository_name("standalone-repo")
        assert result == "standalone-repo"

    def test_full_path_deep_nesting(self):
        """Test full_path with deeply nested groups."""
        config = MappingConfig(strategy=MappingStrategy.FULL_PATH)
        mapper = GroupMapper(config)

        result = mapper.map_repository_name("org/dept/team/project/service/repo")
        assert result == "org-dept-team-project-service-repo"


class TestCustomStrategy:
    """Tests for CUSTOM mapping strategy."""

    def test_custom_exact_match(self):
        """Test custom strategy with exact path match."""
        config = MappingConfig(
            strategy=MappingStrategy.CUSTOM,
            custom_mappings={
                "company/backend/services/auth": "be-auth",
            },
        )
        mapper = GroupMapper(config)

        result = mapper.map_repository_name("company/backend/services/auth")
        assert result == "be-auth"

    def test_custom_prefix_match(self):
        """Test custom strategy with prefix match."""
        config = MappingConfig(
            strategy=MappingStrategy.CUSTOM,
            custom_mappings={
                "company/backend": "be",
                "company/frontend": "fe",
            },
        )
        mapper = GroupMapper(config)

        # Should match "company/backend" prefix and replace
        result = mapper.map_repository_name("company/backend/services/auth")
        assert result == "be-services-auth"

    def test_custom_longest_prefix_match(self):
        """Test custom strategy prioritizes longest prefix match."""
        config = MappingConfig(
            strategy=MappingStrategy.CUSTOM,
            custom_mappings={
                "company": "c",
                "company/backend": "be",
                "company/backend/services": "be-svc",
            },
        )
        mapper = GroupMapper(config)

        # Should match longest prefix: "company/backend/services"
        result = mapper.map_repository_name("company/backend/services/auth")
        assert result == "be-svc-auth"

    def test_custom_fallback_to_flatten(self):
        """Test custom strategy fallback when no match found."""
        config = MappingConfig(
            strategy=MappingStrategy.CUSTOM,
            custom_mappings={
                "company/backend": "be",
            },
            fallback_strategy=MappingStrategy.FLATTEN,
        )
        mapper = GroupMapper(config)

        # No match for "company/frontend" - should fallback to flatten
        result = mapper.map_repository_name("company/frontend/webapp")
        assert result == "company-frontend-webapp"

    def test_custom_fallback_to_prefix(self):
        """Test custom strategy fallback to prefix strategy."""
        config = MappingConfig(
            strategy=MappingStrategy.CUSTOM,
            custom_mappings={
                "company/backend": "be",
            },
            fallback_strategy=MappingStrategy.PREFIX,
        )
        mapper = GroupMapper(config)

        # No match - should fallback to prefix (repo name only)
        result = mapper.map_repository_name("company/frontend/webapp")
        assert result == "webapp"

    def test_custom_no_mappings(self):
        """Test custom strategy with empty mappings (always fallback)."""
        config = MappingConfig(
            strategy=MappingStrategy.CUSTOM,
            custom_mappings={},
            fallback_strategy=MappingStrategy.FLATTEN,
        )
        mapper = GroupMapper(config)

        result = mapper.map_repository_name("company/backend/auth")
        assert result == "company-backend-auth"


class TestExtractTopics:
    """Tests for extract_topics() method."""

    def test_extract_topics_basic(self):
        """Test extracting topics from multi-level path."""
        config = MappingConfig(use_topics=True)
        mapper = GroupMapper(config)

        topics = mapper.extract_topics("company/backend/services/auth")
        assert topics == ["company", "backend", "services"]

    def test_extract_topics_strip_parent_group(self):
        """Test extracting topics with strip_parent_group."""
        config = MappingConfig(use_topics=True, strip_parent_group=True)
        mapper = GroupMapper(config)

        topics = mapper.extract_topics("company/backend/services/auth")
        assert topics == ["backend", "services"]

    def test_extract_topics_single_level(self):
        """Test extracting topics from single-level path."""
        config = MappingConfig(use_topics=True)
        mapper = GroupMapper(config)

        topics = mapper.extract_topics("standalone-repo")
        assert topics == []

    def test_extract_topics_two_levels(self):
        """Test extracting topics from two-level path."""
        config = MappingConfig(use_topics=True)
        mapper = GroupMapper(config)

        topics = mapper.extract_topics("company/repo")
        assert topics == ["company"]

    def test_extract_topics_disabled(self):
        """Test extract_topics when use_topics=False."""
        config = MappingConfig(use_topics=False)
        mapper = GroupMapper(config)

        topics = mapper.extract_topics("company/backend/services/auth")
        assert topics == []

    def test_extract_topics_lowercase(self):
        """Test topics are converted to lowercase."""
        config = MappingConfig(use_topics=True)
        mapper = GroupMapper(config)

        topics = mapper.extract_topics("Company/Backend/Services/Auth")
        assert topics == ["company", "backend", "services"]


class TestValidateGitHubName:
    """Tests for validate_github_name() method."""

    def test_validate_valid_name(self):
        """Test validation of valid GitHub repository name."""
        mapper = GroupMapper(MappingConfig())

        is_valid, error = mapper.validate_github_name("my-repo")
        assert is_valid is True
        assert error is None

    def test_validate_valid_with_underscores(self):
        """Test validation with underscores."""
        mapper = GroupMapper(MappingConfig())

        is_valid, error = mapper.validate_github_name("my_repo_name")
        assert is_valid is True
        assert error is None

    def test_validate_valid_with_periods(self):
        """Test validation with periods."""
        mapper = GroupMapper(MappingConfig())

        is_valid, error = mapper.validate_github_name("my.repo.name")
        assert is_valid is True
        assert error is None

    def test_validate_valid_with_numbers(self):
        """Test validation with numbers."""
        mapper = GroupMapper(MappingConfig())

        is_valid, error = mapper.validate_github_name("repo-123")
        assert is_valid is True
        assert error is None

    def test_validate_exceeds_100_chars(self):
        """Test validation fails for names exceeding 100 characters."""
        mapper = GroupMapper(MappingConfig())

        long_name = "x" * 101
        is_valid, error = mapper.validate_github_name(long_name)
        assert is_valid is False
        assert "exceeds 100 characters" in error

    def test_validate_exactly_100_chars(self):
        """Test validation passes for exactly 100 characters."""
        mapper = GroupMapper(MappingConfig())

        name = "x" * 100
        is_valid, error = mapper.validate_github_name(name)
        assert is_valid is True
        assert error is None

    def test_validate_starts_with_hyphen(self):
        """Test validation fails for names starting with hyphen."""
        mapper = GroupMapper(MappingConfig())

        is_valid, error = mapper.validate_github_name("-invalid")
        assert is_valid is False
        assert "cannot start with hyphen, underscore, or period" in error

    def test_validate_starts_with_underscore(self):
        """Test validation fails for names starting with underscore."""
        mapper = GroupMapper(MappingConfig())

        is_valid, error = mapper.validate_github_name("_invalid")
        assert is_valid is False
        assert "cannot start with hyphen, underscore, or period" in error

    def test_validate_starts_with_period(self):
        """Test validation fails for names starting with period."""
        mapper = GroupMapper(MappingConfig())

        is_valid, error = mapper.validate_github_name(".invalid")
        assert is_valid is False
        assert "cannot start with hyphen, underscore, or period" in error

    def test_validate_ends_with_git(self):
        """Test validation fails for names ending with .git."""
        mapper = GroupMapper(MappingConfig())

        is_valid, error = mapper.validate_github_name("my-repo.git")
        assert is_valid is False
        assert "cannot end with .git" in error

    def test_validate_dot_only(self):
        """Test validation fails for '.' name."""
        mapper = GroupMapper(MappingConfig())

        is_valid, error = mapper.validate_github_name(".")
        assert is_valid is False
        assert "cannot be '.' or '..'" in error

    def test_validate_dot_dot_only(self):
        """Test validation fails for '..' name."""
        mapper = GroupMapper(MappingConfig())

        is_valid, error = mapper.validate_github_name("..")
        assert is_valid is False
        assert "cannot be '.' or '..'" in error

    def test_validate_invalid_characters_space(self):
        """Test validation fails for names with spaces."""
        mapper = GroupMapper(MappingConfig())

        is_valid, error = mapper.validate_github_name("my repo")
        assert is_valid is False
        assert "invalid characters" in error

    def test_validate_invalid_characters_slash(self):
        """Test validation fails for names with slashes."""
        mapper = GroupMapper(MappingConfig())

        is_valid, error = mapper.validate_github_name("my/repo")
        assert is_valid is False
        assert "invalid characters" in error

    def test_validate_invalid_characters_special(self):
        """Test validation fails for names with special characters."""
        mapper = GroupMapper(MappingConfig())

        is_valid, error = mapper.validate_github_name("my@repo")
        assert is_valid is False
        assert "invalid characters" in error


class TestDetectConflicts:
    """Tests for detect_conflicts() method."""

    def test_no_conflicts(self):
        """Test detect_conflicts when all repos map to unique names."""
        config = MappingConfig(strategy=MappingStrategy.FLATTEN)
        mapper = GroupMapper(config)

        paths = [
            "company/backend/auth",
            "company/backend/payment",
            "company/frontend/webapp",
        ]

        conflicts = mapper.detect_conflicts(paths)
        assert conflicts == {}

    def test_conflicts_with_prefix_strategy(self):
        """Test conflict detection with PREFIX strategy."""
        config = MappingConfig(
            strategy=MappingStrategy.PREFIX,
            keep_last_n_levels=1,
        )
        mapper = GroupMapper(config)

        paths = [
            "company/backend/auth",
            "company/frontend/auth",
        ]

        conflicts = mapper.detect_conflicts(paths)
        assert "auth" in conflicts
        assert len(conflicts["auth"]) == 2
        assert "company/backend/auth" in conflicts["auth"]
        assert "company/frontend/auth" in conflicts["auth"]

    def test_conflicts_multiple_groups(self):
        """Test multiple conflicts detected."""
        config = MappingConfig(
            strategy=MappingStrategy.PREFIX,
            keep_last_n_levels=1,
        )
        mapper = GroupMapper(config)

        paths = [
            "company/backend/auth",
            "company/frontend/auth",
            "company/backend/api",
            "company/infrastructure/api",
        ]

        conflicts = mapper.detect_conflicts(paths)
        assert len(conflicts) == 2
        assert "auth" in conflicts
        assert "api" in conflicts
        assert len(conflicts["auth"]) == 2
        assert len(conflicts["api"]) == 2

    def test_conflicts_three_way(self):
        """Test three repos mapping to same name."""
        config = MappingConfig(
            strategy=MappingStrategy.PREFIX,
            keep_last_n_levels=1,
        )
        mapper = GroupMapper(config)

        paths = [
            "company/backend/service",
            "company/frontend/service",
            "company/infrastructure/service",
        ]

        conflicts = mapper.detect_conflicts(paths)
        assert "service" in conflicts
        assert len(conflicts["service"]) == 3

    def test_no_conflicts_with_flatten(self):
        """Test flatten strategy typically avoids conflicts."""
        config = MappingConfig(strategy=MappingStrategy.FLATTEN)
        mapper = GroupMapper(config)

        paths = [
            "company/backend/auth",
            "company/frontend/auth",
            "company/infrastructure/auth",
        ]

        conflicts = mapper.detect_conflicts(paths)
        # Flatten creates unique names:
        # company-backend-auth, company-frontend-auth, company-infrastructure-auth
        assert conflicts == {}

    def test_conflicts_custom_strategy(self):
        """Test conflict detection with custom strategy."""
        config = MappingConfig(
            strategy=MappingStrategy.CUSTOM,
            custom_mappings={
                "company/backend": "be",
                "company/frontend": "fe",
            },
            fallback_strategy=MappingStrategy.PREFIX,
        )
        mapper = GroupMapper(config)

        paths = [
            "company/backend/auth",  # Maps to be-auth
            "other/auth",  # Maps to auth (fallback)
        ]

        conflicts = mapper.detect_conflicts(paths)
        # No conflicts: be-auth vs auth
        assert conflicts == {}

    def test_empty_paths_list(self):
        """Test detect_conflicts with empty list."""
        mapper = GroupMapper(MappingConfig())

        conflicts = mapper.detect_conflicts([])
        assert conflicts == {}


class TestIntegrationScenarios:
    """Integration tests combining multiple features."""

    def test_real_world_backend_group(self):
        """Test realistic backend group scenario."""
        config = MappingConfig(
            strategy=MappingStrategy.FLATTEN,
            strip_parent_group=True,
        )
        mapper = GroupMapper(config)

        paths = [
            "test6452742/again/backend-auth-service",
            "test6452742/again/backend-payment-api",
            "test6452742/again/backend-notification-service",
        ]

        # Test mappings
        assert mapper.map_repository_name(paths[0]) == "again-backend-auth-service"
        assert mapper.map_repository_name(paths[1]) == "again-backend-payment-api"
        assert mapper.map_repository_name(paths[2]) == "again-backend-notification-service"

        # Test no conflicts
        conflicts = mapper.detect_conflicts(paths)
        assert conflicts == {}

        # Test topics
        topics = mapper.extract_topics(paths[0])
        assert "again" in topics

    def test_prefix_strategy_with_topics(self):
        """Test prefix strategy combined with topic extraction."""
        config = MappingConfig(
            strategy=MappingStrategy.PREFIX,
            keep_last_n_levels=2,
            use_topics=True,
            strip_parent_group=True,
        )
        mapper = GroupMapper(config)

        gitlab_path = "company/backend/services/auth-service"

        # Mapping: keep last 2 levels = services-auth-service
        github_name = mapper.map_repository_name(gitlab_path)
        assert github_name == "services-auth-service"

        # Topics: parent groups (minus company) = backend, services
        topics = mapper.extract_topics(gitlab_path)
        assert topics == ["backend", "services"]

    def test_validation_catches_long_names(self):
        """Test validation prevents excessively long flattened names."""
        config = MappingConfig(strategy=MappingStrategy.FULL_PATH)
        mapper = GroupMapper(config)

        # Create very long path
        long_path = "/".join(["group"] * 20) + "/repo"
        github_name = mapper.map_repository_name(long_path)

        is_valid, error = mapper.validate_github_name(github_name)
        assert is_valid is False
        assert "exceeds 100 characters" in error

    def test_custom_with_validation(self):
        """Test custom mapping with validation."""
        config = MappingConfig(
            strategy=MappingStrategy.CUSTOM,
            custom_mappings={
                "company/backend": "backend",
            },
        )
        mapper = GroupMapper(config)

        gitlab_path = "company/backend/auth"
        github_name = mapper.map_repository_name(gitlab_path)
        assert github_name == "backend-auth"

        is_valid, error = mapper.validate_github_name(github_name)
        assert is_valid is True
        assert error is None
