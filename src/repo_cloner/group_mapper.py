"""Mapper for converting GitLab group paths to GitHub organization names."""

from typing import Dict, Optional


class GroupMapper:
    """Maps GitLab group/subgroup paths to GitHub organization names."""

    def __init__(self, mapping: Dict[str, str], default_org: Optional[str] = None):
        """
        Initialize GroupMapper with mapping configuration.

        Args:
            mapping: Dictionary mapping GitLab group paths to GitHub org names
                     Example: {"mygroup": "myorg", "mygroup/subgroup": "suborg"}
            default_org: Optional default organization for unmapped groups
        """
        self.mapping = mapping
        self.default_org = default_org

    def get_github_org(self, gitlab_group: str) -> str:
        """
        Get GitHub organization name for a GitLab group.

        Args:
            gitlab_group: GitLab group path (e.g., "mygroup" or "parent/child")

        Returns:
            GitHub organization name

        Raises:
            ValueError: If group not found in mapping and no default_org set
        """
        # Check if group is explicitly mapped
        if gitlab_group in self.mapping:
            return self.mapping[gitlab_group]

        # Fall back to default_org if set
        if self.default_org:
            return self.default_org

        # No mapping found and no default
        raise ValueError(f"No GitHub organization mapping found for GitLab group: {gitlab_group}")

    def get_github_org_for_project(self, path_with_namespace: str) -> str:
        """
        Get GitHub organization name from a project's full path.

        This method extracts the group path from a full project path
        (e.g., "mygroup/myrepo" → "mygroup") and looks up the mapping.

        For nested groups, it tries to find the longest matching prefix:
        - "parent/child/repo" → tries "parent/child", then "parent"

        Args:
            path_with_namespace: Full GitLab project path
                                (e.g., "mygroup/repo" or "parent/child/repo")

        Returns:
            GitHub organization name

        Raises:
            ValueError: If no mapping found and no default_org set
        """
        # Split path into components
        parts = path_with_namespace.split("/")

        # Repository name is the last part
        # Everything before that is the group path
        # Try matching from longest to shortest group path
        for i in range(len(parts) - 1, 0, -1):
            group_path = "/".join(parts[:i])
            if group_path in self.mapping:
                return self.mapping[group_path]

        # No exact match found, use default if available
        if self.default_org:
            return self.default_org

        # Extract group path (everything except last component)
        group_path = "/".join(parts[:-1])
        raise ValueError(f"No GitHub organization mapping found for GitLab group: {group_path}")
