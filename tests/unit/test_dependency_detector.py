"""Tests for dependency detection system."""

import pytest

from repo_cloner.dependency_detector import DependencyDetector, LanguageType


class TestDependencyDetector:
    """Test suite for DependencyDetector class."""

    def test_detect_python_from_requirements_txt(self, tmp_path):
        """Test that Python is detected when requirements.txt exists."""
        # Create a test repository with requirements.txt
        requirements_file = tmp_path / "requirements.txt"
        requirements_file.write_text("requests==2.31.0\nflask>=2.0.0\n")

        detector = DependencyDetector(str(tmp_path))
        languages = detector.detect_languages()

        assert LanguageType.PYTHON in languages
        assert detector.has_language(LanguageType.PYTHON)

    def test_detect_python_from_pyproject_toml(self, tmp_path):
        """Test that Python is detected when pyproject.toml exists."""
        pyproject_file = tmp_path / "pyproject.toml"
        pyproject_file.write_text(
            """
[build-system]
requires = ["setuptools", "wheel"]

[project]
name = "myproject"
dependencies = ["requests>=2.31.0"]
"""
        )

        detector = DependencyDetector(str(tmp_path))
        languages = detector.detect_languages()

        assert LanguageType.PYTHON in languages

    def test_detect_python_from_pipfile(self, tmp_path):
        """Test that Python is detected when Pipfile exists."""
        pipfile = tmp_path / "Pipfile"
        pipfile.write_text(
            """
[packages]
requests = "*"
flask = ">=2.0.0"
"""
        )

        detector = DependencyDetector(str(tmp_path))
        languages = detector.detect_languages()

        assert LanguageType.PYTHON in languages

    def test_detect_python_from_setup_py(self, tmp_path):
        """Test that Python is detected when setup.py exists."""
        setup_file = tmp_path / "setup.py"
        setup_file.write_text(
            """
from setuptools import setup

setup(
    name="myproject",
    install_requires=["requests>=2.31.0"],
)
"""
        )

        detector = DependencyDetector(str(tmp_path))
        languages = detector.detect_languages()

        assert LanguageType.PYTHON in languages

    def test_detect_no_languages_in_empty_repo(self, tmp_path):
        """Test that no languages are detected in empty repository."""
        detector = DependencyDetector(str(tmp_path))
        languages = detector.detect_languages()

        assert len(languages) == 0
        assert not detector.has_language(LanguageType.PYTHON)

    def test_detect_multiple_languages_in_monorepo(self, tmp_path):
        """Test that multiple languages are detected in a monorepo."""
        # Create Python manifest
        requirements = tmp_path / "requirements.txt"
        requirements.write_text("requests==2.31.0\n")

        # Create Node.js manifest
        package_json = tmp_path / "package.json"
        package_json.write_text('{"dependencies": {"express": "^4.18.0"}}')

        detector = DependencyDetector(str(tmp_path))
        languages = detector.detect_languages()

        assert LanguageType.PYTHON in languages
        assert LanguageType.NODEJS in languages
        assert len(languages) == 2

    def test_get_manifest_files_for_python(self, tmp_path):
        """Test getting all manifest files for Python."""
        requirements = tmp_path / "requirements.txt"
        requirements.write_text("requests==2.31.0\n")

        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text('[project]\nname = "test"\n')

        detector = DependencyDetector(str(tmp_path))
        manifest_files = detector.get_manifest_files(LanguageType.PYTHON)

        assert len(manifest_files) == 2
        assert requirements in manifest_files
        assert pyproject in manifest_files

    def test_get_manifest_files_returns_empty_for_undetected_language(self, tmp_path):
        """Test that get_manifest_files returns empty list for undetected language."""
        # Create only Python files
        requirements = tmp_path / "requirements.txt"
        requirements.write_text("requests==2.31.0\n")

        detector = DependencyDetector(str(tmp_path))

        # Try to get Node.js manifests (which don't exist)
        manifest_files = detector.get_manifest_files(LanguageType.NODEJS)

        assert len(manifest_files) == 0

    def test_detect_languages_in_subdirectories(self, tmp_path):
        """Test that languages are detected in subdirectories."""
        # Create Python manifest in subdirectory
        backend_dir = tmp_path / "backend"
        backend_dir.mkdir()
        requirements = backend_dir / "requirements.txt"
        requirements.write_text("django==4.2.0\n")

        # Create Node.js manifest in another subdirectory
        frontend_dir = tmp_path / "frontend"
        frontend_dir.mkdir()
        package_json = frontend_dir / "package.json"
        package_json.write_text('{"dependencies": {"react": "^18.0.0"}}')

        detector = DependencyDetector(str(tmp_path))
        languages = detector.detect_languages()

        assert LanguageType.PYTHON in languages
        assert LanguageType.NODEJS in languages

    def test_get_all_detected_languages_with_metadata(self, tmp_path):
        """Test getting all detected languages with their metadata."""
        requirements = tmp_path / "requirements.txt"
        requirements.write_text("requests==2.31.0\n")

        detector = DependencyDetector(str(tmp_path))
        languages_metadata = detector.get_detected_languages_metadata()

        assert LanguageType.PYTHON in languages_metadata
        metadata = languages_metadata[LanguageType.PYTHON]
        assert metadata["manifest_count"] == 1
        assert len(metadata["manifest_files"]) == 1
        assert "requirements.txt" in str(metadata["manifest_files"][0])

    def test_raises_error_for_nonexistent_repository(self):
        """Test that ValueError is raised for nonexistent repository path."""
        with pytest.raises(ValueError, match="Repository path does not exist"):
            DependencyDetector("/nonexistent/path")

    def test_raises_error_for_file_instead_of_directory(self, tmp_path):
        """Test that ValueError is raised when path is a file, not a directory."""
        file_path = tmp_path / "test.txt"
        file_path.write_text("test")

        with pytest.raises(ValueError, match="Repository path must be a directory"):
            DependencyDetector(str(file_path))
