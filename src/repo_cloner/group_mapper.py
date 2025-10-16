"""Group hierarchy mapping for GitLab → GitHub organization synchronization."""

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional


class MappingStrategy(Enum):
    """Supported mapping strategies for GitLab groups → GitHub repos."""

    FLATTEN = "flatten"
    PREFIX = "prefix"
    FULL_PATH = "full_path"
    CUSTOM = "custom"


@dataclass
class MappingConfig:
    """Configuration for group-to-org mapping."""

    strategy: MappingStrategy = MappingStrategy.FLATTEN
    separator: str = "-"
    keep_last_n_levels: Optional[int] = None
    use_topics: bool = True
    strip_parent_group: bool = False
    custom_mappings: Dict[str, str] = field(default_factory=dict)
    fallback_strategy: MappingStrategy = MappingStrategy.FLATTEN


class GroupMapper:
    """Maps GitLab group hierarchies to GitHub organization structure.

    GitLab supports nested groups (e.g., company/backend/services/auth),
    but GitHub has flat organizations. This class handles the mapping.
    """

    def __init__(self, config: MappingConfig):
        """
        Initialize GroupMapper.

        Args:
            config: Mapping configuration
        """
        self.config = config

    def map_repository_name(
        self, gitlab_path: str, strategy: Optional[MappingStrategy] = None
    ) -> str:
        """
        Map GitLab repository path to GitHub repository name.

        Args:
            gitlab_path: Full GitLab path (e.g., "company/backend/services/auth-service")
            strategy: Override default strategy

        Returns:
            GitHub repository name (without org prefix)

        Examples:
            >>> mapper = GroupMapper(MappingConfig(strategy=MappingStrategy.FLATTEN))
            >>> mapper.map_repository_name("company/backend/services/auth")
            'company-backend-services-auth'

            >>> config = MappingConfig(strategy=MappingStrategy.PREFIX, keep_last_n_levels=2)
            >>> mapper = GroupMapper(config)
            >>> mapper.map_repository_name("company/backend/services/auth")
            'services-auth'
        """
        strategy = strategy or self.config.strategy

        if strategy == MappingStrategy.FLATTEN:
            return self._flatten_strategy(gitlab_path)
        elif strategy == MappingStrategy.PREFIX:
            return self._prefix_strategy(gitlab_path)
        elif strategy == MappingStrategy.FULL_PATH:
            return self._full_path_strategy(gitlab_path)
        elif strategy == MappingStrategy.CUSTOM:
            return self._custom_strategy(gitlab_path)
        else:
            raise ValueError(f"Unknown mapping strategy: {strategy}")

    def extract_topics(self, gitlab_path: str) -> List[str]:
        """
        Extract GitHub topics from GitLab path for hierarchy representation.

        Topics are derived from parent groups (excluding the repository name).

        Args:
            gitlab_path: Full GitLab path (e.g., "company/backend/services/auth-service")

        Returns:
            List of topics for GitHub repository

        Examples:
            >>> mapper = GroupMapper(MappingConfig(use_topics=True))
            >>> mapper.extract_topics("company/backend/services/auth-service")
            ['company', 'backend', 'services']

            >>> config = MappingConfig(use_topics=True, strip_parent_group=True)
            >>> mapper = GroupMapper(config)
            >>> mapper.extract_topics("company/backend/services/auth-service")
            ['backend', 'services']
        """
        if not self.config.use_topics:
            return []

        parts = gitlab_path.split("/")[:-1]  # Exclude repo name

        # Optionally strip root parent group
        if self.config.strip_parent_group and len(parts) > 1:
            parts = parts[1:]

        return [p.lower() for p in parts]

    def _flatten_strategy(self, gitlab_path: str) -> str:
        """
        Flatten: company/backend/services/auth → company-backend-services-auth

        Args:
            gitlab_path: Full GitLab path

        Returns:
            Flattened repository name
        """
        parts = gitlab_path.split("/")

        # Strip parent group if configured
        if self.config.strip_parent_group and len(parts) > 1:
            parts = parts[1:]

        # Limit depth if configured
        if self.config.keep_last_n_levels:
            parts = parts[-self.config.keep_last_n_levels :]

        return self.config.separator.join(parts)

    def _prefix_strategy(self, gitlab_path: str) -> str:
        """
        Prefix: company/backend/services/auth → services-auth or auth
        (parent groups become topics)

        Args:
            gitlab_path: Full GitLab path

        Returns:
            Prefixed repository name (shortened)
        """
        parts = gitlab_path.split("/")

        if self.config.keep_last_n_levels:
            relevant_parts = parts[-self.config.keep_last_n_levels :]
        else:
            relevant_parts = [parts[-1]]  # Just repo name

        return self.config.separator.join(relevant_parts)

    def _full_path_strategy(self, gitlab_path: str) -> str:
        """
        Full path: company/backend/services/auth → company_backend_services_auth

        Args:
            gitlab_path: Full GitLab path

        Returns:
            Full path with slashes replaced by separator
        """
        return gitlab_path.replace("/", self.config.separator)

    def _custom_strategy(self, gitlab_path: str) -> str:
        """
        Custom: Use user-defined mappings from config.

        Checks for exact matches first, then prefix matches.
        Falls back to fallback strategy if no match found.

        Args:
            gitlab_path: Full GitLab path

        Returns:
            Mapped repository name
        """
        # Check for exact match
        if gitlab_path in self.config.custom_mappings:
            return self.config.custom_mappings[gitlab_path]

        # Check for prefix match (longest first)
        sorted_mappings = sorted(
            self.config.custom_mappings.items(), key=lambda x: len(x[0]), reverse=True
        )

        for prefix, replacement in sorted_mappings:
            if gitlab_path.startswith(prefix + "/"):
                # Replace prefix and continue with remaining path
                remaining = gitlab_path[len(prefix) + 1 :]
                remaining_mapped = remaining.replace("/", self.config.separator)
                return f"{replacement}{self.config.separator}{remaining_mapped}"

        # No match found - use fallback strategy
        return self.map_repository_name(gitlab_path, self.config.fallback_strategy)

    def validate_github_name(self, name: str) -> tuple[bool, Optional[str]]:
        """
        Validate GitHub repository name constraints.

        GitHub repository name rules:
        - Max 100 characters
        - Alphanumeric, hyphens, underscores, periods
        - Cannot start with hyphen, underscore, or period
        - Cannot end with .git
        - Cannot be "." or ".."

        Args:
            name: Proposed GitHub repository name

        Returns:
            Tuple of (is_valid, error_message)
            If valid, error_message is None

        Examples:
            >>> mapper = GroupMapper(MappingConfig())
            >>> mapper.validate_github_name("my-repo")
            (True, None)

            >>> mapper.validate_github_name("-invalid")
            (False, 'Name cannot start with hyphen, underscore, or period')

            >>> mapper.validate_github_name("x" * 101)
            (False, 'Name exceeds 100 characters: 101')
        """
        if len(name) > 100:
            return False, f"Name exceeds 100 characters: {len(name)}"

        if name in (".", ".."):
            return False, "Name cannot be '.' or '..'"

        if name.endswith(".git"):
            return False, "Name cannot end with .git"

        if name.startswith(("-", "_", ".")):
            return False, "Name cannot start with hyphen, underscore, or period"

        # Check valid characters (alphanumeric, hyphens, underscores, periods)
        if not re.match(r"^[a-zA-Z0-9._-]+$", name):
            return False, "Name contains invalid characters (only alphanumeric, -, _, . allowed)"

        return True, None

    def detect_conflicts(self, gitlab_paths: List[str]) -> Dict[str, List[str]]:
        """
        Detect naming conflicts when mapping multiple GitLab repos.

        Multiple GitLab repos may map to the same GitHub name with certain
        strategies (e.g., PREFIX strategy).

        Args:
            gitlab_paths: List of GitLab repository paths

        Returns:
            Dictionary mapping GitHub names to conflicting GitLab paths
            Only includes entries with conflicts (2+ GitLab paths → same GitHub name)

        Examples:
            >>> config = MappingConfig(
            ...     strategy=MappingStrategy.PREFIX, keep_last_n_levels=1
            ... )
            >>> mapper = GroupMapper(config)
            >>> paths = ["company/backend/auth", "company/frontend/auth"]
            >>> conflicts = mapper.detect_conflicts(paths)
            >>> conflicts
            {'auth': ['company/backend/auth', 'company/frontend/auth']}
        """
        github_to_gitlab: Dict[str, List[str]] = {}

        for gitlab_path in gitlab_paths:
            github_name = self.map_repository_name(gitlab_path)

            if github_name not in github_to_gitlab:
                github_to_gitlab[github_name] = []

            github_to_gitlab[github_name].append(gitlab_path)

        # Return only conflicts (where multiple GitLab paths map to same GitHub name)
        return {
            github_name: paths for github_name, paths in github_to_gitlab.items() if len(paths) > 1
        }


# Legacy classes - kept for backward compatibility


class FlattenMapper:
    """
    Maps GitLab group hierarchies to flat GitHub repository names.

    Converts GitLab paths like "group/subgroup/repo" to "group-subgroup-repo"
    by replacing path separators with a configurable separator (default: hyphen).
    """

    def __init__(self, separator: str = "-"):
        """
        Initialize FlattenMapper.

        Args:
            separator: Character to use as separator (default: "-")
        """
        self.separator = separator

    def map(self, gitlab_path: str) -> str:
        """
        Map GitLab path to flattened GitHub repository name.

        Args:
            gitlab_path: GitLab repository path (e.g., "group/subgroup/repo")

        Returns:
            Flattened GitHub repository name (e.g., "group-subgroup-repo")

        Raises:
            ValueError: If gitlab_path is empty
            TypeError: If gitlab_path is None
        """
        if gitlab_path is None:
            raise TypeError("gitlab_path cannot be None")

        if not gitlab_path or not gitlab_path.strip():
            raise ValueError("gitlab_path cannot be empty")

        # Normalize path: remove leading/trailing slashes, collapse multiple slashes
        normalized = re.sub(r"/+", "/", gitlab_path.strip("/"))

        # Replace path separators with configured separator
        github_name = normalized.replace("/", self.separator)

        return github_name

    def reverse(self, github_name: str) -> str:
        """
        Reverse mapping from GitHub name to GitLab path.

        Note: This is not a true reverse operation as the original path
        structure cannot be uniquely determined from the flattened name.
        Returns the name as-is for informational purposes.

        Args:
            github_name: GitHub repository name

        Returns:
            The same name (cannot uniquely reverse flatten operation)
        """
        # Cannot uniquely reverse flatten operation without additional context
        # Return as-is to indicate this limitation
        return github_name


class PrefixMapper:
    """
    Maps GitLab repositories to GitHub with a prefix, dropping parent group paths.

    Extracts only the repository name (last component of path) and adds a prefix.
    For example: "backend/api-service" with prefix "be" becomes "be-api-service"
    """

    def __init__(self, prefix: Optional[str] = None, separator: str = "-"):
        """
        Initialize PrefixMapper.

        Args:
            prefix: Prefix to add to repository names (default: None)
            separator: Character to use between prefix and repo name (default: "-")
        """
        self.prefix = prefix
        self.separator = separator

    def map(self, gitlab_path: str) -> str:
        """
        Map GitLab path to GitHub repository name with prefix.

        Extracts the repository name (last component) from the path and
        optionally prepends a prefix.

        Args:
            gitlab_path: GitLab repository path (e.g., "group/subgroup/repo")

        Returns:
            GitHub repository name with prefix (e.g., "prefix-repo")

        Raises:
            ValueError: If gitlab_path is empty
            TypeError: If gitlab_path is None
        """
        if gitlab_path is None:
            raise TypeError("gitlab_path cannot be None")

        if not gitlab_path or not gitlab_path.strip():
            raise ValueError("gitlab_path cannot be empty")

        # Normalize path: remove leading/trailing slashes, collapse multiple slashes
        normalized = re.sub(r"/+", "/", gitlab_path.strip("/"))

        # Extract repository name (last component)
        parts = normalized.split("/")
        repo_name = parts[-1]

        # Add prefix if provided
        if self.prefix:
            github_name = f"{self.prefix}{self.separator}{repo_name}"
        else:
            github_name = repo_name

        return github_name

    def reverse(self, github_name: str) -> str:
        """
        Reverse mapping from GitHub name to GitLab path.

        Note: This is not a true reverse operation as the original path
        structure cannot be uniquely determined from the prefixed name.
        Returns the name as-is for informational purposes.

        Args:
            github_name: GitHub repository name

        Returns:
            The same name (cannot uniquely reverse prefix operation)
        """
        # Cannot uniquely reverse prefix operation without additional context
        # Return as-is to indicate this limitation
        return github_name
