"""Tests for Python dependency manifest parser."""

import pytest

from repo_cloner.python_parser import PythonDependency, PythonManifestParser


class TestPythonManifestParser:
    """Test suite for PythonManifestParser class."""

    def test_parse_requirements_txt_simple(self, tmp_path):
        """Test parsing simple requirements.txt with pinned versions."""
        requirements_file = tmp_path / "requirements.txt"
        requirements_file.write_text(
            """requests==2.31.0
flask>=2.0.0
django<5.0
numpy
"""
        )

        parser = PythonManifestParser(str(requirements_file))
        dependencies = parser.parse()

        assert len(dependencies) == 4

        # requests with exact version
        req = next(d for d in dependencies if d.name == "requests")
        assert req.version_spec == "==2.31.0"
        assert req.extras == []

        # flask with minimum version
        flask = next(d for d in dependencies if d.name == "flask")
        assert flask.version_spec == ">=2.0.0"

        # django with maximum version
        django = next(d for d in dependencies if d.name == "django")
        assert django.version_spec == "<5.0"

        # numpy without version
        numpy = next(d for d in dependencies if d.name == "numpy")
        assert numpy.version_spec == ""

    def test_parse_requirements_txt_with_comments(self, tmp_path):
        """Test parsing requirements.txt with comments and blank lines."""
        requirements_file = tmp_path / "requirements.txt"
        requirements_file.write_text(
            """# Web framework
flask==2.3.0

# Database
sqlalchemy>=2.0.0  # ORM

# Blank lines should be ignored

requests==2.31.0
"""
        )

        parser = PythonManifestParser(str(requirements_file))
        dependencies = parser.parse()

        assert len(dependencies) == 3
        assert {d.name for d in dependencies} == {"flask", "sqlalchemy", "requests"}

    def test_parse_requirements_txt_with_extras(self, tmp_path):
        """Test parsing requirements.txt with extras."""
        requirements_file = tmp_path / "requirements.txt"
        requirements_file.write_text(
            """requests[security,socks]==2.31.0
celery[redis,msgpack]>=5.3.0
"""
        )

        parser = PythonManifestParser(str(requirements_file))
        dependencies = parser.parse()

        assert len(dependencies) == 2

        requests = next(d for d in dependencies if d.name == "requests")
        assert requests.extras == ["security", "socks"]
        assert requests.version_spec == "==2.31.0"

        celery = next(d for d in dependencies if d.name == "celery")
        assert celery.extras == ["redis", "msgpack"]

    def test_parse_requirements_txt_with_environment_markers(self, tmp_path):
        """Test parsing requirements.txt with environment markers."""
        requirements_file = tmp_path / "requirements.txt"
        requirements_file.write_text(
            """requests==2.31.0
pywin32>=300 ; sys_platform == 'win32'
uvloop>=0.17.0 ; sys_platform != 'win32'
"""
        )

        parser = PythonManifestParser(str(requirements_file))
        dependencies = parser.parse()

        assert len(dependencies) == 3

        pywin32 = next(d for d in dependencies if d.name == "pywin32")
        assert pywin32.markers == "sys_platform == 'win32'"

        uvloop = next(d for d in dependencies if d.name == "uvloop")
        assert uvloop.markers == "sys_platform != 'win32'"

    def test_parse_pyproject_toml_poetry(self, tmp_path):
        """Test parsing pyproject.toml with Poetry format."""
        pyproject_file = tmp_path / "pyproject.toml"
        pyproject_file.write_text(
            """[tool.poetry]
name = "myproject"
version = "0.1.0"

[tool.poetry.dependencies]
python = "^3.9"
requests = "^2.31.0"
flask = {version = ">=2.0.0", optional = true}
numpy = "1.24.0"

[tool.poetry.dev-dependencies]
pytest = "^7.0.0"
black = "^23.0.0"
"""
        )

        parser = PythonManifestParser(str(pyproject_file))
        dependencies = parser.parse()

        # Should only return runtime dependencies, not dev dependencies
        assert len(dependencies) == 3  # python, requests, flask, numpy (excluding python runtime)

        assert {d.name for d in dependencies} == {"requests", "flask", "numpy"}

    def test_parse_pyproject_toml_pep621(self, tmp_path):
        """Test parsing pyproject.toml with PEP 621 format."""
        pyproject_file = tmp_path / "pyproject.toml"
        pyproject_file.write_text(
            """[project]
name = "myproject"
version = "0.1.0"
dependencies = [
    "requests>=2.31.0",
    "flask==2.3.0",
    "numpy",
]

[project.optional-dependencies]
dev = ["pytest>=7.0.0", "black>=23.0.0"]
"""
        )

        parser = PythonManifestParser(str(pyproject_file))
        dependencies = parser.parse()

        assert len(dependencies) == 3
        assert {d.name for d in dependencies} == {"requests", "flask", "numpy"}

    def test_parse_setup_py_basic(self, tmp_path):
        """Test parsing setup.py with install_requires."""
        setup_file = tmp_path / "setup.py"
        setup_file.write_text(
            """from setuptools import setup

setup(
    name="myproject",
    version="0.1.0",
    install_requires=[
        "requests>=2.31.0",
        "flask==2.3.0",
        "numpy",
    ],
)
"""
        )

        parser = PythonManifestParser(str(setup_file))
        dependencies = parser.parse()

        assert len(dependencies) == 3
        assert {d.name for d in dependencies} == {"requests", "flask", "numpy"}

    def test_parse_pipfile(self, tmp_path):
        """Test parsing Pipfile."""
        pipfile = tmp_path / "Pipfile"
        pipfile.write_text(
            """[packages]
requests = "==2.31.0"
flask = ">=2.0.0"
numpy = "*"

[dev-packages]
pytest = "*"
black = "==23.0.0"
"""
        )

        parser = PythonManifestParser(str(pipfile))
        dependencies = parser.parse()

        # Should only return runtime dependencies
        assert len(dependencies) == 3
        assert {d.name for d in dependencies} == {"requests", "flask", "numpy"}

    def test_raises_error_for_nonexistent_file(self):
        """Test that FileNotFoundError is raised for nonexistent file."""
        parser = PythonManifestParser("/nonexistent/requirements.txt")
        with pytest.raises(FileNotFoundError):
            parser.parse()

    def test_raises_error_for_unsupported_format(self, tmp_path):
        """Test that ValueError is raised for unsupported file format."""
        unsupported_file = tmp_path / "requirements.json"
        unsupported_file.write_text('{"requests": "2.31.0"}')

        with pytest.raises(ValueError, match="Unsupported manifest format"):
            parser = PythonManifestParser(str(unsupported_file))
            parser.parse()

    def test_python_dependency_equality(self):
        """Test PythonDependency equality comparison."""
        dep1 = PythonDependency(name="requests", version_spec="==2.31.0")
        dep2 = PythonDependency(name="requests", version_spec="==2.31.0")
        dep3 = PythonDependency(name="flask", version_spec="==2.3.0")

        assert dep1 == dep2
        assert dep1 != dep3

    def test_python_dependency_repr(self):
        """Test PythonDependency string representation."""
        dep = PythonDependency(
            name="requests",
            version_spec="==2.31.0",
            extras=["security"],
            markers="sys_platform == 'linux'",
        )

        repr_str = repr(dep)
        assert "requests" in repr_str
        assert "==2.31.0" in repr_str

    def test_parse_requirements_txt_with_urls(self, tmp_path):
        """Test parsing requirements.txt with URL dependencies."""
        requirements_file = tmp_path / "requirements.txt"
        requirements_file.write_text(
            """requests==2.31.0
git+https://github.com/django/django.git@stable/4.2.x#egg=django
https://github.com/psf/black/archive/refs/tags/23.1.0.zip
"""
        )

        parser = PythonManifestParser(str(requirements_file))
        dependencies = parser.parse()

        # Should parse regular dependency and skip URL-based ones for now
        # (URL dependencies require special handling)
        assert len(dependencies) >= 1
        assert any(d.name == "requests" for d in dependencies)

    def test_parse_requirements_txt_with_editable_installs(self, tmp_path):
        """Test parsing requirements.txt with editable installs (-e flag)."""
        requirements_file = tmp_path / "requirements.txt"
        requirements_file.write_text(
            """requests==2.31.0
-e git+https://github.com/django/django.git@stable/4.2.x#egg=django
-e /path/to/local/package
flask==2.3.0
"""
        )

        parser = PythonManifestParser(str(requirements_file))
        dependencies = parser.parse()

        # Should parse regular dependencies and handle/skip editable installs
        assert len(dependencies) >= 2
        assert any(d.name == "requests" for d in dependencies)
        assert any(d.name == "flask" for d in dependencies)

    def test_parse_empty_requirements_txt(self, tmp_path):
        """Test parsing empty requirements.txt."""
        requirements_file = tmp_path / "requirements.txt"
        requirements_file.write_text("")

        parser = PythonManifestParser(str(requirements_file))
        dependencies = parser.parse()

        assert len(dependencies) == 0

    def test_parse_requirements_txt_with_complex_version_specs(self, tmp_path):
        """Test parsing requirements.txt with complex version specifiers."""
        requirements_file = tmp_path / "requirements.txt"
        requirements_file.write_text(
            """django>=3.2,<5.0
requests>=2.28.0,!=2.29.0,<3.0.0
numpy~=1.24.0
scipy===1.10.0
"""
        )

        parser = PythonManifestParser(str(requirements_file))
        dependencies = parser.parse()

        assert len(dependencies) == 4

        django = next(d for d in dependencies if d.name == "django")
        assert ">=3.2" in django.version_spec
        assert "<5.0" in django.version_spec

        requests = next(d for d in dependencies if d.name == "requests")
        assert ">=2.28.0" in requests.version_spec
        assert "!=2.29.0" in requests.version_spec

        numpy = next(d for d in dependencies if d.name == "numpy")
        assert "~=1.24.0" in numpy.version_spec

        scipy = next(d for d in dependencies if d.name == "scipy")
        assert "===1.10.0" in scipy.version_spec
