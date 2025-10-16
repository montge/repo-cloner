# Group Hierarchy Mapping Design

## Problem Statement

GitLab supports **nested groups** (e.g., `company/backend/services/auth-service`), but GitHub has a **flat organization structure**. We need to map GitLab's hierarchical groups to GitHub's flat organization model while preserving context and discoverability.

## Mapping Strategies

### Strategy 1: Flatten with Separator (Default)
**Pattern:** `{group}-{subgroup}-{repo}`
**Separator:** Hyphen (`-`) or configurable

**Example:**
```
GitLab:  company/backend/services/auth-service
GitHub:  backend-services-auth-service
```

**Pros:**
- ✅ Simple and predictable
- ✅ Preserves full hierarchy in name
- ✅ Works with all GitHub features
- ✅ Easy to search and filter

**Cons:**
- ⚠️ Can create very long repository names
- ⚠️ May violate GitHub's 100-character repo name limit

**Configuration:**
```yaml
mapping_strategy: flatten
separator: "-"  # or "_" for underscores
strip_parent_group: false  # Include all parent groups
max_depth: null  # Include all levels
```

---

### Strategy 2: Prefix (Drop Parent Groups)
**Pattern:** `{prefix}_{repo}` or just `{repo}` with topics

**Example:**
```
GitLab:  company/backend/services/auth-service
GitHub:  services_auth-service  (or just auth-service)
Topics:  backend, services, microservice
```

**Pros:**
- ✅ Shorter repository names
- ✅ Topics provide hierarchy context
- ✅ Flexible search via topics

**Cons:**
- ⚠️ Potential naming conflicts (multiple groups with same repo name)
- ⚠️ Requires GitHub topics feature

**Configuration:**
```yaml
mapping_strategy: prefix
keep_last_n_levels: 2  # Keep last 2 levels: services/auth-service
use_topics: true
parent_groups_as_topics: true
```

---

### Strategy 3: Full Path with Underscore
**Pattern:** `{full_path}` with `/` → `_`

**Example:**
```
GitLab:  company/backend/services/auth-service
GitHub:  company_backend_services_auth-service
```

**Pros:**
- ✅ Preserves complete hierarchy
- ✅ Deterministic and unambiguous
- ✅ No naming conflicts

**Cons:**
- ⚠️ Very long names
- ⚠️ Can hit GitHub 100-char limit

**Configuration:**
```yaml
mapping_strategy: full_path
separator: "_"
```

---

### Strategy 4: Custom Mapping
**Pattern:** User-defined mapping via configuration file

**Example:**
```yaml
mapping_strategy: custom
custom_mappings:
  "company/backend/services": "backend-svc"
  "company/frontend/apps": "frontend-app"
  "company/infrastructure": "infra"

fallback_strategy: flatten  # For unmapped repos
```

**Pros:**
- ✅ Maximum flexibility
- ✅ Control over naming
- ✅ Can handle special cases

**Cons:**
- ⚠️ Requires manual configuration
- ⚠️ Harder to maintain at scale

---

## Implementation Design

### 1. GroupMapper Module

```python
# src/repo_cloner/group_mapper.py

class MappingStrategy(Enum):
    FLATTEN = "flatten"
    PREFIX = "prefix"
    FULL_PATH = "full_path"
    CUSTOM = "custom"


@dataclass
class MappingConfig:
    strategy: MappingStrategy
    separator: str = "-"
    keep_last_n_levels: Optional[int] = None
    use_topics: bool = True
    strip_parent_group: bool = False
    custom_mappings: Dict[str, str] = field(default_factory=dict)
    fallback_strategy: MappingStrategy = MappingStrategy.FLATTEN


class GroupMapper:
    """Maps GitLab group hierarchies to GitHub organization structure."""

    def __init__(self, config: MappingConfig):
        self.config = config

    def map_repository_name(
        self,
        gitlab_path: str,  # e.g., "company/backend/services/auth-service"
        strategy: Optional[MappingStrategy] = None
    ) -> str:
        """
        Map GitLab repository path to GitHub repository name.

        Args:
            gitlab_path: Full GitLab path (group/subgroup/repo)
            strategy: Override default strategy

        Returns:
            GitHub repository name (without org)
        """
        strategy = strategy or self.config.strategy

        if strategy == MappingStrategy.FLATTEN:
            return self._flatten_strategy(gitlab_path)
        elif strategy == MappingStrategy.PREFIX:
            return self._prefix_strategy(gitlab_path)
        elif strategy == MappingStrategy.FULL_PATH:
            return self._full_path_strategy(gitlab_path)
        elif strategy == MappingStrategy.CUSTOM:
            return self._custom_strategy(gitlab_path)
        else:
            raise ValueError(f"Unknown mapping strategy: {strategy}")

    def extract_topics(self, gitlab_path: str) -> List[str]:
        """
        Extract GitHub topics from GitLab path for hierarchy representation.

        Example:
            "company/backend/services/auth-service" →
            ["backend", "services", "microservice"]
        """
        if not self.config.use_topics:
            return []

        parts = gitlab_path.split("/")[:-1]  # Exclude repo name

        # Optionally strip root parent group
        if self.config.strip_parent_group and len(parts) > 1:
            parts = parts[1:]

        return [p.lower() for p in parts]

    def _flatten_strategy(self, gitlab_path: str) -> str:
        """
        Flatten: company/backend/services/auth → backend-services-auth
        """
        parts = gitlab_path.split("/")

        # Strip parent group if configured
        if self.config.strip_parent_group and len(parts) > 1:
            parts = parts[1:]

        # Limit depth if configured
        if self.config.keep_last_n_levels:
            parts = parts[-self.config.keep_last_n_levels:]

        return self.config.separator.join(parts)

    def _prefix_strategy(self, gitlab_path: str) -> str:
        """
        Prefix: company/backend/services/auth → services-auth or auth
        (parent groups become topics)
        """
        parts = gitlab_path.split("/")

        if self.config.keep_last_n_levels:
            relevant_parts = parts[-self.config.keep_last_n_levels:]
        else:
            relevant_parts = [parts[-1]]  # Just repo name

        return self.config.separator.join(relevant_parts)

    def _full_path_strategy(self, gitlab_path: str) -> str:
        """
        Full path: company/backend/services/auth → company_backend_services_auth
        """
        return gitlab_path.replace("/", self.config.separator)

    def _custom_strategy(self, gitlab_path: str) -> str:
        """
        Custom: Use user-defined mappings from config.
        """
        # Check for exact match
        if gitlab_path in self.config.custom_mappings:
            return self.config.custom_mappings[gitlab_path]

        # Check for prefix match (longest first)
        sorted_mappings = sorted(
            self.config.custom_mappings.items(),
            key=lambda x: len(x[0]),
            reverse=True
        )

        for prefix, replacement in sorted_mappings:
            if gitlab_path.startswith(prefix + "/"):
                # Replace prefix and continue with remaining path
                remaining = gitlab_path[len(prefix)+1:]
                return f"{replacement}{self.config.separator}{remaining.replace('/', self.config.separator)}"

        # No match found - use fallback strategy
        return self.map_repository_name(gitlab_path, self.config.fallback_strategy)

    def validate_github_name(self, name: str) -> tuple[bool, Optional[str]]:
        """
        Validate GitHub repository name constraints.

        GitHub rules:
        - Max 100 characters
        - Alphanumeric, hyphens, underscores
        - Cannot start with hyphen/underscore
        - Cannot end with .git

        Returns:
            (is_valid, error_message)
        """
        if len(name) > 100:
            return False, f"Name exceeds 100 characters: {len(name)}"

        if name.endswith(".git"):
            return False, "Name cannot end with .git"

        if name.startswith(("-", "_")):
            return False, "Name cannot start with hyphen or underscore"

        # Check valid characters
        import re
        if not re.match(r'^[a-zA-Z0-9_-]+$', name):
            return False, "Name contains invalid characters (only alphanumeric, -, _ allowed)"

        return True, None
```

---

### 2. Integration with Sync Workflow

```python
# src/repo_cloner/sync_orchestrator.py

class SyncOrchestrator:
    """Orchestrates bulk repository synchronization from GitLab group to GitHub org."""

    def __init__(
        self,
        gitlab_client: GitLabClient,
        github_client: GitHubClient,
        git_client: GitClient,
        group_mapper: GroupMapper,
        github_org: str,
    ):
        self.gitlab_client = gitlab_client
        self.github_client = github_client
        self.git_client = git_client
        self.group_mapper = group_mapper
        self.github_org = github_org

    def sync_group_to_org(
        self,
        gitlab_group_path: str,
        auto_create: bool = True,
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        """
        Sync all repositories from GitLab group to GitHub organization.

        Args:
            gitlab_group_path: GitLab group path (e.g., "company/backend")
            auto_create: Automatically create missing GitHub repos
            dry_run: Show what would be done without executing

        Returns:
            Summary report with success/failure counts
        """
        # 1. Discover all repositories in GitLab group
        repos = self.gitlab_client.list_projects(gitlab_group_path)

        # 2. Map repository names
        repo_mappings = []
        for repo in repos:
            gitlab_path = repo["path_with_namespace"]
            github_name = self.group_mapper.map_repository_name(gitlab_path)
            topics = self.group_mapper.extract_topics(gitlab_path)

            # Validate GitHub name
            is_valid, error = self.group_mapper.validate_github_name(github_name)
            if not is_valid:
                # Log warning and skip
                continue

            repo_mappings.append({
                "gitlab_path": gitlab_path,
                "gitlab_url": repo["http_url_to_repo"],
                "github_name": github_name,
                "github_full_name": f"{self.github_org}/{github_name}",
                "topics": topics,
            })

        # 3. Check which repos exist on GitHub
        for mapping in repo_mappings:
            exists = self.github_client.repository_exists(mapping["github_full_name"])
            mapping["github_exists"] = exists

        # 4. Auto-create missing repositories (if enabled)
        if auto_create and not dry_run:
            for mapping in repo_mappings:
                if not mapping["github_exists"]:
                    # Get GitLab repo details for description
                    gitlab_details = self.gitlab_client.get_project_details(
                        repo["id"]  # Need to track ID
                    )

                    self.github_client.create_repository(
                        org_name=self.github_org,
                        repo_name=mapping["github_name"],
                        description=gitlab_details.description,
                        topics=mapping["topics"],
                    )
                    mapping["github_exists"] = True
                    mapping["created"] = True

        # 5. Sync repositories (parallel)
        # ... use existing sync logic ...

        return repo_mappings
```

---

### 3. CLI Command

```python
# Add to src/repo_cloner/cli.py

@main.command()
@click.option("--source-group", required=True, help="GitLab group path (e.g., company/backend)")
@click.option("--target-org", required=True, help="GitHub organization name")
@click.option("--mapping-strategy", type=click.Choice(["flatten", "prefix", "full_path", "custom"]), default="flatten")
@click.option("--separator", default="-", help="Separator for flattened names (default: -)")
@click.option("--auto-create", is_flag=True, help="Auto-create missing GitHub repositories")
@click.option("--dry-run", is_flag=True, help="Show what would be done")
@click.option("--workers", default=5, type=int, help="Number of concurrent workers")
@click.pass_context
def sync_group(ctx, source_group, target_org, mapping_strategy, separator, auto_create, dry_run, workers):
    """Sync entire GitLab group to GitHub organization.

    Examples:
        # Sync with flatten strategy (default)
        repo-cloner sync-group --source-group company/backend --target-org my-org --auto-create

        # Dry run to preview mappings
        repo-cloner sync-group --source-group company/backend --target-org my-org --dry-run

        # Use prefix strategy with topics
        repo-cloner sync-group --source-group company/backend --target-org my-org \\
            --mapping-strategy prefix --auto-create
    """
    # Implementation here...
```

---

## Testing Strategy

### Integration Tests

```python
# tests/integration/test_group_mapping.py

class TestGroupMapping:
    """Integration tests for group-to-org mapping with real GitLab/GitHub."""

    @pytest.fixture
    def setup_gitlab_repos(self):
        """Create test repositories in GitLab with nested groups."""
        # Create repos:
        # - company/backend/services/auth
        # - company/backend/services/payment
        # - company/frontend/apps/web
        # - company/infrastructure/terraform
        pass

    def test_flatten_strategy_mapping(self, setup_gitlab_repos):
        """Test flatten strategy creates correct GitHub repo names."""
        # Expected:
        # - backend-services-auth
        # - backend-services-payment
        # - frontend-apps-web
        # - infrastructure-terraform
        pass

    def test_prefix_strategy_with_topics(self, setup_gitlab_repos):
        """Test prefix strategy with topics."""
        # Expected repos:
        # - auth (topics: backend, services)
        # - payment (topics: backend, services)
        # - web (topics: frontend, apps)
        # - terraform (topics: infrastructure)
        pass

    def test_auto_create_missing_repos(self):
        """Test auto-creation of missing GitHub repositories."""
        pass

    def test_name_conflict_detection(self):
        """Test detection of naming conflicts."""
        # company/backend/auth
        # company/frontend/auth
        # Both map to "auth" with prefix strategy - should warn/error
        pass
```

---

## Configuration Examples

### Example 1: Flatten Strategy (Default)
```yaml
source:
  type: gitlab
  url: https://gitlab.com
  token: ${GITLAB_TOKEN}
  group: company/backend

target:
  type: github
  url: https://github.com
  token: ${GITHUB_TOKEN}
  organization: my-github-org

mapping:
  strategy: flatten
  separator: "-"
  strip_parent_group: true  # Drop "company" from names

# Result:
# company/backend/services/auth → backend-services-auth
```

### Example 2: Prefix Strategy with Topics
```yaml
mapping:
  strategy: prefix
  keep_last_n_levels: 1  # Just repo name
  use_topics: true
  parent_groups_as_topics: true

# Result:
# company/backend/services/auth → auth
# Topics: [backend, services]
```

### Example 3: Custom Mapping
```yaml
mapping:
  strategy: custom
  custom_mappings:
    "company/backend": "be"
    "company/frontend": "fe"
    "company/infrastructure": "infra"
  fallback_strategy: flatten

# Result:
# company/backend/services/auth → be-services-auth
# company/frontend/apps/web → fe-apps-web
```

---

## Next Steps

1. ✅ Implement `GroupMapper` class
2. ✅ Implement `SyncOrchestrator` class
3. ✅ Add `sync-group` CLI command
4. ✅ Write unit tests for mapping logic
5. ✅ Write integration tests with real GitLab/GitHub
6. ✅ Document all mapping strategies
7. ✅ Add example configurations
