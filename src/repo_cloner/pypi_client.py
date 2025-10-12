"""PyPI client for fetching packages and resolving transitive dependencies."""

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Set

import requests
from packaging.requirements import Requirement
from packaging.specifiers import SpecifierSet
from packaging.version import Version

from .python_parser import PythonDependency


class VersionConflictError(Exception):
    """Raised when conflicting version requirements are detected."""

    pass


@dataclass
class PyPIPackage:
    """Represents a PyPI package with metadata."""

    name: str
    version: str
    dependencies: List[str]
    wheel_url: str
    sdist_url: str
    wheel_sha256: str
    sdist_sha256: str

    def __eq__(self, other: object) -> bool:
        """Check equality based on name and version."""
        if not isinstance(other, PyPIPackage):
            return NotImplemented
        return self.name == other.name and self.version == other.version

    def __hash__(self) -> int:
        """Hash based on name and version."""
        return hash((self.name, self.version))


@dataclass
class ResolvedDependency:
    """Represents a resolved dependency with version and download info."""

    name: str
    version: str
    filename: str

    def to_dict(self) -> Dict[str, str]:
        """Convert to dictionary for serialization."""
        return {
            "name": self.name,
            "version": self.version,
            "filename": self.filename,
        }


class PyPIClient:
    """Client for interacting with PyPI and resolving dependencies."""

    def __init__(
        self,
        index_url: str = "https://pypi.org",
        username: Optional[str] = None,
        password: Optional[str] = None,
    ) -> None:
        """Initialize PyPI client.

        Args:
            index_url: PyPI index URL (default: https://pypi.org)
            username: Username for private PyPI authentication
            password: Password for private PyPI authentication
        """
        self.index_url = index_url.rstrip("/")
        self.username = username
        self.password = password
        self.session = requests.Session()

        # Set authentication if provided
        if self.username and self.password:
            self.session.auth = (self.username, self.password)

    def fetch_package_metadata(self, name: str, version: str) -> PyPIPackage:
        """Fetch package metadata from PyPI JSON API.

        Args:
            name: Package name
            version: Package version

        Returns:
            PyPIPackage with metadata

        Raises:
            ValueError: If package not found
            ConnectionError: If network error occurs
        """
        # PyPI JSON API endpoint
        url = f"{self.index_url}/pypi/{name}/{version}/json"

        try:
            response = self.session.get(url)
        except requests.exceptions.ConnectionError as e:
            raise ConnectionError(f"Network error: {e}") from e

        if response.status_code == 404:
            raise ValueError(f"Package not found: {name}=={version}")

        if response.status_code != 200:
            raise ValueError(f"Failed to fetch package metadata: {response.status_code}")

        data = response.json()
        info = data["info"]
        urls = data.get("urls", [])

        # Extract dependencies
        dependencies = info.get("requires_dist", []) or []

        # Find wheel and sdist URLs
        wheel_url = ""
        sdist_url = ""
        wheel_sha256 = ""
        sdist_sha256 = ""

        for url_info in urls:
            package_type = url_info.get("packagetype", "")
            if package_type == "bdist_wheel":
                wheel_url = url_info.get("url", "")
                wheel_sha256 = url_info.get("digests", {}).get("sha256", "")
            elif package_type == "sdist":
                sdist_url = url_info.get("url", "")
                sdist_sha256 = url_info.get("digests", {}).get("sha256", "")

        return PyPIPackage(
            name=info["name"],
            version=info["version"],
            dependencies=dependencies,
            wheel_url=wheel_url,
            sdist_url=sdist_url,
            wheel_sha256=wheel_sha256,
            sdist_sha256=sdist_sha256,
        )

    def resolve_dependencies(
        self, root_dependencies: List[PythonDependency]
    ) -> List[ResolvedDependency]:
        """Resolve transitive dependencies from root dependencies.

        Args:
            root_dependencies: List of root dependencies to resolve

        Returns:
            List of resolved dependencies with versions

        Raises:
            VersionConflictError: If conflicting version requirements detected
        """
        resolved: Dict[str, ResolvedDependency] = {}
        requirements_map: Dict[str, List[SpecifierSet]] = {}
        to_process: List[PythonDependency] = list(root_dependencies)
        processed: Set[str] = set()

        while to_process:
            dep = to_process.pop(0)
            package_key = dep.name.lower()

            # Skip if already processed
            if package_key in processed:
                continue

            # Track version requirements for conflict detection
            if package_key not in requirements_map:
                requirements_map[package_key] = []

            # Parse version specifier
            if dep.version_spec:
                try:
                    spec_set = SpecifierSet(dep.version_spec)
                    requirements_map[package_key].append(spec_set)
                except Exception:
                    # If parsing fails, skip version constraint
                    pass

            # Find a version that satisfies all constraints
            version = self._find_compatible_version(package_key, requirements_map[package_key])

            if version is None:
                raise VersionConflictError(
                    f"Cannot find version of {dep.name} that satisfies: "
                    f"{[str(s) for s in requirements_map[package_key]]}"
                )

            # Fetch package metadata
            try:
                package = self.fetch_package_metadata(dep.name, version)
            except Exception:
                # If package fetch fails, skip it
                processed.add(package_key)
                continue

            # Add to resolved list
            filename = self._get_package_filename(package, prefer_wheel=True)
            resolved[package_key] = ResolvedDependency(
                name=package.name,
                version=package.version,
                filename=filename,
            )

            # Add transitive dependencies to process queue
            for dep_str in package.dependencies:
                # Skip environment markers for now (simplified)
                if ";" in dep_str:
                    dep_str = dep_str.split(";")[0].strip()

                if not dep_str:
                    continue

                try:
                    req = Requirement(dep_str)
                    trans_dep = PythonDependency(
                        name=req.name,
                        version_spec=str(req.specifier) if req.specifier else "",
                    )
                    to_process.append(trans_dep)
                except Exception:
                    # If parsing fails, skip dependency
                    continue

            processed.add(package_key)

        return list(resolved.values())

    def _find_compatible_version(
        self, package_name: str, spec_sets: List[SpecifierSet]
    ) -> Optional[str]:
        """Find a version that satisfies all specifier sets.

        Args:
            package_name: Name of the package
            spec_sets: List of version specifier sets to satisfy

        Returns:
            Compatible version string or None if no compatible version found
        """
        # For now, fetch latest version from PyPI
        # In production, this should query PyPI for available versions
        # and find the highest version that satisfies all constraints
        try:
            url = f"{self.index_url}/pypi/{package_name}/json"
            response = self.session.get(url)
            if response.status_code == 200:
                data = response.json()
                latest_version = str(data["info"]["version"])

                # Check if latest version satisfies all constraints
                version_obj = Version(latest_version)
                for spec_set in spec_sets:
                    if not spec_set.contains(version_obj):
                        return None

                return latest_version
        except Exception:
            pass

        return None

    def _get_package_filename(self, package: PyPIPackage, prefer_wheel: bool = True) -> str:
        """Get filename for package download.

        Args:
            package: PyPIPackage object
            prefer_wheel: Prefer wheel over sdist if available

        Returns:
            Filename string
        """
        if prefer_wheel and package.wheel_url:
            return package.wheel_url.split("/")[-1]
        elif package.sdist_url:
            return package.sdist_url.split("/")[-1]
        return f"{package.name}-{package.version}.tar.gz"

    def download_package(
        self, package: PyPIPackage, output_dir: str, prefer_wheel: bool = True
    ) -> Path:
        """Download package (wheel or sdist) to output directory.

        Args:
            package: PyPIPackage to download
            output_dir: Directory to save downloaded file
            prefer_wheel: Prefer wheel over sdist if available

        Returns:
            Path to downloaded file

        Raises:
            ValueError: If no download URL available
        """
        # Determine which package to download
        if prefer_wheel and package.wheel_url:
            url = package.wheel_url
            filename = package.wheel_url.split("/")[-1]
        elif package.sdist_url:
            url = package.sdist_url
            filename = package.sdist_url.split("/")[-1]
        else:
            raise ValueError(f"No download URL available for {package.name}")

        # Download file
        response = self.session.get(url)
        if response.status_code != 200:
            raise ValueError(f"Failed to download {filename}: {response.status_code}")

        # Save to output directory
        output_path = Path(output_dir) / filename
        output_path.write_bytes(response.content)

        return output_path

    def download_all(self, resolved: List[ResolvedDependency], output_dir: str) -> List[Path]:
        """Download all resolved dependencies.

        Args:
            resolved: List of resolved dependencies
            output_dir: Directory to save downloaded files

        Returns:
            List of paths to downloaded files
        """
        downloaded: List[Path] = []

        for dep in resolved:
            try:
                # Fetch package metadata
                package = self.fetch_package_metadata(dep.name, dep.version)

                # Download package
                path = self.download_package(package, output_dir, prefer_wheel=True)
                downloaded.append(path)
            except Exception:
                # Skip packages that fail to download
                continue

        return downloaded

    def verify_checksum(self, file_path: Path, expected_sha256: str) -> bool:
        """Verify SHA256 checksum of downloaded file.

        Args:
            file_path: Path to file to verify
            expected_sha256: Expected SHA256 checksum

        Returns:
            True if checksum matches, False otherwise
        """
        if not file_path.exists():
            return False

        # Calculate SHA256
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)

        actual_sha256 = sha256_hash.hexdigest()
        return actual_sha256 == expected_sha256

    def generate_offline_requirements(
        self, resolved: List[ResolvedDependency], output_dir: str
    ) -> Path:
        """Generate offline-compatible requirements.txt with local file paths.

        Args:
            resolved: List of resolved dependencies
            output_dir: Directory containing downloaded packages

        Returns:
            Path to generated requirements.txt
        """
        output_path = Path(output_dir) / "requirements.txt"

        lines: List[str] = []
        lines.append(
            "# Offline requirements - install with: "
            "pip install -r requirements.txt --no-index --find-links ."
        )
        lines.append("")

        for dep in resolved:
            lines.append(f"{dep.filename}")

        output_path.write_text("\n".join(lines))
        return output_path

    def parse_version_specifier(self, spec: str) -> Optional[SpecifierSet]:
        """Parse version specifier string.

        Args:
            spec: Version specifier string (e.g., ">=2.0.0", ">=2.0,<3.0")

        Returns:
            SpecifierSet object or None if parsing fails
        """
        try:
            return SpecifierSet(spec)
        except Exception:
            return None
