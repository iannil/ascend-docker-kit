"""
Tests for ADK Core Analyzer Module

Unit tests for environment detection and analysis.
"""

import json
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from adk_core import (
    EnvironmentAnalyzer,
    EnvironmentInfo,
    EnvironmentDetectionError,
    DriverNotInstalledError,
    NPUNotDetectedError,
)


class TestOSDetection:
    """Tests for OS detection functionality."""

    def test_parse_ubuntu_2004(self):
        """Test parsing Ubuntu 20.04."""
        content = '''
ID=ubuntu
VERSION_ID="20.04"
'''
        result = EnvironmentAnalyzer._parse_os_release(content)
        assert result == "ubuntu20.04"

    def test_parse_ubuntu_2204(self):
        """Test parsing Ubuntu 22.04."""
        content = '''
ID=ubuntu
VERSION_ID="22.04"
'''
        result = EnvironmentAnalyzer._parse_os_release(content)
        assert result == "ubuntu22.04"

    def test_parse_ubuntu_2404(self):
        """Test parsing Ubuntu 24.04."""
        content = '''
ID=ubuntu
VERSION_ID="24.04"
'''
        result = EnvironmentAnalyzer._parse_os_release(content)
        assert result == "ubuntu24.04"

    def test_parse_openeuler_2203(self):
        """Test parsing openEuler 22.03."""
        content = '''
ID=openEuler
VERSION_ID="22.03"
'''
        result = EnvironmentAnalyzer._parse_os_release(content)
        assert result == "openEuler22.03"

    def test_parse_openeuler_lowercase(self):
        """Test parsing openEuler with lowercase ID."""
        content = '''
ID=openeuler
VERSION_ID="22.03"
'''
        result = EnvironmentAnalyzer._parse_os_release(content)
        assert result == "openEuler22.03"

    def test_parse_kylin_v10(self):
        """Test parsing Kylin V10."""
        content = '''
ID=kylin
VERSION_ID="V10"
'''
        result = EnvironmentAnalyzer._parse_os_release(content)
        assert result == "kylinV10"

    def test_parse_unknown_os(self):
        """Test parsing unknown OS falls back to id+version."""
        content = '''
ID=centos
VERSION_ID="7"
'''
        result = EnvironmentAnalyzer._parse_os_release(content)
        assert result == "centos7"

    def test_parse_missing_id(self):
        """Test parsing with missing ID."""
        content = '''
VERSION_ID="22.04"
'''
        with pytest.raises(EnvironmentDetectionError) as exc:
            EnvironmentAnalyzer._parse_os_release(content)
        assert "ID not found" in str(exc.value)

    def test_parse_missing_version_id(self):
        """Test parsing with missing VERSION_ID."""
        content = '''
ID=ubuntu
'''
        with pytest.raises(EnvironmentDetectionError) as exc:
            EnvironmentAnalyzer._parse_os_release(content)
        assert "VERSION_ID not found" in str(exc.value)

    @patch("pathlib.Path.exists")
    @patch("pathlib.Path.read_text")
    def test_detect_os_success(self, mock_read, mock_exists):
        """Test successful OS detection."""
        mock_exists.return_value = True
        mock_read.return_value = '''
ID=ubuntu
VERSION_ID="22.04"
'''
        result = EnvironmentAnalyzer.detect_os()
        assert result == "ubuntu22.04"

    @patch("pathlib.Path.exists")
    def test_detect_os_file_not_found(self, mock_exists):
        """Test OS detection when /etc/os-release doesn't exist."""
        mock_exists.return_value = False
        with pytest.raises(EnvironmentDetectionError) as exc:
            EnvironmentAnalyzer.detect_os()
        assert "/etc/os-release not found" in str(exc.value)


class TestArchDetection:
    """Tests for architecture detection."""

    @patch("platform.machine")
    def test_detect_x86_64(self, mock_machine):
        """Test x86_64 detection."""
        mock_machine.return_value = "x86_64"
        result = EnvironmentAnalyzer.detect_arch()
        assert result == "x86_64"

    @patch("platform.machine")
    def test_detect_aarch64(self, mock_machine):
        """Test aarch64 detection."""
        mock_machine.return_value = "aarch64"
        result = EnvironmentAnalyzer.detect_arch()
        assert result == "aarch64"

    @patch("platform.machine")
    def test_detect_arm64(self, mock_machine):
        """Test arm64 (macOS) maps to aarch64."""
        mock_machine.return_value = "arm64"
        result = EnvironmentAnalyzer.detect_arch()
        assert result == "aarch64"

    @patch("platform.machine")
    def test_detect_amd64(self, mock_machine):
        """Test AMD64 maps to x86_64."""
        mock_machine.return_value = "AMD64"
        result = EnvironmentAnalyzer.detect_arch()
        assert result == "x86_64"

    @patch("platform.machine")
    def test_detect_unknown_arch(self, mock_machine):
        """Test unknown architecture returns as-is."""
        mock_machine.return_value = "riscv64"
        result = EnvironmentAnalyzer.detect_arch()
        assert result == "riscv64"


class TestNPUDetection:
    """Tests for NPU detection functionality."""

    SAMPLE_NPU_SMI_OUTPUT = """
+-------------------------------------------------------------------------------------------+
| npu-smi 24.1.rc1                          Version: 24.1.rc1                               |
+===========================================================================================+
| NPU   Name      Health          Power(W)     Temp(C)           Hugepages-Usage(page)      |
| Chip    Device  Bus-Id          AICore(%)    Memory-Usage(MB)                             |
+===========================================================================================+
| 0       910B    OK              75           42                0    / 0                   |
| 0       0       0000:81:00.0    0            0     / 15171                                |
+===========================================================================================+
| 1       910B    OK              72           41                0    / 0                   |
| 0       1       0000:82:00.0    0            0     / 15171                                |
+===========================================================================================+
"""

    def test_parse_npu_smi_output(self):
        """Test parsing npu-smi output."""
        result = EnvironmentAnalyzer._parse_npu_smi_output(self.SAMPLE_NPU_SMI_OUTPUT)

        assert result["driver_version"] == "24.1.rc1"
        assert result["npu_type"] == "910B"
        assert result["npu_count"] == 2
        assert len(result["npus"]) == 2
        assert result["npus"][0]["id"] == 0
        assert result["npus"][0]["type"] == "910B"
        # firmware_version is not set by _parse_npu_smi_output directly
        assert "firmware_version" not in result

    def test_parse_npu_smi_single_npu(self):
        """Test parsing output with single NPU."""
        output = """
+-------------------------------------------------------------------------------------------+
| npu-smi 23.0.3                          Version: 23.0.3                                   |
+===========================================================================================+
| NPU   Name      Health          Power(W)     Temp(C)           Hugepages-Usage(page)      |
+===========================================================================================+
| 0       910A    OK              65           38                0    / 0                   |
+===========================================================================================+
"""
        result = EnvironmentAnalyzer._parse_npu_smi_output(output)

        assert result["driver_version"] == "23.0.3"
        assert result["npu_type"] == "910A"
        assert result["npu_count"] == 1

    def test_parse_npu_smi_310p(self):
        """Test parsing output with 310P NPU."""
        output = """
+-------------------------------------------------------------------------------------------+
| npu-smi 24.1.0                          Version: 24.1.0                                   |
+===========================================================================================+
| NPU   Name      Health          Power(W)     Temp(C)           Hugepages-Usage(page)      |
+===========================================================================================+
| 0       310P    OK              35           32                0    / 0                   |
+===========================================================================================+
"""
        result = EnvironmentAnalyzer._parse_npu_smi_output(output)

        assert result["npu_type"] == "310P"
        assert result["npu_count"] == 1

    def test_parse_npu_smi_no_driver_version(self):
        """Test parsing output without valid driver version."""
        output = """
+-------------------------------------------------------------------------------------------+
| npu-smi                                                                                   |
+===========================================================================================+
"""
        with pytest.raises(NPUNotDetectedError) as exc:
            EnvironmentAnalyzer._parse_npu_smi_output(output)
        assert "Cannot parse driver version" in str(exc.value)

    def test_parse_npu_smi_no_npu(self):
        """Test parsing output with no NPUs listed."""
        output = """
+-------------------------------------------------------------------------------------------+
| npu-smi 24.1.rc1                          Version: 24.1.rc1                               |
+===========================================================================================+
| No NPU devices found                                                                      |
+===========================================================================================+
"""
        with pytest.raises(NPUNotDetectedError) as exc:
            EnvironmentAnalyzer._parse_npu_smi_output(output)
        assert "No NPU devices found" in str(exc.value)

    @patch.object(EnvironmentAnalyzer, "_find_npu_smi")
    def test_detect_npu_not_installed(self, mock_find):
        """Test NPU detection when npu-smi is not installed."""
        mock_find.return_value = None

        with pytest.raises(DriverNotInstalledError) as exc:
            EnvironmentAnalyzer.detect_npu()
        assert "npu-smi command not found" in str(exc.value)

    @patch.object(EnvironmentAnalyzer, "_find_npu_smi")
    @patch("subprocess.run")
    def test_detect_npu_command_failed(self, mock_run, mock_find):
        """Test NPU detection when npu-smi command fails."""
        mock_find.return_value = "/usr/local/bin/npu-smi"
        mock_run.return_value = MagicMock(
            returncode=1,
            stderr="Error: device not found",
            stdout=""
        )

        with pytest.raises(NPUNotDetectedError) as exc:
            EnvironmentAnalyzer.detect_npu()
        assert "device not found" in str(exc.value)

    @patch.object(EnvironmentAnalyzer, "_find_npu_smi")
    @patch.object(EnvironmentAnalyzer, "_get_firmware_version")
    @patch("subprocess.run")
    def test_detect_npu_success(self, mock_run, mock_firmware, mock_find):
        """Test successful NPU detection."""
        mock_find.return_value = "/usr/local/bin/npu-smi"
        mock_firmware.return_value = "7.1.0.5"
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=self.SAMPLE_NPU_SMI_OUTPUT,
            stderr=""
        )

        result = EnvironmentAnalyzer.detect_npu()

        assert result["driver_version"] == "24.1.rc1"
        assert result["npu_type"] == "910B"
        assert result["npu_count"] == 2


class TestFullAnalysis:
    """Tests for full environment analysis."""

    @patch.object(EnvironmentAnalyzer, "detect_os")
    @patch.object(EnvironmentAnalyzer, "detect_arch")
    @patch.object(EnvironmentAnalyzer, "detect_npu")
    def test_analyze_success(self, mock_npu, mock_arch, mock_os):
        """Test successful full analysis."""
        mock_os.return_value = "ubuntu22.04"
        mock_arch.return_value = "x86_64"
        mock_npu.return_value = {
            "driver_version": "24.1.rc1",
            "npu_type": "910B",
            "npu_count": 2,
            "firmware_version": "7.1.0.5",
        }

        result = EnvironmentAnalyzer.analyze()

        assert isinstance(result, EnvironmentInfo)
        assert result.os_name == "ubuntu22.04"
        assert result.arch == "x86_64"
        assert result.driver_version == "24.1.rc1"
        assert result.npu_type == "910B"
        assert result.npu_count == 2
        assert result.firmware_version == "7.1.0.5"

    @patch.object(EnvironmentAnalyzer, "detect_os")
    @patch.object(EnvironmentAnalyzer, "detect_arch")
    @patch.object(EnvironmentAnalyzer, "detect_npu")
    def test_analyze_safe_success(self, mock_npu, mock_arch, mock_os):
        """Test successful safe analysis."""
        mock_os.return_value = "openEuler22.03"
        mock_arch.return_value = "aarch64"
        mock_npu.return_value = {
            "driver_version": "23.0.3",
            "npu_type": "910A",
            "npu_count": 8,
            "firmware_version": None,
        }

        result, errors = EnvironmentAnalyzer.analyze_safe()

        assert result is not None
        assert len(errors) == 0
        assert result.os_name == "openEuler22.03"
        assert result.arch == "aarch64"
        assert result.driver_version == "23.0.3"
        assert result.npu_type == "910A"
        assert result.npu_count == 8

    @patch.object(EnvironmentAnalyzer, "detect_os")
    @patch.object(EnvironmentAnalyzer, "detect_arch")
    @patch.object(EnvironmentAnalyzer, "detect_npu")
    def test_analyze_safe_os_error(self, mock_npu, mock_arch, mock_os):
        """Test safe analysis with OS detection error."""
        mock_os.side_effect = EnvironmentDetectionError("OS detection failed")
        mock_arch.return_value = "x86_64"
        mock_npu.return_value = {
            "driver_version": "24.1.rc1",
            "npu_type": "910B",
            "npu_count": 1,
            "firmware_version": None,
        }

        result, errors = EnvironmentAnalyzer.analyze_safe()

        assert result is not None
        assert len(errors) == 1
        assert "OS detection" in errors[0]
        assert result.os_name == "unknown"

    @patch.object(EnvironmentAnalyzer, "detect_os")
    @patch.object(EnvironmentAnalyzer, "detect_arch")
    @patch.object(EnvironmentAnalyzer, "detect_npu")
    def test_analyze_safe_npu_error(self, mock_npu, mock_arch, mock_os):
        """Test safe analysis with NPU detection error."""
        mock_os.return_value = "ubuntu22.04"
        mock_arch.return_value = "x86_64"
        mock_npu.side_effect = DriverNotInstalledError("npu-smi not found")

        result, errors = EnvironmentAnalyzer.analyze_safe()

        assert result is None
        assert len(errors) == 1
        assert "NPU detection" in errors[0]


class TestExceptions:
    """Tests for analyzer-related exceptions."""

    def test_environment_detection_error(self):
        """Test EnvironmentDetectionError."""
        error = EnvironmentDetectionError(
            "Test error",
            suggestions=["Suggestion 1", "Suggestion 2"]
        )
        assert "Test error" in str(error)
        assert "Suggestion 1" in str(error)
        assert error.suggestions == ["Suggestion 1", "Suggestion 2"]

    def test_driver_not_installed_error(self):
        """Test DriverNotInstalledError."""
        error = DriverNotInstalledError()
        assert "npu-smi" in str(error)
        assert len(error.suggestions) > 0

    def test_driver_not_installed_error_custom(self):
        """Test DriverNotInstalledError with custom reason."""
        error = DriverNotInstalledError("custom reason")
        assert "custom reason" in str(error)
        assert error.reason == "custom reason"

    def test_npu_not_detected_error(self):
        """Test NPUNotDetectedError."""
        error = NPUNotDetectedError()
        assert "No NPU device found" in str(error)
        assert len(error.suggestions) > 0

    def test_npu_not_detected_error_custom(self):
        """Test NPUNotDetectedError with custom reason."""
        error = NPUNotDetectedError("Device busy")
        assert "Device busy" in str(error)
        assert error.reason == "Device busy"


class TestScriptDetection:
    """Tests for shell script-based detection."""

    @patch("subprocess.run")
    @patch("pathlib.Path.exists")
    def test_detect_from_script_success(self, mock_exists, mock_run):
        """Test successful detection via shell script."""
        mock_exists.return_value = True
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=json.dumps({
                "status": "ok",
                "driver_version": "24.1.rc1",
                "npu_count": 2,
                "npus": [
                    {"id": 0, "type": "910B"},
                    {"id": 1, "type": "910B"}
                ]
            }),
            stderr=""
        )

        result = EnvironmentAnalyzer.detect_from_script()

        assert result["status"] == "ok"
        assert result["driver_version"] == "24.1.rc1"
        assert result["npu_count"] == 2

    @patch("subprocess.run")
    @patch("pathlib.Path.exists")
    def test_detect_from_script_driver_missing(self, mock_exists, mock_run):
        """Test script detection when driver is missing."""
        mock_exists.return_value = True
        mock_run.return_value = MagicMock(
            returncode=1,
            stdout=json.dumps({
                "status": "error",
                "error": "npu-smi not found",
                "suggestion": "Please install Ascend NPU driver"
            }),
            stderr=""
        )

        with pytest.raises(DriverNotInstalledError) as exc:
            EnvironmentAnalyzer.detect_from_script()
        assert "npu-smi not found" in str(exc.value)

    @patch("pathlib.Path.exists")
    def test_detect_from_script_not_found(self, mock_exists):
        """Test script detection when script doesn't exist."""
        mock_exists.return_value = False

        with pytest.raises(EnvironmentDetectionError) as exc:
            EnvironmentAnalyzer.detect_from_script()
        assert "script not found" in str(exc.value)
