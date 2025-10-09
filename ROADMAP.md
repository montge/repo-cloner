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
- [ ] Poetry/pip requirements setup
- [ ] Pre-commit hooks (black, flake8, mypy)
- [ ] pytest configuration with coverage
- [ ] GitHub Actions CI workflow (run tests on PR)
- [ ] README with setup instructions
- [ ] CONTRIBUTING.md with TDD guidelines
- [ ] .gitignore configured
- [ ] Development branch strategy documented

### Test Strategy
- Unit tests for utility functions
- Integration test framework scaffold

### Dependencies
- Python 3.9+
- pytest, pytest-cov
- black, flake8, mypy
- GitPython
- PyGithub, python-gitlab

### Definition of Done
- ✅ Project builds successfully
- ✅ CI pipeline runs tests
- ✅ Code quality checks pass
- ✅ Documentation complete

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

### Deliverables
- [ ] `GitClient` class for Git operations
  - `clone_mirror(source_url, local_path)`
  - `push_mirror(local_path, target_url)`
- [ ] `AuthManager` class for credential handling
  - Support for GitLab PAT
  - Support for GitHub PAT
  - Environment variable injection
- [ ] Configuration model (Python dataclass/Pydantic)
- [ ] CLI entry point with basic arguments

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

5. **Integration Test**: `test_full_clone_and_push_flow()`
   - Use test repositories on GitLab/GitHub

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

### Deliverables
- [ ] `GitLabClient` class
  - `list_projects(group_path)`
  - `get_project_details(project_id)`
  - Support for gitlab.com and self-hosted
- [ ] `GitHubClient` class
  - `create_repository(org, name, description)`
  - `repository_exists(org, name)`
  - Support for github.com and GitHub Enterprise
- [ ] `GroupMapper` class
  - Basic naming strategy (flatten with separator)
  - Configuration for custom mappings
- [ ] Configuration file format (YAML)

### Test Strategy (TDD)
**Write tests FIRST:**

1. **Test**: `test_gitlab_client_lists_projects()`
   - Mock API responses
   - **Then**: Implement `list_projects()`

2. **Test**: `test_gitlab_client_handles_pagination()`
   - **Then**: Implement pagination logic

3. **Test**: `test_github_client_creates_repo()`
   - Mock API responses
   - **Then**: Implement `create_repository()`

4. **Test**: `test_github_client_checks_existence()`
   - **Then**: Implement `repository_exists()`

5. **Test**: `test_group_mapper_flattens_hierarchy()`
   - Input: `group/subgroup/repo`
   - Expected: `group-subgroup-repo`
   - **Then**: Implement mapping logic

6. **Integration Test**: `test_discover_and_create_repos()`
   - Use test GitLab group and GitHub org

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
- **US-3.1**: As a user, I can sync updates from GitLab to GitHub
- **US-3.2**: As a user, I can detect new branches and tags
- **US-3.3**: As a system, I track when each repository was last synced

### Deliverables
- [ ] `SyncEngine` class
  - `sync_repository(source, target, strategy)`
  - `detect_changes(source, local_mirror)`
  - `handle_force_pushes()`
- [ ] State persistence (JSON or SQLite)
  - Store last sync timestamp per repo
  - Store last commit SHA per branch
- [ ] Sync strategies
  - Full mirror (overwrite everything)
  - Incremental (fetch only new refs)
- [ ] Conflict detection and handling

### Test Strategy (TDD)
**Write tests FIRST:**

1. **Test**: `test_sync_detects_new_commits()`
   - Set up repo with initial state
   - Add commits
   - **Then**: Implement change detection

2. **Test**: `test_sync_handles_new_branches()`
   - **Then**: Implement branch sync logic

3. **Test**: `test_sync_handles_deleted_branches()`
   - **Then**: Implement deletion propagation

4. **Test**: `test_state_persists_last_sync_time()`
   - **Then**: Implement state storage

5. **Test**: `test_sync_handles_force_push()`
   - **Then**: Implement force push detection and handling

6. **Integration Test**: `test_full_sync_cycle()`
   - Initial clone → make changes → sync → verify target

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
- **US-6.1**: As a user, I can export synced repositories to tar.gz archives
- **US-6.2**: As a user, I can upload archives to S3-compatible storage
- **US-6.3**: As a user, I can import repositories from archives
- **US-6.4**: As a user, I receive a manifest file describing archived content

### Deliverables
- [ ] `ArchiveManager` class
  - `create_archive(repo_path, output_path, include_lfs)`
  - `extract_archive(archive_path, output_path)`
- [ ] `StorageClient` class
  - S3 backend (using boto3)
  - Pluggable interface for other backends
  - `upload_archive(archive_path, bucket, key)`
  - `download_archive(bucket, key, output_path)`
- [ ] Manifest generation
  ```json
  {
    "export_date": "2025-10-09T12:00:00Z",
    "repositories": [
      {
        "name": "backend-auth-service",
        "source_url": "https://gitlab.example.com/backend/auth-service",
        "size_bytes": 104857600,
        "lfs_included": true,
        "branches": ["main", "develop"],
        "tags": ["v1.0.0", "v1.1.0"]
      }
    ]
  }
  ```
- [ ] CLI commands: `export`, `import`, `upload`, `download`

### Test Strategy (TDD)
**Write tests FIRST:**

1. **Test**: `test_create_archive_from_repo()`
   - **Then**: Implement tar.gz creation

2. **Test**: `test_archive_includes_lfs_objects()`
   - **Then**: Implement LFS bundling

3. **Test**: `test_extract_archive_restores_repo()`
   - **Then**: Implement extraction

4. **Test**: `test_s3_upload_succeeds()`
   - Use moto for S3 mocking
   - **Then**: Implement S3 upload

5. **Test**: `test_manifest_generation()`
   - **Then**: Implement manifest creation

6. **Test**: `test_manifest_validation_on_import()`
   - **Then**: Implement validation logic

7. **Integration Test**: `test_full_export_upload_download_import_cycle()`
   - End-to-end flow

### Technical Decisions
- Use `tarfile` module for archives
- Use boto3 for S3 (support S3-compatible endpoints)
- Compression: gzip by default, configurable
- Archive naming: `{repo-name}-{timestamp}.tar.gz`
- Manifest: JSON format, stored alongside archives

### Definition of Done
- ✅ Archives create successfully with all repo data
- ✅ LFS objects included when specified
- ✅ S3 upload/download works with real AWS/MinIO
- ✅ Manifest accurately describes archive contents
- ✅ Import restores repository to working state

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

## Post-Sprint: Optional Enhancements

### Future Considerations (Not in Initial Roadmap)
- **Web Dashboard**: Monitor sync status via web UI
- **Metrics & Monitoring**: Prometheus/Grafana integration
- **Bi-directional Sync**: GitHub → GitLab
- **Wiki Migration**: Clone GitLab wikis
- **Issue Migration**: Optionally migrate issues (complex, separate project)
- **Advanced Conflict Resolution**: Merge strategies, interactive resolution
- **Multi-cloud Support**: Azure Blob Storage, GCP Cloud Storage
- **Performance Optimization**: Rust rewrite for core Git operations
- **Plugin System**: Allow custom pre/post-sync hooks

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
