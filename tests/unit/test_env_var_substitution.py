"""Unit tests for environment variable substitution in configuration."""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from repo_cloner.config_loader_enhanced import ConfigLoader


@pytest.mark.unit
class TestEnvVarSubstitution:
    """Test environment variable substitution in YAML configuration."""

    def test_substitutes_simple_env_var(self):
        """Test that ${VAR} is replaced with environment variable value."""
        # Arrange
        config_yaml = """
        gitlab:
          url: https://gitlab.example.com
          token: ${GITLAB_TOKEN}

        github:
          url: https://github.com
          token: ${GITHUB_TOKEN}

        mapping_strategy: flatten

        groups:
          - source: backend
            target_org: myorg
        """

        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.yml"
            config_path.write_text(config_yaml)

            loader = ConfigLoader()

            # Act
            with patch.dict(
                os.environ, {"GITLAB_TOKEN": "glpat_test123", "GITHUB_TOKEN": "ghp_test456"}
            ):
                config = loader.load_from_file(str(config_path))

                # Assert
                assert config["gitlab"]["token"] == "glpat_test123"
                assert config["github"]["token"] == "ghp_test456"

    def test_substitutes_env_var_with_default(self):
        """Test that ${VAR:-default} uses default when VAR not set."""
        # Arrange
        config_yaml = """
        gitlab:
          url: ${GITLAB_URL:-https://gitlab.com}
          token: glpat_test123

        github:
          url: ${GITHUB_URL:-https://github.com}
          token: ghp_test456

        mapping_strategy: flatten

        groups:
          - source: backend
            target_org: myorg
        """

        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.yml"
            config_path.write_text(config_yaml)

            loader = ConfigLoader()

            # Act - Environment variables not set
            with patch.dict(os.environ, {}, clear=True):
                config = loader.load_from_file(str(config_path))

                # Assert - Should use defaults
                assert config["gitlab"]["url"] == "https://gitlab.com"
                assert config["github"]["url"] == "https://github.com"

    def test_env_var_overrides_default_when_set(self):
        """Test that ${VAR:-default} uses VAR when it is set."""
        # Arrange
        config_yaml = """
        gitlab:
          url: ${GITLAB_URL:-https://gitlab.com}
          token: glpat_test123

        github:
          url: https://github.com
          token: ghp_test456

        mapping_strategy: flatten

        groups:
          - source: backend
            target_org: myorg
        """

        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.yml"
            config_path.write_text(config_yaml)

            loader = ConfigLoader()

            # Act - Environment variable is set
            with patch.dict(os.environ, {"GITLAB_URL": "https://gitlab.example.com"}):
                config = loader.load_from_file(str(config_path))

                # Assert - Should use environment variable, not default
                assert config["gitlab"]["url"] == "https://gitlab.example.com"

    def test_raises_error_on_missing_required_env_var(self):
        """Test that ${VAR} without default raises error when VAR not set."""
        # Arrange
        config_yaml = """
        gitlab:
          url: https://gitlab.example.com
          token: ${GITLAB_TOKEN}

        github:
          url: https://github.com
          token: ghp_test456

        mapping_strategy: flatten

        groups:
          - source: backend
            target_org: myorg
        """

        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.yml"
            config_path.write_text(config_yaml)

            loader = ConfigLoader()

            # Act & Assert - GITLAB_TOKEN not set
            with patch.dict(os.environ, {}, clear=True):
                with pytest.raises(Exception) as exc_info:
                    loader.load_from_file(str(config_path))

                # Should mention the missing variable
                assert "GITLAB_TOKEN" in str(exc_info.value)

    def test_substitutes_env_vars_in_nested_fields(self):
        """Test that environment variables are substituted in nested config."""
        # Arrange
        config_yaml = """
        gitlab:
          url: https://gitlab.example.com
          token: ${GITLAB_TOKEN}

        github:
          url: https://github.com
          token: ${GITHUB_TOKEN}

        mapping_strategy: ${MAPPING_STRATEGY:-flatten}

        groups:
          - source: ${SOURCE_GROUP:-backend}
            target_org: ${TARGET_ORG}
            prefix: ${REPO_PREFIX:-be}
        """

        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.yml"
            config_path.write_text(config_yaml)

            loader = ConfigLoader()

            # Act
            with patch.dict(
                os.environ,
                {
                    "GITLAB_TOKEN": "glpat_test123",
                    "GITHUB_TOKEN": "ghp_test456",
                    "TARGET_ORG": "myorg",
                },
            ):
                config = loader.load_from_file(str(config_path))

                # Assert
                assert config["mapping_strategy"] == "flatten"  # Uses default
                assert config["groups"][0]["source"] == "backend"  # Uses default
                assert config["groups"][0]["target_org"] == "myorg"  # Uses env var
                assert config["groups"][0]["prefix"] == "be"  # Uses default

    def test_substitutes_multiple_env_vars_in_same_value(self):
        """Test that multiple ${VAR} patterns in same value are all substituted."""
        # Arrange
        config_yaml = """
        gitlab:
          url: ${PROTOCOL:-https}://${GITLAB_HOST}
          token: glpat_test123

        github:
          url: https://github.com
          token: ghp_test456

        mapping_strategy: flatten

        groups:
          - source: backend
            target_org: myorg
        """

        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.yml"
            config_path.write_text(config_yaml)

            loader = ConfigLoader()

            # Act
            with patch.dict(os.environ, {"GITLAB_HOST": "gitlab.example.com"}):
                config = loader.load_from_file(str(config_path))

                # Assert - Both substitutions should work
                assert config["gitlab"]["url"] == "https://gitlab.example.com"

    def test_empty_env_var_treated_as_unset(self):
        """Test that empty string environment variable uses default."""
        # Arrange
        config_yaml = """
        gitlab:
          url: ${GITLAB_URL:-https://gitlab.com}
          token: glpat_test123

        github:
          url: https://github.com
          token: ghp_test456

        mapping_strategy: flatten

        groups:
          - source: backend
            target_org: myorg
        """

        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.yml"
            config_path.write_text(config_yaml)

            loader = ConfigLoader()

            # Act - Empty string environment variable
            with patch.dict(os.environ, {"GITLAB_URL": ""}):
                config = loader.load_from_file(str(config_path))

                # Assert - Should use default when env var is empty
                assert config["gitlab"]["url"] == "https://gitlab.com"

    def test_preserves_literal_dollar_sign(self):
        """Test that $$ is treated as literal $ (escaped)."""
        # Arrange
        config_yaml = """
        gitlab:
          url: https://gitlab.example.com
          token: glpat_test$$123

        github:
          url: https://github.com
          token: ghp_test456

        mapping_strategy: flatten

        groups:
          - source: backend
            target_org: myorg
        """

        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.yml"
            config_path.write_text(config_yaml)

            loader = ConfigLoader()

            # Act
            config = loader.load_from_file(str(config_path))

            # Assert - $$ should become single $
            assert config["gitlab"]["token"] == "glpat_test$123"
