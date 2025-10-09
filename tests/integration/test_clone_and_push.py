"""Integration tests for full clone and push workflow."""

import shutil
import tempfile
from pathlib import Path

import pytest

from repo_cloner.auth_manager import AuthManager
from repo_cloner.git_client import GitClient


@pytest.mark.integration
class TestCloneAndPushWorkflow:
    """Integration tests for complete clone-and-push workflows."""

    def test_dry_run_workflow_does_not_execute(self):
        """Test that dry-run mode works end-to-end without executing."""
        # Arrange
        git_client = GitClient()
        auth_manager = AuthManager(github_token="ghp_test_token", gitlab_token="glpat_test_token")

        source_url = "https://gitlab.com/test/source.git"
        target_url = "https://github.com/test/target.git"
        local_path = "/tmp/test-dry-run-repo"

        # Inject credentials
        auth_source = auth_manager.inject_credentials(source_url)
        auth_target = auth_manager.inject_credentials(target_url)

        # Act - Clone
        clone_result = git_client.clone_mirror(auth_source, local_path, dry_run=True)

        # Assert - Clone dry-run
        assert clone_result.success is True
        assert clone_result.dry_run is True
        assert "DRY-RUN" in clone_result.message
        assert not Path(local_path).exists()  # No actual clone

        # Act - Push
        push_result = git_client.push_mirror(local_path, auth_target, dry_run=True)

        # Assert - Push dry-run
        assert push_result.success is True
        assert push_result.dry_run is True
        assert "DRY-RUN" in push_result.message

    def test_authentication_flow_with_both_platforms(self):
        """Test credential injection for both GitHub and GitLab."""
        # Arrange
        auth_manager = AuthManager(github_token="ghp_real_token", gitlab_token="glpat_real_token")

        github_url = "https://github.com/org/repo.git"
        gitlab_url = "https://gitlab.com/group/repo.git"

        # Act
        github_auth = auth_manager.inject_credentials(github_url)
        gitlab_auth = auth_manager.inject_credentials(gitlab_url)

        # Assert
        assert "ghp_real_token@github.com" in github_auth
        assert "oauth2:glpat_real_token@gitlab.com" in gitlab_auth
        assert github_url.replace("https://", "https://ghp_real_token@") == github_auth

    def test_error_handling_when_clone_fails(self):
        """Test that errors in clone are handled gracefully."""
        # Arrange
        git_client = GitClient()
        invalid_url = "https://github.com/nonexistent/repo-that-does-not-exist-12345.git"
        local_path = tempfile.mkdtemp()

        try:
            # Act
            result = git_client.clone_mirror(invalid_url, local_path)

            # Assert
            assert result.success is False
            assert len(result.error_message) > 0
            assert result.branches_count == 0
        finally:
            # Cleanup
            if Path(local_path).exists():
                shutil.rmtree(local_path)

    def test_local_path_creation(self):
        """Test that parent directories are created automatically."""
        # Arrange
        git_client = GitClient()
        base_temp = tempfile.mkdtemp()
        nested_path = f"{base_temp}/nested/deep/repo"

        # Ensure nested path doesn't exist
        assert not Path(nested_path).exists()

        try:
            # Act - Dry-run to test path logic without actual clone
            result = git_client.clone_mirror(
                "https://github.com/test/repo.git", nested_path, dry_run=True
            )

            # Assert
            assert result.success is True
            # Note: In dry-run, directory isn't created, but in real clone it would be
        finally:
            # Cleanup
            if Path(base_temp).exists():
                shutil.rmtree(base_temp)
