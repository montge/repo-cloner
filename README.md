# Universal Repository Cloner & Synchronization Tool

[![CI](https://github.com/montge/repo-cloner/actions/workflows/ci.yml/badge.svg)](https://github.com/montge/repo-cloner/actions/workflows/ci.yml)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![License: TBD](https://img.shields.io/badge/license-TBD-lightgrey.svg)](LICENSE)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](CONTRIBUTING.md)

A powerful, flexible tool for cloning, synchronizing, and archiving Git repositories across multiple platforms and storage backends. Perfect for migrations, air-gap deployments, and maintaining mirror repositories.

## Features

### Multi-Platform Support
- **GitLab** ↔ **GitHub** (bidirectional sync and migration)
- **GitLab** ↔ **GitLab** (instance-to-instance migration)
- **GitHub** ↔ **GitHub** (organization-to-organization migration)
- **Any Platform** ↔ **Cloud Storage** (archive/restore for air-gap environments)

### Storage Backends (6 Types)
- Local Filesystem (NFS, SMB mounts)
- AWS S3 (all regions)
- Azure Blob Storage (all regions)
- Google Cloud Storage (all regions/multi-regions)
- Oracle OCI Object Storage (all regions)
- S3-Compatible (MinIO, Ceph, DigitalOcean, etc.)

### Key Capabilities
✅ **Full Mirror Cloning** - All branches, tags, and commit history
✅ **Git LFS Support** - Large file storage with checksums
✅ **Bidirectional Sync** - Two-way synchronization with conflict detection
✅ **Air-Gap Deployments** - Full and incremental archives with dependencies
✅ **Dependency Management** - Fetch dependencies for 14+ language ecosystems
✅ **Version Tracking** - Git commit SHAs and SHA256 checksums for all artifacts
✅ **Multi-Cloud** - Upload archives to multiple cloud providers simultaneously
✅ **GitHub Actions** - Automated nightly sync workflows

## Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/montge/repo-cloner.git
cd repo-cloner

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Basic Usage

#### Clone GitLab → GitHub
```bash
# Set authentication tokens
export GITLAB_TOKEN="your_gitlab_token"
export GITHUB_TOKEN="your_github_token"

# Clone single repository
repo-cloner sync \
  --source https://gitlab.com/mygroup/myrepo \
  --target https://github.com/myorg/myrepo

# Clone entire group
repo-cloner sync \
  --source-group gitlab.com/mygroup \
  --target-org github.com/myorg \
  --config config.yml
```

#### Archive for Air-Gap
```bash
# Create full archive with dependencies
repo-cloner archive create \
  --source https://gitlab.com/mygroup/myrepo \
  --output /backups \
  --include-dependencies \
  --include-lfs

# Upload to multiple clouds
repo-cloner archive upload \
  --archive /backups/myrepo-full-20250109.tar.gz \
  --s3 s3://my-bucket/backups/ --region us-east-1 \
  --azure blob://my-account/backups/ --azure-region eastus \
  --gcs gs://my-bucket/backups/ --gcs-location us-central1

# Restore in air-gap environment
repo-cloner archive restore \
  --archive myrepo-full-20250109.tar.gz \
  --target https://github-enterprise.internal/myorg/myrepo \
  --install-dependencies
```

#### Bidirectional Sync
```bash
# Two-way sync with conflict detection
repo-cloner sync \
  --source https://gitlab.com/mygroup/myrepo \
  --target https://github.com/myorg/myrepo \
  --direction bidirectional \
  --conflict-strategy source-wins
```

## Configuration

Create a `config.yml` file:

```yaml
gitlab:
  url: https://gitlab.com
  token: ${GITLAB_TOKEN}

github:
  url: https://github.com
  token: ${GITHUB_TOKEN}

storage:
  - type: s3
    bucket: my-archives
    region: us-east-1
  - type: azure
    account: myaccount
    container: archives
    region: eastus

groups:
  - source: backend
    target_org: myorg
    lfs_enabled: true
    include_dependencies: true
    sync_strategy: mirror
```

## Supported Languages (Dependency Management)

Automatically detects and fetches dependencies for:

**Top 10 Languages 2025:**
- Python, Java, JavaScript/TypeScript, C++, C, C#/.NET, Go, PHP, Rust

**Additional Languages:**
- Ruby, Swift, Scala, Ada, Fortran

**Private Registries:**
Nexus, Artifactory, JFrog, Azure Artifacts, Verdaccio, Athens, Satis

## Documentation

- [Requirements](REQUIREMENTS.md) - Complete functional requirements
- [Roadmap](ROADMAP.md) - Development sprint plan (9 sprints)
- [Contributing](CONTRIBUTING.md) - How to contribute with TDD guidelines
- [Architecture](CLAUDE.md) - System design and technical decisions

## Development Status

✅ **Sprint 0 Complete** - Project setup and foundation
✅ **Sprint 1 Complete** - Core Git operations (clone, push, auth, CLI)
🚧 **Sprint 2-9 In Progress** - See [ROADMAP.md](ROADMAP.md) for detailed plan

**Current Features (Sprint 1):**
- GitLab → GitHub single repository sync
- Token-based authentication (env vars)
- Dry-run mode for safe testing
- CLI with `repo-cloner sync` command

## Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for:
- TDD workflow
- Development environment setup
- Running tests
- Code quality standards
- Pull request process

## License

[License TBD]

## Support

- **Issues**: https://github.com/montge/repo-cloner/issues
- **Discussions**: https://github.com/montge/repo-cloner/discussions

## Credits

Built with Python 3.11+ and powered by:
- GitPython, PyGithub, python-gitlab
- boto3 (AWS), azure-storage-blob, google-cloud-storage, oci (Oracle)
- Docker for test infrastructure

---

**Generated with [Claude Code](https://claude.com/claude-code)**
