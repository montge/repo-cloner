#!/usr/bin/env python3
"""Air-Gap Archive Restoration Workflow.

This example workflow demonstrates restoring repositories from archives
in air-gap environments with validation, integrity checks, and dependency
installation.

Features:
- Download archives from storage backends
- Archive integrity verification
- Repository restoration from git bundles
- Dependency installation (Python, Node.js, etc.)
- Push to target Git platform
- Comprehensive validation and logging

Usage:
    python air-gap-archive-restore.py

Environment Variables:
    ARCHIVE_PATH: Local path to archive file (required if not downloading)
    STORAGE_TYPE: local, s3, azure, gcs (for downloading)
    STORAGE_PATH: Storage location (S3 bucket, Azure container, or filesystem path)
    REMOTE_KEY: Archive key/path in storage (required if downloading)
    TARGET_REPO_URL: Target repository URL to push to (required)
    TARGET_TOKEN: Authentication token for target
    RESTORE_OUTPUT_PATH: Local path for restoration (default: ./restored)
    INSTALL_DEPENDENCIES: Install dependencies after restore (default: true)
"""

import os
import sys
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

# Add repo-cloner to path if running from examples directory
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from repo_cloner.archive_manager import ArchiveManager
from repo_cloner.auth_manager import AuthManager
from repo_cloner.exceptions import (
    ArchiveError,
    AuthenticationError,
    ConfigurationError,
    GitOperationError,
    RepoClonerError,
)
from repo_cloner.git_client import GitClient
from repo_cloner.logging_config import configure_logging, get_logger, log_context
from repo_cloner.storage_backend import LocalFilesystemBackend


class AirGapArchiveRestorer:
    """Air-gap archive restoration workflow."""

    def __init__(self):
        """Initialize the archive restoration workflow."""
        # Generate unique session ID
        self.session_id = f"restore-{datetime.now().strftime('%Y%m%d-%H%M%S')}"

        # Configure logging
        self.logger = configure_logging(
            level="INFO",
            json_format=True,
            log_file=f"/tmp/repo-cloner-restore-{self.session_id}.log"
        )
        self.logger = get_logger("workflows.air_gap_archive_restore")

        # Load configuration
        self.archive_path = os.getenv("ARCHIVE_PATH")
        self.storage_type = os.getenv("STORAGE_TYPE")
        self.storage_path = os.getenv("STORAGE_PATH")
        self.remote_key = os.getenv("REMOTE_KEY")
        self.target_repo_url = os.getenv("TARGET_REPO_URL")
        self.target_token = os.getenv("TARGET_TOKEN")
        self.restore_output_path = os.getenv("RESTORE_OUTPUT_PATH", "./restored")
        self.install_dependencies = os.getenv("INSTALL_DEPENDENCIES", "true").lower() == "true"

        # Validate configuration
        self._validate_config()

        # Initialize components
        self.archive_manager = ArchiveManager()
        self.git_client = GitClient()
        if self.target_token:
            self.auth_manager = AuthManager(github_token=self.target_token)

        # Statistics
        self.stats = {
            "start_time": time.time(),
            "download_duration": 0,
            "verify_duration": 0,
            "restore_duration": 0,
            "dependency_duration": 0,
            "push_duration": 0,
            "archive_size_mb": 0,
        }

    def _validate_config(self):
        """Validate configuration."""
        # Must have either archive_path or storage info
        if not self.archive_path and not (self.storage_type and self.remote_key):
            raise ConfigurationError(
                "Either ARCHIVE_PATH or (STORAGE_TYPE + REMOTE_KEY) is required",
                missing_variables=["ARCHIVE_PATH or STORAGE_TYPE+REMOTE_KEY"]
            )

        if self.target_repo_url and not self.target_token:
            raise AuthenticationError(
                "TARGET_TOKEN is required when TARGET_REPO_URL is specified",
                missing_variables=["TARGET_TOKEN"]
            )

    def run(self):
        """Execute the archive restoration workflow."""
        with log_context(session_id=self.session_id,
                        target_repo=self.target_repo_url or "local"):

            self.logger.info("Archive restoration session started")
            print(f"\n📦 Starting Air-Gap Archive Restoration")
            print(f"   Session ID: {self.session_id}")
            if self.target_repo_url:
                print(f"   Target: {self.target_repo_url}")
            else:
                print(f"   Target: Local filesystem only")

            try:
                # Step 1: Download archive (if needed)
                archive_path = self._download_archive()

                # Step 2: Verify archive integrity
                self._verify_archive(archive_path)

                # Step 3: Restore repository
                repo_path = self._restore_repository(archive_path)

                # Step 4: Install dependencies (if enabled)
                if self.install_dependencies:
                    self._install_dependencies(repo_path)

                # Step 5: Push to target (if configured)
                if self.target_repo_url:
                    self._push_to_target(repo_path)

                # Print summary
                self._print_summary(repo_path)

                self.logger.info("Archive restoration completed successfully",
                               extra=self.stats)

            except RepoClonerError as e:
                self.logger.error(f"Archive restoration failed: {e}",
                                extra={"error_type": type(e).__name__})
                print(f"\n✗ Archive restoration failed: {e}")
                sys.exit(1)
            except Exception as e:
                self.logger.error(f"Unexpected error: {e}", exc_info=True)
                print(f"\n✗ Unexpected error: {e}")
                sys.exit(1)

    def _download_archive(self) -> Path:
        """Download archive from storage if needed."""
        # If archive path is already provided, skip download
        if self.archive_path:
            print(f"\n📄 Step 1/5: Using local archive...")
            print(f"   Archive: {self.archive_path}")
            return Path(self.archive_path)

        with log_context(operation="download_archive", storage_type=self.storage_type):
            print(f"\n☁️  Step 1/5: Downloading from {self.storage_type} storage...")

            start_time = time.time()

            try:
                # Initialize storage backend
                if self.storage_type == "local":
                    storage = LocalFilesystemBackend(self.storage_path)
                elif self.storage_type == "s3":
                    # Would initialize S3Backend here
                    self.logger.info("S3 download not implemented in example")
                    raise ConfigurationError("S3 download not implemented in example")
                else:
                    raise ConfigurationError(f"Unsupported storage type: {self.storage_type}")

                # Create download directory
                download_dir = Path(f"/tmp/repo-cloner-{self.session_id}/downloads")
                download_dir.mkdir(parents=True, exist_ok=True)

                # Download archive
                self.logger.info("Downloading archive from storage",
                               extra={"remote_key": self.remote_key})

                output_path = download_dir / Path(self.remote_key).name
                storage.download_archive(self.remote_key, str(output_path))

                self.stats["download_duration"] = time.time() - start_time
                self.stats["archive_size_mb"] = output_path.stat().st_size / (1024 * 1024)

                self.logger.info("Archive downloaded successfully",
                               extra={
                                   "archive_path": str(output_path),
                                   "size_mb": self.stats["archive_size_mb"],
                                   "duration_seconds": self.stats["download_duration"]
                               })

                print(f"   ✓ Downloaded: {output_path.name}")
                print(f"      Size: {self.stats['archive_size_mb']:.1f} MB")
                print(f"      Duration: {self.stats['download_duration']:.1f}s")

                return output_path

            except Exception as e:
                raise ArchiveError(f"Archive download failed: {e}",
                                 storage_type=self.storage_type,
                                 remote_key=self.remote_key)

    def _verify_archive(self, archive_path: Path):
        """Verify archive integrity."""
        with log_context(operation="verify_archive"):
            print(f"\n✓ Step 2/5: Verifying archive integrity...")

            start_time = time.time()

            try:
                # Verify archive
                self.logger.info("Verifying archive integrity")
                result = self.archive_manager.verify_archive(str(archive_path))

                self.stats["verify_duration"] = time.time() - start_time

                if result["valid"]:
                    self.logger.info("Archive verification successful",
                                   extra={
                                       "manifest_valid": True,
                                       "bundle_valid": True,
                                       "lfs_count": result.get("lfs_count", 0)
                                   })

                    print(f"   ✓ Archive is valid")
                    print(f"      Manifest: ✓")
                    print(f"      Git bundle: ✓")
                    if result.get("lfs_count", 0) > 0:
                        print(f"      LFS objects: ✓ ({result['lfs_count']} files)")
                    print(f"      Duration: {self.stats['verify_duration']:.1f}s")
                else:
                    raise ArchiveError(
                        f"Archive verification failed: {result.get('error', 'Unknown error')}",
                        archive_path=str(archive_path)
                    )

            except Exception as e:
                raise ArchiveError(f"Archive verification failed: {e}",
                                 archive_path=str(archive_path))

    def _restore_repository(self, archive_path: Path) -> Path:
        """Restore repository from archive."""
        with log_context(operation="restore_repository"):
            print(f"\n📥 Step 3/5: Restoring repository from archive...")

            start_time = time.time()

            try:
                # Create restore directory
                restore_dir = Path(self.restore_output_path)
                restore_dir.mkdir(parents=True, exist_ok=True)

                # Extract archive
                self.logger.info("Extracting archive")
                repo_path = self.archive_manager.extract_archive(
                    str(archive_path),
                    str(restore_dir)
                )

                self.stats["restore_duration"] = time.time() - start_time

                self.logger.info("Repository restored successfully",
                               extra={
                                   "repo_path": repo_path,
                                   "duration_seconds": self.stats["restore_duration"]
                               })

                print(f"   ✓ Repository restored")
                print(f"      Location: {repo_path}")
                print(f"      Duration: {self.stats['restore_duration']:.1f}s")

                return Path(repo_path)

            except Exception as e:
                raise ArchiveError(f"Repository restoration failed: {e}",
                                 archive_path=str(archive_path))

    def _install_dependencies(self, repo_path: Path):
        """Install dependencies from archive."""
        with log_context(operation="install_dependencies"):
            print(f"\n🔧 Step 4/5: Installing dependencies...")

            start_time = time.time()

            # Check for dependency manifests
            dependencies_dir = repo_path / "dependencies"
            if not dependencies_dir.exists():
                print(f"   ℹ No dependencies found in archive")
                return

            try:
                # Install Python dependencies
                python_deps = dependencies_dir / "python"
                if python_deps.exists():
                    self.logger.info("Installing Python dependencies")
                    print(f"   Python: Installing from offline cache...")
                    # Would run: pip install --no-index --find-links=python/packages -r requirements.txt
                    print(f"      ✓ Installed 15 packages (simulated)")

                # Install Node.js dependencies
                nodejs_deps = dependencies_dir / "nodejs"
                if nodejs_deps.exists():
                    self.logger.info("Installing Node.js dependencies")
                    print(f"   Node.js: Installing from offline cache...")
                    # Would run: npm install --offline
                    print(f"      ✓ Installed 42 packages (simulated)")

                self.stats["dependency_duration"] = time.time() - start_time

                self.logger.info("Dependencies installed successfully",
                               extra={"duration_seconds": self.stats["dependency_duration"]})

                print(f"   ✓ Dependencies installed ({self.stats['dependency_duration']:.1f}s)")

            except Exception as e:
                self.logger.warning(f"Dependency installation failed: {e}")
                print(f"   ⚠ Warning: Could not install dependencies: {e}")
                # Continue even if dependencies fail

    def _push_to_target(self, repo_path: Path):
        """Push restored repository to target."""
        with log_context(operation="push_to_target", target=self.target_repo_url):
            print(f"\n🚀 Step 5/5: Pushing to target repository...")

            start_time = time.time()

            try:
                # Inject credentials
                target_url_auth = self.auth_manager.inject_credentials(self.target_repo_url)

                # Push to target
                self.logger.info("Pushing repository to target")
                result = self.git_client.push_mirror(
                    str(repo_path),
                    target_url_auth,
                    dry_run=False
                )

                if not result.success:
                    raise GitOperationError(
                        f"Push failed: {result.error_message}",
                        repository=self.target_repo_url,
                        operation="push"
                    )

                self.stats["push_duration"] = time.time() - start_time

                self.logger.info("Repository pushed successfully",
                               extra={
                                   "target": self.target_repo_url,
                                   "duration_seconds": self.stats["push_duration"]
                               })

                print(f"   ✓ Pushed to target")
                print(f"      URL: {self.target_repo_url}")
                print(f"      Duration: {self.stats['push_duration']:.1f}s")

            except Exception as e:
                raise GitOperationError(f"Push to target failed: {e}",
                                      repository=self.target_repo_url)

    def _print_summary(self, repo_path: Path):
        """Print restoration summary."""
        total_duration = time.time() - self.stats["start_time"]
        minutes = int(total_duration // 60)
        seconds = int(total_duration % 60)

        print(f"\n✅ Archive restoration complete!\n")
        print("Summary:")
        print(f"  Repository: {repo_path}")
        if self.target_repo_url:
            print(f"  Target: {self.target_repo_url}")
        print(f"\nTiming:")
        if self.stats['download_duration'] > 0:
            print(f"  Download: {self.stats['download_duration']:.1f}s")
        print(f"  Verify: {self.stats['verify_duration']:.1f}s")
        print(f"  Restore: {self.stats['restore_duration']:.1f}s")
        if self.stats['dependency_duration'] > 0:
            print(f"  Dependencies: {self.stats['dependency_duration']:.1f}s")
        if self.stats['push_duration'] > 0:
            print(f"  Push: {self.stats['push_duration']:.1f}s")
        print(f"  Total: {minutes}m {seconds}s")
        print(f"\nFiles:")
        print(f"  Repository: {repo_path}")
        print(f"  Logs: /tmp/repo-cloner-restore-{self.session_id}.log")


def main():
    """Main entry point."""
    try:
        workflow = AirGapArchiveRestorer()
        workflow.run()
    except KeyboardInterrupt:
        print("\n\n⚠ Archive restoration interrupted by user")
        sys.exit(130)


if __name__ == "__main__":
    main()
