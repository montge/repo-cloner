# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**repo-cloner** is a Python-based tool for cloning and synchronizing Git repositories from GitLab (self-hosted or gitlab.com) to GitHub (Enterprise or github.com). It supports both automated GitHub Actions workflows and manual local execution.

**Key Features:**
- Full mirror clones with branch, tag, and commit history preservation
- Git LFS support
- GitLab group hierarchy mapping to GitHub naming strategies
- Air-gap environment support (export to S3/cloud storage)
- Scheduled sync via GitHub Actions or manual CLI execution
- Handles both cloud (gitlab.com, github.com) and on-premise deployments

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
# Clone single repository
python -m repo_cloner clone \
  --source https://gitlab.example.com/group/repo \
  --target https://github.com/org/repo \
  --gitlab-token $GITLAB_TOKEN \
  --github-token $GITHUB_TOKEN

# Sync from configuration file
python -m repo_cloner sync --config config.yml

# Export to archive
python -m repo_cloner export --config config.yml --output /path/to/archives

# Upload to S3
python -m repo_cloner upload --archives /path/to/archives --bucket my-bucket
```

## Key Design Decisions

### Technology Stack
- **Language**: Python 3.9+ (chosen over Node.js for superior Git/DevOps library ecosystem)
- **Git Operations**: GitPython + git CLI
- **API Clients**: PyGithub (GitHub), python-gitlab (GitLab)
- **Configuration**: YAML with Pydantic validation
- **Cloud Storage**: boto3 for S3-compatible storage
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

- **Unit Tests**: Mock external dependencies (API calls, git operations)
- **Integration Tests**: Use real Git operations with test repositories
- **E2E Tests**: Full workflow with actual GitLab/GitHub test accounts (use dedicated test orgs)
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
gitlab:
  url: https://gitlab.example.com
  token: ${GITLAB_TOKEN}

github:
  url: https://github.example.com
  token: ${GITHUB_TOKEN}

mapping_strategy: flatten

groups:
  - source: backend
    target_org: myorg
    lfs_enabled: true
    sync_strategy: mirror
```

## Current Status

**Phase**: Sprint 0 - Project Setup (Not yet started)

Refer to ROADMAP.md for detailed sprint breakdown and next steps.
