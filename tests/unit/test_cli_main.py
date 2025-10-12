"""Tests for CLI main commands (sync, version)."""

from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from repo_cloner.cli import main


class TestMainCommands:
    """Test suite for main CLI commands."""

    def test_version_command(self):
        """Test version command displays version information."""
        runner = CliRunner()
        result = runner.invoke(main, ["version"])

        assert result.exit_code == 0
        assert "repo-cloner version 0.1.0" in result.output
        assert "Python" in result.output

    def test_main_help_displays_commands(self):
        """Test main help shows available commands."""
        runner = CliRunner()
        result = runner.invoke(main, ["--help"])

        assert result.exit_code == 0
        assert "Universal Repository Cloner" in result.output
        assert "sync" in result.output
        assert "version" in result.output
        assert "archive" in result.output

    def test_main_version_option(self):
        """Test --version option on main command."""
        runner = CliRunner()
        result = runner.invoke(main, ["--version"])

        assert result.exit_code == 0
        assert "0.1.0" in result.output


class TestSyncCommand:
    """Test suite for sync command."""

    @patch("repo_cloner.cli.GitClient")
    @patch("repo_cloner.cli.AuthManager")
    def test_sync_command_with_required_args(self, mock_auth_manager, mock_git_client):
        """Test sync command with minimal required arguments."""
        # Setup mocks
        mock_auth_instance = MagicMock()
        mock_auth_manager.return_value = mock_auth_instance
        mock_auth_instance.inject_credentials.side_effect = lambda url: url

        mock_git_instance = MagicMock()
        mock_git_client.return_value = mock_git_instance

        clone_result = MagicMock()
        clone_result.success = True
        clone_result.branches_count = 3
        mock_git_instance.clone_mirror.return_value = clone_result

        push_result = MagicMock()
        push_result.success = True
        mock_git_instance.push_mirror.return_value = push_result

        runner = CliRunner()
        result = runner.invoke(
            main,
            [
                "sync",
                "--source",
                "https://gitlab.com/test/repo.git",
                "--target",
                "https://github.com/test/repo.git",
            ],
        )

        assert result.exit_code == 0
        assert "Cloning from source" in result.output
        assert "Pushing to target" in result.output
        assert "Synchronization complete" in result.output

    @patch("repo_cloner.cli.GitClient")
    @patch("repo_cloner.cli.AuthManager")
    def test_sync_command_dry_run(self, mock_auth_manager, mock_git_client):
        """Test sync command with dry-run flag."""
        # Setup mocks
        mock_auth_instance = MagicMock()
        mock_auth_manager.return_value = mock_auth_instance
        mock_auth_instance.inject_credentials.side_effect = lambda url: url

        mock_git_instance = MagicMock()
        mock_git_client.return_value = mock_git_instance

        clone_result = MagicMock()
        clone_result.success = True
        clone_result.message = "Would clone repository"
        mock_git_instance.clone_mirror.return_value = clone_result

        push_result = MagicMock()
        push_result.success = True
        push_result.message = "Would push to target"
        mock_git_instance.push_mirror.return_value = push_result

        runner = CliRunner()
        result = runner.invoke(
            main,
            [
                "sync",
                "--source",
                "https://gitlab.com/test/repo.git",
                "--target",
                "https://github.com/test/repo.git",
                "--dry-run",
            ],
        )

        assert result.exit_code == 0
        assert "Would clone repository" in result.output
        assert "Would push to target" in result.output

        # Verify dry_run=True was passed
        mock_git_instance.clone_mirror.assert_called_once()
        mock_git_instance.push_mirror.assert_called_once()
        assert mock_git_instance.clone_mirror.call_args.kwargs["dry_run"] is True
        assert mock_git_instance.push_mirror.call_args.kwargs["dry_run"] is True

    @patch("repo_cloner.cli.GitClient")
    @patch("repo_cloner.cli.AuthManager")
    def test_sync_command_verbose(self, mock_auth_manager, mock_git_client):
        """Test sync command with verbose flag."""
        # Setup mocks
        mock_auth_instance = MagicMock()
        mock_auth_manager.return_value = mock_auth_instance
        mock_auth_instance.inject_credentials.side_effect = lambda url: url

        mock_git_instance = MagicMock()
        mock_git_client.return_value = mock_git_instance

        clone_result = MagicMock()
        clone_result.success = True
        clone_result.branches_count = 3
        mock_git_instance.clone_mirror.return_value = clone_result

        push_result = MagicMock()
        push_result.success = True
        mock_git_instance.push_mirror.return_value = push_result

        runner = CliRunner()
        result = runner.invoke(
            main,
            [
                "sync",
                "--source",
                "https://gitlab.com/test/repo.git",
                "--target",
                "https://github.com/test/repo.git",
                "--verbose",
            ],
        )

        assert result.exit_code == 0
        assert "Source: https://gitlab.com/test/repo.git" in result.output
        assert "Target: https://github.com/test/repo.git" in result.output
        assert "Dry-run: False" in result.output
        assert "Local path:" in result.output

    @patch("repo_cloner.cli.GitClient")
    @patch("repo_cloner.cli.AuthManager")
    def test_sync_command_with_custom_local_path(self, mock_auth_manager, mock_git_client):
        """Test sync command with custom local path."""
        # Setup mocks
        mock_auth_instance = MagicMock()
        mock_auth_manager.return_value = mock_auth_instance
        mock_auth_instance.inject_credentials.side_effect = lambda url: url

        mock_git_instance = MagicMock()
        mock_git_client.return_value = mock_git_instance

        clone_result = MagicMock()
        clone_result.success = True
        clone_result.branches_count = 3
        mock_git_instance.clone_mirror.return_value = clone_result

        push_result = MagicMock()
        push_result.success = True
        mock_git_instance.push_mirror.return_value = push_result

        runner = CliRunner()
        result = runner.invoke(
            main,
            [
                "sync",
                "--source",
                "https://gitlab.com/test/repo.git",
                "--target",
                "https://github.com/test/repo.git",
                "--local-path",
                "/tmp/custom-path",
            ],
        )

        assert result.exit_code == 0
        mock_git_instance.clone_mirror.assert_called_once()
        assert mock_git_instance.clone_mirror.call_args.args[1] == "/tmp/custom-path"

    @patch("repo_cloner.cli.GitClient")
    @patch("repo_cloner.cli.AuthManager")
    def test_sync_command_clone_failure(self, mock_auth_manager, mock_git_client):
        """Test sync command when clone fails."""
        # Setup mocks
        mock_auth_instance = MagicMock()
        mock_auth_manager.return_value = mock_auth_instance
        mock_auth_instance.inject_credentials.side_effect = lambda url: url

        mock_git_instance = MagicMock()
        mock_git_client.return_value = mock_git_instance

        clone_result = MagicMock()
        clone_result.success = False
        clone_result.error_message = "Repository not found"
        mock_git_instance.clone_mirror.return_value = clone_result

        runner = CliRunner()
        result = runner.invoke(
            main,
            [
                "sync",
                "--source",
                "https://gitlab.com/test/repo.git",
                "--target",
                "https://github.com/test/repo.git",
            ],
        )

        assert result.exit_code == 1
        assert "Clone failed: Repository not found" in result.output

    @patch("repo_cloner.cli.GitClient")
    @patch("repo_cloner.cli.AuthManager")
    def test_sync_command_push_failure(self, mock_auth_manager, mock_git_client):
        """Test sync command when push fails."""
        # Setup mocks
        mock_auth_instance = MagicMock()
        mock_auth_manager.return_value = mock_auth_instance
        mock_auth_instance.inject_credentials.side_effect = lambda url: url

        mock_git_instance = MagicMock()
        mock_git_client.return_value = mock_git_instance

        clone_result = MagicMock()
        clone_result.success = True
        clone_result.branches_count = 3
        mock_git_instance.clone_mirror.return_value = clone_result

        push_result = MagicMock()
        push_result.success = False
        push_result.error_message = "Permission denied"
        mock_git_instance.push_mirror.return_value = push_result

        runner = CliRunner()
        result = runner.invoke(
            main,
            [
                "sync",
                "--source",
                "https://gitlab.com/test/repo.git",
                "--target",
                "https://github.com/test/repo.git",
            ],
        )

        assert result.exit_code == 1
        assert "Push failed: Permission denied" in result.output

    @patch("repo_cloner.cli.GitClient")
    @patch("repo_cloner.cli.AuthManager")
    def test_sync_command_auth_error(self, mock_auth_manager, mock_git_client):
        """Test sync command when authentication fails."""
        # Setup mocks
        mock_auth_instance = MagicMock()
        mock_auth_manager.return_value = mock_auth_instance
        mock_auth_instance.inject_credentials.side_effect = ValueError("Invalid token")

        runner = CliRunner()
        result = runner.invoke(
            main,
            [
                "sync",
                "--source",
                "https://gitlab.com/test/repo.git",
                "--target",
                "https://github.com/test/repo.git",
            ],
        )

        assert result.exit_code == 1
        assert "Authentication error: Invalid token" in result.output

    @patch("repo_cloner.cli.GitClient")
    @patch("repo_cloner.cli.AuthManager")
    def test_sync_command_with_tokens(self, mock_auth_manager, mock_git_client):
        """Test sync command with explicit tokens."""
        # Setup mocks
        mock_auth_instance = MagicMock()
        mock_auth_manager.return_value = mock_auth_instance
        mock_auth_instance.inject_credentials.side_effect = lambda url: url

        mock_git_instance = MagicMock()
        mock_git_client.return_value = mock_git_instance

        clone_result = MagicMock()
        clone_result.success = True
        clone_result.branches_count = 3
        mock_git_instance.clone_mirror.return_value = clone_result

        push_result = MagicMock()
        push_result.success = True
        mock_git_instance.push_mirror.return_value = push_result

        runner = CliRunner()
        result = runner.invoke(
            main,
            [
                "sync",
                "--source",
                "https://gitlab.com/test/repo.git",
                "--target",
                "https://github.com/test/repo.git",
                "--github-token",
                "ghp_test123",
                "--gitlab-token",
                "glpat_test456",
            ],
        )

        assert result.exit_code == 0
        # Verify AuthManager was initialized with tokens
        mock_auth_manager.assert_called_once_with(
            github_token="ghp_test123", gitlab_token="glpat_test456"
        )

    def test_sync_command_missing_required_args(self):
        """Test sync command fails with missing required arguments."""
        runner = CliRunner()

        # Missing target
        result = runner.invoke(main, ["sync", "--source", "https://gitlab.com/test/repo.git"])
        assert result.exit_code != 0
        assert "Missing option" in result.output or "required" in result.output.lower()

        # Missing source
        result = runner.invoke(main, ["sync", "--target", "https://github.com/test/repo.git"])
        assert result.exit_code != 0
        assert "Missing option" in result.output or "required" in result.output.lower()
