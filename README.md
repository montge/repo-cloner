# Universal Repository Cloner

[![CI](https://github.com/montge/repo-cloner/actions/workflows/ci.yml/badge.svg)](https://github.com/montge/repo-cloner/actions/workflows/ci.yml)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A powerful Python tool for cloning, synchronizing, and archiving Git repositories across multiple platforms with comprehensive error handling, structured logging, and air-gap support.

## ✨ Features

### 🔄 Universal Repository Synchronization
- **Multi-Platform Support**: GitLab ↔ GitHub ↔ Cloud Storage
- **Bidirectional Sync**: Two-way synchronization with conflict detection
- **Full Mirror Clones**: Preserves all branches, tags, and commit history
- **Git LFS Support**: Handles large files seamlessly
- **Organization/Group Mapping**: Flexible mapping strategies (flatten, prefix, topics)

### 📦 Air-Gap & Archive Management
- **Full & Incremental Archives**: Complete or delta-based repository archives
- **Archive Chain Reconstruction**: Restore from incremental archive chains
- **Multi-Cloud Storage**: AWS S3, Azure Blob, GCS, Oracle OCI, S3-compatible (MinIO, Ceph)
- **Local Filesystem Support**: NFS, SMB mounts for offline scenarios
- **Integrity Verification**: SHA256 checksums for all artifacts

### 🔧 Production-Ready Infrastructure
- **Custom Exception Hierarchy**: Clear error messages with context
- **Retry Logic**: Exponential backoff with jitter for transient failures
- **Structured Logging**: JSON-formatted logs for monitoring systems (ELK, Splunk, Datadog)
- **GitHub Actions Integration**: Automated scheduled synchronization
- **Dry-Run Mode**: Preview operations before execution

### 🎯 Configuration & Flexibility
- **YAML Configuration**: Declarative configuration with validation
- **Environment Variable Substitution**: Secure credential management
- **Group Mapping Strategies**: Flatten, prefix, topics, custom
- **Repository Exclusions**: Fine-grained control over sync scope
- **Per-Repository Settings**: Override global settings per repo

## 🚀 Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/montge/repo-cloner.git
cd repo-cloner

# Create virtual environment
python3.11 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Verify installation
python -m repo_cloner --version
```

### Basic Usage

#### 1. Clone a Single Repository

```bash
python -m repo_cloner clone \
  --source https://gitlab.com/org/repo.git \
  --target https://github.com/org/repo.git \
  --source-token $GITLAB_TOKEN \
  --target-token $GITHUB_TOKEN
```

#### 2. Sync from Configuration File

Create `config.yml`:

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

Run sync:

```bash
export GITLAB_TOKEN="your-gitlab-token"
export GITHUB_TOKEN="your-github-token"

python -m repo_cloner sync --config config.yml
```

#### 3. Dry-Run Mode (Preview Changes)

```bash
python -m repo_cloner sync --config config.yml --dry-run --verbose
```

#### 4. Create Archive for Air-Gap Deployment

```bash
# Create full archive
python -m repo_cloner archive create \
  --source https://gitlab.com/org/repo \
  --output /path/to/archives \
  --type full

# Create incremental archive
python -m repo_cloner archive create \
  --source https://gitlab.com/org/repo \
  --output /path/to/archives \
  --type incremental \
  --base-archive repo-full-20250112.tar.gz
```

#### 5. Upload Archive to Cloud Storage

```bash
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
  --account my-storage-account

# Local Filesystem (NFS/SMB)
python -m repo_cloner archive upload \
  --archives /path/to/archives \
  --storage-type filesystem \
  --path /mnt/backup/repos
```

#### 6. Restore from Archive

```bash
python -m repo_cloner archive restore \
  --storage-type s3 \
  --bucket my-bucket \
  --archive-key backups/repo-full-20250112.tar.gz \
  --target https://github.com/org/repo \
  --target-token $GITHUB_TOKEN
```

## ⚙️ Configuration

### Complete Configuration Example

```yaml
# Source platforms (sync FROM)
sources:
  - type: gitlab
    url: https://gitlab.example.com
    token: ${GITLAB_TOKEN}
    groups:
      - backend
      - frontend
      - platform

# Target platforms (sync TO)
targets:
  # Primary target: GitHub
  - type: github
    url: https://github.com
    token: ${GITHUB_TOKEN}
    organization: myorg

  # Backup target: S3 archives
  - type: s3
    bucket: repo-backups
    region: us-east-1
    prefix: gitlab-mirrors/
    access_key: ${AWS_ACCESS_KEY_ID}
    secret_key: ${AWS_SECRET_ACCESS_KEY}

# Group/organization mapping strategy
mapping_strategy: flatten  # Options: flatten, prefix, topics, custom

# Synchronization settings
sync:
  mode: unidirectional        # Options: unidirectional, bidirectional
  direction: source_to_target # Options: source_to_target, target_to_source
  lfs_enabled: true
  conflict_resolution: fail   # Options: fail, source_wins, target_wins

# Archive settings
archive:
  type: incremental           # Options: full, incremental
  include_lfs: true
  retention_days: 90

# Repository-specific overrides
repositories:
  - source: backend/auth-service
    target: myorg/backend-auth-service
    sync_strategy: mirror
    lfs_enabled: true
    exclude_branches:
      - experimental/*
```

### Environment Variables

```bash
# GitLab
export GITLAB_TOKEN="glpat-xxxxxxxxxxxx"
export GITLAB_URL="https://gitlab.example.com"  # Optional, defaults to gitlab.com

# GitHub
export GITHUB_TOKEN="ghp_xxxxxxxxxxxx"
export GITHUB_URL="https://github.com"  # Optional, defaults to github.com

# AWS S3
export AWS_ACCESS_KEY_ID="AKIAXXXXXXXX"
export AWS_SECRET_ACCESS_KEY="xxxxxxxx"
export AWS_DEFAULT_REGION="us-east-1"

# Azure Blob Storage
export AZURE_STORAGE_CONNECTION_STRING="DefaultEndpointsProtocol=https;..."
export AZURE_STORAGE_ACCOUNT="mystorageaccount"

# Google Cloud Storage
export GCS_SERVICE_ACCOUNT_JSON='{"type": "service_account", ...}'

# Oracle OCI
export OCI_CONFIG_FILE="~/.oci/config"
```

## 🤖 GitHub Actions Integration

### Scheduled Synchronization

Create `.github/workflows/sync.yml`:

```yaml
name: Repository Synchronization

on:
  schedule:
    - cron: "0 2 * * *"  # Daily at 2 AM UTC
  workflow_dispatch:     # Manual trigger

jobs:
  sync:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'

      - name: Install dependencies
        run: |
          pip install -r requirements.txt

      - name: Run synchronization
        env:
          GITLAB_TOKEN: ${{ secrets.GITLAB_TOKEN }}
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: |
          python -m repo_cloner sync --config config.yml --verbose

      - name: Upload logs on failure
        if: failure()
        uses: actions/upload-artifact@v4
        with:
          name: sync-logs
          path: logs/
          retention-days: 7
```

Configure secrets in **Settings > Secrets and variables > Actions**:
- `GITLAB_TOKEN`: GitLab Personal Access Token (scopes: `read_repository`, `api`)
- `GITHUB_TOKEN`: GitHub Personal Access Token (scopes: `repo`, `workflow`)
- Optional cloud storage credentials (AWS, Azure, GCS)

See [examples/github-actions/README.md](examples/github-actions/README.md) for detailed setup instructions.

## 🏗️ Architecture

### High-Level Design

```
┌─────────────────────────────────────────────────────────────┐
│                     repo-cloner CLI                          │
├─────────────────────────────────────────────────────────────┤
│  Configuration │ Authentication │ Logging │ Error Handling  │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────────┐   ┌──────────────┐   ┌──────────────┐    │
│  │   GitLab     │   │   GitHub     │   │   Storage    │    │
│  │   Client     │   │   Client     │   │   Backends   │    │
│  └──────────────┘   └──────────────┘   └──────────────┘    │
│         │                   │                   │            │
│         └───────────────────┴───────────────────┘            │
│                         │                                    │
│              ┌──────────────────────┐                        │
│              │   Sync Engine        │                        │
│              │   - Detect changes   │                        │
│              │   - Conflict detect  │                        │
│              │   - Retry logic      │                        │
│              └──────────────────────┘                        │
│                         │                                    │
│              ┌──────────────────────┐                        │
│              │   Git Operations     │                        │
│              │   - Clone mirror     │                        │
│              │   - Push mirror      │                        │
│              │   - LFS handling     │                        │
│              └──────────────────────┘                        │
│                         │                                    │
│              ┌──────────────────────┐                        │
│              │   Archive Manager    │                        │
│              │   - Full archives    │                        │
│              │   - Incremental      │                        │
│              │   - Chain restore    │                        │
│              └──────────────────────┘                        │
└─────────────────────────────────────────────────────────────┘
```

### Core Components

- **Configuration Loader**: YAML parsing, validation, env var substitution
- **API Clients**: GitLab (`python-gitlab`), GitHub (`PyGithub`)
- **Git Client**: Mirror clones, LFS support (GitPython + git CLI)
- **Sync Engine**: Change detection, conflict resolution, retry logic
- **Archive Manager**: Full/incremental archives, chain reconstruction
- **Storage Backends**: S3 (boto3), Azure (azure-storage-blob), GCS (google-cloud-storage), OCI (oci), Filesystem
- **Logging System**: JSON formatter, contextual logging, thread-safe
- **Error Handling**: Custom exception hierarchy, retry with exponential backoff

## 🎓 Advanced Usage

### Bidirectional Synchronization

```yaml
sync:
  mode: bidirectional
  conflict_resolution: fail  # Stop on conflicts for manual review

# Or use source_wins / target_wins for automatic resolution
```

### Multi-Target Deployment

```yaml
targets:
  # Production GitHub
  - type: github
    url: https://github.com
    token: ${GITHUB_TOKEN}
    organization: production

  # Backup S3
  - type: s3
    bucket: prod-backups
    region: us-west-2

  # DR Site Azure
  - type: azure
    container: dr-repos
    account: drstorageaccount
```

### Group Mapping Strategies

**Flatten** (default):
- GitLab: `backend/auth/service` → GitHub: `backend-auth-service`

**Prefix**:
- GitLab: `backend/auth/service` → GitHub: `be_service` (drop parent groups)

**Topics**:
- GitLab: `backend/auth/service` → GitHub: `service` with topics `["backend", "auth"]`

### Custom Retry Configuration

```python
from repo_cloner.retry import retry, RetryConfig

# Custom retry for API calls
@retry(max_retries=5, initial_delay=2.0, backoff_factor=2.0, jitter=True)
def fetch_repositories():
    return gitlab_client.list_projects()

# Programmatic retry
config = RetryConfig(max_retries=10, initial_delay=1.0, max_delay=120.0)
result = retry_with_backoff(api_call, config=config)
```

### Structured Logging

```python
from repo_cloner.logging_config import configure_logging, get_logger, log_context

# Configure JSON logging
logger = configure_logging(level="INFO", json_format=True, log_file="sync.log")

# Module-specific logger
logger = get_logger("sync_engine")

# Contextual logging
with log_context(session_id="abc123", operation="clone"):
    logger.info("Starting clone", extra={"repository": "gitlab.com/org/repo"})
    # Logs include: session_id, operation, repository

# JSON output:
# {"timestamp": "2025-10-12T02:30:00", "level": "INFO",
#  "logger": "repo_cloner.sync_engine", "message": "Starting clone",
#  "session_id": "abc123", "operation": "clone",
#  "repository": "gitlab.com/org/repo"}
```

## 🔍 Troubleshooting

### Common Issues

**1. Authentication Failures**

```
Error: AuthenticationError: Authentication failed for GitLab
```

**Solution**:
- Verify token hasn't expired
- Check token scopes (GitLab: `read_repository`, `api`; GitHub: `repo`, `workflow`)
- Ensure environment variables are set correctly

**2. Network Timeouts**

```
Error: NetworkError: Connection timeout (retryable: True)
```

**Solution**:
- Automatic retry with exponential backoff will handle transient failures
- Increase timeout if needed (large repositories)
- Check network connectivity to Git platforms

**3. LFS Objects Missing**

```
Error: Git LFS objects not found
```

**Solution**:
- Install git-lfs: `git lfs install`
- Enable LFS in configuration: `lfs_enabled: true`
- Ensure LFS credentials are configured

**4. Archive Chain Broken**

```
Error: ArchiveError: Parent archive not found
```

**Solution**:
- Verify parent archive exists in storage
- Check manifest references correct parent filename
- Restore from full archive if chain is incomplete

**5. Sync Conflicts (Bidirectional)**

```
Error: SyncConflictError: Divergent branches detected
```

**Solution**:
- Review conflicts manually: check `branch`, `source_commit`, `target_commit` in error
- Set `conflict_resolution: source_wins` or `target_wins` for automatic resolution
- Use unidirectional sync if conflicts are problematic

### Enable Debug Logging

```bash
# Verbose CLI output
python -m repo_cloner sync --config config.yml --verbose

# Debug-level logging (if implemented)
python -m repo_cloner sync --config config.yml --log-level DEBUG
```

## 💻 Development

### Setup Development Environment

```bash
# Clone repository
git clone https://github.com/montge/repo-cloner.git
cd repo-cloner

# Create virtual environment
python3.11 -m venv .venv
source .venv/bin/activate

# Install development dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Install pre-commit hooks
pre-commit install
```

### Run Tests

```bash
# All tests
pytest tests/ -v

# Unit tests only (fast)
pytest tests/unit/ -v

# Integration tests (requires Docker)
docker-compose -f docker-compose.test.yml up -d
pytest tests/integration/ -v

# With coverage
pytest tests/ --cov=src/repo_cloner --cov-report=html
```

### Code Quality

```bash
# Format code
black src/ tests/
isort src/ tests/

# Lint
flake8 src/ tests/

# Type check
mypy src/ --strict

# Run all pre-commit hooks
pre-commit run --all-files
```

## 📚 Documentation

- **[REQUIREMENTS.md](REQUIREMENTS.md)**: Functional and non-functional requirements
- **[ROADMAP.md](ROADMAP.md)**: Development roadmap with sprint-based plan
- **[CLAUDE.md](CLAUDE.md)**: Context for Claude Code (development guide)
- **[examples/github-actions/README.md](examples/github-actions/README.md)**: GitHub Actions setup guide
- **[examples/configs/](examples/configs/)**: Example configuration files

## 📊 Project Status

### Completed Sprints

- ✅ **Sprint 5**: Configuration & Group Mapping (51/51 tests)
- ✅ **Sprint 6**: Air-Gap Support & Archive Management (18/18 tests)
- ✅ **Sprint 7**: GitHub Actions Integration (10/10 tests)
- 🟡 **Sprint 8**: Error Handling & Logging (53/53 tests) - **In Progress**
  - ✅ Phase 1: Exception hierarchy & retry logic (34 tests)
  - ✅ Phase 2: Structured logging (19 tests)
  - ⏳ Phase 3: Documentation (in progress)

### Test Coverage

- **Total Tests**: 132+ passing
- **Code Coverage**: >80% overall
- **CI/CD**: All checks passing (black, isort, flake8, mypy)
- **Latest CI Run**: ✅ Success

### Roadmap

**Current Sprint (Sprint 8):**
- ✅ Custom exception hierarchy with context storage
- ✅ Retry logic with exponential backoff and jitter
- ✅ Structured logging with JSON formatting
- ⏳ Comprehensive documentation
- ⏭️ Notification system (optional, may defer)

**Upcoming Enhancements:**
- Graceful degradation (continue after individual repo failures)
- State recovery (resume from last successful sync)
- Dependency fetching for air-gap deployments (Sprint 9)
- Web dashboard for monitoring

See [ROADMAP.md](ROADMAP.md) for detailed development plan.

## 🤝 Contributing

We welcome contributions! Please follow these guidelines:

1. **Fork the repository** and create a feature branch
2. **Follow TDD**: Write tests first, then implement features
3. **Code quality**: Run `black`, `isort`, `flake8`, `mypy` before committing
4. **Tests**: Ensure all tests pass (`pytest tests/ -v`)
5. **Documentation**: Update README and relevant docs
6. **Commit messages**: Use descriptive commit messages following the project style

See [CONTRIBUTING.md](CONTRIBUTING.md) for detailed guidelines (to be created).

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

- **Issues**: [GitHub Issues](https://github.com/montge/repo-cloner/issues)
- **Discussions**: [GitHub Discussions](https://github.com/montge/repo-cloner/discussions)
- **Documentation**: Check the `docs/` directory and examples

## 🙏 Acknowledgments

- Built with [GitPython](https://github.com/gitpython-developers/GitPython), [PyGithub](https://github.com/PyGithub/PyGithub), [python-gitlab](https://github.com/python-gitlab/python-gitlab)
- Cloud storage: [boto3](https://github.com/boto/boto3), [azure-storage-blob](https://github.com/Azure/azure-sdk-for-python), [google-cloud-storage](https://github.com/googleapis/python-storage), [oci](https://github.com/oracle/oci-python-sdk)
- Developed with [Claude Code](https://claude.com/claude-code) following Test-Driven Development (TDD)

---

**repo-cloner** - Universal repository synchronization for GitOps workflows, air-gap deployments, and multi-platform repository management.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
