"""Enhanced configuration loading with Pydantic validation."""

import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

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

    def _substitute_env_vars(self, value: Any) -> Any:
        """
        Recursively substitute environment variables in configuration values.

        Supports patterns:
        - ${VAR} - Replace with environment variable value (raises error if not set)
        - ${VAR:-default} - Replace with VAR or use default if not set
        - $$ - Escape sequence for literal $

        Args:
            value: Configuration value (string, dict, list, or other)

        Returns:
            Value with environment variables substituted

        Raises:
            ConfigValidationError: If required environment variable is not set
        """
        if isinstance(value, str):
            # Handle $$ escape sequence first
            result = value.replace("$$", "\x00")  # Temporary placeholder

            # Pattern: ${VAR:-default} or ${VAR}
            def replace_var(match: re.Match[str]) -> str:
                full_match = match.group(0)
                var_with_default = match.group(1)

                # Check if it has a default value
                if ":-" in var_with_default:
                    var_name, default_value = var_with_default.split(":-", 1)
                    env_value = os.environ.get(var_name)

                    # Treat empty string as unset
                    if env_value is None or env_value == "":
                        return default_value
                    return env_value
                else:
                    # No default - variable is required
                    var_name = var_with_default
                    env_value = os.environ.get(var_name)

                    if env_value is None:
                        raise ConfigValidationError(
                            f"Required environment variable '{var_name}' is not set"
                        )
                    return env_value

            # Replace ${VAR} and ${VAR:-default} patterns
            result = re.sub(r"\$\{([^}]+)\}", replace_var, result)

            # Restore escaped dollar signs
            result = result.replace("\x00", "$")

            return result

        elif isinstance(value, dict):
            return {k: self._substitute_env_vars(v) for k, v in value.items()}

        elif isinstance(value, list):
            return [self._substitute_env_vars(item) for item in value]

        else:
            # Return other types unchanged (int, bool, None, etc.)
            return value

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

        # Substitute environment variables
        substituted_config = self._substitute_env_vars(raw_config)

        # Validate with Pydantic
        try:
            validated_config = RepoConfig(**substituted_config)
            return validated_config.model_dump()
        except Exception as e:
            raise ConfigValidationError(f"Configuration validation failed: {str(e)}") from e
