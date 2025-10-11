"""Command-line interface for repo-cloner."""

import sys
from pathlib import Path

import click

from .archive_manager import ArchiveManager
from .auth_manager import AuthManager
from .git_client import GitClient


@click.group()
@click.version_option(version="0.1.0")
def main():
    """Universal Repository Cloner & Synchronization Tool.

    Clone, synchronize, and archive Git repositories across platforms.
    """
    pass


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
def sync(source, target, local_path, github_token, gitlab_token, dry_run, verbose):
    """Clone from source and push to target (GitLab → GitHub migration)."""

    if verbose:
        click.echo(f"Source: {source}")
        click.echo(f"Target: {target}")
        click.echo(f"Dry-run: {dry_run}")

    # Initialize clients
    git_client = GitClient()
    auth_manager = AuthManager(github_token=github_token, gitlab_token=gitlab_token)

    # Inject credentials
    try:
        authenticated_source = auth_manager.inject_credentials(source)
        authenticated_target = auth_manager.inject_credentials(target)
    except ValueError as e:
        click.echo(f"❌ Authentication error: {e}", err=True)
        sys.exit(1)

    # Determine local path
    if local_path is None:
        # Use temp directory with repo name
        repo_name = source.rstrip("/").split("/")[-1].replace(".git", "")
        local_path = f"/tmp/repo-cloner/{repo_name}"

    if verbose:
        click.echo(f"Local path: {local_path}")

    # Step 1: Clone from source
    click.echo("📥 Cloning from source...")
    clone_result = git_client.clone_mirror(authenticated_source, local_path, dry_run=dry_run)

    if not clone_result.success:
        click.echo(f"❌ Clone failed: {clone_result.error_message}", err=True)
        sys.exit(1)

    if dry_run:
        click.echo(f"✅ {clone_result.message}")
    else:
        click.echo(f"✅ Cloned {clone_result.branches_count} branches to {local_path}")

    # Step 2: Push to target
    click.echo("📤 Pushing to target...")
    push_result = git_client.push_mirror(local_path, authenticated_target, dry_run=dry_run)

    if not push_result.success:
        click.echo(f"❌ Push failed: {push_result.error_message}", err=True)
        sys.exit(1)

    if dry_run:
        click.echo(f"✅ {push_result.message}")
    else:
        click.echo(f"✅ Successfully pushed to {target}")

    click.echo("\n🎉 Synchronization complete!")


@main.command()
def version():
    """Show version information."""
    click.echo("repo-cloner version 0.1.0")
    click.echo("Built with Python, GitPython, and ❤️")


# Archive management commands
@main.group()
def archive():
    """Archive management commands for air-gap deployments."""
    pass


@archive.command()
@click.option(
    "--repo-path", required=True, help="Path to the git repository to archive", type=click.Path(exists=True)
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
def create(repo_path, output_path, archive_type, parent_archive, include_lfs, verbose):
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
    manager = ArchiveManager()

    if verbose:
        click.echo(f"Repository: {repo_path}")
        click.echo(f"Output path: {output_path}")
        click.echo(f"Archive type: {archive_type}")
        click.echo(f"Include LFS: {include_lfs}")

    try:
        if archive_type == "full":
            click.echo("📦 Creating full archive...")
            result = manager.create_full_archive(
                repo_path=repo_path, output_path=output_path, include_lfs=include_lfs
            )
        else:  # incremental
            if parent_archive is None:
                click.echo("❌ Error: --parent-archive is required for incremental archives", err=True)
                sys.exit(1)

            click.echo("📦 Creating incremental archive...")
            result = manager.create_incremental_archive(
                repo_path=repo_path,
                output_path=output_path,
                parent_archive_path=parent_archive,
                include_lfs=include_lfs,
            )

        if result["success"]:
            click.echo(f"✅ Archive created successfully: {result['archive_path']}")
            if verbose:
                click.echo(f"Archive type: {result['manifest']['type']}")
                if include_lfs and result['manifest'].get('lfs_object_count', 0) > 0:
                    click.echo(f"LFS objects included: {result['manifest']['lfs_object_count']}")
            if archive_type == "incremental":
                click.echo("✅ Incremental archive created successfully")
        else:
            click.echo("❌ Failed to create archive", err=True)
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


if __name__ == "__main__":
    main()
