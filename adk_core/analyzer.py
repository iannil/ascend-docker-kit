"""
ADK Environment Analyzer

Detects host environment information including OS, architecture, NPU type,
and driver version for compatibility validation.
"""

import json
import os
import platform
import re
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .exceptions import (
    DriverNotInstalledError,
    EnvironmentDetectionError,
    NPUNotDetectedError,
)
from .models import EnvironmentInfo


def _get_safe_env() -> Dict[str, str]:
    """
    Create a safe subprocess environment with minimal required variables.

    Returns:
        Dict containing only safe environment variables for subprocess calls
    """
    safe_vars = ["PATH", "HOME", "USER", "LANG", "LC_ALL", "TERM"]
    env = {}
    for var in safe_vars:
        value = os.environ.get(var)
        if value is not None:
            env[var] = value

    # Ensure Ascend-related paths are included for npu-smi
    ascend_paths = [
        "/usr/local/Ascend/driver/bin",
        "/usr/local/bin",
        "/opt/Ascend/driver/bin",
    ]

    current_path = env.get("PATH", "/usr/bin:/bin")
    for ascend_path in ascend_paths:
        if ascend_path not in current_path:
            current_path = f"{ascend_path}:{current_path}"

    env["PATH"] = current_path
    return env


class EnvironmentAnalyzer:
    """Analyzer for detecting host environment configuration."""

    # OS ID to name mapping
    OS_MAPPING: Dict[str, Dict[str, str]] = {
        "ubuntu": {
            "20.04": "ubuntu20.04",
            "22.04": "ubuntu22.04",
            "24.04": "ubuntu24.04",
        },
        "openeuler": {
            "22.03": "openEuler22.03",
            "24.03": "openEuler24.03",
        },
        "kylin": {
            "v10": "kylinV10",
            "V10": "kylinV10",
        },
    }

    @classmethod
    def analyze(cls) -> EnvironmentInfo:
        """
        Perform full environment analysis.

        Returns:
            EnvironmentInfo: Detected environment information

        Raises:
            EnvironmentDetectionError: If critical detection fails
            DriverNotInstalledError: If NPU driver is not installed
            NPUNotDetectedError: If no NPU is detected
        """
        os_name = cls.detect_os()
        arch = cls.detect_arch()
        npu_info = cls.detect_npu()

        return EnvironmentInfo(
            driver_version=npu_info["driver_version"],
            os_name=os_name,
            npu_type=npu_info["npu_type"],
            arch=arch,
            firmware_version=npu_info.get("firmware_version"),
            npu_count=npu_info["npu_count"],
        )

    @classmethod
    def analyze_safe(cls) -> Tuple[Optional[EnvironmentInfo], List[str]]:
        """
        Perform environment analysis without raising exceptions.

        Returns:
            Tuple of (EnvironmentInfo or None, list of error messages)
        """
        errors: List[str] = []
        os_name: Optional[str] = None
        arch: Optional[str] = None
        npu_info: Optional[Dict[str, Any]] = None

        # Detect OS
        try:
            os_name = cls.detect_os()
        except EnvironmentDetectionError as e:
            errors.append(f"OS detection: {e.message}")
            os_name = "unknown"

        # Detect architecture
        try:
            arch = cls.detect_arch()
        except EnvironmentDetectionError as e:
            errors.append(f"Architecture detection: {e.message}")
            arch = "unknown"

        # Detect NPU
        try:
            npu_info = cls.detect_npu()
        except (DriverNotInstalledError, NPUNotDetectedError) as e:
            errors.append(f"NPU detection: {e.message}")

        # If NPU detection failed, we cannot create complete EnvironmentInfo
        if npu_info is None:
            return None, errors

        env_info = EnvironmentInfo(
            driver_version=npu_info["driver_version"],
            os_name=os_name or "unknown",
            npu_type=npu_info["npu_type"],
            arch=arch or "unknown",
            firmware_version=npu_info.get("firmware_version"),
            npu_count=npu_info["npu_count"],
        )

        return env_info, errors

    @classmethod
    def detect_os(cls) -> str:
        """
        Detect operating system from /etc/os-release.

        Returns:
            str: OS name in format like 'ubuntu22.04', 'openEuler22.03'

        Raises:
            EnvironmentDetectionError: If OS cannot be detected
        """
        os_release_path = Path("/etc/os-release")

        if not os_release_path.exists():
            raise EnvironmentDetectionError(
                "Cannot detect OS: /etc/os-release not found",
                suggestions=["This tool only supports Linux systems"],
            )

        try:
            content = os_release_path.read_text()
        except PermissionError:
            raise EnvironmentDetectionError(
                "Cannot read /etc/os-release: permission denied",
                suggestions=["Run with appropriate permissions"],
            )
        except OSError as e:
            raise EnvironmentDetectionError(
                f"Cannot read /etc/os-release: {e}",
                suggestions=["Check file accessibility and permissions"],
            )

        return cls._parse_os_release(content)

    @classmethod
    def _parse_os_release(cls, content: str) -> str:
        """
        Parse /etc/os-release content.

        Args:
            content: Content of /etc/os-release file

        Returns:
            str: Normalized OS name
        """
        os_id: Optional[str] = None
        version_id: Optional[str] = None

        for line in content.splitlines():
            line = line.strip()
            if line.startswith("ID="):
                os_id = line.split("=", 1)[1].strip('"').lower()
            elif line.startswith("VERSION_ID="):
                version_id = line.split("=", 1)[1].strip('"')

        if os_id is None:
            raise EnvironmentDetectionError(
                "Cannot parse OS: ID not found in /etc/os-release"
            )

        if version_id is None:
            raise EnvironmentDetectionError(
                f"Cannot parse OS version: VERSION_ID not found for {os_id}"
            )

        # Normalize version (extract major.minor)
        version_match = re.match(r"(\d+\.?\d*)", version_id)
        if version_match:
            version = version_match.group(1)
        else:
            version = version_id

        # Look up in mapping
        if os_id in cls.OS_MAPPING:
            os_versions = cls.OS_MAPPING[os_id]
            # Try exact match first
            if version in os_versions:
                return os_versions[version]
            # Try lowercase version for kylin
            if version.lower() in os_versions:
                return os_versions[version.lower()]

        # Fallback: construct from id + version
        return f"{os_id}{version}"

    @classmethod
    def detect_arch(cls) -> str:
        """
        Detect CPU architecture.

        Returns:
            str: Architecture string ('x86_64' or 'aarch64')
        """
        machine = platform.machine()

        # Normalize architecture names
        arch_map = {
            "x86_64": "x86_64",
            "AMD64": "x86_64",
            "aarch64": "aarch64",
            "arm64": "aarch64",
        }

        return arch_map.get(machine, machine)

    @classmethod
    def detect_npu(cls) -> Dict[str, Any]:
        """
        Detect NPU information using npu-smi.

        Returns:
            Dict with keys: driver_version, npu_type, npu_count, firmware_version

        Raises:
            DriverNotInstalledError: If npu-smi is not available
            NPUNotDetectedError: If no NPU is detected
        """
        # Check if npu-smi exists
        npu_smi_path = cls._find_npu_smi()
        if npu_smi_path is None:
            raise DriverNotInstalledError("npu-smi command not found")

        # Run npu-smi info
        try:
            result = subprocess.run(
                [npu_smi_path, "info"],
                capture_output=True,
                text=True,
                timeout=30,
                env=_get_safe_env(),
            )
        except subprocess.TimeoutExpired:
            raise NPUNotDetectedError("npu-smi command timed out")
        except subprocess.SubprocessError as e:
            raise NPUNotDetectedError(f"Failed to run npu-smi: {e}")

        if result.returncode != 0:
            error_msg = result.stderr.strip() if result.stderr else "Unknown error"
            raise NPUNotDetectedError(f"npu-smi returned error: {error_msg}")

        npu_info = cls._parse_npu_smi_output(result.stdout)

        # Try to get firmware version separately (may not always be available)
        npu_info["firmware_version"] = cls._get_firmware_version()

        return npu_info

    @classmethod
    def _find_npu_smi(cls) -> Optional[str]:
        """
        Find the npu-smi executable path.

        Returns:
            Path to npu-smi or None if not found
        """
        # Try which command first
        try:
            result = subprocess.run(
                ["which", "npu-smi"],
                capture_output=True,
                text=True,
                timeout=5,
                env=_get_safe_env(),
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except subprocess.SubprocessError:
            pass

        # Try common installation paths
        common_paths = [
            "/usr/local/Ascend/driver/bin/npu-smi",
            "/usr/local/bin/npu-smi",
            "/opt/Ascend/driver/bin/npu-smi",
        ]

        for path in common_paths:
            if Path(path).exists():
                return path

        return None

    @classmethod
    def _parse_npu_smi_output(cls, output: str) -> Dict[str, Any]:
        """
        Parse npu-smi info output.

        Args:
            output: stdout from npu-smi info command

        Returns:
            Dict with NPU information (without firmware_version)

        Raises:
            NPUNotDetectedError: If output cannot be parsed or no NPUs found
        """
        # Extract driver version
        # Format: "| npu-smi 24.1.rc1          |"
        driver_match = re.search(r"npu-smi\s+([\d.]+[a-zA-Z0-9.]*)", output)
        if not driver_match:
            raise NPUNotDetectedError("Cannot parse driver version from npu-smi output")

        driver_version = driver_match.group(1)

        # Extract NPU entries
        # Format: "| 0    910B   OK      75W   |"
        npu_pattern = re.compile(r"^\|\s+(\d+)\s+(\d{3}[A-Z0-9]{0,10})\s+", re.MULTILINE)
        npus = npu_pattern.findall(output)

        if not npus:
            raise NPUNotDetectedError("No NPU devices found in npu-smi output")

        npu_count = len(npus)
        # Use the first NPU type as the representative type
        npu_type = npus[0][1]

        return {
            "driver_version": driver_version,
            "npu_type": npu_type,
            "npu_count": npu_count,
            "npus": [{"id": int(npu[0]), "type": npu[1]} for npu in npus],
        }

    @classmethod
    def _get_firmware_version(cls) -> Optional[str]:
        """
        Attempt to get firmware version from npu-smi.

        Returns:
            Firmware version string or None if not available
        """
        try:
            result = subprocess.run(
                ["npu-smi", "info", "-t", "board"],
                capture_output=True,
                text=True,
                timeout=10,
                env=_get_safe_env(),
            )
            if result.returncode == 0:
                # Try to extract firmware version from output
                fw_match = re.search(r"firmware[^\d]*([\d.]+)", result.stdout, re.I)
                if fw_match:
                    return fw_match.group(1)
        except subprocess.SubprocessError:
            pass

        return None

    @classmethod
    def detect_from_script(cls) -> Dict[str, Any]:
        """
        Detect NPU information using the check_npu.sh script.

        This method provides an alternative detection path using the shell script.

        Returns:
            Dict with NPU information in JSON format

        Raises:
            DriverNotInstalledError: If detection fails due to missing driver
            NPUNotDetectedError: If no NPU is detected
        """
        script_path = Path(__file__).parent.parent / "scripts" / "check_npu.sh"

        if not script_path.exists():
            raise EnvironmentDetectionError(
                f"Detection script not found: {script_path}",
                suggestions=["Ensure scripts/check_npu.sh exists"],
            )

        try:
            result = subprocess.run(
                ["bash", str(script_path)],
                capture_output=True,
                text=True,
                timeout=60,
                env=_get_safe_env(),
            )
        except subprocess.TimeoutExpired:
            raise NPUNotDetectedError("NPU detection script timed out")
        except subprocess.SubprocessError as e:
            raise EnvironmentDetectionError(f"Failed to run detection script: {e}")

        # Check for empty output before parsing
        if not result.stdout or not result.stdout.strip():
            raise EnvironmentDetectionError(
                "Detection script returned empty output",
                suggestions=[
                    "Check if NPU driver is properly installed",
                    "Verify npu-smi is accessible",
                ],
            )

        try:
            data = json.loads(result.stdout)
        except json.JSONDecodeError as e:
            raise EnvironmentDetectionError(
                f"Failed to parse detection script output: {e}",
                suggestions=[
                    "Check script output format",
                    f"Raw output: {result.stdout[:200]}..."
                    if len(result.stdout) > 200
                    else f"Raw output: {result.stdout}",
                ],
            )

        if data.get("status") == "error":
            error_msg = data.get("error", "Unknown error")
            if "npu-smi not found" in error_msg:
                raise DriverNotInstalledError(error_msg)
            else:
                raise NPUNotDetectedError(error_msg)

        return data
