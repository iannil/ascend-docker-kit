"""
ADK Core - Ascend Docker Kit Core Library

This module provides compatibility matrix resolution for Huawei Ascend NPU environments.
"""

from .analyzer import EnvironmentAnalyzer
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

__version__ = "0.1.0"

__all__ = [
    # Main classes
    "CompatibilityResolver",
    "EnvironmentAnalyzer",
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
    "CompatibilityError",
    "ConfigurationError",
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
