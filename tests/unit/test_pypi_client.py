"""Tests for PyPI client with transitive dependency resolution."""

from unittest.mock import Mock, patch

import pytest

from repo_cloner.pypi_client import (
    PyPIClient,
    PyPIPackage,
    ResolvedDependency,
    VersionConflictError,
)
from repo_cloner.python_parser import PythonDependency


class TestPyPIClient:
    """Test suite for PyPIClient class."""

    def test_fetch_package_metadata_from_pypi(self):
        """Test fetching package metadata from PyPI JSON API."""
        client = PyPIClient()

        # Mock response from PyPI JSON API
        mock_response = {
            "info": {
                "name": "requests",
                "version": "2.31.0",
                "requires_dist": [
                    "charset-normalizer (<4,>=2)",
                    "idna (<4,>=2.5)",
                    "urllib3 (<3,>=1.21.1)",
                    "certifi (>=2017.4.17)",
                ],
            },
            "urls": [
                {
                    "packagetype": "bdist_wheel",
                    "filename": "requests-2.31.0-py3-none-any.whl",
                    "url": "https://files.pythonhosted.org/packages/.../"
                    "requests-2.31.0-py3-none-any.whl",
                    "digests": {"sha256": "abc123..."},
                },
                {
                    "packagetype": "sdist",
                    "filename": "requests-2.31.0.tar.gz",
                    "url": "https://files.pythonhosted.org/packages/.../requests-2.31.0.tar.gz",
                    "digests": {"sha256": "def456..."},
                },
            ],
        }

        mock_response_obj = Mock()
        mock_response_obj.json.return_value = mock_response
        mock_response_obj.status_code = 200

        with patch.object(client.session, "get", return_value=mock_response_obj):
            package = client.fetch_package_metadata("requests", "2.31.0")

            assert package.name == "requests"
            assert package.version == "2.31.0"
            assert len(package.dependencies) == 4
            assert any(dep.startswith("charset-normalizer") for dep in package.dependencies)

    def test_fetch_package_metadata_with_authentication(self):
        """Test fetching from private PyPI with authentication."""
        client = PyPIClient(
            index_url="https://pypi.example.com/simple",
            username="user",
            password="pass",
        )

        mock_response = {
            "info": {
                "name": "private-package",
                "version": "1.0.0",
                "requires_dist": [],
            },
            "urls": [],
        }

        mock_response_obj = Mock()
        mock_response_obj.json.return_value = mock_response
        mock_response_obj.status_code = 200

        with patch.object(client.session, "get", return_value=mock_response_obj):
            package = client.fetch_package_metadata("private-package", "1.0.0")

            # Verify authentication is configured on the session
            assert client.session.auth == ("user", "pass")
            assert package.name == "private-package"

    def test_resolve_transitive_dependencies_simple(self):
        """Test resolving transitive dependencies (A → B, A → C)."""
        client = PyPIClient()

        # Mock package metadata
        packages = {
            "myapp": PyPIPackage(
                name="myapp",
                version="1.0.0",
                dependencies=["requests>=2.31.0", "flask>=2.0.0"],
                wheel_url="",
                sdist_url="",
                wheel_sha256="",
                sdist_sha256="",
            ),
            "requests": PyPIPackage(
                name="requests",
                version="2.31.0",
                dependencies=["urllib3>=1.21.1"],
                wheel_url="",
                sdist_url="",
                wheel_sha256="",
                sdist_sha256="",
            ),
            "flask": PyPIPackage(
                name="flask",
                version="2.3.0",
                dependencies=["werkzeug>=2.0.0"],
                wheel_url="",
                sdist_url="",
                wheel_sha256="",
                sdist_sha256="",
            ),
            "urllib3": PyPIPackage(
                name="urllib3",
                version="1.26.0",
                dependencies=[],
                wheel_url="",
                sdist_url="",
                wheel_sha256="",
                sdist_sha256="",
            ),
            "werkzeug": PyPIPackage(
                name="werkzeug",
                version="2.3.0",
                dependencies=[],
                wheel_url="",
                sdist_url="",
                wheel_sha256="",
                sdist_sha256="",
            ),
        }

        with patch.object(
            client, "fetch_package_metadata", side_effect=lambda name, version: packages.get(name)
        ):
            root_deps = [
                PythonDependency(name="requests", version_spec=">=2.31.0"),
                PythonDependency(name="flask", version_spec=">=2.0.0"),
            ]

            resolved = client.resolve_dependencies(root_deps)

            # Should resolve requests, flask, urllib3, werkzeug
            assert len(resolved) >= 4
            assert any(dep.name == "requests" for dep in resolved)
            assert any(dep.name == "flask" for dep in resolved)
            assert any(dep.name == "urllib3" for dep in resolved)
            assert any(dep.name == "werkzeug" for dep in resolved)

    def test_resolve_transitive_dependencies_diamond(self):
        """Test resolving diamond dependency (A → B → D, A → C → D)."""
        client = PyPIClient()

        # Mock diamond dependency structure
        packages = {
            "pkgb": PyPIPackage(
                name="pkgB",
                version="1.0.0",
                dependencies=["pkgD>=1.0.0"],
                wheel_url="http://test/pkgB-1.0.0-py3-none-any.whl",
                sdist_url="",
                wheel_sha256="",
                sdist_sha256="",
            ),
            "pkgc": PyPIPackage(
                name="pkgC",
                version="1.0.0",
                dependencies=["pkgD>=1.0.0"],
                wheel_url="http://test/pkgC-1.0.0-py3-none-any.whl",
                sdist_url="",
                wheel_sha256="",
                sdist_sha256="",
            ),
            "pkgd": PyPIPackage(
                name="pkgD",
                version="1.5.0",
                dependencies=[],
                wheel_url="http://test/pkgD-1.5.0-py3-none-any.whl",
                sdist_url="",
                wheel_sha256="",
                sdist_sha256="",
            ),
        }

        with patch.object(
            client,
            "fetch_package_metadata",
            side_effect=lambda name, version: packages.get(name.lower()),
        ):
            with patch.object(
                client,
                "_find_compatible_version",
                side_effect=lambda name, specs: "1.0.0" if name in ["pkgb", "pkgc"] else "1.5.0",
            ):
                root_deps = [
                    PythonDependency(name="pkgB", version_spec=">=1.0.0"),
                    PythonDependency(name="pkgC", version_spec=">=1.0.0"),
                ]

                resolved = client.resolve_dependencies(root_deps)

                # Should resolve B, C, and D only once
                pkg_d_count = sum(1 for dep in resolved if dep.name == "pkgD")
                assert pkg_d_count == 1  # Diamond dependency resolved once

    def test_version_conflict_detection(self):
        """Test detection of conflicting version requirements."""
        client = PyPIClient()

        # Mock packages with conflicting requirements
        packages = {
            "pkga": PyPIPackage(
                name="pkgA",
                version="1.0.0",
                dependencies=["pkgC>=2.0.0"],
                wheel_url="http://test/pkgA-1.0.0-py3-none-any.whl",
                sdist_url="",
                wheel_sha256="",
                sdist_sha256="",
            ),
            "pkgb": PyPIPackage(
                name="pkgB",
                version="1.0.0",
                dependencies=["pkgC<1.5.0"],
                wheel_url="http://test/pkgB-1.0.0-py3-none-any.whl",
                sdist_url="",
                wheel_sha256="",
                sdist_sha256="",
            ),
        }

        # Mock _find_compatible_version to return None for conflicting pkgC
        def mock_find_version(name, specs):
            if name == "pkga" or name == "pkgb":
                return "1.0.0"
            elif name == "pkgc":
                # Simulate conflict - cannot satisfy both >=2.0.0 and <1.5.0
                return None
            return "1.0.0"

        with patch.object(
            client,
            "fetch_package_metadata",
            side_effect=lambda name, version: packages.get(name.lower()),
        ):
            with patch.object(client, "_find_compatible_version", side_effect=mock_find_version):
                root_deps = [
                    PythonDependency(name="pkgA", version_spec=">=1.0.0"),
                    PythonDependency(name="pkgB", version_spec=">=1.0.0"),
                ]

                with pytest.raises(VersionConflictError, match="pkgC"):
                    client.resolve_dependencies(root_deps)

    def test_download_package_wheel(self, tmp_path):
        """Test downloading wheel package."""
        client = PyPIClient()
        output_dir = tmp_path / "packages"
        output_dir.mkdir()

        package = PyPIPackage(
            name="requests",
            version="2.31.0",
            dependencies=[],
            wheel_url="https://files.pythonhosted.org/packages/.../"
            "requests-2.31.0-py3-none-any.whl",
            sdist_url="",
            wheel_sha256="abc123def456",
            sdist_sha256="",
        )

        mock_content = b"fake wheel content"
        mock_response_obj = Mock()
        mock_response_obj.content = mock_content
        mock_response_obj.status_code = 200

        with patch.object(client.session, "get", return_value=mock_response_obj):
            downloaded_path = client.download_package(package, str(output_dir), prefer_wheel=True)

            assert downloaded_path.exists()
            assert downloaded_path.name == "requests-2.31.0-py3-none-any.whl"
            assert downloaded_path.read_bytes() == mock_content

    def test_download_package_sdist_fallback(self, tmp_path):
        """Test falling back to sdist when wheel is not available."""
        client = PyPIClient()
        output_dir = tmp_path / "packages"
        output_dir.mkdir()

        package = PyPIPackage(
            name="mypackage",
            version="1.0.0",
            dependencies=[],
            wheel_url="",  # No wheel
            sdist_url="https://files.pythonhosted.org/packages/.../mypackage-1.0.0.tar.gz",
            wheel_sha256="",
            sdist_sha256="def456abc789",
        )

        mock_content = b"fake sdist content"
        mock_response_obj = Mock()
        mock_response_obj.content = mock_content
        mock_response_obj.status_code = 200

        with patch.object(client.session, "get", return_value=mock_response_obj):
            downloaded_path = client.download_package(package, str(output_dir), prefer_wheel=True)

            assert downloaded_path.exists()
            assert downloaded_path.name == "mypackage-1.0.0.tar.gz"

    def test_verify_package_checksum(self, tmp_path):
        """Test SHA256 checksum verification of downloaded packages."""
        client = PyPIClient()

        # Create test file with known content
        test_file = tmp_path / "package.whl"
        test_content = b"test content for checksum"
        test_file.write_bytes(test_content)

        # Calculate expected SHA256
        import hashlib

        expected_sha256 = hashlib.sha256(test_content).hexdigest()

        # Verification should pass with correct checksum
        assert client.verify_checksum(test_file, expected_sha256) is True

        # Verification should fail with incorrect checksum
        assert client.verify_checksum(test_file, "wrongchecksum123") is False

    def test_generate_offline_requirements(self, tmp_path):
        """Test generating offline-compatible requirements.txt."""
        client = PyPIClient()
        output_dir = tmp_path / "packages"
        output_dir.mkdir()

        # Create fake package files
        (output_dir / "requests-2.31.0-py3-none-any.whl").write_text("fake")
        (output_dir / "urllib3-1.26.0-py3-none-any.whl").write_text("fake")

        resolved = [
            ResolvedDependency(
                name="requests",
                version="2.31.0",
                filename="requests-2.31.0-py3-none-any.whl",
            ),
            ResolvedDependency(
                name="urllib3",
                version="1.26.0",
                filename="urllib3-1.26.0-py3-none-any.whl",
            ),
        ]

        requirements_file = client.generate_offline_requirements(resolved, str(output_dir))

        assert requirements_file.exists()
        content = requirements_file.read_text()

        # Should contain relative paths to local files
        assert "requests-2.31.0-py3-none-any.whl" in content
        assert "urllib3-1.26.0-py3-none-any.whl" in content

    def test_download_all_resolved_dependencies(self, tmp_path):
        """Test downloading all resolved dependencies."""
        client = PyPIClient()
        output_dir = tmp_path / "packages"
        output_dir.mkdir()

        resolved = [
            ResolvedDependency(
                name="requests",
                version="2.31.0",
                filename="requests-2.31.0-py3-none-any.whl",
            ),
            ResolvedDependency(
                name="flask",
                version="2.3.0",
                filename="flask-2.3.0-py3-none-any.whl",
            ),
        ]

        packages = {
            "requests": PyPIPackage(
                name="requests",
                version="2.31.0",
                dependencies=[],
                wheel_url="https://example.com/requests.whl",
                sdist_url="",
                wheel_sha256="abc123",
                sdist_sha256="",
            ),
            "flask": PyPIPackage(
                name="flask",
                version="2.3.0",
                dependencies=[],
                wheel_url="https://example.com/flask.whl",
                sdist_url="",
                wheel_sha256="def456",
                sdist_sha256="",
            ),
        }

        with patch.object(
            client, "fetch_package_metadata", side_effect=lambda name, version: packages.get(name)
        ):
            with patch.object(client, "download_package") as mock_download:
                mock_download.side_effect = [
                    output_dir / "requests-2.31.0-py3-none-any.whl",
                    output_dir / "flask-2.3.0-py3-none-any.whl",
                ]

                downloaded = client.download_all(resolved, str(output_dir))

                assert len(downloaded) == 2
                assert mock_download.call_count == 2

    def test_pypi_package_equality(self):
        """Test PyPIPackage equality comparison."""
        pkg1 = PyPIPackage(
            name="requests",
            version="2.31.0",
            dependencies=[],
            wheel_url="https://example.com/wheel",
            sdist_url="",
            wheel_sha256="abc",
            sdist_sha256="",
        )
        pkg2 = PyPIPackage(
            name="requests",
            version="2.31.0",
            dependencies=[],
            wheel_url="https://example.com/wheel",
            sdist_url="",
            wheel_sha256="abc",
            sdist_sha256="",
        )
        pkg3 = PyPIPackage(
            name="flask",
            version="2.3.0",
            dependencies=[],
            wheel_url="",
            sdist_url="",
            wheel_sha256="",
            sdist_sha256="",
        )

        assert pkg1 == pkg2
        assert pkg1 != pkg3

    def test_resolved_dependency_to_dict(self):
        """Test ResolvedDependency serialization to dict."""
        dep = ResolvedDependency(
            name="requests",
            version="2.31.0",
            filename="requests-2.31.0-py3-none-any.whl",
        )

        dep_dict = dep.to_dict()

        assert dep_dict["name"] == "requests"
        assert dep_dict["version"] == "2.31.0"
        assert dep_dict["filename"] == "requests-2.31.0-py3-none-any.whl"

    def test_handle_network_errors_gracefully(self):
        """Test graceful handling of network errors."""
        client = PyPIClient()

        with patch.object(
            client.session, "get", side_effect=ConnectionError("Network unreachable")
        ):
            with pytest.raises(ConnectionError):
                client.fetch_package_metadata("requests", "2.31.0")

    def test_handle_package_not_found(self):
        """Test handling of non-existent package."""
        client = PyPIClient()

        mock_response_obj = Mock()
        mock_response_obj.status_code = 404

        with patch.object(client.session, "get", return_value=mock_response_obj):
            with pytest.raises(ValueError, match="Package not found"):
                client.fetch_package_metadata("nonexistent-package", "1.0.0")

    def test_parse_version_specifier(self):
        """Test parsing complex version specifiers."""
        client = PyPIClient()

        # Test various version specifier formats
        specs = [
            (">=2.0.0", True),
            ("==2.0.0", True),
            ("<3.0.0", True),
            (">=2.0,<3.0", True),
            ("~=2.4.0", True),
            ("!=2.5.0", True),
        ]

        for spec, expected in specs:
            result = client.parse_version_specifier(spec)
            assert result is not None
