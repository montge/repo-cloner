# GitHub Actions Workflow Examples

This directory contains example workflows and configurations for automating repository synchronization using GitHub Actions.

## Quick Start

1. **Copy the workflow file** to your repository:
   ```bash
   mkdir -p .github/workflows
   cp examples/github-actions/sync.yml .github/workflows/
   ```

2. **Configure GitHub Secrets** (Settings > Secrets and variables > Actions):
   - `GITLAB_TOKEN`: GitLab Personal Access Token
   - `GITHUB_TOKEN` or `GH_PAT`: GitHub Personal Access Token
   - Optional: Cloud storage credentials (see below)

3. **Create a configuration file** (choose one of the examples below)

4. **Trigger the workflow**:
   - **Automatic**: Runs on schedule (default: daily at 2 AM UTC)
   - **Manual**: Go to Actions > Repository Synchronization > Run workflow

## Required GitHub Secrets

### Core Credentials
```
GITLAB_TOKEN          GitLab Personal Access Token (scope: read_repository, api)
GITLAB_URL            GitLab instance URL (default: https://gitlab.com)
GH_PAT                GitHub Personal Access Token (scope: repo, workflow)
GITHUB_URL            GitHub instance URL (default: https://github.com)
```

### Cloud Storage (Optional)
```
# AWS S3
AWS_ACCESS_KEY_ID
AWS_SECRET_ACCESS_KEY
AWS_DEFAULT_REGION

# Azure Blob Storage
AZURE_STORAGE_CONNECTION_STRING
AZURE_STORAGE_ACCOUNT

# Google Cloud Storage
GCS_SERVICE_ACCOUNT_JSON

# Oracle OCI Object Storage
OCI_CONFIG_FILE
```

## How Source/Destination Configuration Works

The GitHub Actions workflow reads repository synchronization settings from a **configuration file** (`config.yml` by default) in your repository. This configuration file defines:

1. **Sources**: Which Git platforms to sync FROM (GitLab, GitHub, or storage)
2. **Targets**: Which Git platforms/storage to sync TO (GitLab, GitHub, or storage)
3. **Mapping**: How to map organizations/groups between platforms
4. **Sync Settings**: Directionality, LFS support, conflict resolution

### Configuration File Location

The workflow expects configuration in one of these locations:
- **Default**: `config.yml` in repository root
- **Custom**: Specify via `config_path` input when manually triggering workflow

### Configuration Structure

```yaml
# Source systems (where to sync FROM)
sources:
  - type: gitlab | github | s3 | azure | gcs | oci | filesystem
    url: <platform-url>
    token: ${ENV_VAR}
    groups: [...]        # For Git platforms
    bucket: <name>       # For storage backends
    region: <region>     # For cloud storage

# Target systems (where to sync TO)
targets:
  - type: gitlab | github | s3 | azure | gcs | oci | filesystem
    url: <platform-url>
    token: ${ENV_VAR}
    organization: <name>  # For Git platforms
    bucket: <name>        # For storage backends
    region: <region>      # For cloud storage

# Mapping configuration
mapping_strategy: flatten | prefix | topics | custom

# Synchronization settings
sync:
  mode: unidirectional | bidirectional
  direction: source_to_target | target_to_source
  lfs_enabled: true | false
  conflict_resolution: fail | source_wins | target_wins
```

See [REQUIREMENTS.md FR-7](../../REQUIREMENTS.md#fr-7-configuration-management) for full specification.

## Configuration Examples

### Example 1: GitLab → GitHub Sync

Create `config.yml` in your repository root:

```yaml
sources:
  - type: gitlab
    url: https://gitlab.example.com
    token: ${GITLAB_TOKEN}
    groups:
      - backend
      - frontend

targets:
  - type: github
    url: https://github.com
    token: ${GITHUB_TOKEN}
    organization: myorg

mapping_strategy: flatten

sync:
  mode: unidirectional
  direction: source_to_target
  lfs_enabled: true
```

### Example 2: Bidirectional Sync with Conflict Detection

```yaml
sources:
  - type: gitlab
    url: https://gitlab.company.com
    token: ${GITLAB_TOKEN}
    groups:
      - engineering

targets:
  - type: github
    url: https://github.com
    token: ${GITHUB_TOKEN}
    organization: company-oss

sync:
  mode: bidirectional
  lfs_enabled: true
  conflict_resolution: fail  # Stop on conflicts for manual review
```

### Example 3: Multi-Target with Archive Backup

```yaml
sources:
  - type: gitlab
    url: https://gitlab.internal.com
    token: ${GITLAB_TOKEN}
    groups:
      - platform

targets:
  # Primary target: GitHub
  - type: github
    url: https://github.enterprise.com
    token: ${GITHUB_TOKEN}
    organization: platform-team

  # Backup target: S3 archives
  - type: s3
    bucket: repo-backups
    region: us-east-1
    prefix: gitlab-mirrors/
    access_key: ${AWS_ACCESS_KEY_ID}
    secret_key: ${AWS_SECRET_ACCESS_KEY}

archive:
  type: full
  include_lfs: true
  retention_days: 90
```

### Example 4: Air-Gap Archive to Multiple Storage Backends

```yaml
sources:
  - type: gitlab
    url: https://gitlab.secure.mil
    token: ${GITLAB_TOKEN}
    groups:
      - classified-projects

targets:
  # AWS GovCloud
  - type: s3
    bucket: secure-archives
    region: us-gov-west-1
    prefix: repos/
    access_key: ${AWS_ACCESS_KEY_ID}
    secret_key: ${AWS_SECRET_ACCESS_KEY}

  # Azure Government
  - type: azure
    container: secure-repos
    account: securestorage
    region: usgovvirginia
    connection_string: ${AZURE_STORAGE_CONNECTION_STRING}

  # Local NFS mount
  - type: filesystem
    path: /mnt/secure-backup/repos

archive:
  type: incremental
  include_lfs: true
  base_archive: platform-full-20250109.tar.gz
```

### Example 5: Scheduled Sync with Multiple Frequencies

Modify `.github/workflows/sync.yml`:

```yaml
"on":
  schedule:
    # Production repositories: every 6 hours
    - cron: "0 */6 * * *"

    # Development repositories: daily at 3 AM
    - cron: "0 3 * * *"

    # Archive backup: weekly on Sunday
    - cron: "0 0 * * 0"
```

Then create multiple config files:
- `config-prod.yml` - Critical repositories
- `config-dev.yml` - Development repositories
- `config-archive.yml` - Full archive backup

## Workflow Customization

### Custom Schedule

Edit the `cron` expression in `.github/workflows/sync.yml`:

```yaml
"on":
  schedule:
    - cron: "0 */4 * * *"  # Every 4 hours
```

Common cron patterns:
- `"0 2 * * *"` - Daily at 2 AM UTC
- `"0 */6 * * *"` - Every 6 hours
- `"0 0 * * 0"` - Weekly on Sunday at midnight
- `"0 0 1 * *"` - Monthly on the 1st at midnight
- `"*/15 * * * *"` - Every 15 minutes (use cautiously!)

### Manual Trigger Options

When manually triggering the workflow, you can configure:

- **Config Path**: Path to YAML configuration file (default: `config.yml`)
- **Dry Run**: Preview changes without applying (default: `false`)
- **Verbose**: Enable detailed logging (default: `false`)
- **Sync Mode**: `unidirectional` or `bidirectional` (default: `unidirectional`)
- **Force**: Overwrite conflicts (default: `false`)

### Custom Python Version

Edit `.github/workflows/sync.yml`:

```yaml
- name: Set up Python
  uses: actions/setup-python@v5
  with:
    python-version: '3.11'  # Change to 3.10, 3.11, or 3.12
```

### Notification Integration

The workflow generates a summary report accessible in the Actions run. To add external notifications:

#### Slack Notification

Add this step after "Run synchronization":

```yaml
- name: Notify Slack on Success
  if: success()
  uses: slackapi/slack-github-action@v1.25.0
  with:
    webhook-url: ${{ secrets.SLACK_WEBHOOK_URL }}
    payload: |
      {
        "text": "✅ Repository sync completed successfully",
        "blocks": [
          {
            "type": "section",
            "text": {
              "type": "mrkdwn",
              "text": "*Repository Sync Complete*\n• Workflow: ${{ github.workflow }}\n• Status: Success\n• <${{ github.server_url }}/${{ github.repository }}/actions/runs/${{ github.run_id }}|View Run>"
            }
          }
        ]
      }

- name: Notify Slack on Failure
  if: failure()
  uses: slackapi/slack-github-action@v1.25.0
  with:
    webhook-url: ${{ secrets.SLACK_WEBHOOK_URL }}
    payload: |
      {
        "text": "❌ Repository sync failed",
        "blocks": [
          {
            "type": "section",
            "text": {
              "type": "mrkdwn",
              "text": "*Repository Sync Failed*\n• Workflow: ${{ github.workflow }}\n• Status: Failed\n• <${{ github.server_url }}/${{ github.repository }}/actions/runs/${{ github.run_id }}|View Run>"
            }
          }
        ]
      }
```

Required secret: `SLACK_WEBHOOK_URL`

#### Email Notification

Add to workflow:

```yaml
- name: Send email on failure
  if: failure()
  uses: dawidd6/action-send-mail@v3
  with:
    server_address: smtp.gmail.com
    server_port: 587
    username: ${{ secrets.EMAIL_USERNAME }}
    password: ${{ secrets.EMAIL_PASSWORD }}
    subject: "Repository Sync Failed - ${{ github.repository }}"
    to: ops-team@example.com
    from: github-actions@example.com
    body: |
      Repository synchronization failed.

      Repository: ${{ github.repository }}
      Run: ${{ github.server_url }}/${{ github.repository }}/actions/runs/${{ github.run_id }}
```

## Troubleshooting

### Workflow doesn't trigger on schedule

- Ensure the repository is active (has recent commits)
- GitHub may delay scheduled workflows by up to 10 minutes
- Check that the workflow file is on the default branch (main/master)

### Authentication failures

- Verify secrets are configured correctly
- Check token scopes:
  - GitLab: `read_repository`, `api`
  - GitHub: `repo`, `workflow`
- Ensure tokens haven't expired

### Sync fails with conflicts

- Review logs in the Actions run
- Use `--dry-run` to preview changes
- Consider setting `conflict_resolution: source_wins` or `target_wins`
- For bidirectional sync, use `fail` to review conflicts manually

### "Config file not found" warning

- Ensure `config.yml` exists in repository root
- Or specify custom path in workflow_dispatch inputs
- Workflow falls back to environment variables if config missing

## Best Practices

1. **Start with dry-run**: Test configuration with `--dry-run` first
2. **Use separate configs**: Maintain different configs for prod/dev/archive
3. **Monitor first runs**: Watch the first few scheduled executions
4. **Set retention policies**: Configure archive retention to manage storage costs
5. **Enable notifications**: Get alerted on failures
6. **Review logs**: Check `sync-logs-*` artifacts on failures
7. **Use secrets rotation**: Regularly rotate access tokens
8. **Test locally**: Run `repo-cloner sync --config config.yml --dry-run` locally first

## Security Considerations

- **Never commit tokens** to the repository
- **Use GitHub Secrets** for all credentials
- **Rotate tokens regularly** (quarterly recommended)
- **Use minimal token scopes** (read-only when possible)
- **Review workflow runs** for exposed secrets in logs
- **Enable branch protection** on default branch
- **Require workflow approval** for first-time contributors

## Support

For issues or questions:
- Check logs in Actions runs
- Review [REQUIREMENTS.md](../../REQUIREMENTS.md) for feature documentation
- Report issues at https://github.com/anthropics/claude-code/issues
