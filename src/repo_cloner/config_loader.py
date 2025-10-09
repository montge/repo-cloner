"""Configuration loader for YAML-based sync configurations."""

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

import yaml


@dataclass
class SyncConfig:
    """Configuration for repository synchronization."""

    gitlab_url: str
    gitlab_groups: List[str]
    group_mappings: Dict[str, str]
    default_github_org: Optional[str] = None


class ConfigLoader:
    """Loads YAML configuration files for repository synchronization."""

    def __init__(self, config_path: str):
        """
        Initialize ConfigLoader with path to YAML configuration file.

        Args:
            config_path: Path to YAML configuration file (.yaml or .yml)
        """
        self.config_path = config_path

    def load(self) -> SyncConfig:
        """
        Load and parse YAML configuration file.

        Returns:
            SyncConfig dataclass with parsed configuration

        Raises:
            FileNotFoundError: If configuration file not found
            ValueError: If required sections or fields are missing
            Exception: If YAML parsing fails
        """
        # Read YAML file
        config_file = Path(self.config_path)
        if not config_file.exists():
            raise FileNotFoundError(f"Configuration file not found: {self.config_path}")

        with open(config_file, "r") as f:
            data = yaml.safe_load(f)

        # Validate required sections
        if "gitlab" not in data:
            raise ValueError("Missing required 'gitlab' section in configuration")
        if "github" not in data:
            raise ValueError("Missing required 'github' section in configuration")

        # Extract GitLab configuration
        gitlab_config = data["gitlab"]
        gitlab_url = gitlab_config.get("url")
        gitlab_groups = gitlab_config.get("groups", [])

        if not gitlab_url:
            raise ValueError("Missing required 'url' field in gitlab section")

        # Extract GitHub configuration
        github_config = data["github"]
        group_mappings = github_config.get("mappings", {})
        default_github_org = github_config.get("default_org")

        return SyncConfig(
            gitlab_url=gitlab_url,
            gitlab_groups=gitlab_groups,
            group_mappings=group_mappings,
            default_github_org=default_github_org,
        )
