"""
ADK Data Models

Pydantic v2 models for type-safe compatibility matrix data.
"""

from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, Field, field_validator

from .version import is_version_valid


class SupportedOS(str, Enum):
    """Supported operating systems."""

    UBUNTU_20_04 = "ubuntu20.04"
    UBUNTU_22_04 = "ubuntu22.04"
    UBUNTU_24_04 = "ubuntu24.04"
    OPENEULER_22_03 = "openEuler22.03"
    OPENEULER_24_03 = "openEuler24.03"
    KYLIN_V10 = "kylinV10"


class SupportedNPU(str, Enum):
    """Supported NPU types."""

    ATLAS_910A = "910A"
    ATLAS_910B = "910B"
    ATLAS_910B2 = "910B2"
    ATLAS_910B3 = "910B3"
    ATLAS_310P = "310P"
    ATLAS_310 = "310"


class SupportedArch(str, Enum):
    """Supported CPU architectures."""

    X86_64 = "x86_64"
    AARCH64 = "aarch64"


class FrameworkType(str, Enum):
    """Supported deep learning frameworks."""

    PYTORCH = "pytorch"
    MINDSPORE = "mindspore"


class FrameworkConfig(BaseModel):
    """Configuration for a deep learning framework."""

    version: str = Field(..., description="Framework version")
    torch_npu_version: Optional[str] = Field(
        None, description="torch_npu version (PyTorch only)"
    )
    python_versions: List[str] = Field(
        ..., description="Supported Python versions", min_length=1
    )
    whl_url: Optional[str] = Field(
        None, description="Download URL for pre-built wheel"
    )
    install_command: Optional[str] = Field(
        None, description="Alternative installation command"
    )

    @field_validator("version")
    @classmethod
    def validate_version(cls, v: str) -> str:
        if not is_version_valid(v):
            raise ValueError(f"Invalid version format: {v}")
        return v

    @field_validator("python_versions")
    @classmethod
    def validate_python_versions(cls, v: List[str]) -> List[str]:
        for pv in v:
            if not pv.replace(".", "").isdigit():
                raise ValueError(f"Invalid Python version format: {pv}")
        return v


class CANNVersionEntry(BaseModel):
    """Configuration for a single CANN version."""

    min_driver_version: str = Field(..., description="Minimum driver version required")
    max_driver_version: Optional[str] = Field(
        None, description="Maximum driver version supported"
    )
    supported_os: List[str] = Field(
        ..., description="Supported operating systems", min_length=1
    )
    supported_npu: List[str] = Field(
        ..., description="Supported NPU types", min_length=1
    )
    supported_arch: List[str] = Field(
        ..., description="Supported CPU architectures", min_length=1
    )
    frameworks: Dict[str, FrameworkConfig] = Field(
        default_factory=dict, description="Framework configurations"
    )
    cann_toolkit_url: Optional[str] = Field(
        None, description="Download URL for CANN toolkit"
    )
    kernels_url: Optional[str] = Field(
        None, description="Download URL for CANN kernels"
    )
    release_notes: Optional[str] = Field(None, description="URL to release notes")
    deprecated: bool = Field(False, description="Whether this version is deprecated")

    @field_validator("min_driver_version")
    @classmethod
    def validate_driver_version(cls, v: str) -> str:
        if not is_version_valid(v):
            raise ValueError(f"Invalid driver version format: {v}")
        return v


class CompatibilityMatrix(BaseModel):
    """Root model for the compatibility matrix."""

    version: str = Field(..., description="Matrix schema version")
    last_updated: str = Field(..., description="Last update date (YYYY-MM-DD)")
    cann_versions: Dict[str, CANNVersionEntry] = Field(
        ..., description="CANN version configurations", min_length=1
    )

    @field_validator("version")
    @classmethod
    def validate_matrix_version(cls, v: str) -> str:
        if not is_version_valid(v):
            raise ValueError(f"Invalid matrix version format: {v}")
        return v

    def get_cann_version(self, version: str) -> Optional[CANNVersionEntry]:
        """Get CANN version entry by version string."""
        return self.cann_versions.get(version)

    def list_cann_versions(self) -> List[str]:
        """List all available CANN versions."""
        return list(self.cann_versions.keys())

    def list_frameworks(self, cann_version: str) -> List[str]:
        """List available frameworks for a CANN version."""
        entry = self.get_cann_version(cann_version)
        if entry is None:
            return []
        return list(entry.frameworks.keys())


class QueryResult(BaseModel):
    """Structured result for compatibility queries."""

    success: bool = Field(..., description="Whether the query succeeded")
    data: Optional[Dict] = Field(None, description="Query result data")
    error: Optional[str] = Field(None, description="Error message if failed")
    suggestions: List[str] = Field(
        default_factory=list, description="Suggestions for resolving issues"
    )


class EnvironmentInfo(BaseModel):
    """Information about the host environment."""

    driver_version: str = Field(..., description="NPU driver version")
    os_name: str = Field(..., description="Operating system name")
    npu_type: str = Field(..., description="NPU type")
    arch: str = Field(..., description="CPU architecture")
    firmware_version: Optional[str] = Field(None, description="NPU firmware version")
    npu_count: int = Field(1, description="Number of NPUs", ge=1)


class ValidationResult(BaseModel):
    """Result of environment validation."""

    valid: bool = Field(..., description="Whether the environment is valid")
    compatible_cann_versions: List[str] = Field(
        default_factory=list, description="Compatible CANN versions"
    )
    errors: List[str] = Field(default_factory=list, description="Validation errors")
    warnings: List[str] = Field(default_factory=list, description="Validation warnings")
