"""
ADK Core - Ascend Docker Kit Core Library

This module provides compatibility matrix resolution and Dockerfile generation
for Huawei Ascend NPU environments.
"""

from .analyzer import EnvironmentAnalyzer
from .checksum import ChecksumError, ChecksumVerifier, PackageVerifier
from .exceptions import (
    ADKError,
    CompatibilityError,
    ConfigurationError,
    DriverIncompatibleError,
    DriverNotInstalledError,
    EnvironmentDetectionError,
    FrameworkNotFoundError,
    NPUNotDetectedError,
    NPUNotSupportedError,
    OSNotSupportedError,
    VersionNotFoundError,
)
from .generator import (
    BuildContext,
    BuildTarget,
    DockerfileGenerator,
    DockerfileGeneratorError,
    GeneratorOutput,
)
from .matrix import CompatibilityResolver
from .models import (
    CANNVersionEntry,
    CompatibilityMatrix,
    EnvironmentInfo,
    FrameworkConfig,
    FrameworkType,
    QueryResult,
    SupportedArch,
    SupportedNPU,
    SupportedOS,
    ValidationResult,
)
from .version import (
    compare_versions,
    find_latest_compatible,
    get_major_minor,
    is_compatible,
    is_version_valid,
    parse_version,
    sort_versions,
)

__version__ = "0.2.0"

__all__ = [
    # Main classes
    "CompatibilityResolver",
    "EnvironmentAnalyzer",
    "DockerfileGenerator",
    # Generator types
    "BuildContext",
    "BuildTarget",
    "GeneratorOutput",
    # Checksum verification
    "ChecksumVerifier",
    "PackageVerifier",
    # Models
    "CANNVersionEntry",
    "CompatibilityMatrix",
    "EnvironmentInfo",
    "FrameworkConfig",
    "FrameworkType",
    "QueryResult",
    "SupportedArch",
    "SupportedNPU",
    "SupportedOS",
    "ValidationResult",
    # Exceptions
    "ADKError",
    "ChecksumError",
    "CompatibilityError",
    "ConfigurationError",
    "DockerfileGeneratorError",
    "DriverIncompatibleError",
    "DriverNotInstalledError",
    "EnvironmentDetectionError",
    "FrameworkNotFoundError",
    "NPUNotDetectedError",
    "NPUNotSupportedError",
    "OSNotSupportedError",
    "VersionNotFoundError",
    # Version utilities
    "compare_versions",
    "find_latest_compatible",
    "get_major_minor",
    "is_compatible",
    "is_version_valid",
    "parse_version",
    "sort_versions",
]
