# Development Roadmap: GitLab to GitHub Repository Cloner

## Overview

This roadmap follows an iterative, sprint-based approach using Test-Driven Development (TDD). Each sprint delivers a working increment with automated tests.

**Estimated Timeline**: 6-8 sprints (12-16 weeks at 2 weeks per sprint)

---

## Sprint 0: Project Setup & Foundation (Week 1-2)

### Goals
- Set up development environment
- Establish project structure
- Configure CI/CD pipeline
- Create initial test framework

### Deliverables
- [ ] Python project structure (src/, tests/, docs/)
- [ ] **`.venv` virtual environment** setup (standardized Python environment)
- [ ] `requirements.txt` and `requirements-dev.txt` for dependencies
- [ ] Pre-commit hooks (black, flake8, mypy)
- [ ] pytest configuration with coverage
- [ ] **Docker Compose** for local test infrastructure (`docker-compose.test.yml`)
- [ ] GitHub Actions CI workflow (run tests on PR)
- [ ] README with setup instructions
- [ ] CONTRIBUTING.md with TDD guidelines
- [ ] .gitignore configured (include `.venv/`, `__pycache__/`, etc.)
- [ ] Development branch strategy documented
- [ ] **Makefile** or task runner for common development commands

### Test Strategy
- **Unit tests** with mocked dependencies (fast, no Docker required)
- **Integration test framework** using Docker Compose for emulators
  - LocalStack (S3), Azurite (Azure), fake-gcs-server (GCS), MinIO
  - GitLab CE Docker, Gitea (lightweight Git server)
- **Optional**: k3s setup documentation for advanced testing scenarios

### Dependencies

**Python Runtime:**
- Python 3.11+ (use `.venv` virtual environment)

**Core Libraries:**
- GitPython
- PyGithub, python-gitlab
- boto3, azure-storage-blob, google-cloud-storage, oci
- PyYAML, Pydantic
- click (CLI framework)

**Testing Libraries:**
- pytest, pytest-cov, pytest-mock
- moto[s3] (AWS S3 mocking)
- responses, requests-mock (HTTP mocking)
- faker, freezegun
- docker, testcontainers (for Docker-based integration tests)

**Code Quality:**
- black, flake8, mypy, isort
- pre-commit

**Test Infrastructure (Docker):**
- LocalStack (AWS S3 emulator)
- Azurite (Azure Blob emulator)
- fake-gcs-server (GCS emulator)
- MinIO (S3-compatible storage)
- GitLab CE (full GitLab instance)
- Gitea (lightweight Git server)

### Environment Setup Commands

```bash
# Create virtual environment
python3.11 -m venv .venv

# Activate virtual environment
source .venv/bin/activate  # Linux/macOS
.venv\Scripts\activate     # Windows

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Install pre-commit hooks
pre-commit install

# Start test infrastructure (Docker Compose)
docker-compose -f docker-compose.test.yml up -d

# Run tests
pytest tests/ -v --cov=src/repo_cloner

# Code formatting
black src/ tests/
isort src/ tests/
flake8 src/ tests/
mypy src/

# Stop test infrastructure
docker-compose -f docker-compose.test.yml down
```

### Definition of Done
- ✅ `.venv` virtual environment configured and documented
- ✅ Project builds successfully with `pip install -r requirements.txt`
- ✅ Docker Compose test infrastructure starts and stops cleanly
- ✅ CI pipeline runs tests (unit + integration with Docker)
- ✅ Code quality checks pass (black, flake8, mypy)
- ✅ Documentation complete with setup instructions
- ✅ All developers can run tests locally with Docker

---

## Sprint 1: Core Git Operations (Week 3-4)

### Goals
- Implement basic Git clone and mirror functionality
- Handle authentication
- Test with single repository

### User Stories
- **US-1.1**: As a developer, I can clone a GitLab repository using a PAT
- **US-1.2**: As a developer, I can create a mirror clone preserving all refs
- **US-1.3**: As a developer, I can push mirrored content to GitHub
- **US-1.4**: As a developer, I can run in dry-run mode to preview operations without making changes

### Deliverables
- [ ] `GitClient` class for Git operations
  - `clone_mirror(source_url, local_path, dry_run=False)`
  - `push_mirror(local_path, target_url, dry_run=False)`
- [ ] `AuthManager` class for credential handling
  - Support for GitLab PAT
  - Support for GitHub PAT
  - Environment variable injection
- [ ] Configuration model (Python dataclass/Pydantic)
- [ ] CLI entry point with basic arguments
  - `--dry-run` flag for preview mode (FR-6.3)
  - Log what would be done without executing
- [ ] Dry-run mode implementation
  - Preview clone operations without cloning
  - Preview push operations without pushing
  - Log all planned actions with clear "DRY-RUN" prefix

### Test Strategy (TDD)
**Write tests FIRST for each feature:**

1. **Test**: `test_clone_mirror_creates_local_repo()`
   - **Then**: Implement `clone_mirror()`

2. **Test**: `test_clone_mirror_preserves_all_branches()`
   - **Then**: Verify mirror flag usage

3. **Test**: `test_push_mirror_to_github()`
   - **Then**: Implement `push_mirror()`

4. **Test**: `test_auth_manager_injects_credentials()`
   - **Then**: Implement URL rewriting with credentials

5. **Test**: `test_dry_run_mode_logs_without_cloning()`
   - **Then**: Implement dry-run for clone operations

6. **Test**: `test_dry_run_mode_logs_without_pushing()`
   - **Then**: Implement dry-run for push operations

7. **Integration Test**: `test_full_clone_and_push_flow()`
   - Use test repositories on GitLab/GitHub

8. **Integration Test**: `test_dry_run_end_to_end()`
   - Run full workflow in dry-run, verify no changes made

### Technical Decisions
- Use GitPython for most operations, shell out to git CLI for mirror
- Store credentials in environment variables only
- Temporary clone directory cleanup strategy

### Definition of Done
- ✅ All unit tests pass (>80% coverage)
- ✅ Integration test with real repositories succeeds
- ✅ CLI can clone and push single repository
- ✅ No credentials logged or stored in plain text

---

## Sprint 2: GitLab & GitHub API Integration (Week 5-6)

### Goals
- Discover repositories via GitLab API
- Create repositories via GitHub API
- Handle basic group/organization mapping

### User Stories
- **US-2.1**: As a user, I can list all repositories in a GitLab group
- **US-2.2**: As a user, I can automatically create GitHub repositories if they don't exist
- **US-2.3**: As a user, I can map a GitLab group to a GitHub organization
- **US-2.4**: As a user, repository metadata (description, topics/tags) is preserved during migration

### Deliverables
- [ ] `GitLabClient` class
  - `list_projects(group_path)`
  - `get_project_details(project_id)` - includes description, topics/tags
  - Support for gitlab.com and self-hosted
- [ ] `GitHubClient` class
  - `create_repository(org, name, description, topics)` - FR-1.5 metadata support
  - `update_repository_metadata(org, name, description, topics)` - update existing repos
  - `repository_exists(org, name)`
  - Support for github.com and GitHub Enterprise
- [ ] `MetadataMapper` class (FR-1.5)
  - Map GitLab tags → GitHub topics
  - Preserve repository descriptions
  - Handle visibility settings (public/private/internal)
- [ ] `GroupMapper` class
  - Basic naming strategy (flatten with separator)
  - Configuration for custom mappings
- [ ] Configuration file format (YAML)

### Test Strategy (TDD)
**Write tests FIRST:**

1. **Test**: `test_gitlab_client_lists_projects()`
   - Mock API responses
   - **Then**: Implement `list_projects()`

2. **Test**: `test_gitlab_client_gets_project_metadata()`
   - Mock API response with description, tags
   - **Then**: Implement `get_project_details()` with metadata

3. **Test**: `test_gitlab_client_handles_pagination()`
   - **Then**: Implement pagination logic

4. **Test**: `test_github_client_creates_repo_with_metadata()`
   - Mock API responses
   - **Then**: Implement `create_repository()` with description and topics

5. **Test**: `test_github_client_updates_repo_metadata()`
   - **Then**: Implement `update_repository_metadata()`

6. **Test**: `test_github_client_checks_existence()`
   - **Then**: Implement `repository_exists()`

7. **Test**: `test_metadata_mapper_converts_tags_to_topics()`
   - GitLab tags: ["backend", "python", "microservice"]
   - GitHub topics: ["backend", "python", "microservice"]
   - **Then**: Implement metadata mapping

8. **Test**: `test_group_mapper_flattens_hierarchy()`
   - Input: `group/subgroup/repo`
   - Expected: `group-subgroup-repo`
   - **Then**: Implement mapping logic

9. **Integration Test**: `test_discover_and_create_repos_with_metadata()`
   - Use test GitLab group and GitHub org
   - Verify description and topics preserved

### Technical Decisions
- Use `python-gitlab` library for GitLab API
- Use `PyGithub` library for GitHub API
- YAML configuration with schema validation (use Pydantic or Cerberus)
- Default naming strategy: `{group}-{subgroup}-{repo}`

### Definition of Done
- ✅ Can list repositories from GitLab via API
- ✅ Can create repositories on GitHub via API
- ✅ Group mapping produces consistent names
- ✅ Configuration file loads and validates
- ✅ All tests pass with mocked APIs

---

## Sprint 3: Synchronization Engine (Week 7-8)

### Goals
- Implement incremental sync logic
- Handle updates to existing repositories
- Track sync state

### User Stories
- **US-3.1**: As a user, I can sync updates from GitLab to GitHub (unidirectional)
- **US-3.2**: As a user, I can sync bidirectionally between any Git platforms
- **US-3.3**: As a user, I can configure sync direction (source→target, target→source, bidirectional)
- **US-3.4**: As a user, I can detect new branches and tags
- **US-3.5**: As a system, I track when each repository was last synced
- **US-3.6**: As a system, I detect conflicts during bidirectional sync and provide resolution strategies

### Deliverables
- [ ] `SyncEngine` class
  - `sync_repository(source, target, strategy, direction)` - supports unidirectional and bidirectional
  - `detect_changes(source, local_mirror)`
  - `handle_force_pushes()`
  - `detect_conflicts(source, target)` - for bidirectional sync
  - `resolve_conflicts(strategy)` - conflict resolution strategies
- [ ] State persistence (JSON or SQLite)
  - Store last sync timestamp per repo per direction
  - Store last commit SHA per branch per remote
  - Track sync direction configuration
- [ ] Sync strategies
  - Full mirror (overwrite everything)
  - Incremental (fetch only new refs)
- [ ] Sync direction modes (FR-3.7)
  - **Source → Target** (unidirectional forward)
  - **Target → Source** (unidirectional reverse)
  - **Bidirectional** (two-way sync with conflict detection)
- [ ] Conflict detection and resolution (FR-3.5, FR-3.6)
  - Detect divergent commits on same branch
  - Resolution strategies: fail-fast, source-wins, target-wins, manual
  - Log conflicts for manual review

### Test Strategy (TDD)
**Write tests FIRST:**

1. **Test**: `test_sync_detects_new_commits()`
   - Set up repo with initial state, add commits
   - **Then**: Implement change detection

2. **Test**: `test_sync_handles_new_branches()`
   - **Then**: Implement branch sync logic

3. **Test**: `test_sync_handles_deleted_branches()`
   - **Then**: Implement deletion propagation

4. **Test**: `test_state_persists_last_sync_time_per_direction()`
   - **Then**: Implement state storage with direction tracking

5. **Test**: `test_sync_handles_force_push()`
   - **Then**: Implement force push detection and handling

6. **Test**: `test_bidirectional_sync_without_conflicts()`
   - Changes on both sides, no overlaps
   - **Then**: Implement bidirectional sync

7. **Test**: `test_bidirectional_sync_detects_conflicts()`
   - Divergent commits on same branch
   - **Then**: Implement conflict detection

8. **Test**: `test_conflict_resolution_source_wins()`
   - **Then**: Implement source-wins strategy

9. **Test**: `test_conflict_resolution_fail_fast()`
   - **Then**: Implement fail-fast on conflict

10. **Test**: `test_sync_direction_source_to_target()`
    - **Then**: Implement unidirectional forward

11. **Test**: `test_sync_direction_target_to_source()`
    - **Then**: Implement unidirectional reverse

12. **Integration Test**: `test_full_bidirectional_sync_cycle()`
    - Make changes on both platforms → sync bidirectionally → verify both sides

### Technical Decisions
- Use `git fetch --all --tags --prune` for sync
- Store state in JSON file by default (SQLite for scale)
- Fail fast on conflicts by default, provide override flag
- Mirror mode: use `git push --mirror` for full sync

### Definition of Done
- ✅ Incremental sync only fetches new changes
- ✅ State correctly persists between runs
- ✅ Sync handles branches, tags, and force pushes
- ✅ All edge cases tested (empty repos, first sync, etc.)

---

## Sprint 4: LFS Support & Large Repository Handling (Week 9-10)

### Goals
- Support Git LFS objects
- Optimize for large repositories
- Handle bandwidth and storage efficiently

### User Stories
- **US-4.1**: As a user, I can clone repositories with LFS objects
- **US-4.2**: As a user, I can sync LFS updates
- **US-4.3**: As a system, I handle large files without running out of memory

### Deliverables
- [ ] LFS detection and handling
  - Check for `.gitattributes` with LFS patterns
  - Install/verify git-lfs CLI
- [ ] LFS clone and sync operations
  - `GIT_LFS_SKIP_SMUDGE` for faster clone
  - Selective LFS fetch based on configuration
- [ ] Performance optimizations
  - Shallow clone option (configurable depth)
  - Partial clone (if Git version supports)
  - Concurrent operations (multiple repos in parallel)
- [ ] Progress reporting for large operations

### Test Strategy (TDD)
**Write tests FIRST:**

1. **Test**: `test_detects_lfs_enabled_repo()`
   - **Then**: Implement LFS detection

2. **Test**: `test_clone_with_lfs_objects()`
   - Create test repo with LFS files
   - **Then**: Implement LFS clone

3. **Test**: `test_lfs_sync_updates_only_changed_objects()`
   - **Then**: Implement incremental LFS sync

4. **Test**: `test_large_repo_clone_succeeds()`
   - Mock or use >1GB test repo
   - **Then**: Implement streaming/chunking

5. **Test**: `test_concurrent_clone_multiple_repos()`
   - **Then**: Implement parallel processing with thread/process pool

### Technical Decisions
- Require git-lfs CLI installed (check at startup)
- Use `git lfs fetch --all` for LFS sync
- Default: 4 concurrent repository operations
- Progress bars using `tqdm` library

### Definition of Done
- ✅ LFS repositories clone successfully
- ✅ LFS objects sync correctly
- ✅ Large repositories (>1GB) handle without errors
- ✅ Concurrent operations improve performance
- ✅ Memory usage stays reasonable (<2GB for typical workloads)

---

## Sprint 5: Configuration & Group Mapping Strategies (Week 11-12)

### Goals
- Implement flexible configuration system
- Support multiple group mapping strategies
- Allow per-repo customization

### User Stories
- **US-5.1**: As a user, I can configure multiple GitLab groups to sync
- **US-5.2**: As a user, I can choose different group mapping strategies
- **US-5.3**: As a user, I can exclude specific repositories from sync
- **US-5.4**: As a user, I can set per-repository sync options

### Deliverables
- [ ] Enhanced configuration schema
  ```yaml
  gitlab:
    url: https://gitlab.example.com
    token: ${GITLAB_TOKEN}
  github:
    url: https://github.example.com
    token: ${GITHUB_TOKEN}

  mapping_strategy: flatten  # flatten, prefix, topics, custom

  groups:
    - source: backend
      target_org: myorg
      prefix: be
      exclude:
        - backend/deprecated-service
      lfs_enabled: true
      sync_strategy: mirror
  ```
- [ ] Group mapping strategies
  - **Flatten**: `group-subgroup-repo`
  - **Prefix**: `prefix_repo` (drop parent groups)
  - **Topics**: Use GitHub topics to represent hierarchy
  - **Custom**: User-defined mapping function
- [ ] Schema validation with helpful error messages
- [ ] Configuration inheritance (global → group → repo)

### Test Strategy (TDD)
**Write tests FIRST:**

1. **Test**: `test_config_loads_from_yaml()`
   - **Then**: Implement YAML parsing

2. **Test**: `test_config_validates_required_fields()`
   - **Then**: Implement validation

3. **Test**: `test_env_var_substitution()`
   - **Then**: Implement `${VAR}` expansion

4. **Test**: `test_flatten_strategy_mapping()`
   - **Then**: Implement flatten mapper

5. **Test**: `test_prefix_strategy_mapping()`
   - **Then**: Implement prefix mapper

6. **Test**: `test_topics_strategy_adds_labels()`
   - **Then**: Implement topics via GitHub API

7. **Test**: `test_exclude_filters_repos()`
   - **Then**: Implement exclusion logic

8. **Test**: `test_config_inheritance()`
   - Global setting → group override → repo override
   - **Then**: Implement inheritance resolution

### Technical Decisions
- Use PyYAML for parsing, Pydantic for validation
- Environment variable substitution: `${VAR}` or `${VAR:-default}`
- Support both single file and directory of configs
- Provide example configurations in `examples/`

### Definition of Done
- ✅ Configuration file validates correctly
- ✅ All mapping strategies work as documented
- ✅ Exclusions filter correctly
- ✅ Inheritance resolves in correct priority order
- ✅ Example configs provided and tested

---

## Sprint 6: Air-Gap Support & Archive Management (Week 13-14)

### Goals
- Export repositories to archives
- Upload to S3/cloud storage
- Support import from archives

### User Stories
- **US-6.1**: As a user, I can export synced repositories to tar.gz archives (full and incremental)
- **US-6.2**: As a user, I can upload archives to multiple storage backends (local filesystem, AWS S3, Azure Blob, GCS, Oracle OCI, S3-compatible)
- **US-6.3**: As a user, I can import repositories from archives
- **US-6.4**: As a user, I receive a manifest file describing archived content with version tracking and checksums
- **US-6.5**: As a user, I can select specific regions for cloud storage backends
- **US-6.6**: As a user, I can list and query archives across all storage backends
- **US-6.7**: As a user, I can reconstruct full repository from incremental archive chains

### Deliverables
- [ ] `ArchiveManager` class
  - `create_full_archive(repo_path, output_path, include_lfs)` - complete repo with all history
  - `create_incremental_archive(repo_path, output_path, parent_archive)` - delta since parent
  - `extract_archive(archive_path, output_path)`
  - `reconstruct_from_chain(base_archive, incremental_archives[])` - apply incremental deltas
- [ ] `StorageManager` class with pluggable backends
  - **Local Filesystem Backend**: Direct file system paths (NFS, SMB mounts)
  - **AWS S3 Backend** (boto3): All regions with region selection
  - **Azure Blob Backend** (azure-storage-blob): All regions
  - **GCS Backend** (google-cloud-storage): All regions/multi-regions
  - **Oracle OCI Backend** (oci): All regions with namespace
  - **S3-Compatible Backend**: MinIO, Ceph, DigitalOcean, etc.
  - Methods: `upload_archive()`, `download_archive()`, `list_archives()`, `query_archives()`
- [ ] Version tracking and integrity verification (FR-10)
  - Track Git commit SHAs for all branches and tags in manifest
  - Generate SHA256 checksums for all artifacts (bundles, archives, LFS objects)
  - Preserve lock files with checksums
  - Implement verification workflows
- [ ] Enhanced manifest generation (see REQUIREMENTS.md for full example)
  - Archive metadata (type: full/incremental, timestamp, size)
  - Git metadata with commit SHAs for all branches/tags
  - Archive file checksums (SHA256 for bundles and tar.gz)
  - LFS object checksums (SHA256 OIDs)
  - Storage backend info (type, region, location)
  - Parent archive reference (for incremental archives)
  - Verification status
- [ ] Archive retention policies (FR-5.11)
  - Delete old archives after N days/versions
  - Configurable retention per repository or globally
- [ ] CLI commands: `archive create`, `archive restore`, `archive upload`, `archive download`, `archive list`, `archive query`

### Test Strategy (TDD)
**Write tests FIRST:**

1. **Test**: `test_create_full_archive_from_repo()`
   - **Then**: Implement full archive creation with git bundle

2. **Test**: `test_create_incremental_archive_from_repo()`
   - **Then**: Implement delta archive with parent reference

3. **Test**: `test_reconstruct_from_archive_chain()`
   - Base + 3 incremental archives
   - **Then**: Implement chain reconstruction

4. **Test**: `test_archive_includes_lfs_objects_with_checksums()`
   - **Then**: Implement LFS bundling with SHA256

5. **Test**: `test_extract_archive_restores_repo()`
   - **Then**: Implement extraction

6. **Test**: `test_s3_upload_with_region_selection()`
   - Use moto for S3 mocking
   - **Then**: Implement S3 backend with region support

7. **Test**: `test_azure_blob_upload_with_region()`
   - Use Azurite for Azure emulation
   - **Then**: Implement Azure Blob backend

8. **Test**: `test_gcs_upload_with_location()`
   - Use fake-gcs-server
   - **Then**: Implement GCS backend

9. **Test**: `test_oci_upload_with_namespace_region()`
   - Mock OCI SDK
   - **Then**: Implement Oracle OCI backend

10. **Test**: `test_local_filesystem_backend()`
    - **Then**: Implement local filesystem backend

11. **Test**: `test_s3_compatible_minio()`
    - Use MinIO container
    - **Then**: Implement S3-compatible backend

12. **Test**: `test_list_archives_across_all_backends()`
    - **Then**: Implement unified archive listing

13. **Test**: `test_manifest_includes_commit_shas_and_checksums()`
    - **Then**: Implement comprehensive manifest

14. **Test**: `test_verification_workflow_detects_corruption()`
    - **Then**: Implement checksum verification

15. **Test**: `test_archive_retention_policy()`
    - **Then**: Implement retention cleanup

16. **Integration Test**: `test_full_multi_cloud_archive_restore_cycle()`
    - Archive → upload to S3, Azure, GCS → download → restore → verify

### Technical Decisions
- Use `tarfile` module for archives with gzip compression
- **Cloud Storage SDKs**:
  - boto3 for AWS S3
  - azure-storage-blob for Azure Blob Storage
  - google-cloud-storage for GCS
  - oci for Oracle Cloud Infrastructure
  - boto3 with custom endpoint for S3-compatible storage
- Archive naming: `{repo-name}-{full|inc}-{timestamp}.tar.gz`
- Manifest: JSON format (same structure as in REQUIREMENTS.md example)
- Git bundles for complete ref/commit storage
- Incremental archives use `git bundle create --since` for deltas
- Checksum algorithm: SHA256 for all artifacts
- Lock file preservation: Store alongside dependency manifests

### Definition of Done
- ✅ Full and incremental archives create successfully
- ✅ Archive chain reconstruction works (base + N incrementals)
- ✅ LFS objects included with SHA256 checksums
- ✅ All 6 storage backends implemented and tested:
  - Local filesystem
  - AWS S3 (with region selection)
  - Azure Blob Storage (with region selection)
  - GCS (with location selection)
  - Oracle OCI (with namespace and region)
  - S3-compatible (MinIO tested)
- ✅ Archive listing/querying works across all backends
- ✅ Manifest includes commit SHAs for all branches/tags
- ✅ Manifest includes SHA256 checksums for all artifacts
- ✅ Verification workflows detect corruption
- ✅ Archive retention policies work
- ✅ Import restores repository to working state with integrity verification

---

## Sprint 7: GitHub Actions Integration & Scheduling (Week 15-16)

### Goals
- Create GitHub Actions workflow
- Support scheduled execution
- Provide workflow configuration options

### User Stories
- **US-7.1**: As a user, I can run the tool via GitHub Actions on a schedule
- **US-7.2**: As a user, I can manually trigger the workflow
- **US-7.3**: As a user, I receive notifications of sync status
- **US-7.4**: As a user, I can configure workflow via repository variables/secrets

### Deliverables
- [ ] GitHub Actions workflow file (`.github/workflows/sync.yml`)
  ```yaml
  name: Sync GitLab to GitHub

  on:
    schedule:
      - cron: '0 2 * * *'  # 2 AM daily
    workflow_dispatch:     # Manual trigger

  jobs:
    sync:
      runs-on: ubuntu-latest
      steps:
        - uses: actions/checkout@v3
        - name: Set up Python
          uses: actions/setup-python@v4
          with:
            python-version: '3.11'
        - name: Install dependencies
          run: |
            pip install -r requirements.txt
        - name: Run sync
          env:
            GITLAB_TOKEN: ${{ secrets.GITLAB_TOKEN }}
            GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          run: |
            python -m repo_cloner sync --config config.yml
        - name: Upload logs
          uses: actions/upload-artifact@v3
          if: always()
          with:
            name: sync-logs
            path: logs/
  ```
- [ ] Notification integration
  - GitHub Action summary (success/failure counts)
  - Optional: Slack webhook, email
- [ ] Workflow configuration documentation
- [ ] Secrets management guide

### Test Strategy (TDD)
**Write tests FIRST:**

1. **Test**: `test_github_action_workflow_syntax_valid()`
   - Use action-validator or yamllint
   - **Then**: Create workflow file

2. **Test**: `test_cli_exits_with_error_code_on_failure()`
   - Ensures Actions marks step as failed
   - **Then**: Implement proper exit codes

3. **Test**: `test_summary_report_generates_for_actions()`
   - **Then**: Implement GitHub Actions summary output

4. **Test**: `test_slack_notification_sends_on_completion()`
   - Mock webhook
   - **Then**: Implement Slack integration

### Technical Decisions
- Use official GitHub-provided actions where possible
- Store logs as workflow artifacts
- Use GitHub Action summary for quick status view
- Support GitHub Action environment variables
- Provide template for customization

### Definition of Done
- ✅ Workflow runs successfully on schedule
- ✅ Manual trigger works via Actions UI
- ✅ Secrets properly injected from repository settings
- ✅ Logs available as artifacts
- ✅ Summary shows sync results clearly
- ✅ Documentation complete for setup

---

## Sprint 8: Error Handling, Logging & Documentation (Week 17-18)

### Goals
- Robust error handling and recovery
- Comprehensive logging
- Complete documentation
- Production readiness

### User Stories
- **US-8.1**: As a user, I receive clear error messages when operations fail
- **US-8.2**: As a user, I can review detailed logs for troubleshooting
- **US-8.3**: As a user, I can resume operations after transient failures
- **US-8.4**: As a user, I have complete documentation to set up and use the tool

### Deliverables
- [ ] Enhanced error handling
  - Custom exception hierarchy
  - Retry logic with exponential backoff
  - Graceful degradation (skip failed repos, continue)
  - State recovery (resume from last successful sync)
- [ ] Structured logging
  - JSON logging option
  - Log levels: DEBUG, INFO, WARN, ERROR
  - Contextual information (repo name, operation, timestamp)
  - Log rotation for long-running operations
- [ ] Notification system
  - Email alerts on failure (SMTP)
  - Slack/Discord webhooks
  - Custom webhook support
- [ ] Complete documentation
  - README: Quick start, installation
  - USAGE.md: Detailed CLI reference
  - CONFIGURATION.md: Config file schema
  - ARCHITECTURE.md: System design
  - TROUBLESHOOTING.md: Common issues
  - API.md: Developer reference (if exposing as library)
  - **FORK_WORKFLOW.md**: Local fork support (FR-11)
    - How to fork cloned repositories locally
    - Branch protection rule setup
    - Adding local features while maintaining upstream sync
    - Excluding local-only branches from sync
    - Best practices for dual-use repositories (synced + local dev)

### Test Strategy (TDD)
**Write tests FIRST:**

1. **Test**: `test_retry_logic_on_network_failure()`
   - Mock network errors
   - **Then**: Implement retry with backoff

2. **Test**: `test_continues_after_single_repo_failure()`
   - **Then**: Implement error isolation

3. **Test**: `test_state_recovery_after_interruption()`
   - **Then**: Implement checkpoint/resume

4. **Test**: `test_structured_json_logging()`
   - **Then**: Implement JSON formatter

5. **Test**: `test_email_notification_on_failure()`
   - **Then**: Implement SMTP integration

6. **Test**: `test_log_rotation_after_size_limit()`
   - **Then**: Implement log rotation

7. **Integration Test**: `test_full_workflow_with_failures()`
   - Simulate various failure scenarios
   - Verify recovery and logging

### Technical Decisions
- Use Python `logging` module with custom formatters
- Retry library: `tenacity` or custom implementation
- Email: `smtplib` for notifications
- Log rotation: `logging.handlers.RotatingFileHandler`
- Documentation: Markdown in `docs/` directory

### Definition of Done
- ✅ All error scenarios handled gracefully
- ✅ Retry logic prevents transient failures from stopping execution
- ✅ Logs provide sufficient detail for debugging
- ✅ Notifications work for configured channels
- ✅ Documentation complete and accurate
- ✅ Code coverage >85%
- ✅ Tool is production-ready

---

---

## Sprint 9 (Enhancement): Dependency Fetching & Air-Gap Package Management (Week 19-20)

### Goals
- Fetch and archive external dependencies from package repositories
- Support multiple language ecosystems
- Handle authenticated package registries
- Enable true air-gap deployments with all dependencies

### User Stories
- **US-9.1**: As a user, I can fetch all dependencies for a repository automatically
- **US-9.2**: As a user, I can archive dependencies alongside repository archives
- **US-9.3**: As a user, I can authenticate to private package registries (Nexus, Artifactory, etc.)
- **US-9.4**: As a user, I can restore dependencies in an air-gap environment

### Overview

For true air-gap deployments, repositories alone are insufficient. Dependencies from external package repositories (PyPI, npm, Maven Central, crates.io, etc.) must also be archived. This sprint adds comprehensive dependency detection, fetching, and archiving across multiple language ecosystems.

### Deliverables

#### 1. Dependency Detection System
- [ ] `DependencyDetector` class
  - Auto-detect language/framework from repository structure
  - Parse dependency manifest files
  - Support for multiple languages in monorepos

#### 2. Language-Specific Dependency Fetchers (Top 10 Languages + Additional)

**Python** (#1 in 2025 - AI, ML, Data Science, Web)
- [ ] Parse `requirements.txt`, `Pipfile`, `pyproject.toml`, `setup.py`, `poetry.lock`
- [ ] Fetch from PyPI, private PyPI servers (Nexus, Artifactory, JFrog)
- [ ] **Resolve transitive dependencies**: Use pip's resolver or parse package metadata recursively
- [ ] Support authentication (username/password, token, .pypirc)
- [ ] Download wheels and source distributions for all dependency levels
- [ ] Generate `pip install --no-index --find-links` compatible directory

**Java** (#2 in 2025 - Enterprise, Android)
- [ ] Parse `pom.xml` (Maven), `build.gradle` (Gradle), `build.sbt` (SBT)
- [ ] Fetch from Maven Central, JCenter, private Nexus/Artifactory
- [ ] **Resolve all transitive dependencies**: Use Maven/Gradle dependency resolution algorithms
- [ ] Support `settings.xml` authentication and mirror configuration
- [ ] Download JARs, POMs, and all transitive dependencies (unlimited depth)
- [ ] Generate local Maven repository structure with complete dependency tree

**JavaScript/TypeScript** (#3/#7 in 2025 - Web Development, Large-Scale Apps)
- [ ] Parse `package.json`, `package-lock.json`, `yarn.lock`, `pnpm-lock.yaml`
- [ ] Detect TypeScript (tsconfig.json) but use same npm/yarn tooling
- [ ] Fetch from npm, Yarn, pnpm, private npm registries (Verdaccio, Nexus, Artifactory)
- [ ] **Resolve deep dependency trees**: npm can have 10+ levels of nested dependencies
- [ ] Use lock files for deterministic resolution of transitive dependencies
- [ ] Support `.npmrc` authentication (tokens, credentials)
- [ ] Download tarballs for entire dependency graph (all nested levels)
- [ ] Generate offline-compatible `node_modules` archive with complete tree

**C++** (#4 in 2025 - System Programming, High Performance)
- [ ] Parse `CMakeLists.txt` (CMake with FetchContent/CPM.cmake)
- [ ] Parse `conanfile.txt`, `conanfile.py` (Conan)
- [ ] Parse `vcpkg.json` (vcpkg)
- [ ] Fetch from Conan Center, vcpkg, private Conan servers
- [ ] Support authentication for private Conan remotes
- [ ] Download pre-built binaries and sources

**C** (#5 in 2025 - Embedded Systems, Speed)
- [ ] Parse `CMakeLists.txt` (CMake - same as C++)
- [ ] Parse `conanfile.txt/py`, `vcpkg.json` (same tooling as C++)
- [ ] Fetch dependencies using same C++ package managers
- [ ] Download libraries and headers

**C#/.NET** (#6 in 2025 - Enterprise, Unity Game Dev)
- [ ] Parse `*.csproj` (PackageReference format)
- [ ] Parse `packages.config` (legacy format)
- [ ] Parse `global.json` (SDK version pinning)
- [ ] Fetch from NuGet.org, private NuGet feeds (Nexus, Artifactory, Azure Artifacts)
- [ ] **Resolve transitive dependencies**: NuGet automatically resolves package dependencies
- [ ] Support `nuget.config` authentication
- [ ] Download `.nupkg` files for all dependency levels
- [ ] Generate offline NuGet package cache with complete dependency graph

**Go** (#8 in 2025 - Cloud, Backend Services)
- [ ] Parse `go.mod`, `go.sum`
- [ ] Fetch from proxy.golang.org, private Go proxies (Athens, Artifactory)
- [ ] **Resolve transitive module dependencies**: Go modules automatically resolve indirect dependencies
- [ ] Support GOPRIVATE and authentication via .netrc
- [ ] Download all modules (direct + indirect) with checksums from go.sum
- [ ] Generate GOPROXY-compatible directory with complete module graph

**PHP** (#9 in 2025 - Server-Side, 75.6% of Websites)
- [ ] Parse `composer.json`, `composer.lock`
- [ ] Fetch from Packagist.org, private Satis/Toran repositories
- [ ] **Resolve transitive dependencies**: Composer resolves multi-level package dependencies
- [ ] Use composer.lock for deterministic resolution
- [ ] Support `auth.json` authentication
- [ ] Download all packages (direct + transitive dependencies)
- [ ] Generate offline-compatible `vendor/` directory with complete dependency tree

**Rust** (#10 in 2025 - System Programming, Performance-Critical)
- [ ] Parse `Cargo.toml`, `Cargo.lock`
- [ ] Fetch from crates.io, private Cargo registries
- [ ] **Resolve transitive dependencies**: Cargo.lock contains full dependency graph
- [ ] Support `.cargo/config.toml` with registry authentication
- [ ] Download all crates (direct + transitive) from dependency graph
- [ ] Generate local crate mirror with complete dependency tree

**Additional Languages**

**Ruby** (Still widely used in web)
- [ ] Parse `Gemfile`, `Gemfile.lock`
- [ ] Fetch from RubyGems.org, private gem servers
- [ ] Support bundler configuration and credentials
- [ ] Download gems with dependency resolution
- [ ] Generate `bundle install --local` compatible gem directory

**Swift** (iOS, macOS development)
- [ ] Parse `Podfile`, `Podfile.lock` (CocoaPods)
- [ ] Parse `Package.swift` (Swift Package Manager)
- [ ] Fetch from CocoaPods specs, GitHub
- [ ] Download pods and SPM packages

**Scala** (JVM functional programming)
- [ ] Parse `build.sbt` (SBT)
- [ ] Fetch from Maven Central, private repositories
- [ ] Generate local Ivy/Maven cache

**Ada** (Safety-critical systems)
- [ ] Parse `alire.toml` (Alire package manager)
- [ ] Fetch from Alire index
- [ ] Support custom Alire repositories
- [ ] Download crates

**Fortran** (Scientific computing)
- [ ] Parse `fpm.toml` (Fortran Package Manager)
- [ ] Fetch from fpm registry
- [ ] Download dependencies

#### 3. Package Registry Clients
- [ ] `PackageRegistryClient` abstract base class
- [ ] Pluggable architecture for each package ecosystem
- [ ] Authentication handling (tokens, username/password, certificates)
- [ ] Retry logic for network failures
- [ ] Checksum verification for downloaded packages

#### 4. Dependency Archive Manager
- [ ] `DependencyArchiver` class
  - Archive dependencies by language/ecosystem
  - Create manifest of all fetched packages (name, version, URL, checksum)
  - Support for multiple ecosystems in single repository
  - Integrate with existing `ArchiveManager` for unified archives

#### 5. Configuration Extensions
```yaml
dependencies:
  enabled: true

  # Package registry authentication
  registries:
    pypi:
      url: https://pypi.org/simple
      username: ${PYPI_USER}
      password: ${PYPI_PASS}

    npm:
      url: https://registry.npmjs.org
      token: ${NPM_TOKEN}

    maven:
      url: https://repo.maven.apache.org/maven2
      mirrors:
        - id: nexus
          url: https://nexus.example.com/repository/maven-public
          username: ${NEXUS_USER}
          password: ${NEXUS_PASS}

    rubygems:
      url: https://rubygems.org
      credentials: ~/.gem/credentials

    cargo:
      registry: https://crates.io
      token: ${CARGO_TOKEN}

  # Per-language settings
  python:
    include_dev_dependencies: false
    prefer_wheels: true

  nodejs:
    include_dev_dependencies: false
    lock_file_type: auto  # auto, package-lock, yarn, pnpm

  java:
    include_test_dependencies: false
    download_sources: true
    download_javadocs: false
```

#### 6. CLI Commands
```bash
# Fetch dependencies for a repository
repo-cloner deps fetch \
  --repo /path/to/repo \
  --output /path/to/deps

# Archive repo + dependencies together
repo-cloner archive create \
  --source https://gitlab.com/org/repo \
  --output /path/to/archives \
  --include-dependencies

# Restore repo with dependencies in air-gap
repo-cloner archive restore \
  --archive repo-full-20250109.tar.gz \
  --target https://github.com/org/repo \
  --install-dependencies  # Set up local package cache

# List detected dependencies
repo-cloner deps list --repo /path/to/repo
```

### Test Strategy (TDD)

**Write tests FIRST:**

1. **Test**: `test_detect_python_dependencies()`
   - Given repo with `requirements.txt`
   - **Then**: Detect Python, parse dependencies

2. **Test**: `test_fetch_python_package_from_pypi()`
   - Mock PyPI HTTP responses
   - **Then**: Download wheel/sdist with checksum verification

3. **Test**: `test_resolve_python_transitive_dependencies()`
   - Given package `requests` (which depends on `urllib3`, `certifi`, `charset-normalizer`, `idna`)
   - **Then**: Fetch all 5 packages (1 direct + 4 transitive)
   - Verify complete dependency tree

4. **Test**: `test_resolve_nodejs_deep_dependency_tree()`
   - Given package with 10+ levels of nested dependencies
   - Use package-lock.json for deterministic resolution
   - **Then**: Fetch all packages from all levels
   - Verify no missing dependencies

5. **Test**: `test_resolve_java_transitive_dependencies()`
   - Given pom.xml with Spring Boot (has 50+ transitive dependencies)
   - **Then**: Use Maven resolver to fetch all JARs
   - Verify complete dependency graph

6. **Test**: `test_circular_dependency_detection()`
   - Given packages with circular dependencies (A→B→C→A)
   - **Then**: Detect cycle, resolve without infinite loop

7. **Test**: `test_authenticate_to_private_pypi()`
   - Mock private registry with 401 → authenticated request
   - **Then**: Implement auth injection

8. **Test**: `test_detect_multiple_languages_in_monorepo()`
   - Given repo with `package.json` + `requirements.txt`
   - **Then**: Detect both, fetch from both ecosystems with all transitive deps

9. **Test**: `test_generate_offline_installation_structure()`
   - **Then**: Create directory layout compatible with offline install
   - Verify all transitive dependencies included

10. **Test**: `test_dependency_manifest_includes_full_graph()`
    - **Then**: Generate manifest with dependency tree visualization
    - Show direct → transitive → nested relationships

11. **Test**: `test_archive_includes_all_transitive_dependencies()`
    - **Then**: Unified archive with repo + complete dependency graph

12. **Integration Test**: `test_full_air_gap_workflow_with_deep_dependencies()`
    - Clone repo with deep dependency trees → fetch all levels → archive → restore → verify install works offline without any missing packages

### Technical Decisions

**Dependency Resolution:**
- Use existing language-specific tools where possible:
  - Python: `pip download` or parse lock files
  - Node.js: Parse lock files (package-lock.json, yarn.lock)
  - Java: Maven Dependency Plugin or Gradle
  - Ruby: `bundle package`
  - Rust: `cargo fetch`
- Parse lock files for deterministic dependency trees
- Implement fallback manual parsing for simple cases

**Authentication:**
- Support environment variables for credentials
- Support config files (`.npmrc`, `.pypirc`, `settings.xml`, etc.)
- Secure credential storage (encrypted or via secret managers)
- Never log credentials

**Storage Layout:**
```
archive-root/
├── repo/                      # Git repository
├── dependencies/
│   ├── python/
│   │   ├── packages/          # .whl and .tar.gz files
│   │   └── manifest.json
│   ├── nodejs/
│   │   ├── node_modules/      # Offline node_modules
│   │   └── manifest.json
│   ├── java/
│   │   ├── m2-repo/           # Local Maven repo structure
│   │   └── manifest.json
│   └── ruby/
│       ├── gems/
│       └── manifest.json
└── restore-scripts/
    ├── setup-python.sh        # pip install --no-index --find-links
    ├── setup-nodejs.sh        # npm install --offline
    └── setup-java.sh          # mvn install with local repo
```

**Manifest Format (with Transitive Dependencies):**
```json
{
  "language": "python",
  "manifest_file": "requirements.txt",
  "packages": [
    {
      "name": "requests",
      "version": "2.31.0",
      "source_url": "https://pypi.org/simple/requests/",
      "filename": "requests-2.31.0-py3-none-any.whl",
      "sha256": "58cd2187c01e70e6e26505bca751777aa9f2ee0b7f4300988b709f44e013003f",
      "size_bytes": 62574,
      "dependency_type": "direct",
      "dependencies": ["urllib3", "certifi", "charset-normalizer", "idna"]
    },
    {
      "name": "urllib3",
      "version": "2.0.7",
      "source_url": "https://pypi.org/simple/urllib3/",
      "filename": "urllib3-2.0.7-py3-none-any.whl",
      "sha256": "...",
      "size_bytes": 123904,
      "dependency_type": "transitive",
      "required_by": ["requests"]
    },
    {
      "name": "certifi",
      "version": "2023.7.22",
      "source_url": "https://pypi.org/simple/certifi/",
      "filename": "certifi-2023.7.22-py3-none-any.whl",
      "sha256": "...",
      "size_bytes": 158000,
      "dependency_type": "transitive",
      "required_by": ["requests"]
    }
  ],
  "dependency_tree": {
    "requests": {
      "version": "2.31.0",
      "dependencies": {
        "urllib3": {"version": "2.0.7", "dependencies": {}},
        "certifi": {"version": "2023.7.22", "dependencies": {}},
        "charset-normalizer": {"version": "3.3.0", "dependencies": {}},
        "idna": {"version": "3.4", "dependencies": {}}
      }
    }
  },
  "total_packages": 25,
  "direct_packages": 3,
  "transitive_packages": 22,
  "max_dependency_depth": 2,
  "total_size_bytes": 5242880,
  "fetched_at": "2025-10-09T12:00:00Z"
}
```

### Definition of Done
- ✅ Detect dependencies for **Top 10 Languages 2025**:
  - Python, Java, JavaScript/TypeScript, C++, C, C#/.NET, Go, PHP, Rust
- ✅ Detect dependencies for **Additional Languages**:
  - Ruby, Swift, Scala, Ada, Fortran
- ✅ **Resolve all transitive dependencies** (unlimited depth):
  - Direct dependencies (explicitly listed in manifest files)
  - Transitive dependencies (dependencies of dependencies)
  - Deep nested dependencies (10+ levels for Node.js, 50+ for Java Spring Boot)
  - Circular dependency detection and resolution
- ✅ Fetch packages from public and private registries for all supported languages
- ✅ Authentication works for major private registry types (Nexus, Artifactory, JFrog, Azure Artifacts, Verdaccio, Athens, Satis)
- ✅ Dependencies included in unified archives with per-language subdirectories
  - Complete dependency graphs (no missing transitive dependencies)
  - Dependency tree visualization in manifest
- ✅ Restore scripts successfully install dependencies offline for all languages
  - No network calls required during restore
  - No missing packages errors
- ✅ Manifest accurately describes all fetched packages with checksums
  - Include dependency_type: "direct" or "transitive"
  - Include required_by: list of packages that depend on this one
  - Include dependency_tree: nested structure showing relationships
  - Include max_dependency_depth: deepest level in tree
- ✅ All tests pass with >80% coverage
  - Tests for transitive dependency resolution
  - Tests for deep dependency trees (10+ levels)
  - Tests for circular dependency detection
- ✅ Documentation includes comprehensive air-gap deployment guide with examples for top 10 languages

### Libraries/Tools to Use

```python
# requirements-dev.txt additions
packaging>=23.0          # Parse version specifiers
toml>=0.10.2            # Parse TOML files (Cargo.toml, pyproject.toml)
xmltodict>=0.13.0       # Parse Maven pom.xml
semver>=3.0.0           # Semantic versioning
httpx>=0.24.0           # Async HTTP client for downloads
aiofiles>=23.0.0        # Async file I/O
```

**Command-Line Tools (optional, shell out if needed):**
- `pip download`
- `npm pack` / `yarn pack`
- `mvn dependency:copy-dependencies`
- `bundle package`
- `cargo fetch`

---

## Post-Sprint: Future Enhancements

### Future Considerations (Beyond Sprint 9)
- **Web Dashboard**: Monitor sync status via web UI
- **Metrics & Monitoring**: Prometheus/Grafana integration
- **Wiki Migration**: Clone GitLab wikis
- **Issue Migration**: Optionally migrate issues (complex, separate project)
- **Advanced Conflict Resolution**: Merge strategies, interactive resolution
- **Performance Optimization**: Rust rewrite for core Git operations
- **Plugin System**: Allow custom pre/post-sync hooks
- **Container Image Archiving**: Fetch Docker/OCI images referenced in repos
- **Dependency Vulnerability Scanning**: Integrate with Snyk, Dependabot
- **Build Artifact Caching**: Cache compiled artifacts for faster air-gap deployments

---

## Testing Strategy Summary

### TDD Process for Each Sprint
1. **Write failing tests first** for each requirement
2. **Implement minimum code** to make tests pass
3. **Refactor** while keeping tests green
4. **Integration tests** for end-to-end scenarios
5. **Code review** focusing on test coverage

### Test Pyramid
```
     /\
    /  \   E2E Tests (few, critical paths)
   /____\
  /      \  Integration Tests (moderate)
 /________\
/__________\ Unit Tests (many, fast)
```

### Test Categories
- **Unit Tests**: 70% of tests, fast (<1s each)
- **Integration Tests**: 25% of tests, use real Git operations
- **E2E Tests**: 5% of tests, full workflow with real APIs (can use test accounts)

### CI/CD Testing
- Run unit tests on every commit
- Run integration tests on PR
- Run E2E tests on merge to main
- Nightly: Full workflow test with production config (against test repos)

---

## Risk Management

| Risk | Impact | Mitigation |
|------|--------|------------|
| API rate limits | High | Implement rate limiting, caching, pagination |
| Large repository clones timeout | Medium | Increase timeouts, use shallow clones, parallelize |
| LFS object storage costs | Medium | Configurable LFS depth, selective fetch |
| Authentication changes | High | Abstract auth layer, support multiple methods |
| Network instability | High | Retry logic, resume capability, checkpointing |
| GitHub/GitLab API changes | Medium | Pin library versions, monitor changelogs |
| Conflicting local changes | Medium | Branch protection, clear workflow documentation |

---

## Definition of Ready (For Each Sprint)

- [ ] User stories defined with acceptance criteria
- [ ] Test scenarios identified
- [ ] Dependencies available (libraries, access to test systems)
- [ ] Technical design reviewed
- [ ] Previous sprint completed and tested

## Definition of Done (For Each Sprint)

- [ ] All tests pass (unit, integration, E2E where applicable)
- [ ] Code coverage meets threshold (>80%)
- [ ] Code reviewed and approved
- [ ] Documentation updated
- [ ] No critical bugs
- [ ] Deployed/integrated with main branch
- [ ] Sprint demo completed

---

## Metrics to Track

- **Test Coverage**: Target >85%
- **Build Time**: Keep CI <5 minutes
- **Sync Performance**: Track time per repository size
- **Error Rate**: <5% of repos fail per run
- **Recovery Rate**: 100% of transient failures recover with retry

---

## Getting Started

1. Review and approve this roadmap
2. Set up development environment (Sprint 0)
3. Begin Sprint 1 with TDD approach
4. Hold sprint planning before each sprint
5. Hold sprint retrospective after each sprint
6. Adjust roadmap based on learnings

**Next Step**: Approve this roadmap and begin Sprint 0 setup!
