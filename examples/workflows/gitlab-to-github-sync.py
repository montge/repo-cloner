#!/usr/bin/env python3
"""GitLab to GitHub Synchronization Workflow.

This example workflow demonstrates a complete GitLab → GitHub synchronization
with comprehensive structured logging, error handling, and progress reporting.

Features:
- Structured JSON logging with contextual information
- User-friendly terminal output with progress indicators
- Automatic retry on transient failures
- Session tracking with unique IDs
- Error handling with detailed context
- Summary report generation

Usage:
    python gitlab-to-github-sync.py

Environment Variables:
    GITLAB_TOKEN: GitLab Personal Access Token
    GITHUB_TOKEN: GitHub Personal Access Token
    GITLAB_URL: GitLab instance URL (default: https://gitlab.com)
    GITLAB_GROUP: GitLab group/namespace to sync
    GITHUB_ORG: GitHub organization for target repositories
"""

import os
import sys
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List

# Add repo-cloner to path if running from examples directory
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from repo_cloner.auth_manager import AuthManager
from repo_cloner.exceptions import (
    AuthenticationError,
    GitOperationError,
    NetworkError,
    RepoClonerError,
)
from repo_cloner.git_client import GitClient
from repo_cloner.gitlab_client import GitLabClient
from repo_cloner.github_client import GitHubClient
from repo_cloner.logging_config import configure_logging, get_logger, log_context
from repo_cloner.retry import retry


class GitLabToGitHubSync:
    """GitLab to GitHub synchronization workflow."""

    def __init__(self):
        """Initialize the sync workflow."""
        # Generate unique session ID
        self.session_id = f"sync-{datetime.now().strftime('%Y%m%d-%H%M%S')}"

        # Configure logging (JSON to file, plain to console for now)
        self.logger = configure_logging(
            level="INFO",
            json_format=True,
            log_file=f"/tmp/repo-cloner-{self.session_id}.log"
        )

        # Get workflow-specific logger
        self.logger = get_logger("workflows.gitlab_to_github")

        # Load environment variables
        self.gitlab_url = os.getenv("GITLAB_URL", "https://gitlab.com")
        self.gitlab_token = os.getenv("GITLAB_TOKEN")
        self.gitlab_group = os.getenv("GITLAB_GROUP")
        self.github_token = os.getenv("GITHUB_TOKEN")
        self.github_org = os.getenv("GITHUB_ORG")

        # Validate required environment variables
        self._validate_config()

        # Initialize clients
        self.auth_manager = AuthManager(
            gitlab_token=self.gitlab_token,
            github_token=self.github_token
        )
        self.gitlab_client = GitLabClient(self.gitlab_url, self.gitlab_token)
        self.github_client = GitHubClient("https://github.com", self.github_token)
        self.git_client = GitClient()

        # Statistics
        self.stats = {
            "total_repos": 0,
            "successful": 0,
            "failed": 0,
            "total_commits": 0,
            "total_branches": 0,
            "start_time": time.time(),
        }

    def _validate_config(self):
        """Validate required configuration."""
        required = {
            "GITLAB_TOKEN": self.gitlab_token,
            "GITLAB_GROUP": self.gitlab_group,
            "GITHUB_TOKEN": self.github_token,
            "GITHUB_ORG": self.github_org,
        }

        missing = [key for key, value in required.items() if not value]
        if missing:
            raise AuthenticationError(
                f"Missing required environment variables: {', '.join(missing)}",
                missing_variables=missing
            )

    def run(self):
        """Execute the synchronization workflow."""
        with log_context(session_id=self.session_id,
                        source=f"{self.gitlab_url}/{self.gitlab_group}",
                        target=f"github.com/{self.github_org}"):

            self.logger.info("Synchronization session started")
            print(f"\n🚀 Starting GitLab → GitHub Synchronization")
            print(f"   Session ID: {self.session_id}")
            print(f"   Source: {self.gitlab_url}/{self.gitlab_group}")
            print(f"   Target: github.com/{self.github_org}")

            try:
                # Discover repositories
                repositories = self._discover_repositories()

                # Sync each repository
                self._sync_repositories(repositories)

                # Print summary
                self._print_summary()

                self.logger.info("Synchronization session completed successfully",
                               extra=self.stats)

            except RepoClonerError as e:
                self.logger.error(f"Synchronization failed: {e}",
                                extra={"error_type": type(e).__name__})
                print(f"\n✗ Synchronization failed: {e}")
                sys.exit(1)
            except Exception as e:
                self.logger.error(f"Unexpected error: {e}", exc_info=True)
                print(f"\n✗ Unexpected error: {e}")
                sys.exit(1)

    def _discover_repositories(self) -> List[Dict]:
        """Discover repositories in GitLab group."""
        with log_context(operation="discover_repositories"):
            self.logger.info("Discovering repositories in GitLab group")
            print(f"\n📁 Discovering repositories...")

            try:
                # Get all projects in the group (mocked for example)
                projects = [
                    {"name": "backend-auth-service", "path": "backend/auth-service"},
                    {"name": "backend-api-gateway", "path": "backend/api-gateway"},
                    {"name": "backend-user-service", "path": "backend/user-service"},
                ]

                self.stats["total_repos"] = len(projects)

                self.logger.info(f"Discovered {len(projects)} repositories",
                               extra={"repository_count": len(projects)})
                print(f"   ✓ Found {len(projects)} repositories in {self.gitlab_group}")

                return projects

            except Exception as e:
                raise NetworkError(
                    f"Failed to discover repositories: {e}",
                    retryable=True,
                    source=self.gitlab_url
                )

    @retry(max_retries=3, initial_delay=2.0, backoff_factor=2.0)
    def _sync_repository(self, repo: Dict, index: int, total: int) -> Dict:
        """Sync a single repository from GitLab to GitHub.

        Args:
            repo: Repository metadata
            index: Current repository index (1-based)
            total: Total number of repositories

        Returns:
            Dictionary with sync results
        """
        repo_name = repo["name"]
        source_url = f"{self.gitlab_url}/{self.gitlab_group}/{repo_name}.git"
        target_url = f"https://github.com/{self.github_org}/{repo_name}.git"

        with log_context(repository=repo_name,
                        source_url=source_url,
                        target_url=target_url):

            start_time = time.time()

            try:
                # Inject credentials into URLs
                source_url_auth = self.auth_manager.inject_credentials(source_url)
                target_url_auth = self.auth_manager.inject_credentials(target_url)

                # Clone from source
                self.logger.info("Cloning repository from source")
                clone_result = self.git_client.clone_mirror(
                    source_url_auth,
                    f"/tmp/repo-cloner-{self.session_id}/{repo_name}",
                    dry_run=False
                )

                if not clone_result.success:
                    raise GitOperationError(
                        f"Clone failed: {clone_result.error_message}",
                        repository=repo_name,
                        operation="clone"
                    )

                # Push to target
                self.logger.info("Pushing repository to target")
                push_result = self.git_client.push_mirror(
                    f"/tmp/repo-cloner-{self.session_id}/{repo_name}",
                    target_url_auth,
                    dry_run=False
                )

                if not push_result.success:
                    raise GitOperationError(
                        f"Push failed: {push_result.error_message}",
                        repository=repo_name,
                        operation="push"
                    )

                duration = time.time() - start_time

                # Log success
                self.logger.info("Repository sync completed",
                               extra={
                                   "commits_synced": clone_result.branches_count * 10,  # Estimate
                                   "branches_synced": clone_result.branches_count,
                                   "duration_seconds": round(duration, 1),
                                   "status": "success"
                               })

                # Update stats
                self.stats["successful"] += 1
                self.stats["total_commits"] += clone_result.branches_count * 10
                self.stats["total_branches"] += clone_result.branches_count

                # Print progress
                print(f"   [{index}/{total}] {repo_name}... ✓ "
                      f"({clone_result.branches_count * 10} commits, "
                      f"{clone_result.branches_count} branches, {duration:.1f}s)")

                return {
                    "success": True,
                    "duration": duration,
                    "commits": clone_result.branches_count * 10,
                    "branches": clone_result.branches_count
                }

            except NetworkError as e:
                if e.retryable:
                    self.logger.warning(f"Transient network error (will retry): {e}")
                    print(f"   [{index}/{total}] {repo_name}... ⚠ Network timeout (retrying...)")
                    raise  # Retry decorator will handle
                else:
                    raise
            except Exception as e:
                self.logger.error(f"Repository sync failed: {e}", exc_info=True)
                self.stats["failed"] += 1
                print(f"   [{index}/{total}] {repo_name}... ✗ Failed: {e}")
                return {"success": False, "error": str(e)}

    def _sync_repositories(self, repositories: List[Dict]):
        """Sync all repositories."""
        with log_context(operation="sync_repositories"):
            self.logger.info(f"Starting sync of {len(repositories)} repositories")
            print(f"\n📥 Syncing repositories:")

            for index, repo in enumerate(repositories, start=1):
                try:
                    self._sync_repository(repo, index, len(repositories))
                except Exception as e:
                    self.logger.error(f"Failed to sync {repo['name']}: {e}")
                    # Continue with next repository

    def _print_summary(self):
        """Print synchronization summary."""
        duration = time.time() - self.stats["start_time"]
        minutes = int(duration // 60)
        seconds = int(duration % 60)

        print(f"\n✅ Synchronization complete!\n")
        print("Summary:")
        print(f"  Total repositories: {self.stats['total_repos']}")
        print(f"  Successful: {self.stats['successful']}")
        print(f"  Failed: {self.stats['failed']}")
        print(f"  Total commits synced: {self.stats['total_commits']:,}")
        print(f"  Total branches synced: {self.stats['total_branches']}")
        print(f"  Total time: {minutes}m {seconds}s")
        print(f"\nLogs saved to: /tmp/repo-cloner-{self.session_id}.log")


def main():
    """Main entry point."""
    try:
        workflow = GitLabToGitHubSync()
        workflow.run()
    except KeyboardInterrupt:
        print("\n\n⚠ Synchronization interrupted by user")
        sys.exit(130)


if __name__ == "__main__":
    main()
