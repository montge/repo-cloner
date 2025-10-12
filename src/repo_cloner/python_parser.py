"""Python dependency manifest parser for requirements.txt, pyproject.toml, Pipfile, setup.py."""

import ast
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

try:
    import tomllib  # Python 3.11+
except ImportError:
    import tomli as tomllib  # Python 3.9-3.10


@dataclass
class PythonDependency:
    """Represents a Python package dependency."""

    name: str
    version_spec: str = ""
    extras: List[str] = field(default_factory=list)
    markers: str = ""
    url: Optional[str] = None
    editable: bool = False

    def __eq__(self, other: object) -> bool:
        """Check equality based on name and version_spec."""
        if not isinstance(other, PythonDependency):
            return NotImplemented
        return self.name == other.name and self.version_spec == other.version_spec

    def __hash__(self) -> int:
        """Hash based on name and version_spec."""
        return hash((self.name, self.version_spec))

    def __repr__(self) -> str:
        """String representation of dependency."""
        extras_str = f"[{','.join(self.extras)}]" if self.extras else ""
        markers_str = f" ; {self.markers}" if self.markers else ""
        return f"PythonDependency({self.name}{extras_str}{self.version_spec}{markers_str})"


class PythonManifestParser:
    """Parser for Python dependency manifest files."""

    # Pattern to parse requirement lines: pkg[extras]>=1.0.0 ; markers
    REQUIREMENT_PATTERN = re.compile(
        r"^(?P<name>[a-zA-Z0-9][\w\-\.]*)"  # Package name
        r"(?:\[(?P<extras>[^\]]+)\])?"  # Optional extras
        r"(?P<version>[^;]+)?"  # Version specifier
        r"(?:\s*;\s*(?P<markers>.+))?"  # Environment markers
    )

    def __init__(self, manifest_path: str) -> None:
        """Initialize the parser with a manifest file path.

        Args:
            manifest_path: Path to the manifest file

        Raises:
            ValueError: If file format is not supported
        """
        self.manifest_path = Path(manifest_path)
        self.manifest_name = self.manifest_path.name.lower()

        # Determine parser method based on filename
        if self.manifest_name in (
            "requirements.txt",
            "requirements-dev.txt",
            "requirements-test.txt",
        ):
            self.parser_method = self._parse_requirements_txt
        elif self.manifest_name == "pyproject.toml":
            self.parser_method = self._parse_pyproject_toml
        elif self.manifest_name == "pipfile":
            self.parser_method = self._parse_pipfile
        elif self.manifest_name == "setup.py":
            self.parser_method = self._parse_setup_py
        else:
            raise ValueError(f"Unsupported manifest format: {self.manifest_name}")

    def parse(self) -> List[PythonDependency]:
        """Parse the manifest file and return list of dependencies.

        Returns:
            List of PythonDependency objects

        Raises:
            FileNotFoundError: If manifest file does not exist
        """
        if not self.manifest_path.exists():
            raise FileNotFoundError(f"Manifest file not found: {self.manifest_path}")

        return self.parser_method()

    def _parse_requirements_txt(self) -> List[PythonDependency]:
        """Parse requirements.txt format.

        Returns:
            List of PythonDependency objects
        """
        dependencies: List[PythonDependency] = []
        content = self.manifest_path.read_text(encoding="utf-8")

        for line in content.splitlines():
            line = line.strip()

            # Skip empty lines and comments
            if not line or line.startswith("#"):
                continue

            # Skip option flags (-e, -r, --index-url, etc.)
            if line.startswith("-"):
                # Handle editable installs separately
                if line.startswith("-e "):
                    # Extract package name from editable install if possible
                    # For now, we'll skip editable installs as they require special handling
                    continue
                # Skip other flags
                continue

            # Skip URL-based dependencies (git+, https://, etc.)
            if any(
                line.startswith(prefix)
                for prefix in ("git+", "hg+", "svn+", "bzr+", "http://", "https://")
            ):
                continue

            # Parse the requirement line
            dep = self._parse_requirement_line(line)
            if dep:
                dependencies.append(dep)

        return dependencies

    def _parse_requirement_line(self, line: str) -> Optional[PythonDependency]:
        """Parse a single requirement line.

        Args:
            line: Requirement line to parse

        Returns:
            PythonDependency object or None if parsing fails
        """
        # Remove inline comments
        if " #" in line:
            line = line.split(" #")[0].strip()

        match = self.REQUIREMENT_PATTERN.match(line)
        if not match:
            return None

        name = match.group("name")
        extras_str = match.group("extras")
        version = match.group("version")
        markers = match.group("markers")

        # Parse extras
        extras = []
        if extras_str:
            extras = [e.strip() for e in extras_str.split(",")]

        # Clean up version spec
        version_spec = ""
        if version:
            version_spec = version.strip()

        # Clean up markers
        markers_clean = ""
        if markers:
            markers_clean = markers.strip()

        return PythonDependency(
            name=name,
            version_spec=version_spec,
            extras=extras,
            markers=markers_clean,
        )

    def _parse_pyproject_toml(self) -> List[PythonDependency]:
        """Parse pyproject.toml format (PEP 621 or Poetry).

        Returns:
            List of PythonDependency objects
        """
        dependencies: List[PythonDependency] = []
        content = self.manifest_path.read_bytes()
        data = tomllib.loads(content.decode("utf-8"))

        # Try PEP 621 format first
        if "project" in data and "dependencies" in data["project"]:
            for dep_str in data["project"]["dependencies"]:
                dep = self._parse_requirement_line(dep_str)
                if dep:
                    dependencies.append(dep)

        # Try Poetry format
        elif "tool" in data and "poetry" in data["tool"]:
            poetry_deps = data["tool"]["poetry"].get("dependencies", {})
            for name, spec in poetry_deps.items():
                # Skip python version requirement
                if name == "python":
                    continue

                # Handle different spec formats
                if isinstance(spec, str):
                    # Simple version: "^2.31.0"
                    version_spec = spec
                elif isinstance(spec, dict):
                    # Complex spec: {version = ">=2.0.0", optional = true}
                    version_spec = spec.get("version", "")
                else:
                    version_spec = ""

                dependencies.append(
                    PythonDependency(
                        name=name,
                        version_spec=version_spec,
                    )
                )

        return dependencies

    def _parse_pipfile(self) -> List[PythonDependency]:
        """Parse Pipfile format.

        Returns:
            List of PythonDependency objects
        """
        dependencies: List[PythonDependency] = []
        content = self.manifest_path.read_bytes()
        data = tomllib.loads(content.decode("utf-8"))

        # Only parse [packages], not [dev-packages]
        packages = data.get("packages", {})
        for name, spec in packages.items():
            if isinstance(spec, str):
                # Handle "*" wildcard
                version_spec = spec if spec != "*" else ""
            elif isinstance(spec, dict):
                version_spec = spec.get("version", "")
            else:
                version_spec = ""

            dependencies.append(
                PythonDependency(
                    name=name,
                    version_spec=version_spec,
                )
            )

        return dependencies

    def _parse_setup_py(self) -> List[PythonDependency]:
        """Parse setup.py format (extract install_requires).

        Returns:
            List of PythonDependency objects

        Note:
            This uses AST parsing to extract install_requires without executing the file.
            This is safer but may miss dynamically generated dependencies.
        """
        dependencies: List[PythonDependency] = []
        content = self.manifest_path.read_text(encoding="utf-8")

        try:
            tree = ast.parse(content)
        except SyntaxError:
            # If parsing fails, return empty list
            return dependencies

        # Find setup() call and extract install_requires
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                # Check if this is a setup() call
                if isinstance(node.func, ast.Name) and node.func.id == "setup":
                    # Look for install_requires keyword argument
                    for keyword in node.keywords:
                        if keyword.arg == "install_requires":
                            # Extract list of dependencies
                            if isinstance(keyword.value, ast.List):
                                for elt in keyword.value.elts:
                                    if isinstance(elt, ast.Constant) and isinstance(
                                        elt.value, str
                                    ):
                                        dep_str = elt.value
                                        dep = self._parse_requirement_line(dep_str)
                                        if dep:
                                            dependencies.append(dep)

        return dependencies
