"""Enhanced configuration loading with Pydantic validation."""

from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml
from pydantic import BaseModel, Field, field_validator


class ConfigValidationError(Exception):
    """Raised when configuration validation fails."""

    pass


class PlatformConfig(BaseModel):
    """Configuration for a Git platform (GitLab or GitHub)."""

    url: str = Field(..., description="Platform URL")
    token: str = Field(..., description="Authentication token")


class GroupConfig(BaseModel):
    """Configuration for a GitLab group mapping."""

    source: str = Field(..., description="Source GitLab group path")
    target_org: str = Field(..., description="Target GitHub organization")
    prefix: Optional[str] = Field(None, description="Prefix for repository names")
    exclude: Optional[List[str]] = Field(default_factory=list, description="Excluded repositories")
    lfs_enabled: Optional[bool] = Field(None, description="Enable LFS for this group")
    sync_strategy: Optional[str] = Field(None, description="Sync strategy (mirror, incremental)")
    dry_run: Optional[bool] = Field(None, description="Dry run mode")
    clone_depth: Optional[int] = Field(None, description="Clone depth for shallow clones")


class RepoConfig(BaseModel):
    """Root configuration model."""

    gitlab: PlatformConfig = Field(..., description="GitLab configuration")
    github: PlatformConfig = Field(..., description="GitHub configuration")
    mapping_strategy: str = Field(..., description="Mapping strategy (flatten, prefix, topics)")
    groups: List[GroupConfig] = Field(..., description="Group mappings")

    @field_validator("mapping_strategy")
    @classmethod
    def validate_mapping_strategy(cls, v: str) -> str:
        """Validate mapping strategy is one of the allowed values."""
        allowed = ["flatten", "prefix", "topics", "custom"]
        if v not in allowed:
            raise ValueError(f"mapping_strategy must be one of {allowed}, got '{v}'")
        return v


class ConfigLoader:
    """Load and validate configuration from YAML files."""

    def __init__(self):
        """Initialize config loader."""
        pass

    def load_from_file(self, file_path: str) -> Dict[str, Any]:
        """
        Load configuration from YAML file with validation.

        Args:
            file_path: Path to YAML configuration file

        Returns:
            Validated configuration dictionary

        Raises:
            FileNotFoundError: If config file doesn't exist
            yaml.YAMLError: If YAML syntax is invalid
            ConfigValidationError: If configuration validation fails
        """
        config_path = Path(file_path)

        if not config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {file_path}")

        # Load YAML
        with open(config_path, "r") as f:
            raw_config = yaml.safe_load(f)

        # Validate with Pydantic
        try:
            validated_config = RepoConfig(**raw_config)
            return validated_config.model_dump()
        except Exception as e:
            raise ConfigValidationError(f"Configuration validation failed: {str(e)}") from e
