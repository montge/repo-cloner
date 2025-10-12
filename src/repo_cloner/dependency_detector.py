"""Dependency detection system for identifying programming languages in repositories."""

from enum import Enum
from pathlib import Path
from typing import Dict, List, Set


class LanguageType(Enum):
    """Supported programming language types."""

    PYTHON = "python"
    NODEJS = "nodejs"
    JAVA = "java"
    MAVEN = "maven"
    GRADLE = "gradle"
    GO = "go"
    RUST = "rust"
    RUBY = "ruby"
    PHP = "php"
    DOTNET = "dotnet"
    CPP = "cpp"
    C = "c"
    CSHARP = "csharp"
    SWIFT = "swift"
    SCALA = "scala"
    ADA = "ada"
    FORTRAN = "fortran"


# Mapping of language types to their manifest files
LANGUAGE_MANIFESTS: Dict[LanguageType, List[str]] = {
    LanguageType.PYTHON: [
        "requirements.txt",
        "requirements-dev.txt",
        "requirements-test.txt",
        "pyproject.toml",
        "Pipfile",
        "Pipfile.lock",
        "setup.py",
        "setup.cfg",
        "poetry.lock",
        "conda.yml",
        "environment.yml",
    ],
    LanguageType.NODEJS: [
        "package.json",
        "package-lock.json",
        "yarn.lock",
        "pnpm-lock.yaml",
        "npm-shrinkwrap.json",
    ],
    LanguageType.JAVA: [
        "pom.xml",
        "build.gradle",
        "build.gradle.kts",
        "gradle.properties",
        "settings.gradle",
        "settings.gradle.kts",
    ],
    LanguageType.GO: [
        "go.mod",
        "go.sum",
        "Gopkg.toml",
        "Gopkg.lock",
    ],
    LanguageType.RUST: [
        "Cargo.toml",
        "Cargo.lock",
    ],
    LanguageType.RUBY: [
        "Gemfile",
        "Gemfile.lock",
        "*.gemspec",
    ],
    LanguageType.PHP: [
        "composer.json",
        "composer.lock",
    ],
    LanguageType.DOTNET: [
        "*.csproj",
        "*.fsproj",
        "*.vbproj",
        "packages.config",
        "project.json",
        "paket.dependencies",
        "paket.lock",
    ],
    LanguageType.CPP: [
        "conanfile.py",
        "conanfile.txt",
        "vcpkg.json",
        "CMakeLists.txt",
    ],
    LanguageType.SWIFT: [
        "Package.swift",
        "Podfile",
        "Podfile.lock",
        "Cartfile",
        "Cartfile.resolved",
    ],
    LanguageType.SCALA: [
        "build.sbt",
        "build.sc",
    ],
    LanguageType.ADA: [
        "alire.toml",
    ],
    LanguageType.FORTRAN: [
        "fpm.toml",
    ],
}


class DependencyDetector:
    """Detects programming languages and their dependency manifests in a repository."""

    def __init__(self, repo_path: str) -> None:
        """Initialize the dependency detector.

        Args:
            repo_path: Path to the repository root directory

        Raises:
            ValueError: If repo_path does not exist or is not a directory
        """
        self.repo_path = Path(repo_path)

        if not self.repo_path.exists():
            raise ValueError(f"Repository path does not exist: {repo_path}")

        if not self.repo_path.is_dir():
            raise ValueError(f"Repository path must be a directory: {repo_path}")

        # Cache for detected languages and their manifest files
        self._detected_languages: Dict[LanguageType, List[Path]] = {}
        self._scan_complete = False

    def detect_languages(self) -> Set[LanguageType]:
        """Detect all programming languages present in the repository.

        Returns:
            Set of detected language types
        """
        if not self._scan_complete:
            self._scan_repository()

        return set(self._detected_languages.keys())

    def has_language(self, language: LanguageType) -> bool:
        """Check if a specific language is present in the repository.

        Args:
            language: The language type to check for

        Returns:
            True if the language is detected, False otherwise
        """
        if not self._scan_complete:
            self._scan_repository()

        return language in self._detected_languages

    def get_manifest_files(self, language: LanguageType) -> List[Path]:
        """Get all manifest files for a specific language.

        Args:
            language: The language type to get manifests for

        Returns:
            List of Path objects for manifest files, empty if language not detected
        """
        if not self._scan_complete:
            self._scan_repository()

        return self._detected_languages.get(language, [])

    def get_detected_languages_metadata(self) -> Dict[LanguageType, Dict[str, object]]:
        """Get metadata about all detected languages.

        Returns:
            Dictionary mapping language types to metadata including:
            - manifest_count: Number of manifest files found
            - manifest_files: List of manifest file paths
        """
        if not self._scan_complete:
            self._scan_repository()

        metadata: Dict[LanguageType, Dict[str, object]] = {}
        for language, manifest_files in self._detected_languages.items():
            metadata[language] = {
                "manifest_count": len(manifest_files),
                "manifest_files": manifest_files,
            }

        return metadata

    def _scan_repository(self) -> None:
        """Recursively scan repository for language manifest files."""
        self._detected_languages.clear()

        # Recursively search for manifest files
        for language, manifest_patterns in LANGUAGE_MANIFESTS.items():
            manifest_files: List[Path] = []

            for pattern in manifest_patterns:
                # Handle glob patterns (e.g., *.gemspec, *.csproj)
                if "*" in pattern:
                    manifest_files.extend(self.repo_path.rglob(pattern))
                else:
                    # Search for exact filename recursively
                    manifest_files.extend(self.repo_path.rglob(pattern))

            # Only add language if we found manifest files
            if manifest_files:
                self._detected_languages[language] = sorted(manifest_files)

        self._scan_complete = True
