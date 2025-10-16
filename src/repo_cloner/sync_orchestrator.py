"""Orchestrator for bulk repository synchronization from GitLab group to GitHub org."""

import concurrent.futures
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from .auth_manager import AuthManager
from .git_client import GitClient
from .github_client import GitHubClient
from .gitlab_client import GitLabClient, ProjectDetails
from .group_mapper import GroupMapper


@dataclass
class RepositoryMapping:
    """Mapping of a GitLab repository to GitHub repository."""

    gitlab_id: int
    gitlab_path: str
    gitlab_url: str
    github_name: str
    github_full_name: str
    github_url: str
    topics: List[str] = field(default_factory=list)
    github_exists: bool = False
    created: bool = False
    sync_success: bool = False
    sync_error: Optional[str] = None
    details: Optional[ProjectDetails] = None


@dataclass
class SyncSummary:
    """Summary of bulk synchronization operation."""

    total_repos: int
    mapped_repos: int
    skipped_repos: int
    conflicts: Dict[str, List[str]]
    invalid_names: List[Dict[str, str]]
    created_repos: int
    synced_repos: int
    failed_repos: int
    mappings: List[RepositoryMapping]


class SyncOrchestrator:
    """Orchestrates bulk repository synchronization from GitLab group to GitHub org."""

    def __init__(
        self,
        gitlab_client: GitLabClient,
        github_client: GitHubClient,
        git_client: GitClient,
        auth_manager: AuthManager,
        group_mapper: GroupMapper,
        github_org: str,
        github_base_url: str = "https://github.com",
    ):
        """
        Initialize SyncOrchestrator.

        Args:
            gitlab_client: GitLab API client
            github_client: GitHub API client
            git_client: Git operations client
            auth_manager: Authentication manager
            group_mapper: Group hierarchy mapper
            github_org: Target GitHub organization name
            github_base_url: GitHub base URL (default: https://github.com)
        """
        self.gitlab_client = gitlab_client
        self.github_client = github_client
        self.git_client = git_client
        self.auth_manager = auth_manager
        self.group_mapper = group_mapper
        self.github_org = github_org
        self.github_base_url = github_base_url

    def sync_group_to_org(
        self,
        gitlab_group_path: str,
        auto_create: bool = False,
        dry_run: bool = False,
        workers: int = 5,
    ) -> SyncSummary:
        """
        Sync all repositories from GitLab group to GitHub organization.

        Args:
            gitlab_group_path: GitLab group path (e.g., "company/backend")
            auto_create: Automatically create missing GitHub repos
            dry_run: Show what would be done without executing
            workers: Number of concurrent workers for syncing

        Returns:
            SyncSummary with detailed results

        Raises:
            Exception: If group not found or critical API error occurs
        """
        # Step 1: Discover all repositories in GitLab group
        repos = self.gitlab_client.list_projects(gitlab_group_path)

        # Step 2: Map repository names and validate
        repo_mappings = []
        invalid_names = []

        for repo in repos:
            gitlab_path = repo["path_with_namespace"]
            github_name = self.group_mapper.map_repository_name(gitlab_path)
            topics = self.group_mapper.extract_topics(gitlab_path)

            # Validate GitHub name
            is_valid, error = self.group_mapper.validate_github_name(github_name)
            if not is_valid:
                invalid_names.append(
                    {
                        "gitlab_path": gitlab_path,
                        "github_name": github_name,
                        "error": error,
                    }
                )
                continue

            # Create mapping
            github_full_name = f"{self.github_org}/{github_name}"
            github_url = f"{self.github_base_url}/{github_full_name}.git"

            mapping = RepositoryMapping(
                gitlab_id=repo["id"],
                gitlab_path=gitlab_path,
                gitlab_url=repo.get("http_url_to_repo", repo.get("web_url", "")),
                github_name=github_name,
                github_full_name=github_full_name,
                github_url=github_url,
                topics=topics,
            )

            repo_mappings.append(mapping)

        # Step 3: Detect naming conflicts
        gitlab_paths = [m.gitlab_path for m in repo_mappings]
        conflicts = self.group_mapper.detect_conflicts(gitlab_paths)

        # Step 4: Check which repos exist on GitHub
        for mapping in repo_mappings:
            exists = self.github_client.repository_exists(mapping.github_full_name)
            mapping.github_exists = exists

        # Step 5: Fetch details for all mappings (for descriptions, topics, etc.)
        for mapping in repo_mappings:
            try:
                details = self.gitlab_client.get_project_details(mapping.gitlab_id)
                mapping.details = details
            except Exception:
                # Continue without details if fetch fails
                pass

        # Early return for dry-run (before creating/syncing)
        if dry_run:
            return SyncSummary(
                total_repos=len(repos),
                mapped_repos=len(repo_mappings),
                skipped_repos=len(invalid_names),
                conflicts=conflicts,
                invalid_names=invalid_names,
                created_repos=0,
                synced_repos=0,
                failed_repos=0,
                mappings=repo_mappings,
            )

        # Step 6: Auto-create missing repositories (if enabled)
        created_count = 0
        if auto_create:
            for mapping in repo_mappings:
                if not mapping.github_exists:
                    try:
                        # Get description from details if available
                        description = ""
                        if mapping.details:
                            description = mapping.details.description

                        self.github_client.create_repository(
                            org_name=self.github_org,
                            repo_name=mapping.github_name,
                            description=description,
                            private=True,  # Default to private for safety
                            topics=mapping.topics,
                        )
                        mapping.github_exists = True
                        mapping.created = True
                        created_count += 1
                    except Exception as e:
                        # Mark sync as failed if creation fails
                        mapping.sync_error = f"Failed to create repo: {str(e)}"
                        continue

        # Step 7: Sync repositories concurrently
        synced_count = 0
        failed_count = 0

        # Only sync repos that exist on GitHub
        repos_to_sync = [m for m in repo_mappings if m.github_exists and not m.sync_error]

        if workers > 1 and len(repos_to_sync) > 1:
            # Concurrent sync
            with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
                future_to_mapping = {
                    executor.submit(self._sync_single_repository, mapping): mapping
                    for mapping in repos_to_sync
                }

                for future in concurrent.futures.as_completed(future_to_mapping):
                    mapping = future_to_mapping[future]
                    try:
                        success = future.result()
                        if success:
                            synced_count += 1
                        else:
                            failed_count += 1
                    except Exception as e:
                        mapping.sync_error = str(e)
                        failed_count += 1
        else:
            # Sequential sync (for single worker or single repo)
            for mapping in repos_to_sync:
                try:
                    success = self._sync_single_repository(mapping)
                    if success:
                        synced_count += 1
                    else:
                        failed_count += 1
                except Exception as e:
                    mapping.sync_error = str(e)
                    failed_count += 1

        return SyncSummary(
            total_repos=len(repos),
            mapped_repos=len(repo_mappings),
            skipped_repos=len(invalid_names),
            conflicts=conflicts,
            invalid_names=invalid_names,
            created_repos=created_count,
            synced_repos=synced_count,
            failed_repos=failed_count,
            mappings=repo_mappings,
        )

    def _sync_single_repository(self, mapping: RepositoryMapping) -> bool:
        """
        Sync a single repository from GitLab to GitHub.

        Args:
            mapping: Repository mapping with source and target URLs

        Returns:
            True if sync succeeded, False otherwise
            Updates mapping.sync_success and mapping.sync_error
        """
        try:
            # Inject credentials into URLs
            authenticated_source = self.auth_manager.inject_credentials(mapping.gitlab_url)
            authenticated_target = self.auth_manager.inject_credentials(mapping.github_url)

            # Determine local path (temp directory)
            repo_name = mapping.github_name
            local_path = f"/tmp/repo-cloner/{repo_name}"

            # Clone from source (mirror)
            clone_result = self.git_client.clone_mirror(authenticated_source, local_path)

            if not clone_result.success:
                mapping.sync_error = f"Clone failed: {clone_result.error_message}"
                mapping.sync_success = False
                return False

            # Push to target (mirror)
            push_result = self.git_client.push_mirror(local_path, authenticated_target)

            if not push_result.success:
                mapping.sync_error = f"Push failed: {push_result.error_message}"
                mapping.sync_success = False
                return False

            mapping.sync_success = True
            return True

        except Exception as e:
            mapping.sync_error = str(e)
            mapping.sync_success = False
            return False
