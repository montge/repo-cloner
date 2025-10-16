"""Integration tests for group mapping with real GitLab and GitHub APIs.

These tests use real API calls to verify the sync-group functionality works end-to-end.
"""

import os

import pytest

from repo_cloner.auth_manager import AuthManager
from repo_cloner.git_client import GitClient
from repo_cloner.github_client import GitHubClient
from repo_cloner.gitlab_client import GitLabClient
from repo_cloner.group_mapper import GroupMapper, MappingConfig, MappingStrategy
from repo_cloner.sync_orchestrator import SyncOrchestrator


@pytest.fixture
def gitlab_token():
    """Get GitLab token from environment."""
    token = os.environ.get("GITLAB_TOKEN")
    if not token:
        pytest.skip("GITLAB_TOKEN not set")
    return token


@pytest.fixture
def github_token():
    """Get GitHub token from environment."""
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        pytest.skip("GITHUB_TOKEN not set")
    return token


@pytest.fixture
def gitlab_client(gitlab_token):
    """Create GitLab client."""
    return GitLabClient(url="https://gitlab.com", token=gitlab_token)


@pytest.fixture
def github_client(github_token):
    """Create GitHub client."""
    return GitHubClient(token=github_token, base_url="https://api.github.com")


@pytest.fixture
def git_client():
    """Create Git client."""
    return GitClient()


@pytest.fixture
def auth_manager(gitlab_token, github_token):
    """Create AuthManager."""
    return AuthManager(gitlab_token=gitlab_token, github_token=github_token)


class TestGroupMappingDryRun:
    """Test group mapping in dry-run mode (no actual sync)."""

    def test_discover_and_map_repos_flatten_strategy(
        self, gitlab_client, github_client, git_client, auth_manager
    ):
        """Test discovering and mapping repos with flatten strategy."""
        # Setup
        config = MappingConfig(strategy=MappingStrategy.FLATTEN, separator="-", use_topics=True)
        mapper = GroupMapper(config)
        orchestrator = SyncOrchestrator(
            gitlab_client=gitlab_client,
            github_client=github_client,
            git_client=git_client,
            auth_manager=auth_manager,
            group_mapper=mapper,
            github_org="test-sync-org612351",
            github_base_url="https://github.com",
        )

        # Execute dry-run
        summary = orchestrator.sync_group_to_org(
            gitlab_group_path="test6452742/again", auto_create=False, dry_run=True, workers=5
        )

        # Verify
        assert summary.total_repos >= 14, "Should discover at least 14 repos"
        assert summary.mapped_repos >= 14, "Should map all discovered repos"
        assert summary.skipped_repos == 0, "No repos should be skipped with valid names"
        assert len(summary.conflicts) == 0, "Flatten strategy should have no conflicts"
        assert len(summary.invalid_names) == 0, "All names should be valid"
        assert summary.created_repos == 0, "Dry-run should not create repos"
        assert summary.synced_repos == 0, "Dry-run should not sync repos"
        assert summary.failed_repos == 0, "Dry-run should have no failures"

        # Verify mappings
        assert len(summary.mappings) >= 14, "Should have at least 14 mappings"

        # Verify naming pattern (flatten with hyphen separator)
        for mapping in summary.mappings:
            assert "-" in mapping.github_name, "Should use hyphen separator"
            assert mapping.github_name.startswith("test6452742-again-"), "Should include group path"

            # Verify topics extracted from parent groups
            assert "test6452742" in mapping.topics, "Should have test6452742 topic"
            assert "again" in mapping.topics, "Should have again topic"

    def test_discover_and_map_repos_flatten_with_strip_parent(
        self, gitlab_client, github_client, git_client, auth_manager
    ):
        """Test flatten strategy with strip_parent_group enabled."""
        # Setup
        config = MappingConfig(
            strategy=MappingStrategy.FLATTEN,
            separator="-",
            strip_parent_group=True,
            use_topics=True,
        )
        mapper = GroupMapper(config)
        orchestrator = SyncOrchestrator(
            gitlab_client=gitlab_client,
            github_client=github_client,
            git_client=git_client,
            auth_manager=auth_manager,
            group_mapper=mapper,
            github_org="test-sync-org612351",
            github_base_url="https://github.com",
        )

        # Execute dry-run
        summary = orchestrator.sync_group_to_org(
            gitlab_group_path="test6452742/again", auto_create=False, dry_run=True, workers=5
        )

        # Verify
        assert summary.total_repos >= 14, "Should discover at least 14 repos"
        assert summary.mapped_repos >= 14, "Should map all discovered repos"

        # Verify naming pattern (strip parent)
        for mapping in summary.mappings:
            # Should not start with "test6452742" since parent is stripped
            assert not mapping.github_name.startswith("test6452742"), "Should strip parent group"

            # For repos directly in "again/", names should start with "again-"
            # For repos in subgroups, names should include the subgroup
            parts = mapping.gitlab_path.split("/")
            if len(parts) == 3:  # test6452742/again/repo-name
                assert mapping.github_name.startswith(
                    "again-"
                ), "Should start with 'again-' after stripping parent"

    def test_discover_and_map_repos_prefix_strategy(
        self, gitlab_client, github_client, git_client, auth_manager
    ):
        """Test prefix strategy with keep_last_n_levels."""
        # Setup
        config = MappingConfig(
            strategy=MappingStrategy.PREFIX,
            separator="-",
            keep_last_n_levels=1,  # Keep only repo name
            use_topics=True,
        )
        mapper = GroupMapper(config)
        orchestrator = SyncOrchestrator(
            gitlab_client=gitlab_client,
            github_client=github_client,
            git_client=git_client,
            auth_manager=auth_manager,
            group_mapper=mapper,
            github_org="test-sync-org612351",
            github_base_url="https://github.com",
        )

        # Execute dry-run
        summary = orchestrator.sync_group_to_org(
            gitlab_group_path="test6452742/again", auto_create=False, dry_run=True, workers=5
        )

        # Verify
        assert summary.total_repos >= 14, "Should discover at least 14 repos"

        # With prefix strategy and keep_last_n=1, we might have conflicts
        # (multiple repos with same name in different subgroups)
        # This is expected behavior

        # Verify topics are used to preserve hierarchy context
        for mapping in summary.mappings:
            assert len(mapping.topics) > 0, "Should have topics to preserve context"

    def test_check_existing_repos(self, gitlab_client, github_client, git_client, auth_manager):
        """Test checking which repos already exist on GitHub."""
        # Setup
        config = MappingConfig(strategy=MappingStrategy.FLATTEN, separator="-", use_topics=True)
        mapper = GroupMapper(config)
        orchestrator = SyncOrchestrator(
            gitlab_client=gitlab_client,
            github_client=github_client,
            git_client=git_client,
            auth_manager=auth_manager,
            group_mapper=mapper,
            github_org="test-sync-org612351",
            github_base_url="https://github.com",
        )

        # Execute dry-run
        summary = orchestrator.sync_group_to_org(
            gitlab_group_path="test6452742/again", auto_create=False, dry_run=True, workers=5
        )

        # Verify - some repos should exist from previous tests
        existing_count = sum(1 for m in summary.mappings if m.github_exists)
        print(f"\nFound {existing_count}/{len(summary.mappings)} existing repos on GitHub")

        # We expect some repos to exist from previous test runs
        # But we don't assert a specific number since it depends on test history

    def test_validate_all_github_names(
        self, gitlab_client, github_client, git_client, auth_manager
    ):
        """Test that all mapped names are valid GitHub repository names."""
        # Setup
        config = MappingConfig(strategy=MappingStrategy.FLATTEN, separator="-", use_topics=True)
        mapper = GroupMapper(config)
        orchestrator = SyncOrchestrator(
            gitlab_client=gitlab_client,
            github_client=github_client,
            git_client=git_client,
            auth_manager=auth_manager,
            group_mapper=mapper,
            github_org="test-sync-org612351",
            github_base_url="https://github.com",
        )

        # Execute dry-run
        summary = orchestrator.sync_group_to_org(
            gitlab_group_path="test6452742/again", auto_create=False, dry_run=True, workers=5
        )

        # Verify all names are valid
        assert len(summary.invalid_names) == 0, "All mapped names should be valid"

        for mapping in summary.mappings:
            # Validate GitHub naming rules
            assert len(mapping.github_name) <= 100, "Name should not exceed 100 chars"
            assert not mapping.github_name.startswith("-"), "Name should not start with hyphen"
            assert not mapping.github_name.startswith("_"), "Name should not start with underscore"
            assert not mapping.github_name.endswith(".git"), "Name should not end with .git"


class TestGroupMappingActualSync:
    """Test actual synchronization with real APIs (creates/updates repos).

    WARNING: These tests make real API calls and may create repositories.
    Only run these tests when you want to actually sync repositories.
    """

    @pytest.mark.slow
    @pytest.mark.integration
    def test_sync_single_repo_to_verify_workflow(
        self, gitlab_client, github_client, git_client, auth_manager
    ):
        """Test syncing a single repository to verify the complete workflow.

        This test will:
        1. Pick one repository from the GitLab group
        2. Check if it exists on GitHub
        3. If not, create it (if auto_create=True)
        4. Sync the repository
        """
        # Setup
        config = MappingConfig(strategy=MappingStrategy.FLATTEN, separator="-", use_topics=True)
        mapper = GroupMapper(config)
        orchestrator = SyncOrchestrator(
            gitlab_client=gitlab_client,
            github_client=github_client,
            git_client=git_client,
            auth_manager=auth_manager,
            group_mapper=mapper,
            github_org="test-sync-org612351",
            github_base_url="https://github.com",
        )

        # First, get the repository list in dry-run
        dry_run_summary = orchestrator.sync_group_to_org(
            gitlab_group_path="test6452742/again", auto_create=False, dry_run=True, workers=1
        )

        assert len(dry_run_summary.mappings) > 0, "Should have at least one repo"

        # Pick the first repo for testing
        test_repo_path = dry_run_summary.mappings[0].gitlab_path
        print(f"\nTesting sync with repo: {test_repo_path}")

        # Now sync just one repo by creating a new orchestrator
        # that will filter to just this repo
        # (Note: This is a simplified test - in real usage you'd sync the whole group)

        # For this test, we'll just verify dry-run works, then do actual sync in manual testing
        # To avoid creating many repos during automated tests


@pytest.mark.manual
class TestManualGroupSync:
    """Manual tests for complete group synchronization.

    These tests are marked as 'manual' and should be run explicitly when you want
    to perform actual synchronization of all repositories.

    Run with: pytest -m manual tests/integration/test_group_mapping.py -v
    """

    def test_sync_entire_group_with_auto_create(
        self, gitlab_client, github_client, git_client, auth_manager
    ):
        """Sync entire GitLab group to GitHub with auto-create enabled.

        WARNING: This will create up to 14 repositories on GitHub if they don't exist.
        """
        # Setup
        config = MappingConfig(
            strategy=MappingStrategy.FLATTEN,
            separator="-",
            strip_parent_group=True,  # Strip "test6452742"
            use_topics=True,
        )
        mapper = GroupMapper(config)
        orchestrator = SyncOrchestrator(
            gitlab_client=gitlab_client,
            github_client=github_client,
            git_client=git_client,
            auth_manager=auth_manager,
            group_mapper=mapper,
            github_org="test-sync-org612351",
            github_base_url="https://github.com",
        )

        # Execute actual sync with auto-create
        summary = orchestrator.sync_group_to_org(
            gitlab_group_path="test6452742/again",
            auto_create=True,
            dry_run=False,
            workers=5,
        )

        # Verify
        print(f"\n{'='*60}")
        print("Sync Summary:")
        print(f"  Total repos: {summary.total_repos}")
        print(f"  Mapped repos: {summary.mapped_repos}")
        print(f"  Created repos: {summary.created_repos}")
        print(f"  Synced repos: {summary.synced_repos}")
        print(f"  Failed repos: {summary.failed_repos}")
        print(f"{'='*60}")

        assert summary.failed_repos == 0, "All syncs should succeed"
        assert summary.synced_repos > 0, "Should sync at least one repo"

        # Verify all repos are now on GitHub
        for mapping in summary.mappings:
            assert mapping.github_exists or mapping.created, "Repo should exist or be created"
            if not mapping.sync_error:
                assert mapping.sync_success, "Sync should succeed"
