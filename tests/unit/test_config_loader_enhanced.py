"""Unit tests for enhanced configuration loading and validation."""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

from repo_cloner.config_loader_enhanced import ConfigLoader, ConfigValidationError


@pytest.mark.unit
class TestConfigLoader:
    """Test enhanced configuration loading with Pydantic validation."""

    def test_loads_valid_yaml_config(self):
        """Test that valid YAML configuration loads successfully."""
        # Arrange
        config_yaml = """
        gitlab:
          url: https://gitlab.example.com
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
            config = loader.load_from_file(str(config_path))

            # Assert
            assert config is not None
            assert config["gitlab"]["url"] == "https://gitlab.example.com"
            assert config["github"]["url"] == "https://github.com"
            assert config["mapping_strategy"] == "flatten"
            assert len(config["groups"]) == 1
            assert config["groups"][0]["source"] == "backend"

    def test_raises_error_on_missing_required_fields(self):
        """Test that missing required fields raise validation error."""
        # Arrange
        config_yaml = """
        gitlab:
          url: https://gitlab.example.com
          # Missing token

        github:
          url: https://github.com
          token: ghp_test456
        """

        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.yml"
            config_path.write_text(config_yaml)

            loader = ConfigLoader()

            # Act & Assert
            with pytest.raises(ConfigValidationError) as exc_info:
                loader.load_from_file(str(config_path))

            assert "token" in str(exc_info.value).lower()

    def test_loads_config_with_multiple_groups(self):
        """Test loading configuration with multiple GitLab groups."""
        # Arrange
        config_yaml = """
        gitlab:
          url: https://gitlab.example.com
          token: glpat_test123

        github:
          url: https://github.com
          token: ghp_test456

        mapping_strategy: prefix

        groups:
          - source: backend
            target_org: myorg
            prefix: be
          - source: frontend
            target_org: myorg
            prefix: fe
          - source: infra
            target_org: infra-org
        """

        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.yml"
            config_path.write_text(config_yaml)

            loader = ConfigLoader()

            # Act
            config = loader.load_from_file(str(config_path))

            # Assert
            assert len(config["groups"]) == 3
            assert config["groups"][0]["prefix"] == "be"
            assert config["groups"][1]["prefix"] == "fe"
            assert config["groups"][2]["source"] == "infra"

    def test_loads_config_with_exclusions(self):
        """Test loading configuration with repository exclusions."""
        # Arrange
        config_yaml = """
        gitlab:
          url: https://gitlab.example.com
          token: glpat_test123

        github:
          url: https://github.com
          token: ghp_test456

        mapping_strategy: flatten

        groups:
          - source: backend
            target_org: myorg
            exclude:
              - backend/deprecated-service
              - backend/old-api
        """

        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.yml"
            config_path.write_text(config_yaml)

            loader = ConfigLoader()

            # Act
            config = loader.load_from_file(str(config_path))

            # Assert
            assert "exclude" in config["groups"][0]
            assert len(config["groups"][0]["exclude"]) == 2
            assert "backend/deprecated-service" in config["groups"][0]["exclude"]

    def test_loads_config_with_lfs_settings(self):
        """Test loading configuration with LFS-specific settings."""
        # Arrange
        config_yaml = """
        gitlab:
          url: https://gitlab.example.com
          token: glpat_test123

        github:
          url: https://github.com
          token: ghp_test456

        mapping_strategy: flatten

        groups:
          - source: design
            target_org: myorg
            lfs_enabled: true
            sync_strategy: mirror
        """

        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.yml"
            config_path.write_text(config_yaml)

            loader = ConfigLoader()

            # Act
            config = loader.load_from_file(str(config_path))

            # Assert
            assert config["groups"][0]["lfs_enabled"] is True
            assert config["groups"][0]["sync_strategy"] == "mirror"

    def test_raises_error_on_invalid_yaml_syntax(self):
        """Test that invalid YAML syntax raises appropriate error."""
        # Arrange
        config_yaml = """
        gitlab:
          url: https://gitlab.example.com
          token: glpat_test123
        invalid yaml syntax: [
        """

        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.yml"
            config_path.write_text(config_yaml)

            loader = ConfigLoader()

            # Act & Assert
            with pytest.raises(yaml.YAMLError):
                loader.load_from_file(str(config_path))

    def test_raises_error_on_nonexistent_file(self):
        """Test that attempting to load nonexistent file raises error."""
        # Arrange
        loader = ConfigLoader()

        # Act & Assert
        with pytest.raises(FileNotFoundError):
            loader.load_from_file("/nonexistent/config.yml")

    def test_loads_config_with_optional_fields(self):
        """Test that configuration with optional fields loads correctly."""
        # Arrange
        config_yaml = """
        gitlab:
          url: https://gitlab.example.com
          token: glpat_test123

        github:
          url: https://github.com
          token: ghp_test456

        mapping_strategy: flatten

        groups:
          - source: backend
            target_org: myorg
            dry_run: true
            clone_depth: 1
        """

        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.yml"
            config_path.write_text(config_yaml)

            loader = ConfigLoader()

            # Act
            config = loader.load_from_file(str(config_path))

            # Assert
            assert config["groups"][0].get("dry_run") is True
            assert config["groups"][0].get("clone_depth") == 1
