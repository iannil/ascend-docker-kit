"""
ADK Compatibility Matrix

Core logic for querying CANN/driver/framework compatibility information.
"""

from pathlib import Path
from typing import Dict, List, Optional, Union

import yaml
from pydantic import ValidationError

from .exceptions import (
    ConfigurationError,
    DriverIncompatibleError,
    FrameworkNotFoundError,
    NPUNotSupportedError,
    OSNotSupportedError,
    VersionNotFoundError,
)
from .models import (
    CANNVersionEntry,
    CompatibilityMatrix,
    EnvironmentInfo,
    FrameworkConfig,
    QueryResult,
    ValidationResult,
)
from .version import is_compatible, sort_versions


class CompatibilityResolver:
    """
    Resolver for CANN compatibility queries.

    Provides methods to query compatibility information and validate environments.
    """

    def __init__(self, matrix: CompatibilityMatrix):
        """
        Initialize resolver with a compatibility matrix.

        Args:
            matrix: Parsed compatibility matrix
        """
        self._matrix = matrix

    @classmethod
    def from_yaml(cls, path: Union[str, Path]) -> "CompatibilityResolver":
        """
        Create resolver from YAML file.

        Args:
            path: Path to compatibility.yaml

        Returns:
            CompatibilityResolver instance

        Raises:
            ConfigurationError: If file is invalid or cannot be parsed
        """
        path = Path(path)

        if not path.exists():
            raise ConfigurationError(
                f"Configuration file not found: {path}",
                suggestions=[f"Ensure {path} exists in the project root"],
            )

        try:
            with open(path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise ConfigurationError(
                f"Invalid YAML format in {path}: {e}",
                suggestions=["Check YAML syntax", "Validate file encoding is UTF-8"],
            )

        try:
            matrix = CompatibilityMatrix(**data)
        except ValidationError as e:
            raise ConfigurationError(
                f"Invalid configuration schema: {e}",
                suggestions=["Check field types and required fields"],
            )

        return cls(matrix)

    @property
    def matrix(self) -> CompatibilityMatrix:
        """Get the underlying compatibility matrix."""
        return self._matrix

    def list_cann_versions(self, include_deprecated: bool = False) -> List[str]:
        """
        List available CANN versions.

        Args:
            include_deprecated: Whether to include deprecated versions

        Returns:
            List of CANN version strings, sorted descending
        """
        versions = []
        for v, entry in self._matrix.cann_versions.items():
            if include_deprecated or not entry.deprecated:
                versions.append(v)
        return sort_versions(versions, reverse=True)

    def get_cann_requirements(self, cann_version: str) -> QueryResult:
        """
        Get requirements for a specific CANN version.

        Args:
            cann_version: CANN version string

        Returns:
            QueryResult with driver, OS, NPU, and framework requirements
        """
        entry = self._matrix.get_cann_version(cann_version)
        if entry is None:
            return QueryResult(
                success=False,
                error=f"CANN version '{cann_version}' not found",
                suggestions=[
                    f"Available versions: {', '.join(self.list_cann_versions())}"
                ],
            )

        return QueryResult(
            success=True,
            data={
                "cann_version": cann_version,
                "min_driver_version": entry.min_driver_version,
                "max_driver_version": entry.max_driver_version,
                "supported_os": entry.supported_os,
                "supported_npu": entry.supported_npu,
                "supported_arch": entry.supported_arch,
                "frameworks": list(entry.frameworks.keys()),
                "deprecated": entry.deprecated,
            },
        )

    def find_compatible_cann(
        self,
        driver_version: str,
        os_name: Optional[str] = None,
        npu_type: Optional[str] = None,
    ) -> List[str]:
        """
        Find CANN versions compatible with the given environment.

        Args:
            driver_version: Current driver version
            os_name: Operating system name (optional filter)
            npu_type: NPU type (optional filter)

        Returns:
            List of compatible CANN versions, sorted descending
        """
        compatible = []

        for version, entry in self._matrix.cann_versions.items():
            if entry.deprecated:
                continue

            if not is_compatible(driver_version, entry.min_driver_version):
                continue

            if entry.max_driver_version:
                if is_compatible(driver_version, entry.max_driver_version):
                    if driver_version > entry.max_driver_version:
                        continue

            if os_name and os_name not in entry.supported_os:
                continue

            if npu_type and npu_type not in entry.supported_npu:
                continue

            compatible.append(version)

        return sort_versions(compatible, reverse=True)

    def get_framework_config(
        self, cann_version: str, framework: str
    ) -> Optional[FrameworkConfig]:
        """
        Get framework configuration for a CANN version.

        Args:
            cann_version: CANN version string
            framework: Framework name (pytorch, mindspore)

        Returns:
            FrameworkConfig or None if not found
        """
        entry = self._matrix.get_cann_version(cann_version)
        if entry is None:
            return None
        return entry.frameworks.get(framework)

    def find_framework_config(
        self, cann_version: str, framework: str
    ) -> QueryResult:
        """
        Find framework configuration with detailed result.

        Args:
            cann_version: CANN version string
            framework: Framework name

        Returns:
            QueryResult with framework configuration
        """
        entry = self._matrix.get_cann_version(cann_version)
        if entry is None:
            return QueryResult(
                success=False,
                error=f"CANN version '{cann_version}' not found",
                suggestions=[
                    f"Available versions: {', '.join(self.list_cann_versions())}"
                ],
            )

        config = entry.frameworks.get(framework)
        if config is None:
            available = list(entry.frameworks.keys())
            return QueryResult(
                success=False,
                error=f"Framework '{framework}' not available for CANN {cann_version}",
                suggestions=[f"Available frameworks: {', '.join(available)}"],
            )

        return QueryResult(
            success=True,
            data={
                "framework": framework,
                "version": config.version,
                "torch_npu_version": config.torch_npu_version,
                "python_versions": config.python_versions,
                "whl_url": config.whl_url,
                "install_command": config.install_command,
            },
        )

    def validate_environment(self, env: EnvironmentInfo) -> ValidationResult:
        """
        Validate environment against compatibility matrix.

        Args:
            env: Environment information

        Returns:
            ValidationResult with compatibility status
        """
        errors: List[str] = []
        warnings: List[str] = []
        compatible_versions: List[str] = []

        for version, entry in self._matrix.cann_versions.items():
            version_errors: List[str] = []

            if not is_compatible(env.driver_version, entry.min_driver_version):
                version_errors.append(
                    f"Driver {env.driver_version} < required {entry.min_driver_version}"
                )

            if env.os_name not in entry.supported_os:
                version_errors.append(f"OS {env.os_name} not supported")

            if env.npu_type not in entry.supported_npu:
                version_errors.append(f"NPU {env.npu_type} not supported")

            if env.arch not in entry.supported_arch:
                version_errors.append(f"Architecture {env.arch} not supported")

            if not version_errors:
                if entry.deprecated:
                    warnings.append(f"CANN {version} is deprecated")
                compatible_versions.append(version)

        if not compatible_versions:
            errors.append("No compatible CANN versions found for this environment")
            errors.append(f"Driver: {env.driver_version}, OS: {env.os_name}, NPU: {env.npu_type}")

        return ValidationResult(
            valid=len(errors) == 0,
            compatible_cann_versions=sort_versions(compatible_versions, reverse=True),
            errors=errors,
            warnings=warnings,
        )

    def get_cann_entry(self, cann_version: str) -> CANNVersionEntry:
        """
        Get CANN version entry, raising exception if not found.

        Args:
            cann_version: CANN version string

        Returns:
            CANNVersionEntry

        Raises:
            VersionNotFoundError: If version not found
        """
        entry = self._matrix.get_cann_version(cann_version)
        if entry is None:
            raise VersionNotFoundError(
                "CANN",
                cann_version,
                self.list_cann_versions(include_deprecated=True),
            )
        return entry

    def check_driver_compatibility(
        self, driver_version: str, cann_version: str
    ) -> None:
        """
        Check if driver is compatible with CANN version.

        Args:
            driver_version: Current driver version
            cann_version: Target CANN version

        Raises:
            VersionNotFoundError: If CANN version not found
            DriverIncompatibleError: If driver is incompatible
        """
        entry = self.get_cann_entry(cann_version)

        if not is_compatible(driver_version, entry.min_driver_version):
            raise DriverIncompatibleError(
                driver_version,
                cann_version,
                entry.min_driver_version,
            )

    def check_os_compatibility(self, os_name: str, cann_version: str) -> None:
        """
        Check if OS is compatible with CANN version.

        Args:
            os_name: Operating system name
            cann_version: Target CANN version

        Raises:
            VersionNotFoundError: If CANN version not found
            OSNotSupportedError: If OS is not supported
        """
        entry = self.get_cann_entry(cann_version)

        if os_name not in entry.supported_os:
            raise OSNotSupportedError(
                os_name,
                cann_version,
                entry.supported_os,
            )

    def check_npu_compatibility(self, npu_type: str, cann_version: str) -> None:
        """
        Check if NPU is compatible with CANN version.

        Args:
            npu_type: NPU type
            cann_version: Target CANN version

        Raises:
            VersionNotFoundError: If CANN version not found
            NPUNotSupportedError: If NPU is not supported
        """
        entry = self.get_cann_entry(cann_version)

        if npu_type not in entry.supported_npu:
            raise NPUNotSupportedError(
                npu_type,
                cann_version,
                entry.supported_npu,
            )

    def get_framework(
        self, cann_version: str, framework: str
    ) -> FrameworkConfig:
        """
        Get framework configuration, raising exception if not found.

        Args:
            cann_version: CANN version string
            framework: Framework name

        Returns:
            FrameworkConfig

        Raises:
            VersionNotFoundError: If CANN version not found
            FrameworkNotFoundError: If framework not available
        """
        entry = self.get_cann_entry(cann_version)

        config = entry.frameworks.get(framework)
        if config is None:
            raise FrameworkNotFoundError(
                framework,
                cann_version,
                list(entry.frameworks.keys()),
            )
        return config

    def get_recommended_cann(
        self,
        driver_version: str,
        os_name: Optional[str] = None,
        npu_type: Optional[str] = None,
    ) -> Optional[str]:
        """
        Get recommended (latest compatible) CANN version.

        Args:
            driver_version: Current driver version
            os_name: Operating system name (optional)
            npu_type: NPU type (optional)

        Returns:
            Recommended CANN version or None
        """
        compatible = self.find_compatible_cann(driver_version, os_name, npu_type)
        return compatible[0] if compatible else None
