"""
ADK Compatibility Matrix

Core logic for querying CANN/driver/framework compatibility information.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import yaml
from pydantic import ValidationError

# Module-level cache for parsed YAML files: {(path, mtime): CompatibilityMatrix}
# Note: Cache is not thread-safe. For multi-threaded use, add locking.
_yaml_cache: Dict[Tuple[str, float], "CompatibilityMatrix"] = {}


def clear_yaml_cache() -> None:
    """Clear the YAML file cache. Useful for testing or after file updates."""
    _yaml_cache.clear()

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
from .version import compare_versions, is_compatible, sort_versions


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

        Uses module-level cache keyed by file path and modification time
        to avoid re-parsing unchanged files.

        Args:
            path: Path to compatibility.yaml

        Returns:
            CompatibilityResolver instance

        Raises:
            ConfigurationError: If file is invalid or cannot be parsed
        """
        path = Path(path).resolve()

        if not path.exists():
            raise ConfigurationError(
                f"Configuration file not found: {path}",
                suggestions=[f"Ensure {path} exists in the project root"],
            )

        # Check cache using file path and modification time
        mtime = path.stat().st_mtime
        cache_key = (str(path), mtime)

        if cache_key in _yaml_cache:
            return cls(_yaml_cache[cache_key])

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

        # Store in cache
        _yaml_cache[cache_key] = matrix

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
            QueryResult with the following structure:
            - success (bool): True if version was found
            - data (dict): When success=True, contains:
                - cann_version (str): The queried CANN version
                - min_driver_version (str): Minimum required driver version
                - max_driver_version (str|None): Maximum supported driver version
                - supported_os (list[str]): List of supported OS names
                - supported_npu (list[str]): List of supported NPU types
                - supported_arch (list[str]): List of supported architectures
                - frameworks (list[str]): Available framework names
                - deprecated (bool): Whether this version is deprecated
            - error (str): When success=False, error message
            - suggestions (list[str]): Helpful suggestions
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
            List of compatible CANN version strings, sorted in descending order
            (newest first). Returns empty list if no compatible versions found.
            Only non-deprecated versions are included.
        """
        compatible = []

        for version, entry in self._matrix.cann_versions.items():
            if entry.deprecated:
                continue

            if not is_compatible(driver_version, entry.min_driver_version):
                continue

            if entry.max_driver_version:
                # Skip if driver version exceeds maximum supported
                if compare_versions(driver_version, entry.max_driver_version) > 0:
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
            framework: Framework name (e.g., "pytorch", "mindspore")

        Returns:
            QueryResult with the following structure:
            - success (bool): True if framework config was found
            - data (dict): When success=True, contains:
                - framework (str): Framework name
                - version (str): Framework version (e.g., "2.4.0")
                - torch_npu_version (str|None): torch_npu version for PyTorch
                - python_versions (list[str]): Supported Python versions
                - whl_url (str|None): Download URL for pre-built wheel
                - install_command (str|None): Alternative installation command
            - error (str): When success=False, error message
            - suggestions (list[str]): Available frameworks or versions
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
            env: Environment information containing driver_version, os_name,
                 npu_type, arch, and optional firmware_version/npu_count

        Returns:
            ValidationResult with the following structure:
            - valid (bool): True if at least one compatible CANN version exists
            - compatible_cann_versions (list[str]): Compatible versions sorted
              descending (newest first). Empty if validation fails.
            - errors (list[str]): List of error messages. Non-empty when valid=False.
              Contains details about why no compatible version was found.
            - warnings (list[str]): Non-fatal warnings (e.g., deprecated versions)
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

            if entry.max_driver_version:
                if compare_versions(env.driver_version, entry.max_driver_version) > 0:
                    version_errors.append(
                        f"Driver {env.driver_version} > max supported {entry.max_driver_version}"
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
                min_required=entry.min_driver_version,
            )

        if entry.max_driver_version:
            if compare_versions(driver_version, entry.max_driver_version) > 0:
                raise DriverIncompatibleError(
                    driver_version,
                    cann_version,
                    max_allowed=entry.max_driver_version,
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
            os_name: Operating system name (optional filter)
            npu_type: NPU type (optional filter)

        Returns:
            The latest compatible CANN version string (e.g., "8.0.0"),
            or None if no compatible version exists for the given environment.
        """
        compatible = self.find_compatible_cann(driver_version, os_name, npu_type)
        return compatible[0] if compatible else None
