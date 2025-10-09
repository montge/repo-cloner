# Configuration Examples

This directory contains example configuration files demonstrating various features of the repo-cloner tool.

## Quick Start

1. Copy an example configuration:
   ```bash
   cp examples/configs/simple-sync.yml config.yml
   ```

2. Set required environment variables:
   ```bash
   export GITLAB_TOKEN=glpat_your_gitlab_token
   export GITHUB_TOKEN=ghp_your_github_token
   ```

3. Run the sync:
   ```bash
   repo-cloner sync --config config.yml
   ```

## Configuration Files

### Basic Examples

#### `simple-sync.yml`
Minimal configuration for syncing GitLab repositories to GitHub.
- Uses flatten strategy (converts `group/subgroup/repo` to `group-subgroup-repo`)
- Environment variables for tokens
- Single group mapping

#### `env-var-examples.yml`
Demonstrates environment variable substitution patterns.
- Required variables: `${VAR}` (raises error if not set)
- Optional with defaults: `${VAR:-default}`
- Multiple environment variables per config

### Mapping Strategy Examples

#### `flatten-strategy.yml`
Preserves full GitLab group hierarchy in repository names.
- Example: `company/backend/api-service` → `company-backend-api-service`
- Best for: Maintaining context from deep hierarchies
- Use case: Large organizations with nested group structures

#### `prefix-strategy.yml`
Uses repository name with a prefix, drops parent groups.
- Example: `company/backend/api-service` with prefix `"be"` → `"be-api-service"`
- Best for: Clean names without hierarchy clutter
- Use case: Multiple teams each with their own GitHub org

### Advanced Examples

#### `advanced-sync.yml`
Demonstrates all configuration features:
- Multiple groups with different settings
- Repository exclusions (`exclude` lists)
- LFS enablement per group
- Sync strategies (mirror vs incremental)
- Shallow clones (`clone_depth`)
- Dry-run mode

#### `multi-group-sync.yml`
Real-world example with 10+ groups.
- Multiple GitHub organizations
- Different prefixes per team
- LFS for design/mobile/ML teams
- Exclusions for experimental/deprecated repos
- Shallow clones for large infrastructure repos

## Configuration Schema

### Top-Level Fields

```yaml
gitlab:
  url: string                # GitLab instance URL
  token: string              # GitLab Personal Access Token

github:
  url: string                # GitHub instance URL
  token: string              # GitHub Personal Access Token

mapping_strategy: string     # flatten, prefix, topics, custom

groups:                      # List of group mappings
  - source: string           # GitLab group path
    target_org: string       # GitHub organization name
    # ... group-specific options
```

### Group Configuration Options

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `source` | string | Yes | GitLab group path (e.g., `company/backend`) |
| `target_org` | string | Yes | GitHub organization name |
| `prefix` | string | No | Prefix for repository names (prefix strategy only) |
| `exclude` | list[string] | No | Repository paths to exclude from sync |
| `lfs_enabled` | boolean | No | Enable Git LFS support |
| `sync_strategy` | string | No | `mirror` (full) or `incremental` (default) |
| `dry_run` | boolean | No | Preview mode - no actual sync |
| `clone_depth` | integer | No | Shallow clone depth (e.g., `1` for latest commit only) |

## Environment Variable Patterns

### Required Variables
```yaml
token: ${GITLAB_TOKEN}
```
- Raises error if `GITLAB_TOKEN` is not set
- Use for secrets and required configuration

### Optional with Defaults
```yaml
url: ${GITLAB_URL:-https://gitlab.com}
```
- Uses `GITLAB_URL` if set
- Falls back to `https://gitlab.com` if not set
- Use for configuration that has sensible defaults

### Escaped Dollar Signs
```yaml
token: my-token-$$123
```
- `$$` becomes literal `$`
- Result: `my-token-$123`

## Mapping Strategies

### Flatten
Converts GitLab group hierarchy to hyphenated repository names.

**Example:**
- GitLab: `company/backend/services/api-service`
- GitHub: `company-backend-services-api-service`

**Best for:** Preserving full context from deep hierarchies

### Prefix
Uses repository name with a prefix, drops parent groups.

**Example:**
- GitLab: `company/backend/services/api-service`
- Prefix: `backend`
- GitHub: `backend-api-service`

**Best for:** Clean names organized by team/category

### Topics (Coming Soon)
Uses GitHub topics/labels to represent hierarchy.

**Example:**
- GitLab: `company/backend/api-service`
- GitHub: `api-service` with topics: `["company", "backend"]`

**Best for:** Flat repository structure with metadata-based organization

## Common Use Cases

### Use Case 1: Simple GitLab.com to GitHub.com Sync
```yaml
# simple-sync.yml
gitlab:
  url: https://gitlab.com
  token: ${GITLAB_TOKEN}

github:
  url: https://github.com
  token: ${GITHUB_TOKEN}

mapping_strategy: flatten

groups:
  - source: mycompany/backend
    target_org: mycompany
```

### Use Case 2: Self-Hosted GitLab to GitHub Enterprise
```yaml
gitlab:
  url: https://gitlab.company.internal
  token: ${GITLAB_TOKEN}

github:
  url: https://github.company.com
  token: ${GITHUB_TOKEN}

mapping_strategy: prefix

groups:
  - source: engineering/services
    target_org: company-engineering
    prefix: svc
```

### Use Case 3: Large Files (LFS) and Design Assets
```yaml
groups:
  - source: design/ui-kits
    target_org: company-design
    lfs_enabled: true        # Handle .psd, .sketch, .fig files
    sync_strategy: mirror    # Full sync with all history
```

### Use Case 4: Excluding Deprecated Repositories
```yaml
groups:
  - source: backend
    target_org: company
    exclude:
      - backend/old-api-v1
      - backend/deprecated-service
      - backend/experimental/prototype
```

### Use Case 5: Shallow Clones for Large Repositories
```yaml
groups:
  - source: infrastructure
    target_org: company-devops
    clone_depth: 1           # Only clone latest commit
    lfs_enabled: false       # Skip LFS for faster clone
```

## Best Practices

1. **Use Environment Variables for Secrets**
   - Never commit tokens to version control
   - Use `${VAR}` pattern for all secrets

2. **Test with Dry-Run First**
   ```yaml
   groups:
     - source: mygroup
       target_org: myorg
       dry_run: true  # Preview before actual sync
   ```

3. **Start with Incremental Sync**
   - Default `sync_strategy: incremental` is safer
   - Use `mirror` only when full history sync is needed

4. **Exclude Before You Regret**
   - Add deprecated/experimental repos to `exclude` list
   - Prevents cluttering target organization

5. **Use Appropriate Mapping Strategy**
   - **Flatten**: Deep hierarchies that need context
   - **Prefix**: Multiple teams, clean names
   - **Topics**: Flat structure, metadata-driven

## Troubleshooting

### Error: "Required environment variable 'GITLAB_TOKEN' is not set"
- **Solution:** Export the environment variable before running
  ```bash
  export GITLAB_TOKEN=glpat_your_token_here
  ```

### Error: "Configuration validation failed: mapping_strategy must be one of..."
- **Solution:** Use valid strategy: `flatten`, `prefix`, `topics`, or `custom`

### Error: "FileNotFoundError: Configuration file not found"
- **Solution:** Check file path is correct
  ```bash
  repo-cloner sync --config examples/configs/simple-sync.yml
  ```

## Additional Resources

- [ROADMAP.md](../ROADMAP.md) - Sprint 5 configuration details
- [REQUIREMENTS.md](../REQUIREMENTS.md) - Full requirements specification
- [CLAUDE.md](../CLAUDE.md) - Development context and architecture

## Contributing

When adding new example configurations:
1. Follow existing naming conventions
2. Add clear comments explaining each feature
3. Include use case description in this README
4. Test configuration validates correctly before committing
