"""
Tests for ADK Core Matrix Module

Unit tests for compatibility matrix loading and querying.
"""

import pytest
from pathlib import Path

from adk_core import (
    CompatibilityResolver,
    EnvironmentInfo,
    VersionNotFoundError,
    DriverIncompatibleError,
    OSNotSupportedError,
    NPUNotSupportedError,
    FrameworkNotFoundError,
    ConfigurationError,
    is_compatible,
    compare_versions,
    sort_versions,
    is_version_valid,
)


DATA_DIR = Path(__file__).parent.parent / "data"
YAML_PATH = DATA_DIR / "compatibility.yaml"


class TestVersionUtilities:
    """Tests for version comparison utilities."""

    def test_is_version_valid(self):
        assert is_version_valid("1.0.0") is True
        assert is_version_valid("8.0.0rc3") is True
        assert is_version_valid("2.4.0.post2") is True
        assert is_version_valid("invalid") is False

    def test_compare_versions(self):
        assert compare_versions("2.0.0", "1.0.0") == 1
        assert compare_versions("1.0.0", "2.0.0") == -1
        assert compare_versions("1.0.0", "1.0.0") == 0
        assert compare_versions("8.0.0", "8.0.0rc3") == 1
        assert compare_versions("2.4.0.post2", "2.4.0") == 1

    def test_is_compatible(self):
        assert is_compatible("24.1.0", "24.0.0") is True
        assert is_compatible("23.0.0", "24.0.0") is False
        assert is_compatible("24.0.0", "24.0.0") is True

    def test_sort_versions(self):
        versions = ["1.0.0", "3.0.0", "2.0.0"]
        assert sort_versions(versions) == ["1.0.0", "2.0.0", "3.0.0"]
        assert sort_versions(versions, reverse=True) == ["3.0.0", "2.0.0", "1.0.0"]


class TestCompatibilityResolver:
    """Tests for CompatibilityResolver."""

    @pytest.fixture
    def resolver(self):
        """Create resolver from YAML file."""
        return CompatibilityResolver.from_yaml(YAML_PATH)

    def test_load_yaml(self, resolver):
        """Test YAML loading."""
        assert resolver.matrix is not None
        assert resolver.matrix.version == "1.0.0"

    def test_load_invalid_path(self):
        """Test loading from non-existent file."""
        with pytest.raises(ConfigurationError) as exc:
            CompatibilityResolver.from_yaml("nonexistent.yaml")
        assert "not found" in str(exc.value)

    def test_list_cann_versions(self, resolver):
        """Test listing CANN versions."""
        versions = resolver.list_cann_versions()
        assert "8.0.0" in versions
        assert "7.0.0" in versions
        assert "6.3.0" not in versions

        all_versions = resolver.list_cann_versions(include_deprecated=True)
        assert "6.3.0" in all_versions

    def test_get_cann_requirements(self, resolver):
        """Test getting CANN requirements."""
        result = resolver.get_cann_requirements("8.0.0")
        assert result.success is True
        assert result.data["min_driver_version"] == "24.1.rc1"
        assert "910B" in result.data["supported_npu"]
        assert "pytorch" in result.data["frameworks"]

    def test_get_cann_requirements_not_found(self, resolver):
        """Test getting requirements for non-existent version."""
        result = resolver.get_cann_requirements("99.0.0")
        assert result.success is False
        assert "not found" in result.error

    def test_find_compatible_cann(self, resolver):
        """Test finding compatible CANN versions."""
        compatible = resolver.find_compatible_cann("24.1.0")
        assert "8.0.0" in compatible
        assert "8.0.0rc3" in compatible

        compatible_old = resolver.find_compatible_cann("23.0.3")
        assert "7.0.0" in compatible_old

    def test_find_compatible_cann_with_filters(self, resolver):
        """Test finding compatible CANN with OS/NPU filters."""
        compatible = resolver.find_compatible_cann(
            "24.1.0", os_name="ubuntu22.04", npu_type="910B"
        )
        assert "8.0.0" in compatible

        no_match = resolver.find_compatible_cann(
            "24.1.0", os_name="unsupported_os"
        )
        assert len(no_match) == 0

    def test_get_framework_config(self, resolver):
        """Test getting framework configuration."""
        config = resolver.get_framework_config("8.0.0", "pytorch")
        assert config is not None
        assert config.version == "2.4.0"
        assert config.torch_npu_version == "2.4.0.post2"

    def test_find_framework_config(self, resolver):
        """Test finding framework config with QueryResult."""
        result = resolver.find_framework_config("8.0.0", "pytorch")
        assert result.success is True
        assert result.data["version"] == "2.4.0"

        result_fail = resolver.find_framework_config("8.0.0", "tensorflow")
        assert result_fail.success is False

    def test_validate_environment(self, resolver):
        """Test environment validation."""
        env = EnvironmentInfo(
            driver_version="24.1.0",
            os_name="ubuntu22.04",
            npu_type="910B",
            arch="x86_64",
        )
        result = resolver.validate_environment(env)
        assert result.valid is True
        assert "8.0.0" in result.compatible_cann_versions

    def test_validate_environment_incompatible(self, resolver):
        """Test validation with incompatible environment."""
        env = EnvironmentInfo(
            driver_version="20.0.0",
            os_name="ubuntu22.04",
            npu_type="910B",
            arch="x86_64",
        )
        result = resolver.validate_environment(env)
        assert result.valid is False
        assert len(result.errors) > 0


class TestExceptions:
    """Tests for custom exceptions."""

    @pytest.fixture
    def resolver(self):
        return CompatibilityResolver.from_yaml(YAML_PATH)

    def test_version_not_found_error(self, resolver):
        """Test VersionNotFoundError."""
        with pytest.raises(VersionNotFoundError) as exc:
            resolver.get_cann_entry("99.0.0")
        assert "99.0.0" in str(exc.value)
        assert "CANN" in str(exc.value)

    def test_driver_incompatible_error(self, resolver):
        """Test DriverIncompatibleError."""
        with pytest.raises(DriverIncompatibleError) as exc:
            resolver.check_driver_compatibility("20.0.0", "8.0.0")
        assert "20.0.0" in str(exc.value)
        assert "8.0.0" in str(exc.value)

    def test_os_not_supported_error(self, resolver):
        """Test OSNotSupportedError."""
        with pytest.raises(OSNotSupportedError) as exc:
            resolver.check_os_compatibility("unsupported_os", "8.0.0")
        assert "unsupported_os" in str(exc.value)

    def test_npu_not_supported_error(self, resolver):
        """Test NPUNotSupportedError."""
        with pytest.raises(NPUNotSupportedError) as exc:
            resolver.check_npu_compatibility("unsupported_npu", "8.0.0")
        assert "unsupported_npu" in str(exc.value)

    def test_framework_not_found_error(self, resolver):
        """Test FrameworkNotFoundError."""
        with pytest.raises(FrameworkNotFoundError) as exc:
            resolver.get_framework("8.0.0", "tensorflow")
        assert "tensorflow" in str(exc.value)


class TestRecommendation:
    """Tests for recommendation features."""

    @pytest.fixture
    def resolver(self):
        return CompatibilityResolver.from_yaml(YAML_PATH)

    def test_get_recommended_cann(self, resolver):
        """Test getting recommended CANN version."""
        recommended = resolver.get_recommended_cann("24.1.0")
        assert recommended is not None
        assert recommended == "8.0.0"

    def test_get_recommended_cann_with_constraints(self, resolver):
        """Test recommendation with constraints."""
        recommended = resolver.get_recommended_cann(
            "24.1.0", os_name="ubuntu22.04", npu_type="910B"
        )
        assert recommended == "8.0.0"

    def test_get_recommended_cann_no_match(self, resolver):
        """Test recommendation when no match found."""
        recommended = resolver.get_recommended_cann(
            "10.0.0", os_name="unsupported"
        )
        assert recommended is None
