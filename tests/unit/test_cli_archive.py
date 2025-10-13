"""Tests for CLI archive management commands."""

import subprocess
import tempfile
from pathlib import Path

from click.testing import CliRunner

from repo_cloner.cli import main


class TestCLIArchiveCreate:
    """Test suite for 'archive create' command."""

    def test_create_full_archive_from_repo(self):
        """Test creating a full archive from a repository."""
        runner = CliRunner()

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create test repository
            repo_path = Path(tmpdir) / "test-repo"
            subprocess.run(["git", "init", str(repo_path)], check=True, capture_output=True)
            subprocess.run(
                ["git", "config", "user.name", "Test"],
                cwd=str(repo_path),
                check=True,
                capture_output=True,
            )
            subprocess.run(
                ["git", "config", "user.email", "test@example.com"],
                cwd=str(repo_path),
                check=True,
                capture_output=True,
            )
            (repo_path / "test.txt").write_text("test content")
            subprocess.run(
                ["git", "add", "test.txt"], cwd=str(repo_path), check=True, capture_output=True
            )
            subprocess.run(
                ["git", "commit", "-m", "Initial"],
                cwd=str(repo_path),
                check=True,
                capture_output=True,
            )

            # Create output directory
            output_path = Path(tmpdir) / "archives"
            output_path.mkdir()

            # Act
            result = runner.invoke(
                main,
                [
                    "archive",
                    "create",
                    "--repo-path",
                    str(repo_path),
                    "--output-path",
                    str(output_path),
                ],
            )

            # Assert
            assert result.exit_code == 0
            assert "Archive created" in result.output or "✓" in result.output
            # Check that archive was created
            archives = list(output_path.glob("*.tar.gz"))
            assert len(archives) == 1

    def test_create_full_archive_with_lfs(self):
        """Test creating a full archive with LFS objects."""
        runner = CliRunner()

        with tempfile.TemporaryDirectory() as tmpdir:
            repo_path = Path(tmpdir) / "test-repo"
            subprocess.run(["git", "init", str(repo_path)], check=True, capture_output=True)
            subprocess.run(
                ["git", "config", "user.name", "Test"],
                cwd=str(repo_path),
                check=True,
                capture_output=True,
            )
            subprocess.run(
                ["git", "config", "user.email", "test@example.com"],
                cwd=str(repo_path),
                check=True,
                capture_output=True,
            )
            (repo_path / "test.txt").write_text("test")
            subprocess.run(
                ["git", "add", "test.txt"], cwd=str(repo_path), check=True, capture_output=True
            )
            subprocess.run(
                ["git", "commit", "-m", "Initial"],
                cwd=str(repo_path),
                check=True,
                capture_output=True,
            )

            output_path = Path(tmpdir) / "archives"
            output_path.mkdir()

            # Act - with --include-lfs flag
            result = runner.invoke(
                main,
                [
                    "archive",
                    "create",
                    "--repo-path",
                    str(repo_path),
                    "--output-path",
                    str(output_path),
                    "--include-lfs",
                ],
            )

            # Assert
            assert result.exit_code == 0
            assert (
                "LFS objects" in result.output
                or "Archive created" in result.output
                or "✓" in result.output
            )

    def test_create_incremental_archive(self):
        """Test creating an incremental archive."""
        runner = CliRunner()

        with tempfile.TemporaryDirectory() as tmpdir:
            repo_path = Path(tmpdir) / "test-repo"
            subprocess.run(["git", "init", str(repo_path)], check=True, capture_output=True)
            subprocess.run(
                ["git", "config", "user.name", "Test"],
                cwd=str(repo_path),
                check=True,
                capture_output=True,
            )
            subprocess.run(
                ["git", "config", "user.email", "test@example.com"],
                cwd=str(repo_path),
                check=True,
                capture_output=True,
            )
            (repo_path / "test.txt").write_text("test")
            subprocess.run(
                ["git", "add", "test.txt"], cwd=str(repo_path), check=True, capture_output=True
            )
            subprocess.run(
                ["git", "commit", "-m", "Initial"],
                cwd=str(repo_path),
                check=True,
                capture_output=True,
            )

            output_path = Path(tmpdir) / "archives"
            output_path.mkdir()

            # Create full archive first
            result1 = runner.invoke(
                main,
                [
                    "archive",
                    "create",
                    "--repo-path",
                    str(repo_path),
                    "--output-path",
                    str(output_path),
                ],
            )
            assert result1.exit_code == 0
            full_archive = list(output_path.glob("*-full-*.tar.gz"))[0]

            # Make new commit
            (repo_path / "test2.txt").write_text("test2")
            subprocess.run(
                ["git", "add", "test2.txt"], cwd=str(repo_path), check=True, capture_output=True
            )
            subprocess.run(
                ["git", "commit", "-m", "Second"],
                cwd=str(repo_path),
                check=True,
                capture_output=True,
            )

            # Act - create incremental archive
            result2 = runner.invoke(
                main,
                [
                    "archive",
                    "create",
                    "--repo-path",
                    str(repo_path),
                    "--output-path",
                    str(output_path),
                    "--type",
                    "incremental",
                    "--parent-archive",
                    str(full_archive),
                ],
            )

            # Assert
            assert result2.exit_code == 0
            assert "Archive created" in result2.output or "incremental" in result2.output
            incremental_archives = list(output_path.glob("*-incremental-*.tar.gz"))
            assert len(incremental_archives) == 1

    def test_create_fails_if_repo_not_exists(self):
        """Test that create fails if repository doesn't exist."""
        runner = CliRunner()

        result = runner.invoke(
            main,
            [
                "archive",
                "create",
                "--repo-path",
                "/nonexistent/repo",
                "--output-path",
                "/tmp/output",
            ],
        )

        assert result.exit_code != 0
        assert "does not exist" in result.output.lower() or "error" in result.output.lower()


class TestCLIArchiveVerify:
    """Test suite for 'archive verify' command."""

    def test_verify_valid_archive(self):
        """Test verifying a valid archive."""
        runner = CliRunner()

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create test repository and archive
            repo_path = Path(tmpdir) / "test-repo"
            subprocess.run(["git", "init", str(repo_path)], check=True, capture_output=True)
            subprocess.run(
                ["git", "config", "user.name", "Test"],
                cwd=str(repo_path),
                check=True,
                capture_output=True,
            )
            subprocess.run(
                ["git", "config", "user.email", "test@example.com"],
                cwd=str(repo_path),
                check=True,
                capture_output=True,
            )
            (repo_path / "test.txt").write_text("test")
            subprocess.run(
                ["git", "add", "test.txt"], cwd=str(repo_path), check=True, capture_output=True
            )
            subprocess.run(
                ["git", "commit", "-m", "Initial"],
                cwd=str(repo_path),
                check=True,
                capture_output=True,
            )

            output_path = Path(tmpdir) / "archives"
            output_path.mkdir()

            # Create archive
            result1 = runner.invoke(
                main,
                [
                    "archive",
                    "create",
                    "--repo-path",
                    str(repo_path),
                    "--output-path",
                    str(output_path),
                ],
            )
            assert result1.exit_code == 0
            archive_file = list(output_path.glob("*.tar.gz"))[0]

            # Act - verify archive
            result2 = runner.invoke(
                main, ["archive", "verify", "--archive-path", str(archive_file)]
            )

            # Assert
            assert result2.exit_code == 0
            assert "valid" in result2.output.lower() or "✓" in result2.output

    def test_verify_detects_invalid_archive(self):
        """Test that verify detects invalid archives."""
        runner = CliRunner()

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a fake invalid archive
            invalid_archive = Path(tmpdir) / "invalid.tar.gz"
            invalid_archive.write_bytes(b"not a valid tar.gz")

            # Act
            result = runner.invoke(
                main, ["archive", "verify", "--archive-path", str(invalid_archive)]
            )

            # Assert
            assert result.exit_code != 0
            assert "invalid" in result.output.lower() or "error" in result.output.lower()


class TestCLIArchiveRestore:
    """Test suite for 'archive restore' command."""

    def test_restore_archive_to_directory(self):
        """Test restoring an archive to a directory."""
        runner = CliRunner()

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create test repository and archive
            repo_path = Path(tmpdir) / "test-repo"
            subprocess.run(["git", "init", str(repo_path)], check=True, capture_output=True)
            subprocess.run(
                ["git", "config", "user.name", "Test"],
                cwd=str(repo_path),
                check=True,
                capture_output=True,
            )
            subprocess.run(
                ["git", "config", "user.email", "test@example.com"],
                cwd=str(repo_path),
                check=True,
                capture_output=True,
            )
            (repo_path / "test.txt").write_text("test content")
            subprocess.run(
                ["git", "add", "test.txt"], cwd=str(repo_path), check=True, capture_output=True
            )
            subprocess.run(
                ["git", "commit", "-m", "Initial"],
                cwd=str(repo_path),
                check=True,
                capture_output=True,
            )

            archives_path = Path(tmpdir) / "archives"
            archives_path.mkdir()

            # Create archive
            result1 = runner.invoke(
                main,
                [
                    "archive",
                    "create",
                    "--repo-path",
                    str(repo_path),
                    "--output-path",
                    str(archives_path),
                ],
            )
            assert result1.exit_code == 0
            archive_file = list(archives_path.glob("*.tar.gz"))[0]

            # Act - restore archive
            restore_path = Path(tmpdir) / "restored"
            restore_path.mkdir()
            result2 = runner.invoke(
                main,
                [
                    "archive",
                    "restore",
                    "--archive-path",
                    str(archive_file),
                    "--output-path",
                    str(restore_path),
                ],
            )

            # Assert
            assert result2.exit_code == 0
            assert "restored successfully" in result2.output.lower() or "✓" in result2.output
            # Check that repository was restored
            restored_repo = restore_path / "repository"
            assert restored_repo.exists()
            assert (restored_repo / "test.txt").exists()


class TestCLIArchiveRetention:
    """Test suite for 'archive retention' command."""

    def test_retention_applies_age_policy(self):
        """Test applying retention policy based on age."""
        runner = CliRunner()

        with tempfile.TemporaryDirectory() as tmpdir:
            archives_dir = Path(tmpdir) / "archives"
            archives_dir.mkdir()

            # Create some test archives
            (archives_dir / "repo-full-20200101.tar.gz").write_bytes(b"old archive")
            (archives_dir / "repo-full-20251010.tar.gz").write_bytes(b"recent archive")

            # Set old modification time
            import os
            import time

            old_time = time.time() - (60 * 24 * 60 * 60)  # 60 days ago
            os.utime(archives_dir / "repo-full-20200101.tar.gz", (old_time, old_time))

            # Act - apply retention policy (30 days)
            result = runner.invoke(
                main,
                [
                    "archive",
                    "retention",
                    "--archives-path",
                    str(archives_dir),
                    "--max-age-days",
                    "30",
                ],
            )

            # Assert
            assert result.exit_code == 0
            assert "deleted" in result.output.lower() or "removed" in result.output.lower()
            # Old archive should be deleted
            assert not (archives_dir / "repo-full-20200101.tar.gz").exists()
            # Recent archive should remain
            assert (archives_dir / "repo-full-20251010.tar.gz").exists()

    def test_retention_dry_run_mode(self):
        """Test retention policy in dry-run mode."""
        runner = CliRunner()

        with tempfile.TemporaryDirectory() as tmpdir:
            archives_dir = Path(tmpdir) / "archives"
            archives_dir.mkdir()

            # Create test archive
            old_archive = archives_dir / "repo-old.tar.gz"
            old_archive.write_bytes(b"old")

            import os
            import time

            old_time = time.time() - (60 * 24 * 60 * 60)
            os.utime(old_archive, (old_time, old_time))

            # Act - dry run
            result = runner.invoke(
                main,
                [
                    "archive",
                    "retention",
                    "--archives-path",
                    str(archives_dir),
                    "--max-age-days",
                    "30",
                    "--dry-run",
                ],
            )

            # Assert
            assert result.exit_code == 0
            assert "dry run" in result.output.lower() or "would delete" in result.output.lower()
            # Archive should still exist
            assert old_archive.exists()


class TestCLIArchiveUpload:
    """Test suite for 'archive upload' command."""

    def test_upload_archive_to_storage(self):
        """Test uploading an archive to storage backend."""
        runner = CliRunner()

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create test repository and archive
            repo_path = Path(tmpdir) / "test-repo"
            subprocess.run(["git", "init", str(repo_path)], check=True, capture_output=True)
            subprocess.run(
                ["git", "config", "user.name", "Test"],
                cwd=str(repo_path),
                check=True,
                capture_output=True,
            )
            subprocess.run(
                ["git", "config", "user.email", "test@example.com"],
                cwd=str(repo_path),
                check=True,
                capture_output=True,
            )
            (repo_path / "test.txt").write_text("test")
            subprocess.run(
                ["git", "add", "test.txt"], cwd=str(repo_path), check=True, capture_output=True
            )
            subprocess.run(
                ["git", "commit", "-m", "Initial"],
                cwd=str(repo_path),
                check=True,
                capture_output=True,
            )

            archives_path = Path(tmpdir) / "archives"
            archives_path.mkdir()

            # Create archive
            result1 = runner.invoke(
                main,
                [
                    "archive",
                    "create",
                    "--repo-path",
                    str(repo_path),
                    "--output-path",
                    str(archives_path),
                ],
            )
            assert result1.exit_code == 0
            archive_file = list(archives_path.glob("*.tar.gz"))[0]

            # Create storage directory
            storage_path = Path(tmpdir) / "storage"
            storage_path.mkdir()

            # Act - upload archive
            result2 = runner.invoke(
                main,
                [
                    "archive",
                    "upload",
                    "--archive-path",
                    str(archive_file),
                    "--storage-path",
                    str(storage_path),
                ],
            )

            # Assert
            assert result2.exit_code == 0
            assert "uploaded successfully" in result2.output.lower() or "✓" in result2.output
            # Check that archive was uploaded to storage
            uploaded_files = list(storage_path.glob("*.tar.gz"))
            assert len(uploaded_files) > 0

    def test_upload_archive_with_custom_remote_key(self):
        """Test uploading archive with custom remote key."""
        runner = CliRunner()

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create test repository and archive
            repo_path = Path(tmpdir) / "test-repo"
            subprocess.run(["git", "init", str(repo_path)], check=True, capture_output=True)
            subprocess.run(
                ["git", "config", "user.name", "Test"],
                cwd=str(repo_path),
                check=True,
                capture_output=True,
            )
            subprocess.run(
                ["git", "config", "user.email", "test@example.com"],
                cwd=str(repo_path),
                check=True,
                capture_output=True,
            )
            (repo_path / "test.txt").write_text("test")
            subprocess.run(
                ["git", "add", "test.txt"], cwd=str(repo_path), check=True, capture_output=True
            )
            subprocess.run(
                ["git", "commit", "-m", "Initial"],
                cwd=str(repo_path),
                check=True,
                capture_output=True,
            )

            archives_path = Path(tmpdir) / "archives"
            archives_path.mkdir()

            # Create archive
            result1 = runner.invoke(
                main,
                [
                    "archive",
                    "create",
                    "--repo-path",
                    str(repo_path),
                    "--output-path",
                    str(archives_path),
                ],
            )
            assert result1.exit_code == 0
            archive_file = list(archives_path.glob("*.tar.gz"))[0]

            # Create storage directory
            storage_path = Path(tmpdir) / "storage"
            storage_path.mkdir()

            # Act - upload with custom remote key
            result2 = runner.invoke(
                main,
                [
                    "archive",
                    "upload",
                    "--archive-path",
                    str(archive_file),
                    "--storage-path",
                    str(storage_path),
                    "--remote-key",
                    "backups/custom-name.tar.gz",
                ],
            )

            # Assert
            assert result2.exit_code == 0
            assert (
                "uploaded successfully" in result2.output.lower() or "custom-name" in result2.output
            )

    def test_upload_fails_for_missing_archive(self):
        """Test upload fails when archive doesn't exist."""
        runner = CliRunner()

        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "storage"
            storage_path.mkdir()

            result = runner.invoke(
                main,
                [
                    "archive",
                    "upload",
                    "--archive-path",
                    "/nonexistent/archive.tar.gz",
                    "--storage-path",
                    str(storage_path),
                ],
            )

            assert result.exit_code != 0
            assert "does not exist" in result.output.lower() or "error" in result.output.lower()

    def test_upload_verbose_mode(self):
        """Test upload with verbose output."""
        runner = CliRunner()

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create test repository and archive
            repo_path = Path(tmpdir) / "test-repo"
            subprocess.run(["git", "init", str(repo_path)], check=True, capture_output=True)
            subprocess.run(
                ["git", "config", "user.name", "Test"],
                cwd=str(repo_path),
                check=True,
                capture_output=True,
            )
            subprocess.run(
                ["git", "config", "user.email", "test@example.com"],
                cwd=str(repo_path),
                check=True,
                capture_output=True,
            )
            (repo_path / "test.txt").write_text("test")
            subprocess.run(
                ["git", "add", "test.txt"], cwd=str(repo_path), check=True, capture_output=True
            )
            subprocess.run(
                ["git", "commit", "-m", "Initial"],
                cwd=str(repo_path),
                check=True,
                capture_output=True,
            )

            archives_path = Path(tmpdir) / "archives"
            archives_path.mkdir()

            # Create archive
            result1 = runner.invoke(
                main,
                [
                    "archive",
                    "create",
                    "--repo-path",
                    str(repo_path),
                    "--output-path",
                    str(archives_path),
                ],
            )
            assert result1.exit_code == 0
            archive_file = list(archives_path.glob("*.tar.gz"))[0]

            storage_path = Path(tmpdir) / "storage"
            storage_path.mkdir()

            # Act - upload with verbose
            result2 = runner.invoke(
                main,
                [
                    "archive",
                    "upload",
                    "--archive-path",
                    str(archive_file),
                    "--storage-path",
                    str(storage_path),
                    "--verbose",
                ],
            )

            # Assert
            assert result2.exit_code == 0
            assert "Archive:" in result2.output or "Size:" in result2.output


class TestCLIArchiveDownload:
    """Test suite for 'archive download' command."""

    def test_download_archive_from_storage(self):
        """Test downloading an archive from storage backend."""
        runner = CliRunner()

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create test repository and archive
            repo_path = Path(tmpdir) / "test-repo"
            subprocess.run(["git", "init", str(repo_path)], check=True, capture_output=True)
            subprocess.run(
                ["git", "config", "user.name", "Test"],
                cwd=str(repo_path),
                check=True,
                capture_output=True,
            )
            subprocess.run(
                ["git", "config", "user.email", "test@example.com"],
                cwd=str(repo_path),
                check=True,
                capture_output=True,
            )
            (repo_path / "test.txt").write_text("test")
            subprocess.run(
                ["git", "add", "test.txt"], cwd=str(repo_path), check=True, capture_output=True
            )
            subprocess.run(
                ["git", "commit", "-m", "Initial"],
                cwd=str(repo_path),
                check=True,
                capture_output=True,
            )

            archives_path = Path(tmpdir) / "archives"
            archives_path.mkdir()

            # Create archive
            result1 = runner.invoke(
                main,
                [
                    "archive",
                    "create",
                    "--repo-path",
                    str(repo_path),
                    "--output-path",
                    str(archives_path),
                ],
            )
            assert result1.exit_code == 0
            archive_file = list(archives_path.glob("*.tar.gz"))[0]

            # Upload to storage
            storage_path = Path(tmpdir) / "storage"
            storage_path.mkdir()
            result2 = runner.invoke(
                main,
                [
                    "archive",
                    "upload",
                    "--archive-path",
                    str(archive_file),
                    "--storage-path",
                    str(storage_path),
                ],
            )
            assert result2.exit_code == 0

            # Act - download archive
            download_path = Path(tmpdir) / "downloads" / "downloaded.tar.gz"
            download_path.parent.mkdir()
            result3 = runner.invoke(
                main,
                [
                    "archive",
                    "download",
                    "--storage-path",
                    str(storage_path),
                    "--remote-key",
                    archive_file.name,
                    "--output-path",
                    str(download_path),
                ],
            )

            # Assert
            assert result3.exit_code == 0
            assert "downloaded successfully" in result3.output.lower() or "✓" in result3.output
            assert download_path.exists()

    def test_download_fails_for_missing_remote_key(self):
        """Test download fails when remote key doesn't exist."""
        runner = CliRunner()

        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "storage"
            storage_path.mkdir()

            download_path = Path(tmpdir) / "downloads" / "archive.tar.gz"
            download_path.parent.mkdir()

            result = runner.invoke(
                main,
                [
                    "archive",
                    "download",
                    "--storage-path",
                    str(storage_path),
                    "--remote-key",
                    "nonexistent.tar.gz",
                    "--output-path",
                    str(download_path),
                ],
            )

            assert result.exit_code != 0
            assert (
                "not found" in result.output.lower()
                or "error" in result.output.lower()
                or "does not exist" in result.output.lower()
            )

    def test_download_verbose_mode(self):
        """Test download with verbose output."""
        runner = CliRunner()

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create test repository and archive
            repo_path = Path(tmpdir) / "test-repo"
            subprocess.run(["git", "init", str(repo_path)], check=True, capture_output=True)
            subprocess.run(
                ["git", "config", "user.name", "Test"],
                cwd=str(repo_path),
                check=True,
                capture_output=True,
            )
            subprocess.run(
                ["git", "config", "user.email", "test@example.com"],
                cwd=str(repo_path),
                check=True,
                capture_output=True,
            )
            (repo_path / "test.txt").write_text("test")
            subprocess.run(
                ["git", "add", "test.txt"], cwd=str(repo_path), check=True, capture_output=True
            )
            subprocess.run(
                ["git", "commit", "-m", "Initial"],
                cwd=str(repo_path),
                check=True,
                capture_output=True,
            )

            archives_path = Path(tmpdir) / "archives"
            archives_path.mkdir()

            # Create and upload archive
            result1 = runner.invoke(
                main,
                [
                    "archive",
                    "create",
                    "--repo-path",
                    str(repo_path),
                    "--output-path",
                    str(archives_path),
                ],
            )
            assert result1.exit_code == 0
            archive_file = list(archives_path.glob("*.tar.gz"))[0]

            storage_path = Path(tmpdir) / "storage"
            storage_path.mkdir()
            result2 = runner.invoke(
                main,
                [
                    "archive",
                    "upload",
                    "--archive-path",
                    str(archive_file),
                    "--storage-path",
                    str(storage_path),
                ],
            )
            assert result2.exit_code == 0

            # Act - download with verbose
            download_path = Path(tmpdir) / "downloads" / "archive.tar.gz"
            download_path.parent.mkdir()
            result3 = runner.invoke(
                main,
                [
                    "archive",
                    "download",
                    "--storage-path",
                    str(storage_path),
                    "--remote-key",
                    archive_file.name,
                    "--output-path",
                    str(download_path),
                    "--verbose",
                ],
            )

            # Assert
            assert result3.exit_code == 0
            assert "Storage path:" in result3.output or "Size:" in result3.output


class TestCLIArchiveList:
    """Test suite for 'archive list' command."""

    def test_list_archives_in_storage(self):
        """Test listing archives in storage backend."""
        runner = CliRunner()

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create test repository and archives
            repo_path = Path(tmpdir) / "test-repo"
            subprocess.run(["git", "init", str(repo_path)], check=True, capture_output=True)
            subprocess.run(
                ["git", "config", "user.name", "Test"],
                cwd=str(repo_path),
                check=True,
                capture_output=True,
            )
            subprocess.run(
                ["git", "config", "user.email", "test@example.com"],
                cwd=str(repo_path),
                check=True,
                capture_output=True,
            )
            (repo_path / "test.txt").write_text("test")
            subprocess.run(
                ["git", "add", "test.txt"], cwd=str(repo_path), check=True, capture_output=True
            )
            subprocess.run(
                ["git", "commit", "-m", "Initial"],
                cwd=str(repo_path),
                check=True,
                capture_output=True,
            )

            archives_path = Path(tmpdir) / "archives"
            archives_path.mkdir()

            # Create and upload multiple archives
            storage_path = Path(tmpdir) / "storage"
            storage_path.mkdir()

            for i in range(3):
                result1 = runner.invoke(
                    main,
                    [
                        "archive",
                        "create",
                        "--repo-path",
                        str(repo_path),
                        "--output-path",
                        str(archives_path),
                    ],
                )
                assert result1.exit_code == 0
                archive_file = list(archives_path.glob("*.tar.gz"))[0]

                result2 = runner.invoke(
                    main,
                    [
                        "archive",
                        "upload",
                        "--archive-path",
                        str(archive_file),
                        "--storage-path",
                        str(storage_path),
                        "--remote-key",
                        f"archive-{i}.tar.gz",
                    ],
                )
                assert result2.exit_code == 0
                archive_file.unlink()  # Clean up for next iteration

            # Act - list archives
            result = runner.invoke(main, ["archive", "list", "--storage-path", str(storage_path)])

            # Assert
            assert result.exit_code == 0
            assert "Found" in result.output or "archive" in result.output.lower()
            # Should list at least one archive
            assert "archive-" in result.output

    def test_list_archives_with_prefix_filter(self):
        """Test listing archives with prefix filter."""
        runner = CliRunner()

        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "storage"
            storage_path.mkdir()

            # Create some archives with different prefixes
            (storage_path / "backups").mkdir()
            (storage_path / "backups" / "repo-1.tar.gz").write_bytes(b"archive1")
            (storage_path / "backups" / "repo-2.tar.gz").write_bytes(b"archive2")
            (storage_path / "temp-archive.tar.gz").write_bytes(b"temp")

            # Act - list with prefix filter
            result = runner.invoke(
                main,
                [
                    "archive",
                    "list",
                    "--storage-path",
                    str(storage_path),
                    "--prefix",
                    "backups/",
                ],
            )

            # Assert
            assert result.exit_code == 0
            assert "backups/" in result.output or "repo-" in result.output

    def test_list_archives_verbose_mode(self):
        """Test listing archives with verbose output."""
        runner = CliRunner()

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create test repository and archive
            repo_path = Path(tmpdir) / "test-repo"
            subprocess.run(["git", "init", str(repo_path)], check=True, capture_output=True)
            subprocess.run(
                ["git", "config", "user.name", "Test"],
                cwd=str(repo_path),
                check=True,
                capture_output=True,
            )
            subprocess.run(
                ["git", "config", "user.email", "test@example.com"],
                cwd=str(repo_path),
                check=True,
                capture_output=True,
            )
            (repo_path / "test.txt").write_text("test")
            subprocess.run(
                ["git", "add", "test.txt"], cwd=str(repo_path), check=True, capture_output=True
            )
            subprocess.run(
                ["git", "commit", "-m", "Initial"],
                cwd=str(repo_path),
                check=True,
                capture_output=True,
            )

            archives_path = Path(tmpdir) / "archives"
            archives_path.mkdir()

            # Create and upload archive
            result1 = runner.invoke(
                main,
                [
                    "archive",
                    "create",
                    "--repo-path",
                    str(repo_path),
                    "--output-path",
                    str(archives_path),
                ],
            )
            assert result1.exit_code == 0
            archive_file = list(archives_path.glob("*.tar.gz"))[0]

            storage_path = Path(tmpdir) / "storage"
            storage_path.mkdir()
            result2 = runner.invoke(
                main,
                [
                    "archive",
                    "upload",
                    "--archive-path",
                    str(archive_file),
                    "--storage-path",
                    str(storage_path),
                ],
            )
            assert result2.exit_code == 0

            # Act - list with verbose
            result = runner.invoke(
                main, ["archive", "list", "--storage-path", str(storage_path), "--verbose"]
            )

            # Assert
            assert result.exit_code == 0
            assert "Size:" in result.output or "Timestamp:" in result.output

    def test_list_empty_storage(self):
        """Test listing archives when storage is empty."""
        runner = CliRunner()

        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "storage"
            storage_path.mkdir()

            result = runner.invoke(main, ["archive", "list", "--storage-path", str(storage_path)])

            assert result.exit_code == 0
            assert (
                "no archives found" in result.output.lower() or "0 archive" in result.output.lower()
            )


class TestCLIArchiveVerboseModes:
    """Test suite for verbose modes in archive commands."""

    def test_create_verbose_mode(self):
        """Test create command with verbose flag."""
        runner = CliRunner()

        with tempfile.TemporaryDirectory() as tmpdir:
            repo_path = Path(tmpdir) / "test-repo"
            subprocess.run(["git", "init", str(repo_path)], check=True, capture_output=True)
            subprocess.run(
                ["git", "config", "user.name", "Test"],
                cwd=str(repo_path),
                check=True,
                capture_output=True,
            )
            subprocess.run(
                ["git", "config", "user.email", "test@example.com"],
                cwd=str(repo_path),
                check=True,
                capture_output=True,
            )
            (repo_path / "test.txt").write_text("test")
            subprocess.run(
                ["git", "add", "test.txt"], cwd=str(repo_path), check=True, capture_output=True
            )
            subprocess.run(
                ["git", "commit", "-m", "Initial"],
                cwd=str(repo_path),
                check=True,
                capture_output=True,
            )

            output_path = Path(tmpdir) / "archives"
            output_path.mkdir()

            result = runner.invoke(
                main,
                [
                    "archive",
                    "create",
                    "--repo-path",
                    str(repo_path),
                    "--output-path",
                    str(output_path),
                    "--verbose",
                ],
            )

            assert result.exit_code == 0
            assert "Repository:" in result.output
            assert "Output path:" in result.output
            assert "Archive type:" in result.output

    def test_create_incremental_without_parent_archive(self):
        """Test incremental archive fails without parent-archive."""
        runner = CliRunner()

        with tempfile.TemporaryDirectory() as tmpdir:
            repo_path = Path(tmpdir) / "test-repo"
            subprocess.run(["git", "init", str(repo_path)], check=True, capture_output=True)
            subprocess.run(
                ["git", "config", "user.name", "Test"],
                cwd=str(repo_path),
                check=True,
                capture_output=True,
            )
            subprocess.run(
                ["git", "config", "user.email", "test@example.com"],
                cwd=str(repo_path),
                check=True,
                capture_output=True,
            )
            (repo_path / "test.txt").write_text("test")
            subprocess.run(
                ["git", "add", "test.txt"], cwd=str(repo_path), check=True, capture_output=True
            )
            subprocess.run(
                ["git", "commit", "-m", "Initial"],
                cwd=str(repo_path),
                check=True,
                capture_output=True,
            )

            output_path = Path(tmpdir) / "archives"
            output_path.mkdir()

            result = runner.invoke(
                main,
                [
                    "archive",
                    "create",
                    "--repo-path",
                    str(repo_path),
                    "--output-path",
                    str(output_path),
                    "--type",
                    "incremental",
                ],
            )

            assert result.exit_code == 1
            assert "--parent-archive is required" in result.output

    def test_verify_verbose_mode(self):
        """Test verify command with verbose flag."""
        runner = CliRunner()

        with tempfile.TemporaryDirectory() as tmpdir:
            repo_path = Path(tmpdir) / "test-repo"
            subprocess.run(["git", "init", str(repo_path)], check=True, capture_output=True)
            subprocess.run(
                ["git", "config", "user.name", "Test"],
                cwd=str(repo_path),
                check=True,
                capture_output=True,
            )
            subprocess.run(
                ["git", "config", "user.email", "test@example.com"],
                cwd=str(repo_path),
                check=True,
                capture_output=True,
            )
            (repo_path / "test.txt").write_text("test")
            subprocess.run(
                ["git", "add", "test.txt"], cwd=str(repo_path), check=True, capture_output=True
            )
            subprocess.run(
                ["git", "commit", "-m", "Initial"],
                cwd=str(repo_path),
                check=True,
                capture_output=True,
            )

            output_path = Path(tmpdir) / "archives"
            output_path.mkdir()

            # Create archive
            result1 = runner.invoke(
                main,
                [
                    "archive",
                    "create",
                    "--repo-path",
                    str(repo_path),
                    "--output-path",
                    str(output_path),
                ],
            )
            assert result1.exit_code == 0
            archive_file = list(output_path.glob("*.tar.gz"))[0]

            # Verify with verbose
            result2 = runner.invoke(
                main, ["archive", "verify", "--archive-path", str(archive_file), "--verbose"]
            )

            assert result2.exit_code == 0
            assert "Manifest:" in result2.output or "Bundle:" in result2.output

    def test_restore_verbose_mode(self):
        """Test restore command with verbose flag."""
        runner = CliRunner()

        with tempfile.TemporaryDirectory() as tmpdir:
            repo_path = Path(tmpdir) / "test-repo"
            subprocess.run(["git", "init", str(repo_path)], check=True, capture_output=True)
            subprocess.run(
                ["git", "config", "user.name", "Test"],
                cwd=str(repo_path),
                check=True,
                capture_output=True,
            )
            subprocess.run(
                ["git", "config", "user.email", "test@example.com"],
                cwd=str(repo_path),
                check=True,
                capture_output=True,
            )
            (repo_path / "test.txt").write_text("test")
            subprocess.run(
                ["git", "add", "test.txt"], cwd=str(repo_path), check=True, capture_output=True
            )
            subprocess.run(
                ["git", "commit", "-m", "Initial"],
                cwd=str(repo_path),
                check=True,
                capture_output=True,
            )

            archives_path = Path(tmpdir) / "archives"
            archives_path.mkdir()

            # Create archive
            result1 = runner.invoke(
                main,
                [
                    "archive",
                    "create",
                    "--repo-path",
                    str(repo_path),
                    "--output-path",
                    str(archives_path),
                ],
            )
            assert result1.exit_code == 0
            archive_file = list(archives_path.glob("*.tar.gz"))[0]

            # Restore with verbose
            restore_path = Path(tmpdir) / "restored"
            restore_path.mkdir()
            result2 = runner.invoke(
                main,
                [
                    "archive",
                    "restore",
                    "--archive-path",
                    str(archive_file),
                    "--output-path",
                    str(restore_path),
                    "--verbose",
                ],
            )

            assert result2.exit_code == 0
            assert "Archive:" in result2.output or "Repository name:" in result2.output

    def test_retention_verbose_mode(self):
        """Test retention command with verbose flag."""
        runner = CliRunner()

        with tempfile.TemporaryDirectory() as tmpdir:
            archives_dir = Path(tmpdir) / "archives"
            archives_dir.mkdir()

            # Create test archives
            (archives_dir / "repo-1.tar.gz").write_bytes(b"archive1")
            (archives_dir / "repo-2.tar.gz").write_bytes(b"archive2")

            import os
            import time

            old_time = time.time() - (60 * 24 * 60 * 60)
            os.utime(archives_dir / "repo-1.tar.gz", (old_time, old_time))

            result = runner.invoke(
                main,
                [
                    "archive",
                    "retention",
                    "--archives-path",
                    str(archives_dir),
                    "--max-age-days",
                    "30",
                    "--verbose",
                ],
            )

            assert result.exit_code == 0
            assert "Archives path:" in result.output or "Max age" in result.output
