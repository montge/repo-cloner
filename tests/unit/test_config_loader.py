"""Unit tests for ConfigLoader class."""

import tempfile
from pathlib import Path

import pytest

from repo_cloner.config_loader import ConfigLoader, SyncConfig


@pytest.mark.unit
class TestConfigLoader:
    """Test ConfigLoader for YAML configuration loading."""

    def test_loads_basic_config_from_yaml(self):
        """Test that basic YAML configuration is loaded correctly."""
        # Arrange
        yaml_content = """
gitlab:
  url: https://gitlab.com
  groups:
    - mygroup
    - othergroup

github:
  mappings:
    mygroup: myorg
    othergroup: otherorg
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(yaml_content)
            config_path = f.name

        loader = ConfigLoader(config_path)

        # Act
        config = loader.load()

        # Assert
        assert config.gitlab_url == "https://gitlab.com"
        assert config.gitlab_groups == ["mygroup", "othergroup"]
        assert config.group_mappings == {"mygroup": "myorg", "othergroup": "otherorg"}

        # Cleanup
        Path(config_path).unlink()

    def test_loads_config_with_default_org(self):
        """Test that default GitHub organization is loaded."""
        # Arrange
        yaml_content = """
gitlab:
  url: https://gitlab.example.com
  groups:
    - team-a

github:
  default_org: fallback-org
  mappings:
    team-a: team-org
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(yaml_content)
            config_path = f.name

        loader = ConfigLoader(config_path)

        # Act
        config = loader.load()

        # Assert
        assert config.default_github_org == "fallback-org"
        assert config.group_mappings == {"team-a": "team-org"}

        # Cleanup
        Path(config_path).unlink()

    def test_loads_config_with_empty_mappings(self):
        """Test that configuration with empty mappings is valid."""
        # Arrange
        yaml_content = """
gitlab:
  url: https://gitlab.com
  groups:
    - mygroup

github:
  default_org: catch-all-org
  mappings: {}
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(yaml_content)
            config_path = f.name

        loader = ConfigLoader(config_path)

        # Act
        config = loader.load()

        # Assert
        assert config.group_mappings == {}
        assert config.default_github_org == "catch-all-org"

        # Cleanup
        Path(config_path).unlink()

    def test_loads_config_with_nested_groups(self):
        """Test that nested GitLab groups are supported."""
        # Arrange
        yaml_content = """
gitlab:
  url: https://gitlab.com
  groups:
    - parent/child
    - company/division/team

github:
  mappings:
    parent/child: child-org
    company/division/team: team-org
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(yaml_content)
            config_path = f.name

        loader = ConfigLoader(config_path)

        # Act
        config = loader.load()

        # Assert
        assert "parent/child" in config.gitlab_groups
        assert "company/division/team" in config.gitlab_groups
        assert config.group_mappings["parent/child"] == "child-org"
        assert config.group_mappings["company/division/team"] == "team-org"

        # Cleanup
        Path(config_path).unlink()

    def test_raises_error_for_missing_file(self):
        """Test that FileNotFoundError is raised for missing config file."""
        # Arrange
        loader = ConfigLoader("/nonexistent/config.yaml")

        # Act & Assert
        with pytest.raises(FileNotFoundError):
            loader.load()

    def test_raises_error_for_invalid_yaml(self):
        """Test that error is raised for invalid YAML syntax."""
        # Arrange
        yaml_content = """
gitlab:
  url: https://gitlab.com
  groups: [invalid yaml structure
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(yaml_content)
            config_path = f.name

        loader = ConfigLoader(config_path)

        # Act & Assert
        with pytest.raises(Exception):  # YAML parsing error
            loader.load()

        # Cleanup
        Path(config_path).unlink()

    def test_raises_error_for_missing_gitlab_section(self):
        """Test that error is raised when gitlab section is missing."""
        # Arrange
        yaml_content = """
github:
  default_org: my-org
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(yaml_content)
            config_path = f.name

        loader = ConfigLoader(config_path)

        # Act & Assert
        with pytest.raises(ValueError, match="gitlab"):
            loader.load()

        # Cleanup
        Path(config_path).unlink()

    def test_raises_error_for_missing_github_section(self):
        """Test that error is raised when github section is missing."""
        # Arrange
        yaml_content = """
gitlab:
  url: https://gitlab.com
  groups:
    - mygroup
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(yaml_content)
            config_path = f.name

        loader = ConfigLoader(config_path)

        # Act & Assert
        with pytest.raises(ValueError, match="github"):
            loader.load()

        # Cleanup
        Path(config_path).unlink()

    def test_returns_sync_config_dataclass(self):
        """Test that load() returns a SyncConfig dataclass instance."""
        # Arrange
        yaml_content = """
gitlab:
  url: https://gitlab.com
  groups:
    - test

github:
  mappings:
    test: test-org
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(yaml_content)
            config_path = f.name

        loader = ConfigLoader(config_path)

        # Act
        config = loader.load()

        # Assert
        assert isinstance(config, SyncConfig)

        # Cleanup
        Path(config_path).unlink()

    def test_handles_yml_extension(self):
        """Test that .yml extension is also supported."""
        # Arrange
        yaml_content = """
gitlab:
  url: https://gitlab.com
  groups:
    - mygroup

github:
  mappings:
    mygroup: myorg
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
            f.write(yaml_content)
            config_path = f.name

        loader = ConfigLoader(config_path)

        # Act
        config = loader.load()

        # Assert
        assert config.gitlab_url == "https://gitlab.com"

        # Cleanup
        Path(config_path).unlink()
