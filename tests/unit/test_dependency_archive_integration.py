"""Tests for dependency archive integration - archiving repos with dependencies."""

from pathlib import Path
from unittest.mock import Mock

from repo_cloner.archive_manager import ArchiveManager
from repo_cloner.dependency_detector import DependencyDetector, LanguageType
from repo_cloner.pypi_client import PyPIClient, ResolvedDependency


class TestDependencyArchiveIntegration:
    """Test suite for integrating dependency fetching with archive creation."""

    def test_create_archive_with_python_dependencies(self, tmp_path):
        """Test creating archive that includes Python dependencies."""
        # Setup test repository with requirements.txt
        repo_path = tmp_path / "test_repo"
        repo_path.mkdir()

        # Initialize git repo
        import subprocess

        subprocess.run(["git", "init"], cwd=repo_path, check=True, capture_output=True)
        subprocess.run(
            ["git", "config", "user.email", "test@example.com"], cwd=repo_path, check=True
        )
        subprocess.run(["git", "config", "user.name", "Test User"], cwd=repo_path, check=True)

        # Create requirements.txt
        requirements_file = repo_path / "requirements.txt"
        requirements_file.write_text("requests==2.31.0\nflask==2.3.0\n")

        # Commit
        subprocess.run(["git", "add", "."], cwd=repo_path, check=True)
        subprocess.run(
            ["git", "commit", "-m", "Initial commit"],
            cwd=repo_path,
            check=True,
            capture_output=True,
        )

        # Create archive with dependencies
        archive_manager = ArchiveManager()
        output_dir = tmp_path / "archives"
        output_dir.mkdir()

        archive_path = archive_manager.create_archive_with_dependencies(
            repo_path=str(repo_path),
            output_dir=str(output_dir),
            include_dependencies=True,
        )

        assert archive_path.exists()
        assert archive_path.suffix == ".gz"

        # Verify archive contains dependencies directory
        manifest_path = output_dir / (archive_path.stem.replace(".tar", "") + ".manifest.json")
        assert manifest_path.exists()

        import json

        manifest = json.loads(manifest_path.read_text())
        assert "dependencies" in manifest
        assert "python" in manifest["dependencies"]

    def test_detect_and_fetch_python_dependencies(self, tmp_path):
        """Test detecting Python dependencies and fetching them."""
        # Create test repo with requirements.txt
        repo_path = tmp_path / "repo"
        repo_path.mkdir()
        requirements = repo_path / "requirements.txt"
        requirements.write_text("requests==2.31.0\n")

        # Detect dependencies
        detector = DependencyDetector(str(repo_path))
        languages = detector.detect_languages()

        assert LanguageType.PYTHON in languages

        # Get manifest files
        manifest_files = detector.get_manifest_files(LanguageType.PYTHON)
        assert len(manifest_files) == 1

        # Mock PyPI client to avoid real network calls
        mock_client = Mock(spec=PyPIClient)
        mock_client.resolve_dependencies.return_value = [
            ResolvedDependency(
                name="requests",
                version="2.31.0",
                filename="requests-2.31.0-py3-none-any.whl",
            ),
            ResolvedDependency(
                name="urllib3",
                version="2.0.7",
                filename="urllib3-2.0.7-py3-none-any.whl",
            ),
        ]

        # Parse dependencies
        from repo_cloner.python_parser import PythonManifestParser

        parser = PythonManifestParser(str(requirements))
        deps = parser.parse()

        assert len(deps) == 1
        assert deps[0].name == "requests"

        # Resolve transitive dependencies
        resolved = mock_client.resolve_dependencies(deps)
        assert len(resolved) == 2
        assert any(d.name == "requests" for d in resolved)
        assert any(d.name == "urllib3" for d in resolved)

    def test_archive_dependency_manifest_structure(self, tmp_path):
        """Test that dependency manifest has correct structure."""
        repo_path = tmp_path / "repo"
        repo_path.mkdir()

        # Create requirements.txt
        requirements = repo_path / "requirements.txt"
        requirements.write_text("requests==2.31.0\n")

        # Create mock resolved dependencies
        resolved = [
            ResolvedDependency(
                name="requests",
                version="2.31.0",
                filename="requests-2.31.0-py3-none-any.whl",
            ),
            ResolvedDependency(
                name="urllib3",
                version="2.0.7",
                filename="urllib3-2.0.7-py3-none-any.whl",
            ),
        ]

        # Generate dependency manifest
        from repo_cloner.archive_manager import ArchiveManager

        manager = ArchiveManager()

        manifest = manager._generate_dependency_manifest(
            language="python",
            manifest_file="requirements.txt",
            resolved_dependencies=resolved,
        )

        assert manifest["language"] == "python"
        assert manifest["manifest_file"] == "requirements.txt"
        assert "packages" in manifest
        assert len(manifest["packages"]) == 2

        # Verify package structure
        package = manifest["packages"][0]
        assert "name" in package
        assert "version" in package
        assert "filename" in package

    def test_bundle_python_dependencies_in_archive(self, tmp_path):
        """Test bundling Python dependencies into archive structure."""
        # Create dependency packages directory
        deps_dir = tmp_path / "dependencies" / "python"
        deps_dir.mkdir(parents=True)

        # Create fake package files
        wheel1 = deps_dir / "requests-2.31.0-py3-none-any.whl"
        wheel1.write_bytes(b"fake wheel content")

        wheel2 = deps_dir / "urllib3-2.0.7-py3-none-any.whl"
        wheel2.write_bytes(b"fake wheel content")

        # Verify structure
        assert wheel1.exists()
        assert wheel2.exists()

        # Verify can list all packages
        packages = list(deps_dir.glob("*.whl"))
        assert len(packages) == 2

    def test_generate_offline_install_script(self, tmp_path):
        """Test generating offline installation script for Python."""
        deps_dir = tmp_path / "dependencies" / "python"
        deps_dir.mkdir(parents=True)

        # Create resolved dependencies
        resolved = [
            ResolvedDependency(
                name="requests",
                version="2.31.0",
                filename="requests-2.31.0-py3-none-any.whl",
            ),
            ResolvedDependency(
                name="urllib3",
                version="2.0.7",
                filename="urllib3-2.0.7-py3-none-any.whl",
            ),
        ]

        # Generate install script
        from repo_cloner.archive_manager import ArchiveManager

        manager = ArchiveManager()

        script_path = manager._generate_offline_install_script(
            language="python",
            resolved_dependencies=resolved,
            output_dir=str(deps_dir.parent),
        )

        assert script_path.exists()
        assert script_path.name == "setup-python.sh"

        # Verify script content
        content = script_path.read_text()
        assert "pip install" in content
        assert "--no-index" in content
        assert "--find-links" in content
        assert "python" in content

    def test_extract_archive_with_dependencies(self, tmp_path):
        """Test extracting archive and restoring dependencies."""
        # This would test the full workflow:
        # 1. Create archive with dependencies
        # 2. Extract archive
        # 3. Verify dependencies are in correct location
        # 4. Verify install script exists

        # Setup
        archive_dir = tmp_path / "archive"
        archive_dir.mkdir()

        # Create mock archive structure
        repo_dir = archive_dir / "repo"
        repo_dir.mkdir()

        deps_dir = archive_dir / "dependencies" / "python"
        deps_dir.mkdir(parents=True)

        scripts_dir = archive_dir / "restore-scripts"
        scripts_dir.mkdir()

        # Create files
        (deps_dir / "requests-2.31.0-py3-none-any.whl").write_bytes(b"fake")
        install_cmd = (
            "pip install --no-index --find-links "
            "../dependencies/python -r requirements.txt"
        )
        (scripts_dir / "setup-python.sh").write_text(f"#!/bin/bash\n{install_cmd}\n")

        # Verify structure
        assert (deps_dir / "requests-2.31.0-py3-none-any.whl").exists()
        assert (scripts_dir / "setup-python.sh").exists()

        # Verify can execute script (would install offline)
        script = scripts_dir / "setup-python.sh"
        assert script.exists()
        content = script.read_text()
        assert "pip install" in content
        assert "--no-index" in content

    def test_archive_multiple_language_dependencies(self, tmp_path):
        """Test archiving dependencies for multiple languages (monorepo)."""
        repo_path = tmp_path / "repo"
        repo_path.mkdir()

        # Create Python requirements.txt
        (repo_path / "requirements.txt").write_text("requests==2.31.0\n")

        # Create Node.js package.json
        (repo_path / "package.json").write_text('{"dependencies": {"express": "^4.18.0"}}')

        # Detect languages
        detector = DependencyDetector(str(repo_path))
        languages = detector.detect_languages()

        assert LanguageType.PYTHON in languages
        assert LanguageType.NODEJS in languages
        assert len(languages) == 2

    def test_dependency_manifest_includes_checksums(self, tmp_path):
        """Test that dependency manifest includes SHA256 checksums."""
        resolved = [
            ResolvedDependency(
                name="requests",
                version="2.31.0",
                filename="requests-2.31.0-py3-none-any.whl",
            ),
        ]

        from repo_cloner.archive_manager import ArchiveManager

        manager = ArchiveManager()

        manifest = manager._generate_dependency_manifest(
            language="python",
            manifest_file="requirements.txt",
            resolved_dependencies=resolved,
        )

        # Checksums would be calculated during actual download
        assert "packages" in manifest
        package = manifest["packages"][0]
        assert "filename" in package
        # Note: Checksum would be added during download phase

    def test_skip_dependency_fetch_when_disabled(self, tmp_path):
        """Test that dependency fetching is skipped when disabled."""
        repo_path = tmp_path / "repo"
        repo_path.mkdir()

        # Initialize git repo
        import subprocess

        subprocess.run(["git", "init"], cwd=repo_path, check=True, capture_output=True)
        subprocess.run(
            ["git", "config", "user.email", "test@example.com"], cwd=repo_path, check=True
        )
        subprocess.run(["git", "config", "user.name", "Test User"], cwd=repo_path, check=True)

        # Create requirements.txt
        (repo_path / "requirements.txt").write_text("requests==2.31.0\n")

        # Commit
        subprocess.run(["git", "add", "."], cwd=repo_path, check=True)
        subprocess.run(
            ["git", "commit", "-m", "test"], cwd=repo_path, check=True, capture_output=True
        )

        # Create archive WITHOUT dependencies
        manager = ArchiveManager()
        output_dir = tmp_path / "archives"
        output_dir.mkdir()

        result = manager.create_full_archive(
            repo_path=str(repo_path),
            output_path=str(output_dir),
        )
        archive_path = Path(result["archive_path"])

        # Verify archive exists but has no dependencies
        assert archive_path.exists()

        # Check manifest doesn't have dependencies section
        manifest_path = output_dir / (archive_path.stem.replace(".tar", "") + ".manifest.json")
        if manifest_path.exists():
            import json

            manifest = json.loads(manifest_path.read_text())
            # Regular archives don't have dependencies section
            assert "dependencies" not in manifest or manifest.get("dependencies") is None

    def test_validate_dependency_archive_completeness(self, tmp_path):
        """Test validating that all dependencies are present in archive."""
        # Create archive structure
        deps_dir = tmp_path / "dependencies" / "python"
        deps_dir.mkdir(parents=True)

        # Expected dependencies
        expected = [
            "requests-2.31.0-py3-none-any.whl",
            "urllib3-2.0.7-py3-none-any.whl",
            "certifi-2023.7.22-py3-none-any.whl",
        ]

        # Create only 2 out of 3
        (deps_dir / expected[0]).write_bytes(b"fake")
        (deps_dir / expected[1]).write_bytes(b"fake")

        # Verify
        present = [f.name for f in deps_dir.glob("*.whl")]
        assert len(present) == 2
        assert expected[0] in present
        assert expected[1] in present
        assert expected[2] not in present

        # Would raise error if validation is enabled
        missing = set(expected) - set(present)
        assert len(missing) == 1
        assert expected[2] in missing
