# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**repo-cloner** is a universal Python-based tool for cloning and synchronizing Git repositories between GitLab, GitHub, and multiple cloud storage backends. It supports bidirectional synchronization, air-gap workflows, and both automated GitHub Actions and manual local execution.

**Key Features:**
- Universal repository synchronization (GitLab ↔ GitHub ↔ Cloud Storage)
- Bidirectional sync with conflict detection
- Full mirror clones with branch, tag, and commit history preservation
- Git LFS support
- Organization/group hierarchy mapping between platforms
- Air-gap environment support with full and incremental archives
- Multi-cloud and local filesystem storage support
- Scheduled sync via GitHub Actions or manual CLI execution
- Handles both cloud (gitlab.com, github.com) and on-premise deployments

**Supported Paths:**
- GitLab ↔ GitHub (cross-platform migration and sync)
- GitLab ↔ GitLab, GitHub ↔ GitHub (instance/org migration)
- Any platform ↔ Storage (archive/restore for air-gap)

**Storage Backends:**
- Local Filesystem (including NFS, SMB mounts)
- AWS S3 (all regions)
- Azure Blob Storage (all regions)
- Google Cloud Storage (all regions/multi-regions)
- Oracle OCI Object Storage (all regions)
- S3-Compatible (MinIO, Ceph, etc.)

## Development Approach

This project follows **Test-Driven Development (TDD)**:
1. Write failing tests first for each feature
2. Implement minimum code to pass tests
3. Refactor while keeping tests green
4. Maintain >80% code coverage

## Project Structure (To Be Implemented)

```
repo-cloner/
├── src/
│   └── repo_cloner/
│       ├── __init__.py
│       ├── cli.py              # CLI entry point
│       ├── config.py           # Configuration management
│       ├── git_client.py       # Git operations
│       ├── gitlab_client.py    # GitLab API
│       ├── github_client.py    # GitHub API
│       ├── sync_engine.py      # Synchronization logic
│       ├── group_mapper.py     # Group/org mapping
│       ├── archive_manager.py  # Export/import archives
│       ├── storage_client.py   # S3/cloud storage
│       └── auth.py             # Authentication
├── tests/
│   ├── unit/
│   ├── integration/
│   └── e2e/
├── docs/
├── examples/
│   └── config.example.yml
├── .github/
│   └── workflows/
│       └── sync.yml            # GitHub Actions workflow
├── REQUIREMENTS.md             # Detailed requirements
├── ROADMAP.md                  # Sprint-based development plan
└── pyproject.toml              # Poetry configuration
```

## Commands (Once Implemented)

### Development
```bash
# Install dependencies
poetry install

# Run tests
pytest tests/ -v --cov=src/repo_cloner --cov-report=html

# Run specific test
pytest tests/unit/test_git_client.py::test_clone_mirror -v

# Code quality
black src/ tests/
flake8 src/ tests/
mypy src/

# Run pre-commit hooks
pre-commit run --all-files
```

### CLI Usage
```bash
# Clone single repository (any platform to any platform)
python -m repo_cloner clone \
  --source https://gitlab.example.com/group/repo \
  --target https://github.com/org/repo \
  --source-token $SOURCE_TOKEN \
  --target-token $TARGET_TOKEN

# Sync from configuration file
python -m repo_cloner sync --config config.yml

# Bidirectional sync
python -m repo_cloner sync --config config.yml --bidirectional

# Export to full archive
python -m repo_cloner archive create \
  --source https://gitlab.example.com/group/repo \
  --output /path/to/archives \
  --type full

# Export incremental archive
python -m repo_cloner archive create \
  --source https://gitlab.example.com/group/repo \
  --output /path/to/archives \
  --type incremental \
  --base-archive repo-full-20250109.tar.gz

# Upload archives to storage backend
# AWS S3
python -m repo_cloner archive upload \
  --archives /path/to/archives \
  --storage-type s3 \
  --bucket my-bucket \
  --region us-east-1 \
  --prefix backups/

# Azure Blob Storage
python -m repo_cloner archive upload \
  --archives /path/to/archives \
  --storage-type azure \
  --container my-container \
  --account my-storage-account \
  --region eastus

# Google Cloud Storage
python -m repo_cloner archive upload \
  --archives /path/to/archives \
  --storage-type gcs \
  --bucket my-bucket \
  --location us-central1

# Oracle OCI Object Storage
python -m repo_cloner archive upload \
  --archives /path/to/archives \
  --storage-type oci \
  --bucket my-bucket \
  --namespace my-namespace \
  --region us-ashburn-1

# Local Filesystem
python -m repo_cloner archive upload \
  --archives /path/to/archives \
  --storage-type filesystem \
  --path /mnt/backup/repos

# Restore from storage archive
python -m repo_cloner archive restore \
  --storage-type s3 \
  --bucket my-bucket \
  --region us-east-1 \
  --archive-key backups/repo-full-20250109.tar.gz \
  --incremental backups/repo-inc-*.tar.gz \
  --target https://github.com/org/repo \
  --target-token $GITHUB_TOKEN

# List available archives
python -m repo_cloner archive list \
  --storage-type s3 \
  --bucket my-bucket \
  --region us-east-1 \
  --prefix backups/
```

## Key Design Decisions

### Technology Stack
- **Language**: Python 3.9+ (chosen over Node.js for superior Git/DevOps library ecosystem)
- **Git Operations**: GitPython + git CLI
- **API Clients**: PyGithub (GitHub), python-gitlab (GitLab)
- **Configuration**: YAML with Pydantic validation
- **Cloud Storage SDKs**:
  - boto3 (AWS S3)
  - azure-storage-blob (Azure Blob Storage)
  - google-cloud-storage (GCS)
  - oci (Oracle Cloud Infrastructure)
- **CLI Framework**: argparse or click
- **Testing**: pytest with pytest-cov

### GitLab Group Mapping Strategies
GitLab supports nested groups (e.g., `backend/auth/service`), but GitHub has flat organization structure. Supported strategies:

1. **Flatten**: `backend-auth-service`
2. **Prefix**: `be_service` (configurable prefix, drop parent groups)
3. **Topics**: Use GitHub topics/labels to represent hierarchy
4. **Custom**: User-defined mapping in configuration

### Authentication
- GitLab: Personal Access Token (PAT) preferred, username/password for legacy
- GitHub: Personal Access Token or GitHub App credentials
- Credentials via environment variables only (never logged or stored in plain text)

### Synchronization Strategy
- **Full Mirror**: Use `git push --mirror` to overwrite all refs
- **Incremental**: Fetch only new commits/branches/tags
- **State Tracking**: JSON file (or SQLite for scale) to track last sync timestamp and SHAs
- **Conflict Handling**: Fail fast by default, provide `--force` override

### Air-Gap Support
- Export repositories to tar.gz archives including LFS objects
- Generate JSON manifest describing archive contents
- Upload to S3-compatible storage (AWS S3, MinIO, etc.)
- Import functionality to restore from archives

## Important Constraints

- Must preserve complete Git history (no squashing or rebasing)
- Must handle large repositories (multi-GB) and LFS objects
- Must be resumable after network failures
- No wiki/issue/PR migration (repositories only)
- Must run in GitHub Actions and locally with same configuration

## Testing Requirements

### Testing Infrastructure (No Cloud Accounts Needed!)

**Cloud Storage Emulators:**
- **AWS S3**: LocalStack (Docker) or moto (Python mocking)
- **Azure Blob**: Azurite (official Microsoft emulator)
- **GCS**: fake-gcs-server (Docker)
- **OCI**: unittest.mock (no official emulator)
- **S3-Compatible**: MinIO (Docker)
- **Filesystem**: pytest tmp_path fixtures

**Git Platform Emulators:**
- **GitLab**: GitLab CE Docker container or responses/requests-mock for API
- **GitHub**: responses library for API mocking, or Gitea/Gogs for Git server
- **Git Operations**: Local repositories in temporary directories

**Test Layers:**
- **Unit Tests**: Fast, in-memory mocks (moto, responses, unittest.mock)
- **Integration Tests**: Docker containers (LocalStack, Azurite, MinIO, GitLab CE, Gitea)
- **E2E Tests**: Optional real services in CI/CD only

**Key Testing Tools:**
```bash
# Start all emulators for integration testing
docker-compose -f docker-compose.test.yml up -d

# Run unit tests (fast, mocked)
pytest tests/unit/ -v

# Run integration tests (with Docker emulators)
pytest tests/integration/ -v

# Run all tests with coverage
pytest tests/ -v --cov=src/repo_cloner --cov-report=html
```

### Coverage Requirements
- **Unit Tests**: Mock external dependencies (API calls, git operations)
- **Integration Tests**: Use Docker emulators and real Git operations
- **E2E Tests**: Optional with actual GitLab/GitHub test accounts
- **Coverage Target**: >80% overall, >90% for core logic

## Documentation

- **REQUIREMENTS.md**: Comprehensive functional and non-functional requirements
- **ROADMAP.md**: 8-sprint development plan with TDD approach
- Each sprint has specific user stories, deliverables, and test strategies

## Common Development Patterns

### TDD Workflow
```python
# 1. Write failing test
def test_clone_mirror_preserves_branches():
    client = GitClient()
    client.clone_mirror("https://source.git", "/tmp/repo")
    branches = client.list_branches("/tmp/repo")
    assert "main" in branches
    assert "develop" in branches

# 2. Run test (should fail)
# 3. Implement feature
# 4. Run test (should pass)
# 5. Refactor if needed
```

### Configuration Example
```yaml
# Universal source/target configuration
sources:
  - type: gitlab
    url: https://gitlab.example.com
    token: ${GITLAB_TOKEN}
    groups:
      - backend
      - frontend

targets:
  - type: github
    url: https://github.example.com
    token: ${GITHUB_TOKEN}
    organization: myorg

  # Multiple storage backends can be configured
  - type: s3
    bucket: my-archives
    region: us-east-1
    prefix: repo-backups/
    access_key: ${AWS_ACCESS_KEY_ID}
    secret_key: ${AWS_SECRET_ACCESS_KEY}

  - type: azure
    container: repo-backups
    account: mystorageaccount
    region: eastus
    connection_string: ${AZURE_STORAGE_CONNECTION_STRING}

  - type: gcs
    bucket: my-repo-archives
    location: us-central1
    service_account_json: ${GCS_SERVICE_ACCOUNT_JSON}

  - type: oci
    bucket: repo-archives
    namespace: my-namespace
    region: us-ashburn-1
    config_file: ~/.oci/config

  - type: filesystem
    path: /mnt/backup/repos

# Mapping configuration
mapping_strategy: flatten  # flatten, prefix, topics, custom

# Sync configuration
sync:
  mode: unidirectional  # unidirectional, bidirectional
  direction: source_to_target  # source_to_target, target_to_source
  schedule: "0 2 * * *"  # cron format
  lfs_enabled: true
  conflict_resolution: fail  # fail, source_wins, target_wins

# Archive configuration
archive:
  type: full  # full, incremental
  include_lfs: true
  compression: gzip
  base_archive: repo-full-20250109.tar.gz  # for incremental
  retention_days: 90  # optional: auto-delete old archives

# Repository-specific overrides
repositories:
  - source: backend/auth-service
    target: myorg/backend-auth-service
    sync_strategy: mirror
    archive_type: incremental
    storage_backends:  # can specify per-repo storage
      - s3
      - azure
```

## Current Status

**Phase**: Sprint 0 - Project Setup (Not yet started)

Refer to ROADMAP.md for detailed sprint breakdown and next steps.
