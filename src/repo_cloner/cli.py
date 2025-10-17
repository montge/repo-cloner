"""Command-line interface for repo-cloner."""

import sys
import time
from pathlib import Path

import click
from dotenv import load_dotenv

from .archive_manager import ArchiveManager
from .auth_manager import AuthManager
from .git_client import GitClient
from .github_client import GitHubClient
from .gitlab_client import GitLabClient
from .group_mapper import GroupMapper, MappingConfig, MappingStrategy
from .logging_config import configure_logging
from .storage_backend import LocalFilesystemBackend
from .sync_orchestrator import SyncOrchestrator


# Helper functions for colored output
def echo_success(message, quiet=False):
    """Echo success message in green."""
    if not quiet:
        click.secho(f"✅ {message}", fg="green")


def echo_error(message):
    """Echo error message in red."""
    click.secho(f"❌ {message}", fg="red", err=True)


def echo_info(message, quiet=False):
    """Echo info message in blue."""
    if not quiet:
        click.secho(message, fg="blue")


def echo_warning(message, quiet=False):
    """Echo warning message in yellow."""
    if not quiet:
        click.secho(f"⚠️  {message}", fg="yellow")


def echo_step(step_num, total_steps, message, quiet=False):
    """Echo step progress message."""
    if not quiet:
        click.secho(f"[{step_num}/{total_steps}] {message}", fg="cyan", bold=True)


def format_duration(seconds):
    """Format duration in human-readable format."""
    if seconds < 1:
        return f"{seconds*1000:.0f}ms"
    elif seconds < 60:
        return f"{seconds:.1f}s"
    else:
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes}m {secs}s"


@click.group()
@click.version_option(version="0.1.0")
@click.option("--quiet", "-q", is_flag=True, help="Suppress non-essential output")
@click.option("--json-logs", is_flag=True, help="Enable JSON-formatted structured logging to file")
@click.pass_context
def main(ctx, quiet, json_logs):
    """Universal Repository Cloner & Synchronization Tool.

    Clone, synchronize, and archive Git repositories across platforms.
    """
    # Load environment variables from .env file if it exists
    load_dotenv()

    # Store global options in context for subcommands
    ctx.ensure_object(dict)
    ctx.obj["QUIET"] = quiet
    ctx.obj["JSON_LOGS"] = json_logs

    # Configure logging if JSON logs are enabled
    if json_logs:
        configure_logging(level="INFO", json_format=True)


@main.command()
@click.option(
    "--source", required=True, help="Source repository URL (https://gitlab.com/group/repo.git)"
)
@click.option(
    "--target", required=True, help="Target repository URL (https://github.com/org/repo.git)"
)
@click.option(
    "--local-path", default=None, help="Local path for temporary clone (default: temp directory)"
)
@click.option(
    "--github-token",
    envvar="GITHUB_TOKEN",
    help="GitHub personal access token (or set GITHUB_TOKEN env var)",
)
@click.option(
    "--gitlab-token",
    envvar="GITLAB_TOKEN",
    help="GitLab personal access token (or set GITLAB_TOKEN env var)",
)
@click.option("--dry-run", is_flag=True, help="Show what would be done without executing")
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose output")
@click.pass_context
def sync(ctx, source, target, local_path, github_token, gitlab_token, dry_run, verbose):
    """Clone from source and push to target (GitLab → GitHub migration)."""
    quiet = ctx.obj.get("QUIET", False)
    start_time = time.time()

    if not quiet:
        echo_info("\n🚀 Starting repository synchronization", quiet)
        if verbose:
            click.echo(f"   Source: {source}")
            click.echo(f"   Target: {target}")
            click.echo(f"   Dry-run: {dry_run}")

    # Initialize clients
    git_client = GitClient()
    auth_manager = AuthManager(github_token=github_token, gitlab_token=gitlab_token)

    # Inject credentials
    try:
        authenticated_source = auth_manager.inject_credentials(source)
        authenticated_target = auth_manager.inject_credentials(target)
    except ValueError as e:
        echo_error(f"Authentication error: {e}")
        sys.exit(1)

    # Determine local path
    if local_path is None:
        # Use temp directory with repo name
        repo_name = source.rstrip("/").split("/")[-1].replace(".git", "")
        local_path = f"/tmp/repo-cloner/{repo_name}"

    if verbose and not quiet:
        click.echo(f"   Local path: {local_path}\n")

    # Step 1: Clone from source
    echo_step(1, 2, "📥 Cloning from source...", quiet)
    clone_start = time.time()
    clone_result = git_client.clone_mirror(authenticated_source, local_path, dry_run=dry_run)

    if not clone_result.success:
        echo_error(f"Clone failed: {clone_result.error_message}")
        sys.exit(1)

    clone_duration = time.time() - clone_start
    if dry_run:
        echo_success(clone_result.message, quiet)
    else:
        echo_success(
            f"Cloned {clone_result.branches_count} branches ({format_duration(clone_duration)})",
            quiet,
        )

    # Step 2: Push to target
    echo_step(2, 2, "📤 Pushing to target...", quiet)
    push_start = time.time()
    push_result = git_client.push_mirror(local_path, authenticated_target, dry_run=dry_run)

    if not push_result.success:
        echo_error(f"Push failed: {push_result.error_message}")
        sys.exit(1)

    push_duration = time.time() - push_start
    if dry_run:
        echo_success(push_result.message, quiet)
    else:
        echo_success(f"Successfully pushed to target ({format_duration(push_duration)})", quiet)

    # Summary
    total_duration = time.time() - start_time
    if not quiet:
        click.echo()
        echo_success(f"🎉 Synchronization complete! (Total: {format_duration(total_duration)})")


@main.command()
def version():
    """Show version information."""
    click.echo("repo-cloner version 0.1.0")
    click.echo("Built with Python, GitPython, and ❤️")


@main.command(name="sync-group")
@click.option(
    "--source-group",
    envvar="GITLAB_SOURCE_GROUP",
    help="GitLab group path (e.g., company/backend) or set GITLAB_SOURCE_GROUP env var",
)
@click.option(
    "--target-org",
    envvar="GITHUB_TARGET_ORG",
    help="GitHub organization name or set GITHUB_TARGET_ORG env var",
)
@click.option(
    "--gitlab-url",
    envvar="GITLAB_URL",
    default="https://gitlab.com",
    help="GitLab instance URL (default: https://gitlab.com) or set GITLAB_URL env var",
)
@click.option(
    "--github-url",
    envvar="GITHUB_URL",
    default="https://github.com",
    help="GitHub instance URL (default: https://github.com) or set GITHUB_URL env var",
)
@click.option(
    "--gitlab-token",
    envvar="GITLAB_TOKEN",
    required=True,
    help="GitLab personal access token (or set GITLAB_TOKEN env var)",
)
@click.option(
    "--github-token",
    envvar="GITHUB_TOKEN",
    required=True,
    help="GitHub personal access token (or set GITHUB_TOKEN env var)",
)
@click.option(
    "--mapping-strategy",
    envvar="DEFAULT_MAPPING_STRATEGY",
    type=click.Choice(["flatten", "prefix", "full_path", "custom"], case_sensitive=False),
    default="flatten",
    help="Repository name mapping strategy (default: flatten) or set DEFAULT_MAPPING_STRATEGY env var",
)
@click.option(
    "--separator",
    envvar="DEFAULT_SEPARATOR",
    default="-",
    help="Separator for flattened repository names (default: -) or set DEFAULT_SEPARATOR env var",
)
@click.option(
    "--strip-parent",
    envvar="DEFAULT_STRIP_PARENT",
    is_flag=True,
    help="Strip root parent group from repository names or set DEFAULT_STRIP_PARENT=true env var",
)
@click.option(
    "--keep-last-n",
    envvar="DEFAULT_KEEP_LAST_N",
    type=int,
    default=None,
    help="Keep only last N path levels in repository names or set DEFAULT_KEEP_LAST_N env var",
)
@click.option(
    "--auto-create",
    envvar="DEFAULT_AUTO_CREATE",
    is_flag=True,
    help="Automatically create missing GitHub repositories or set DEFAULT_AUTO_CREATE=true env var",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Preview mappings and actions without executing",
)
@click.option(
    "--workers",
    envvar="DEFAULT_WORKERS",
    default=5,
    type=int,
    help="Number of concurrent workers for syncing (default: 5) or set DEFAULT_WORKERS env var",
)
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose output")
@click.pass_context
def sync_group(
    ctx,
    source_group,
    target_org,
    gitlab_url,
    github_url,
    gitlab_token,
    github_token,
    mapping_strategy,
    separator,
    strip_parent,
    keep_last_n,
    auto_create,
    dry_run,
    workers,
    verbose,
):
    """Sync entire GitLab group to GitHub organization.

    This command discovers all repositories in a GitLab group (including subgroups),
    maps them to GitHub repository names using the specified strategy, and synchronizes
    them to the target GitHub organization.

    Examples:

        # Sync with flatten strategy (default)
        repo-cloner sync-group --source-group company/backend --target-org my-org

        # Sync with prefix strategy and auto-create
        repo-cloner sync-group --source-group company/backend --target-org my-org \\
            --mapping-strategy prefix --auto-create

        # Dry-run to preview mappings
        repo-cloner sync-group --source-group company/backend --target-org my-org \\
            --dry-run --verbose

        # Sync with custom separator and strip parent
        repo-cloner sync-group --source-group company/backend --target-org my-org \\
            --separator _ --strip-parent
    """
    quiet = ctx.obj.get("QUIET", False)
    start_time = time.time()

    if not quiet:
        echo_info("\n🚀 Starting group synchronization", quiet)
        if verbose:
            click.echo(f"   Source group: {source_group}")
            click.echo(f"   Target organization: {target_org}")
            click.echo(f"   Mapping strategy: {mapping_strategy}")
            click.echo(f"   Auto-create: {auto_create}")
            click.echo(f"   Dry-run: {dry_run}")
            click.echo(f"   Workers: {workers}\n")

    # Initialize clients
    try:
        gitlab_client = GitLabClient(url=gitlab_url, token=gitlab_token)
        # Convert GitHub web URL to API URL if needed
        github_api_url = github_url.replace("https://github.com", "https://api.github.com")
        github_client = GitHubClient(token=github_token, base_url=github_api_url)
        git_client = GitClient()
        auth_manager = AuthManager(github_token=github_token, gitlab_token=gitlab_token)
    except Exception as e:
        echo_error(f"Failed to initialize clients: {e}")
        sys.exit(1)

    # Create mapping configuration
    strategy_map = {
        "flatten": MappingStrategy.FLATTEN,
        "prefix": MappingStrategy.PREFIX,
        "full_path": MappingStrategy.FULL_PATH,
        "custom": MappingStrategy.CUSTOM,
    }

    mapping_config = MappingConfig(
        strategy=strategy_map[mapping_strategy.lower()],
        separator=separator,
        strip_parent_group=strip_parent,
        keep_last_n_levels=keep_last_n,
        use_topics=True,  # Always enable topics
    )

    # Create GroupMapper
    group_mapper = GroupMapper(mapping_config)

    # Create SyncOrchestrator
    sync_orchestrator = SyncOrchestrator(
        gitlab_client=gitlab_client,
        github_client=github_client,
        git_client=git_client,
        auth_manager=auth_manager,
        group_mapper=group_mapper,
        github_org=target_org,
        github_base_url=github_url,
    )

    # Execute synchronization
    try:
        echo_step(
            1, 3 if not dry_run else 2, "🔍 Discovering repositories and mapping names...", quiet
        )

        summary = sync_orchestrator.sync_group_to_org(
            gitlab_group_path=source_group,
            auto_create=auto_create,
            dry_run=dry_run,
            workers=workers,
        )

        # Display summary
        if not quiet:
            click.echo()
            echo_info("📊 Synchronization Summary", quiet)
            click.echo(f"   Total repositories: {summary.total_repos}")
            click.echo(f"   Mapped repositories: {summary.mapped_repos}")

            if summary.skipped_repos > 0:
                echo_warning(f"   Skipped (invalid names): {summary.skipped_repos}", quiet)

            if summary.conflicts:
                echo_warning(f"   Naming conflicts detected: {len(summary.conflicts)}", quiet)
                if verbose:
                    click.echo("\n   Conflicts:")
                    for github_name, gitlab_paths in summary.conflicts.items():
                        click.echo(f"      {github_name} ← {', '.join(gitlab_paths)}")

            if summary.invalid_names:
                echo_warning(f"   Invalid repository names: {len(summary.invalid_names)}", quiet)
                if verbose:
                    click.echo("\n   Invalid names:")
                    for invalid in summary.invalid_names:
                        click.echo(f"      {invalid['gitlab_path']} → {invalid['github_name']}")
                        click.echo(f"         Error: {invalid['error']}")

            if not dry_run:
                click.echo()
                if summary.created_repos > 0:
                    echo_success(f"   Created repositories: {summary.created_repos}", quiet)
                echo_info(f"   Synced repositories: {summary.synced_repos}", quiet)
                if summary.failed_repos > 0:
                    echo_error(f"   Failed repositories: {summary.failed_repos}")

                    if verbose:
                        click.echo("\n   Failed repositories:")
                        for mapping in summary.mappings:
                            if mapping.sync_error:
                                click.echo(f"      {mapping.gitlab_path}")
                                click.echo(f"         Error: {mapping.sync_error}")

            # Display mappings in verbose mode
            if verbose and summary.mappings:
                click.echo("\n   Repository Mappings:")
                for mapping in summary.mappings:
                    status = "✅" if mapping.sync_success else ("❌" if mapping.sync_error else "⏭️")
                    created_flag = " [CREATED]" if mapping.created else ""
                    click.echo(f"      {status} {mapping.gitlab_path}")
                    click.echo(f"         → {mapping.github_full_name}{created_flag}")
                    if mapping.topics:
                        click.echo(f"         Topics: {', '.join(mapping.topics)}")
                    if mapping.sync_error:
                        click.echo(f"         Error: {mapping.sync_error}")

        # Success/failure determination
        total_duration = time.time() - start_time

        if dry_run:
            if not quiet:
                click.echo()
                echo_success(f"🎉 Dry-run complete! (Duration: {format_duration(total_duration)})")
                click.echo("\n💡 Run without --dry-run to execute the synchronization")
                if summary.conflicts or summary.invalid_names:
                    echo_warning(
                        "   ⚠️  Please resolve conflicts and invalid names before running",
                        quiet,
                    )
        else:
            if summary.failed_repos == 0:
                if not quiet:
                    click.echo()
                    duration_msg = (
                        f"🎉 Group synchronization complete! "
                        f"(Duration: {format_duration(total_duration)})"
                    )
                    echo_success(duration_msg)
            else:
                if not quiet:
                    click.echo()
                    warning_msg = (
                        f"⚠️  Group synchronization completed with "
                        f"{summary.failed_repos} failure(s)"
                    )
                    echo_warning(warning_msg, quiet)
                sys.exit(1)

    except Exception as e:
        echo_error(f"Synchronization failed: {e}")
        if verbose:
            import traceback

            click.echo(traceback.format_exc(), err=True)
        sys.exit(1)


# Archive management commands
@main.group()
def archive():
    """Archive management commands for air-gap deployments."""
    pass


@archive.command()
@click.option(
    "--repo-path",
    required=True,
    help="Path to the git repository to archive",
    type=click.Path(exists=True),
)
@click.option(
    "--output-path",
    required=True,
    help="Directory where the archive will be created",
    type=click.Path(),
)
@click.option(
    "--type",
    "archive_type",
    default="full",
    type=click.Choice(["full", "incremental"], case_sensitive=False),
    help="Archive type: full or incremental (default: full)",
)
@click.option(
    "--parent-archive",
    default=None,
    help="Parent archive path (required for incremental archives)",
    type=click.Path(exists=True),
)
@click.option("--include-lfs", is_flag=True, help="Include Git LFS objects in the archive")
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose output")
@click.pass_context
def create(ctx, repo_path, output_path, archive_type, parent_archive, include_lfs, verbose):
    """Create an archive of a git repository.

    Examples:
        # Create full archive
        repo-cloner archive create --repo-path /path/to/repo --output-path /archives

        # Create full archive with LFS
        repo-cloner archive create --repo-path /path/to/repo --output-path /archives --include-lfs

        # Create incremental archive
        repo-cloner archive create --repo-path /path/to/repo --output-path /archives \\
            --type incremental --parent-archive /archives/repo-full-20251010.tar.gz
    """
    quiet = ctx.obj.get("QUIET", False)
    manager = ArchiveManager()
    start_time = time.time()

    if verbose and not quiet:
        click.echo("\n📋 Archive Configuration:")
        click.echo(f"   Repository: {repo_path}")
        click.echo(f"   Output path: {output_path}")
        click.echo(f"   Archive type: {archive_type}")
        click.echo(f"   Include LFS: {include_lfs}\n")

    try:
        if archive_type == "full":
            echo_info("📦 Creating full archive...", quiet)
            result = manager.create_full_archive(
                repo_path=repo_path, output_path=output_path, include_lfs=include_lfs
            )
        else:  # incremental
            if parent_archive is None:
                echo_error("Error: --parent-archive is required for incremental archives")
                sys.exit(1)

            echo_info("📦 Creating incremental archive...", quiet)
            result = manager.create_incremental_archive(
                repo_path=repo_path,
                output_path=output_path,
                parent_archive_path=parent_archive,
                include_lfs=include_lfs,
            )

        duration = time.time() - start_time
        if result["success"]:
            archive_size = Path(result["archive_path"]).stat().st_size / (1024 * 1024)
            echo_success(
                f"Archive created: {Path(result['archive_path']).name} "
                f"({archive_size:.1f} MB, {format_duration(duration)})",
                quiet,
            )
            if verbose and not quiet:
                click.echo(f"   Type: {result['manifest']['type']}")
                if include_lfs and result["manifest"].get("lfs_object_count", 0) > 0:
                    click.echo(f"   LFS objects: {result['manifest']['lfs_object_count']}")
        else:
            echo_error("Failed to create archive")
            sys.exit(1)

    except FileNotFoundError as e:
        echo_error(f"Error: {e}")
        sys.exit(1)
    except Exception as e:
        echo_error(f"Unexpected error: {e}")
        sys.exit(1)


@archive.command()
@click.option(
    "--archive-path",
    required=True,
    help="Path to the archive file to verify",
    type=click.Path(exists=True),
)
@click.option("--verbose", "-v", is_flag=True, help="Show detailed verification results")
def verify(archive_path, verbose):
    """Verify integrity and validity of an archive.

    Examples:
        # Verify archive
        repo-cloner archive verify --archive-path /archives/repo-full-20251010.tar.gz

        # Verify with detailed output
        repo-cloner archive verify --archive-path /archives/repo-full-20251010.tar.gz --verbose
    """
    manager = ArchiveManager()

    try:
        click.echo(f"🔍 Verifying archive: {archive_path}")
        result = manager.verify_archive(archive_path)

        if result["valid"]:
            click.echo("✅ Archive is valid")
            if verbose:
                click.echo(f"  Manifest: {'✓' if result['manifest_valid'] else '✗'}")
                click.echo(f"  Bundle: {'✓' if result['bundle_valid'] else '✗'}")
                if result.get("lfs_objects_verified") is not None:
                    click.echo(f"  LFS objects: {'✓' if result['lfs_objects_verified'] else '✗'}")
                    click.echo(f"  LFS object count: {result.get('lfs_object_count', 0)}")
        else:
            click.echo("❌ Archive is invalid", err=True)
            if result["errors"]:
                click.echo("Errors found:")
                for error in result["errors"]:
                    click.echo(f"  - {error}")
            sys.exit(1)

    except FileNotFoundError as e:
        click.echo(f"❌ Error: {e}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"❌ Unexpected error: {e}", err=True)
        sys.exit(1)


@archive.command()
@click.option(
    "--archive-path",
    required=True,
    help="Path to the archive file to restore",
    type=click.Path(exists=True),
)
@click.option(
    "--output-path",
    required=True,
    help="Directory where the repository will be restored",
    type=click.Path(),
)
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose output")
def restore(archive_path, output_path, verbose):
    """Restore a repository from an archive.

    Examples:
        # Restore from archive
        repo-cloner archive restore --archive-path /archives/repo-full-20251010.tar.gz \\
            --output-path /restored

        # Restore with verbose output
        repo-cloner archive restore --archive-path /archives/repo-full-20251010.tar.gz \\
            --output-path /restored --verbose
    """
    manager = ArchiveManager()

    if verbose:
        click.echo(f"Archive: {archive_path}")
        click.echo(f"Output path: {output_path}")

    try:
        click.echo("📦 Restoring repository from archive...")
        result = manager.extract_archive(archive_path=archive_path, output_path=output_path)

        if result["success"]:
            click.echo(f"✅ Repository restored successfully: {result['repository_path']}")
            if verbose:
                manifest = result["manifest"]
                click.echo(f"Repository name: {manifest['repository']['name']}")
                click.echo(f"Archive type: {manifest['type']}")
        else:
            click.echo("❌ Failed to restore archive", err=True)
            sys.exit(1)

    except FileNotFoundError as e:
        click.echo(f"❌ Error: {e}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"❌ Unexpected error: {e}", err=True)
        sys.exit(1)


@archive.command()
@click.option(
    "--archives-path",
    required=True,
    help="Directory containing archives",
    type=click.Path(exists=True),
)
@click.option(
    "--max-age-days",
    default=None,
    type=int,
    help="Delete archives older than N days",
)
@click.option(
    "--max-count",
    default=None,
    type=int,
    help="Keep only N most recent archives",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Show what would be deleted without actually deleting",
)
@click.option("--verbose", "-v", is_flag=True, help="Show detailed results")
def retention(archives_path, max_age_days, max_count, dry_run, verbose):
    """Apply retention policy to archives.

    Examples:
        # Delete archives older than 30 days
        repo-cloner archive retention --archives-path /archives --max-age-days 30

        # Keep only 10 most recent archives
        repo-cloner archive retention --archives-path /archives --max-count 10

        # Dry-run mode (preview)
        repo-cloner archive retention --archives-path /archives --max-age-days 30 --dry-run

        # Combined policy
        repo-cloner archive retention --archives-path /archives --max-age-days 30 --max-count 10
    """
    manager = ArchiveManager()

    if verbose:
        click.echo(f"Archives path: {archives_path}")
        click.echo(f"Max age (days): {max_age_days if max_age_days else 'N/A'}")
        click.echo(f"Max count: {max_count if max_count else 'N/A'}")
        click.echo(f"Dry run: {dry_run}")

    try:
        if dry_run:
            click.echo("🔍 Dry-run mode: No archives will be deleted")

        click.echo("🗑️  Applying retention policy...")
        result = manager.apply_retention_policy(
            archives_path=archives_path,
            max_age_days=max_age_days,
            max_count=max_count,
            dry_run=dry_run,
        )

        # Show results
        if dry_run:
            click.echo(f"Would delete {result['deleted_count']} archive(s)")
        else:
            click.echo(f"Deleted {result['deleted_count']} archive(s)")

        click.echo(f"Kept {result['kept_count']} archive(s)")

        if verbose and result["deleted_files"]:
            click.echo("\nDeleted files:")
            for file_path in result["deleted_files"]:
                click.echo(f"  - {file_path}")

        if result["deleted_count"] > 0:
            if dry_run:
                click.echo("✅ Dry-run complete (no files were actually deleted)")
            else:
                click.echo("✅ Retention policy applied successfully")

    except FileNotFoundError as e:
        click.echo(f"❌ Error: {e}", err=True)
        sys.exit(1)
    except ValueError as e:
        click.echo(f"❌ Error: {e}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"❌ Unexpected error: {e}", err=True)
        sys.exit(1)


@archive.command()
@click.option(
    "--archive-path",
    required=True,
    help="Path to the local archive file to upload",
    type=click.Path(exists=True),
)
@click.option(
    "--storage-path",
    required=True,
    help="Storage backend path (local filesystem directory)",
    type=click.Path(),
)
@click.option(
    "--remote-key",
    default=None,
    help="Remote key/path for the archive (default: use archive filename)",
)
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose output")
def upload(archive_path, storage_path, remote_key, verbose):
    """Upload an archive to storage backend.

    Currently supports local filesystem storage backend.

    Examples:
        # Upload to local storage
        repo-cloner archive upload --archive-path /archives/repo-full-20251010.tar.gz \\
            --storage-path /mnt/backup

        # Upload with custom remote key
        repo-cloner archive upload --archive-path /archives/repo-full-20251010.tar.gz \\
            --storage-path /mnt/backup --remote-key backups/repo-full-20251010.tar.gz
    """
    archive_path_obj = Path(archive_path)

    # Determine remote key
    if remote_key is None:
        remote_key = archive_path_obj.name

    if verbose:
        click.echo(f"Archive: {archive_path}")
        click.echo(f"Storage path: {storage_path}")
        click.echo(f"Remote key: {remote_key}")

    try:
        # Create storage backend
        storage_path_obj = Path(storage_path).absolute()
        backend = LocalFilesystemBackend(storage_path_obj)

        click.echo("📤 Uploading archive to storage...")
        metadata = backend.upload_archive(
            local_path=archive_path_obj,
            remote_key=remote_key,
            metadata={
                "uploaded_at": str(Path(archive_path).stat().st_mtime),
            },
        )

        click.echo(f"✅ Archive uploaded successfully: {metadata.key}")
        if verbose:
            click.echo(f"  Size: {metadata.size_bytes} bytes")
            click.echo(f"  Timestamp: {metadata.timestamp}")

    except FileNotFoundError as e:
        click.echo(f"❌ Error: {e}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"❌ Unexpected error: {e}", err=True)
        sys.exit(1)


@archive.command()
@click.option(
    "--storage-path",
    required=True,
    help="Storage backend path (local filesystem directory)",
    type=click.Path(exists=True),
)
@click.option(
    "--remote-key",
    required=True,
    help="Remote key/path of the archive to download",
)
@click.option(
    "--output-path",
    required=True,
    help="Local path where archive will be downloaded",
    type=click.Path(),
)
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose output")
def download(storage_path, remote_key, output_path, verbose):
    """Download an archive from storage backend.

    Currently supports local filesystem storage backend.

    Examples:
        # Download from local storage
        repo-cloner archive download --storage-path /mnt/backup \\
            --remote-key backups/repo-full-20251010.tar.gz \\
            --output-path /downloads/repo-full-20251010.tar.gz

        # Download with verbose output
        repo-cloner archive download --storage-path /mnt/backup \\
            --remote-key repo-full-20251010.tar.gz --output-path /downloads/archive.tar.gz --verbose
    """
    if verbose:
        click.echo(f"Storage path: {storage_path}")
        click.echo(f"Remote key: {remote_key}")
        click.echo(f"Output path: {output_path}")

    try:
        # Create storage backend
        storage_path_obj = Path(storage_path).absolute()
        backend = LocalFilesystemBackend(storage_path_obj)

        click.echo("📥 Downloading archive from storage...")
        output_path_obj = Path(output_path)
        backend.download_archive(
            remote_key=remote_key,
            local_path=output_path_obj,
        )

        click.echo(f"✅ Archive downloaded successfully: {output_path}")
        if verbose:
            size = output_path_obj.stat().st_size
            click.echo(f"  Size: {size} bytes")

    except FileNotFoundError as e:
        click.echo(f"❌ Error: {e}", err=True)
        sys.exit(1)
    except KeyError as e:
        click.echo(f"❌ Archive not found in storage: {e}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"❌ Unexpected error: {e}", err=True)
        sys.exit(1)


@archive.command()
@click.option(
    "--storage-path",
    required=True,
    help="Storage backend path (local filesystem directory)",
    type=click.Path(exists=True),
)
@click.option(
    "--prefix",
    default="",
    help="Filter archives by prefix (e.g., backups/)",
)
@click.option("--verbose", "-v", is_flag=True, help="Show detailed metadata")
def list(storage_path, prefix, verbose):
    """List archives in storage backend.

    Currently supports local filesystem storage backend.

    Examples:
        # List all archives
        repo-cloner archive list --storage-path /mnt/backup

        # List with prefix filter
        repo-cloner archive list --storage-path /mnt/backup --prefix backups/

        # List with verbose output
        repo-cloner archive list --storage-path /mnt/backup --verbose
    """
    if verbose:
        click.echo(f"Storage path: {storage_path}")
        click.echo(f"Prefix filter: {prefix if prefix else '(none)'}")

    try:
        # Create storage backend
        storage_path_obj = Path(storage_path).absolute()
        backend = LocalFilesystemBackend(storage_path_obj)

        click.echo("📋 Listing archives in storage...")
        archives = backend.list_archives(prefix=prefix if prefix else None)

        if not archives:
            click.echo("No archives found.")
            return

        click.echo(f"\nFound {len(archives)} archive(s):\n")
        for archive_meta in archives:
            click.echo(f"  📦 {archive_meta.key}")
            if verbose:
                click.echo(f"      Size: {archive_meta.size_bytes} bytes")
                click.echo(f"      Timestamp: {archive_meta.timestamp}")
                if archive_meta.archive_type:
                    click.echo(f"      Type: {archive_meta.archive_type}")
                if archive_meta.repository_name:
                    click.echo(f"      Repository: {archive_meta.repository_name}")

    except FileNotFoundError as e:
        click.echo(f"❌ Error: {e}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"❌ Unexpected error: {e}", err=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
