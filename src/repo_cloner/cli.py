"""Command-line interface for repo-cloner."""

import sys

import click

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


if __name__ == "__main__":
    main()
