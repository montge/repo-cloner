"""Unit tests for SyncOrchestrator (bulk group-to-org synchronization)."""

from unittest.mock import Mock

import pytest

from repo_cloner.git_client import CloneResult, PushResult
from repo_cloner.gitlab_client import ProjectDetails
from repo_cloner.group_mapper import GroupMapper, MappingConfig, MappingStrategy
from repo_cloner.sync_orchestrator import SyncOrchestrator


@pytest.fixture
def mock_gitlab_client():
    """Create mock GitLab client."""
    client = Mock()
    client.list_projects.return_value = [
        {
            "id": 1,
            "name": "backend-auth",
            "path_with_namespace": "company/backend/auth",
            "http_url_to_repo": "https://gitlab.com/company/backend/auth.git",
        },
        {
            "id": 2,
            "name": "backend-payment",
            "path_with_namespace": "company/backend/payment",
            "http_url_to_repo": "https://gitlab.com/company/backend/payment.git",
        },
    ]

    client.get_project_details.side_effect = lambda project_id: ProjectDetails(
        id=project_id,
        name=f"repo-{project_id}",
        path_with_namespace=f"company/repo-{project_id}",
        description=f"Description for repo {project_id}",
        topics=["topic1", "topic2"],
        visibility="private",
        default_branch="main",
        http_url_to_repo=f"https://gitlab.com/company/repo-{project_id}.git",
    )

    return client


@pytest.fixture
def mock_github_client():
    """Create mock GitHub client."""
    client = Mock()
    client.repository_exists.return_value = False
    client.create_repository.return_value = {
        "name": "test-repo",
        "full_name": "test-org/test-repo",
        "html_url": "https://github.com/test-org/test-repo",
    }
    return client


@pytest.fixture
def mock_git_client():
    """Create mock Git client."""
    client = Mock()
    client.clone_mirror.return_value = CloneResult(
        success=True,
        local_path="/tmp/test-repo",
        branches_count=3,
    )
    client.push_mirror.return_value = PushResult(
        success=True,
        target_url="https://github.com/test-org/test-repo.git",
    )
    return client


@pytest.fixture
def mock_auth_manager():
    """Create mock AuthManager."""
    manager = Mock()
    manager.inject_credentials.side_effect = lambda url: url.replace("https://", "https://token@")
    return manager


@pytest.fixture
def group_mapper():
    """Create real GroupMapper with flatten strategy."""
    config = MappingConfig(strategy=MappingStrategy.FLATTEN)
    return GroupMapper(config)


@pytest.fixture
def sync_orchestrator(
    mock_gitlab_client,
    mock_github_client,
    mock_git_client,
    mock_auth_manager,
    group_mapper,
):
    """Create SyncOrchestrator with mock dependencies."""
    return SyncOrchestrator(
        gitlab_client=mock_gitlab_client,
        github_client=mock_github_client,
        git_client=mock_git_client,
        auth_manager=mock_auth_manager,
        group_mapper=group_mapper,
        github_org="test-org",
    )


class TestSyncOrchestratorBasics:
    """Basic tests for SyncOrchestrator."""

    def test_initialization(self, sync_orchestrator):
        """Test SyncOrchestrator initializes correctly."""
        assert sync_orchestrator.github_org == "test-org"
        assert sync_orchestrator.github_base_url == "https://github.com"
        assert sync_orchestrator.gitlab_client is not None
        assert sync_orchestrator.github_client is not None
        assert sync_orchestrator.git_client is not None
        assert sync_orchestrator.auth_manager is not None
        assert sync_orchestrator.group_mapper is not None

    def test_discovers_gitlab_repositories(self, sync_orchestrator, mock_gitlab_client):
        """Test that orchestrator discovers repos from GitLab group."""
        summary = sync_orchestrator.sync_group_to_org(
            gitlab_group_path="company/backend",
            dry_run=True,
        )

        mock_gitlab_client.list_projects.assert_called_once_with("company/backend")
        assert summary.total_repos == 2

    def test_maps_repository_names(self, sync_orchestrator):
        """Test that repos are mapped correctly."""
        summary = sync_orchestrator.sync_group_to_org(
            gitlab_group_path="company/backend",
            dry_run=True,
        )

        assert summary.mapped_repos == 2
        assert len(summary.mappings) == 2

        # Check mapping details
        mapping1 = summary.mappings[0]
        assert mapping1.gitlab_path == "company/backend/auth"
        assert mapping1.github_name == "company-backend-auth"
        assert mapping1.github_full_name == "test-org/company-backend-auth"

    def test_validates_github_names(self, sync_orchestrator, mock_gitlab_client):
        """Test that invalid GitHub names are caught."""
        # Create a repo with invalid name (very long path that exceeds 100 chars)
        long_path = "/".join(["verylonggroup"] * 10) + "/repo"
        mock_gitlab_client.list_projects.return_value = [
            {
                "id": 1,
                "name": "repo",
                "path_with_namespace": long_path,
                "http_url_to_repo": f"https://gitlab.com/{long_path}.git",
            }
        ]

        summary = sync_orchestrator.sync_group_to_org(
            gitlab_group_path="company",
            dry_run=True,
        )

        assert summary.mapped_repos == 0
        assert summary.skipped_repos == 1
        assert len(summary.invalid_names) == 1
        assert "exceeds 100 characters" in summary.invalid_names[0]["error"]


class TestDryRun:
    """Tests for dry-run mode."""

    def test_dry_run_does_not_create_repos(self, sync_orchestrator, mock_github_client):
        """Test dry-run doesn't create repos."""
        summary = sync_orchestrator.sync_group_to_org(
            gitlab_group_path="company/backend",
            auto_create=True,
            dry_run=True,
        )

        mock_github_client.create_repository.assert_not_called()
        assert summary.created_repos == 0

    def test_dry_run_does_not_sync_repos(self, sync_orchestrator, mock_git_client):
        """Test dry-run doesn't sync repos."""
        summary = sync_orchestrator.sync_group_to_org(
            gitlab_group_path="company/backend",
            dry_run=True,
        )

        mock_git_client.clone_mirror.assert_not_called()
        mock_git_client.push_mirror.assert_not_called()
        assert summary.synced_repos == 0

    def test_dry_run_returns_mappings(self, sync_orchestrator):
        """Test dry-run returns repository mappings."""
        summary = sync_orchestrator.sync_group_to_org(
            gitlab_group_path="company/backend",
            dry_run=True,
        )

        assert len(summary.mappings) == 2
        assert all(m.github_url for m in summary.mappings)


class TestAutoCreate:
    """Tests for auto-create functionality."""

    def test_auto_create_missing_repos(self, sync_orchestrator, mock_github_client):
        """Test auto-create creates missing repos."""
        mock_github_client.repository_exists.return_value = False

        summary = sync_orchestrator.sync_group_to_org(
            gitlab_group_path="company/backend",
            auto_create=True,
        )

        assert mock_github_client.create_repository.call_count == 2
        assert summary.created_repos == 2

    def test_auto_create_skips_existing_repos(self, sync_orchestrator, mock_github_client):
        """Test auto-create skips existing repos."""
        mock_github_client.repository_exists.return_value = True

        summary = sync_orchestrator.sync_group_to_org(
            gitlab_group_path="company/backend",
            auto_create=True,
        )

        mock_github_client.create_repository.assert_not_called()
        assert summary.created_repos == 0

    def test_auto_create_uses_descriptions_and_topics(
        self, sync_orchestrator, mock_github_client, mock_gitlab_client
    ):
        """Test auto-create uses descriptions and topics from GitLab."""
        mock_github_client.repository_exists.return_value = False

        sync_orchestrator.sync_group_to_org(
            gitlab_group_path="company/backend",
            auto_create=True,
        )

        # Check that create_repository was called with description and topics
        create_calls = mock_github_client.create_repository.call_args_list
        assert len(create_calls) == 2

        first_call = create_calls[0]
        assert first_call[1]["org_name"] == "test-org"
        assert "Description for repo" in first_call[1]["description"]
        assert first_call[1]["topics"] == ["company", "backend"]

    def test_auto_create_disabled_does_not_create(self, sync_orchestrator, mock_github_client):
        """Test that repos are not created when auto_create=False."""
        mock_github_client.repository_exists.return_value = False

        summary = sync_orchestrator.sync_group_to_org(
            gitlab_group_path="company/backend",
            auto_create=False,
        )

        mock_github_client.create_repository.assert_not_called()
        assert summary.created_repos == 0


class TestSynchronization:
    """Tests for repository synchronization."""

    def test_syncs_existing_repos(self, sync_orchestrator, mock_github_client, mock_git_client):
        """Test synchronization of existing repos."""
        mock_github_client.repository_exists.return_value = True

        summary = sync_orchestrator.sync_group_to_org(
            gitlab_group_path="company/backend",
        )

        # Should clone and push both repos
        assert mock_git_client.clone_mirror.call_count == 2
        assert mock_git_client.push_mirror.call_count == 2
        assert summary.synced_repos == 2
        assert summary.failed_repos == 0

    def test_syncs_only_existing_repos(
        self, sync_orchestrator, mock_github_client, mock_git_client
    ):
        """Test only existing repos are synced when auto_create=False."""
        # First repo exists, second doesn't
        mock_github_client.repository_exists.side_effect = [True, False]

        summary = sync_orchestrator.sync_group_to_org(
            gitlab_group_path="company/backend",
            auto_create=False,
        )

        # Only one repo should be synced
        assert mock_git_client.clone_mirror.call_count == 1
        assert mock_git_client.push_mirror.call_count == 1
        assert summary.synced_repos == 1

    def test_handles_clone_failure(self, sync_orchestrator, mock_github_client, mock_git_client):
        """Test handling of clone failures."""
        mock_github_client.repository_exists.return_value = True
        mock_git_client.clone_mirror.return_value = CloneResult(
            success=False,
            local_path="/tmp/test",
            branches_count=0,
            error_message="Clone failed",
        )

        summary = sync_orchestrator.sync_group_to_org(
            gitlab_group_path="company/backend",
        )

        assert summary.failed_repos == 2
        assert summary.synced_repos == 0

        # Check that error messages are recorded
        assert all(m.sync_error for m in summary.mappings)
        assert "Clone failed" in summary.mappings[0].sync_error

    def test_handles_push_failure(self, sync_orchestrator, mock_github_client, mock_git_client):
        """Test handling of push failures."""
        mock_github_client.repository_exists.return_value = True
        mock_git_client.push_mirror.return_value = PushResult(
            success=False,
            target_url="https://github.com/test-org/test-repo.git",
            error_message="Push failed",
        )

        summary = sync_orchestrator.sync_group_to_org(
            gitlab_group_path="company/backend",
        )

        assert summary.failed_repos == 2
        assert summary.synced_repos == 0
        assert "Push failed" in summary.mappings[0].sync_error


class TestConcurrency:
    """Tests for concurrent synchronization."""

    def test_sequential_sync_with_single_worker(
        self, sync_orchestrator, mock_github_client, mock_git_client
    ):
        """Test sequential sync with workers=1."""
        mock_github_client.repository_exists.return_value = True

        summary = sync_orchestrator.sync_group_to_org(
            gitlab_group_path="company/backend",
            workers=1,
        )

        # Should still sync all repos sequentially
        assert mock_git_client.clone_mirror.call_count == 2
        assert mock_git_client.push_mirror.call_count == 2
        assert summary.synced_repos == 2

    def test_concurrent_sync_with_multiple_workers(
        self, sync_orchestrator, mock_github_client, mock_git_client
    ):
        """Test concurrent sync with workers>1."""
        mock_github_client.repository_exists.return_value = True

        summary = sync_orchestrator.sync_group_to_org(
            gitlab_group_path="company/backend",
            workers=5,
        )

        # All repos should be synced
        assert mock_git_client.clone_mirror.call_count == 2
        assert mock_git_client.push_mirror.call_count == 2
        assert summary.synced_repos == 2


class TestConflictDetection:
    """Tests for naming conflict detection."""

    def test_detects_no_conflicts_with_flatten(
        self, mock_gitlab_client, mock_github_client, mock_git_client, mock_auth_manager
    ):
        """Test no conflicts with flatten strategy."""
        config = MappingConfig(strategy=MappingStrategy.FLATTEN)
        mapper = GroupMapper(config)

        orchestrator = SyncOrchestrator(
            gitlab_client=mock_gitlab_client,
            github_client=mock_github_client,
            git_client=mock_git_client,
            auth_manager=mock_auth_manager,
            group_mapper=mapper,
            github_org="test-org",
        )

        summary = orchestrator.sync_group_to_org(
            gitlab_group_path="company",
            dry_run=True,
        )

        assert summary.conflicts == {}

    def test_detects_conflicts_with_prefix_strategy(
        self, mock_gitlab_client, mock_github_client, mock_git_client, mock_auth_manager
    ):
        """Test conflict detection with prefix strategy."""
        # Create repos that will conflict
        mock_gitlab_client.list_projects.return_value = [
            {
                "id": 1,
                "name": "auth",
                "path_with_namespace": "company/backend/auth",
                "http_url_to_repo": "https://gitlab.com/company/backend/auth.git",
            },
            {
                "id": 2,
                "name": "auth",
                "path_with_namespace": "company/frontend/auth",
                "http_url_to_repo": "https://gitlab.com/company/frontend/auth.git",
            },
        ]

        config = MappingConfig(
            strategy=MappingStrategy.PREFIX,
            keep_last_n_levels=1,
        )
        mapper = GroupMapper(config)

        orchestrator = SyncOrchestrator(
            gitlab_client=mock_gitlab_client,
            github_client=mock_github_client,
            git_client=mock_git_client,
            auth_manager=mock_auth_manager,
            group_mapper=mapper,
            github_org="test-org",
        )

        summary = orchestrator.sync_group_to_org(
            gitlab_group_path="company",
            dry_run=True,
        )

        # Should detect conflict
        assert "auth" in summary.conflicts
        assert len(summary.conflicts["auth"]) == 2


class TestTopicExtraction:
    """Tests for topic extraction."""

    def test_extracts_topics_from_parent_groups(self, sync_orchestrator):
        """Test topics are extracted from GitLab path."""
        summary = sync_orchestrator.sync_group_to_org(
            gitlab_group_path="company/backend",
            dry_run=True,
        )

        # Check topics for first mapping
        mapping1 = summary.mappings[0]
        assert "company" in mapping1.topics
        assert "backend" in mapping1.topics

    def test_topics_used_in_repo_creation(self, sync_orchestrator, mock_github_client):
        """Test topics are passed to GitHub when creating repos."""
        mock_github_client.repository_exists.return_value = False

        sync_orchestrator.sync_group_to_org(
            gitlab_group_path="company/backend",
            auto_create=True,
        )

        # Check that topics were passed to create_repository
        create_calls = mock_github_client.create_repository.call_args_list
        first_call = create_calls[0]
        assert first_call[1]["topics"] == ["company", "backend"]


class TestAuthenticationIntegration:
    """Tests for authentication credential injection."""

    def test_injects_credentials_for_clone(
        self, sync_orchestrator, mock_github_client, mock_auth_manager, mock_git_client
    ):
        """Test credentials are injected for clone operations."""
        mock_github_client.repository_exists.return_value = True

        sync_orchestrator.sync_group_to_org(
            gitlab_group_path="company/backend",
        )

        # Check that inject_credentials was called
        assert mock_auth_manager.inject_credentials.call_count >= 2

        # Check that clone was called with authenticated URL
        clone_calls = mock_git_client.clone_mirror.call_args_list
        first_clone_url = clone_calls[0][0][0]
        assert "token@" in first_clone_url

    def test_injects_credentials_for_push(
        self, sync_orchestrator, mock_github_client, mock_auth_manager, mock_git_client
    ):
        """Test credentials are injected for push operations."""
        mock_github_client.repository_exists.return_value = True

        sync_orchestrator.sync_group_to_org(
            gitlab_group_path="company/backend",
        )

        # Check that push was called with authenticated URL
        push_calls = mock_git_client.push_mirror.call_args_list
        first_push_url = push_calls[0][0][1]
        assert "token@" in first_push_url


class TestSummaryReporting:
    """Tests for summary reporting."""

    def test_summary_includes_all_metrics(self, sync_orchestrator, mock_github_client):
        """Test summary includes all key metrics."""
        mock_github_client.repository_exists.return_value = False

        summary = sync_orchestrator.sync_group_to_org(
            gitlab_group_path="company/backend",
            auto_create=True,
        )

        assert summary.total_repos == 2
        assert summary.mapped_repos == 2
        assert summary.skipped_repos == 0
        assert summary.created_repos == 2
        assert summary.synced_repos == 2
        assert summary.failed_repos == 0
        assert len(summary.mappings) == 2

    def test_summary_tracks_created_repos(self, sync_orchestrator, mock_github_client):
        """Test summary correctly tracks created repos."""
        mock_github_client.repository_exists.return_value = False

        summary = sync_orchestrator.sync_group_to_org(
            gitlab_group_path="company/backend",
            auto_create=True,
        )

        created_mappings = [m for m in summary.mappings if m.created]
        assert len(created_mappings) == 2

    def test_summary_tracks_sync_status(self, sync_orchestrator, mock_github_client):
        """Test summary tracks sync success/failure status."""
        mock_github_client.repository_exists.return_value = True

        summary = sync_orchestrator.sync_group_to_org(
            gitlab_group_path="company/backend",
        )

        successful_mappings = [m for m in summary.mappings if m.sync_success]
        assert len(successful_mappings) == 2
        assert all(not m.sync_error for m in successful_mappings)


class TestEdgeCases:
    """Tests for edge cases and error conditions."""

    def test_handles_empty_group(self, sync_orchestrator, mock_gitlab_client):
        """Test handling of empty GitLab group."""
        mock_gitlab_client.list_projects.return_value = []

        summary = sync_orchestrator.sync_group_to_org(
            gitlab_group_path="company/empty",
            dry_run=True,
        )

        assert summary.total_repos == 0
        assert summary.mapped_repos == 0
        assert len(summary.mappings) == 0

    def test_handles_missing_project_details(
        self, sync_orchestrator, mock_gitlab_client, mock_github_client
    ):
        """Test handling when project details fetch fails."""
        mock_gitlab_client.get_project_details.side_effect = Exception("API error")
        mock_github_client.repository_exists.return_value = False

        # Should not crash, should continue without details
        summary = sync_orchestrator.sync_group_to_org(
            gitlab_group_path="company/backend",
            auto_create=True,
        )

        # Repos should still be created (with empty description)
        assert summary.created_repos == 2

    def test_handles_repo_creation_failure(self, sync_orchestrator, mock_github_client):
        """Test handling of repo creation failures."""
        mock_github_client.repository_exists.return_value = False
        mock_github_client.create_repository.side_effect = Exception("Creation failed")

        summary = sync_orchestrator.sync_group_to_org(
            gitlab_group_path="company/backend",
            auto_create=True,
        )

        # Repos should be marked with errors
        assert summary.created_repos == 0
        assert all(m.sync_error for m in summary.mappings)
        assert "Failed to create repo" in summary.mappings[0].sync_error
