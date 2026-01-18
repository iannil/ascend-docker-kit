"""
ADK Core Exceptions

Custom exception classes for the Ascend Docker Kit compatibility layer.
"""

from typing import List, Optional


class ADKError(Exception):
    """Base exception for all ADK errors."""

    def __init__(self, message: str, suggestions: Optional[List[str]] = None):
        super().__init__(message)
        self.message = message
        self.suggestions = suggestions or []

    def __str__(self) -> str:
        result = self.message
        if self.suggestions:
            result += "\n\nSuggestions:\n"
            for suggestion in self.suggestions:
                result += f"  - {suggestion}\n"
        return result


class CompatibilityError(ADKError):
    """Raised when compatibility check fails."""

    pass


class ConfigurationError(ADKError):
    """Raised when configuration file format is invalid."""

    pass


class VersionNotFoundError(ADKError):
    """Raised when a requested version does not exist in the matrix."""

    def __init__(
        self,
        version_type: str,
        version: str,
        available_versions: Optional[List[str]] = None,
    ):
        self.version_type = version_type
        self.version = version
        self.available_versions = available_versions or []

        message = f"{version_type} version '{version}' not found in compatibility matrix."
        suggestions = []
        if self.available_versions:
            suggestions.append(
                f"Available {version_type} versions: {', '.join(self.available_versions)}"
            )

        super().__init__(message, suggestions)


class DriverIncompatibleError(CompatibilityError):
    """Raised when driver version is incompatible with requested CANN version."""

    def __init__(
        self,
        driver_version: str,
        cann_version: str,
        min_required: str,
    ):
        self.driver_version = driver_version
        self.cann_version = cann_version
        self.min_required = min_required

        message = (
            f"Driver version '{driver_version}' is incompatible with CANN {cann_version}. "
            f"Minimum required driver version is '{min_required}'."
        )
        suggestions = [
            f"Upgrade your driver to version {min_required} or later",
            "Check华为官方文档获取驱动升级指南",
        ]

        super().__init__(message, suggestions)


class OSNotSupportedError(CompatibilityError):
    """Raised when OS is not supported for the requested CANN version."""

    def __init__(
        self,
        os_name: str,
        cann_version: str,
        supported_os: List[str],
    ):
        self.os_name = os_name
        self.cann_version = cann_version
        self.supported_os = supported_os

        message = f"OS '{os_name}' is not supported for CANN {cann_version}."
        suggestions = [
            f"Supported operating systems: {', '.join(supported_os)}",
        ]

        super().__init__(message, suggestions)


class NPUNotSupportedError(CompatibilityError):
    """Raised when NPU type is not supported for the requested CANN version."""

    def __init__(
        self,
        npu_type: str,
        cann_version: str,
        supported_npu: List[str],
    ):
        self.npu_type = npu_type
        self.cann_version = cann_version
        self.supported_npu = supported_npu

        message = f"NPU type '{npu_type}' is not supported for CANN {cann_version}."
        suggestions = [
            f"Supported NPU types: {', '.join(supported_npu)}",
        ]

        super().__init__(message, suggestions)


class FrameworkNotFoundError(ADKError):
    """Raised when a framework is not available for the requested CANN version."""

    def __init__(
        self,
        framework: str,
        cann_version: str,
        available_frameworks: List[str],
    ):
        self.framework = framework
        self.cann_version = cann_version
        self.available_frameworks = available_frameworks

        message = f"Framework '{framework}' is not available for CANN {cann_version}."
        suggestions = []
        if available_frameworks:
            suggestions.append(
                f"Available frameworks: {', '.join(available_frameworks)}"
            )

        super().__init__(message, suggestions)


class EnvironmentDetectionError(ADKError):
    """Raised when environment detection fails."""

    pass


class NPUNotDetectedError(EnvironmentDetectionError):
    """Raised when no NPU device is detected on the host."""

    def __init__(self, reason: str = "No NPU device found"):
        self.reason = reason
        message = f"NPU detection failed: {reason}"
        suggestions = [
            "Check if NPU hardware is properly installed",
            "Verify that the NPU driver is loaded (lsmod | grep drv_davinci)",
            "Check device files exist (/dev/davinci*)",
        ]
        super().__init__(message, suggestions)


class DriverNotInstalledError(EnvironmentDetectionError):
    """Raised when NPU driver is not installed."""

    def __init__(self, reason: str = "npu-smi command not found"):
        self.reason = reason
        message = f"NPU driver not installed: {reason}"
        suggestions = [
            "Install the Ascend NPU driver from Huawei official website",
            "Ensure npu-smi is in system PATH",
            "Check driver installation guide at: https://www.hiascend.com",
        ]
        super().__init__(message, suggestions)
