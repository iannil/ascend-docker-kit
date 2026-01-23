"""
Tests for Edge Cases and Boundary Conditions

Comprehensive tests for handling extreme inputs, empty data,
and boundary conditions across ADK Core modules.
"""

import tempfile
from pathlib import Path

import pytest

from adk_core import (
    ChecksumError,
    ChecksumVerifier,
    PackageVerifier,
    compare_versions,
    find_latest_compatible,
    is_compatible,
    is_version_valid,
    parse_version,
    sort_versions,
)
from adk_core.analyzer import EnvironmentAnalyzer
from adk_core.exceptions import NPUNotDetectedError


class TestVersionEdgeCases:
    """Edge case tests for version utilities."""

    def test_zero_version(self):
        """Test version 0.0.0."""
        assert is_version_valid("0.0.0") is True
        assert compare_versions("0.0.0", "1.0.0") == -1
        assert compare_versions("0.0.0", "0.0.0") == 0

    def test_large_version_numbers(self):
        """Test versions with large numbers."""
        assert is_version_valid("999.999.999") is True
        assert compare_versions("999.999.999", "1.0.0") == 1
        assert compare_versions("100.0.0", "99.99.99") == 1

    def test_version_with_many_components(self):
        """Test version with many pre/post/dev components."""
        assert is_version_valid("1.0.0.post1.dev1") is True
        assert is_version_valid("2.4.0.post2") is True
        assert is_version_valid("1.0.0a1") is True
        assert is_version_valid("1.0.0b2") is True
        assert is_version_valid("1.0.0rc3") is True

    def test_invalid_version_formats(self):
        """Test invalid version formats."""
        assert is_version_valid("") is False
        assert is_version_valid("abc") is False
        assert is_version_valid("1.0.0.0.0.0.invalid") is False
        # Note: PEP 440 allows 'v' prefix (it's stripped)
        assert is_version_valid("v1.0.0") is True
        assert is_version_valid("1.0") is True  # Valid in PEP 440
        assert is_version_valid("1") is True  # Also valid

    def test_version_with_special_chars(self):
        """Test versions with special characters."""
        # Note: PEP 440 normalizes hyphens to dots
        assert is_version_valid("1.0.0-beta") is True  # Normalized to 1.0.0b0
        assert is_version_valid("1.0.0_rc1") is True  # Normalized
        assert is_version_valid("1.0.0+local") is True  # Local version
        # Truly invalid formats
        assert is_version_valid("1.0.0--") is False
        assert is_version_valid("not.a.version.at.all") is False

    def test_empty_version_list_sort(self):
        """Test sorting empty version list."""
        result = sort_versions([])
        assert result == []

    def test_single_version_sort(self):
        """Test sorting single version."""
        result = sort_versions(["1.0.0"])
        assert result == ["1.0.0"]

    def test_all_invalid_versions_sort(self):
        """Test sorting list with all invalid versions."""
        result = sort_versions(["invalid", "also_invalid", "nope"])
        assert result == []

    def test_mixed_valid_invalid_sort(self):
        """Test sorting mixed valid/invalid versions."""
        result = sort_versions(["1.0.0", "invalid", "2.0.0"])
        assert result == ["1.0.0", "2.0.0"]

    def test_duplicate_versions_sort(self):
        """Test sorting duplicate versions."""
        result = sort_versions(["1.0.0", "1.0.0", "2.0.0"])
        assert result == ["1.0.0", "1.0.0", "2.0.0"]

    def test_find_latest_empty_list(self):
        """Test find_latest_compatible with empty list."""
        result = find_latest_compatible([])
        assert result is None

    def test_find_latest_all_invalid(self):
        """Test find_latest_compatible with all invalid versions."""
        result = find_latest_compatible(["invalid", "nope"])
        assert result is None

    def test_find_latest_no_match(self):
        """Test find_latest_compatible when no version matches constraints."""
        result = find_latest_compatible(
            ["1.0.0", "2.0.0"], min_version="3.0.0"
        )
        assert result is None

    def test_find_latest_exact_boundary(self):
        """Test find_latest_compatible at exact boundaries."""
        versions = ["1.0.0", "2.0.0", "3.0.0"]

        # Exact min boundary
        result = find_latest_compatible(versions, min_version="2.0.0")
        assert result == "3.0.0"

        # Exact max boundary
        result = find_latest_compatible(versions, max_version="2.0.0")
        assert result == "2.0.0"

        # Both boundaries equal
        result = find_latest_compatible(versions, min_version="2.0.0", max_version="2.0.0")
        assert result == "2.0.0"

    def test_is_compatible_equal_versions(self):
        """Test is_compatible with equal versions."""
        assert is_compatible("1.0.0", "1.0.0") is True
        assert is_compatible("0.0.0", "0.0.0") is True

    def test_compare_rc_vs_release(self):
        """Test comparing rc/pre-release vs release versions."""
        assert compare_versions("8.0.0", "8.0.0rc1") == 1
        assert compare_versions("8.0.0rc1", "8.0.0rc2") == -1
        assert compare_versions("8.0.0a1", "8.0.0b1") == -1
        assert compare_versions("8.0.0b1", "8.0.0rc1") == -1


class TestNPUParsingEdgeCases:
    """Edge case tests for NPU parsing."""

    def test_parse_many_npus(self):
        """Test parsing output with many NPUs (8+)."""
        header = """
+-------------------------------------------------------------------------------------------+
| npu-smi 24.1.rc1                          Version: 24.1.rc1                               |
+===========================================================================================+
| NPU   Name      Health          Power(W)     Temp(C)           Hugepages-Usage(page)      |
+===========================================================================================+
"""
        npu_lines = ""
        for i in range(8):
            npu_lines += f"""| {i}       910B    OK              75           42                0    / 0                   |
| 0       {i}       0000:8{i}:00.0    0            0     / 15171                                |
+===========================================================================================+
"""
        output = header + npu_lines

        result = EnvironmentAnalyzer._parse_npu_smi_output(output)
        assert result["npu_count"] == 8
        assert len(result["npus"]) == 8

    def test_parse_mixed_npu_types(self):
        """Test parsing output with different NPU types."""
        output = """
+-------------------------------------------------------------------------------------------+
| npu-smi 24.1.rc1                          Version: 24.1.rc1                               |
+===========================================================================================+
| NPU   Name      Health          Power(W)     Temp(C)           Hugepages-Usage(page)      |
+===========================================================================================+
| 0       910B    OK              75           42                0    / 0                   |
+===========================================================================================+
| 1       310P    OK              35           32                0    / 0                   |
+===========================================================================================+
"""
        result = EnvironmentAnalyzer._parse_npu_smi_output(output)
        assert result["npu_count"] == 2
        # First NPU type is used as primary
        assert result["npu_type"] == "910B"

    def test_parse_empty_output(self):
        """Test parsing empty output."""
        with pytest.raises(NPUNotDetectedError):
            EnvironmentAnalyzer._parse_npu_smi_output("")

    def test_parse_whitespace_output(self):
        """Test parsing whitespace-only output."""
        with pytest.raises(NPUNotDetectedError):
            EnvironmentAnalyzer._parse_npu_smi_output("   \n\n\t  ")


class TestChecksumEdgeCases:
    """Edge case tests for checksum verification."""

    def test_calculate_empty_file(self):
        """Test checksum of empty file."""
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(b"")
            temp_path = Path(f.name)

        try:
            checksum = ChecksumVerifier.calculate(temp_path)
            # SHA256 of empty file is a known constant
            assert checksum == "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
        finally:
            temp_path.unlink()

    def test_calculate_large_file(self):
        """Test checksum of larger file (1MB)."""
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(b"x" * (1024 * 1024))
            temp_path = Path(f.name)

        try:
            checksum = ChecksumVerifier.calculate(temp_path)
            assert len(checksum) == 64  # SHA256 hex length
        finally:
            temp_path.unlink()

    def test_verify_case_insensitive(self):
        """Test checksum verification is case-insensitive."""
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(b"test content")
            temp_path = Path(f.name)

        try:
            checksum = ChecksumVerifier.calculate(temp_path)
            # Both uppercase and lowercase should work
            assert ChecksumVerifier.verify(temp_path, checksum.upper())
            assert ChecksumVerifier.verify(temp_path, checksum.lower())
        finally:
            temp_path.unlink()

    def test_verify_file_not_found(self):
        """Test verification of non-existent file."""
        with pytest.raises(FileNotFoundError):
            ChecksumVerifier.verify(Path("/nonexistent/file.txt"), "abc123")

    def test_verify_checksum_mismatch(self):
        """Test checksum mismatch raises ChecksumError."""
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(b"test content")
            temp_path = Path(f.name)

        try:
            with pytest.raises(ChecksumError) as exc:
                ChecksumVerifier.verify(temp_path, "wrong_checksum_value")

            assert "expected" in str(exc.value).lower()
            assert exc.value.file_path == str(temp_path)
        finally:
            temp_path.unlink()

    def test_unsupported_algorithm(self):
        """Test unsupported hash algorithm."""
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(b"test")
            temp_path = Path(f.name)

        try:
            with pytest.raises(ValueError) as exc:
                ChecksumVerifier.calculate(temp_path, "unsupported_algo")
            assert "unsupported" in str(exc.value).lower()
        finally:
            temp_path.unlink()

    def test_supported_algorithms(self):
        """Test all supported algorithms produce valid checksums."""
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(b"test content for hashing")
            temp_path = Path(f.name)

        try:
            for algo in ChecksumVerifier.SUPPORTED_ALGORITHMS:
                checksum = ChecksumVerifier.calculate(temp_path, algo)
                assert isinstance(checksum, str)
                assert len(checksum) > 0
        finally:
            temp_path.unlink()

    def test_verify_batch_mixed_results(self):
        """Test batch verification with mixed results."""
        with tempfile.NamedTemporaryFile(delete=False, suffix="_a") as f1:
            f1.write(b"content a")
            path_a = Path(f1.name)

        with tempfile.NamedTemporaryFile(delete=False, suffix="_b") as f2:
            f2.write(b"content b")
            path_b = Path(f2.name)

        try:
            checksum_a = ChecksumVerifier.calculate(path_a)

            files = {
                path_a: checksum_a,
                path_b: "wrong_checksum",
            }

            results = ChecksumVerifier.verify_batch(files)

            assert results[str(path_a)] is True
            assert results[str(path_b)] is False
        finally:
            path_a.unlink()
            path_b.unlink()

    def test_verify_batch_empty(self):
        """Test batch verification with empty dict."""
        results = ChecksumVerifier.verify_batch({})
        assert results == {}


class TestPackageVerifierEdgeCases:
    """Edge case tests for PackageVerifier."""

    def test_verify_package_no_checksum(self):
        """Test package verification when no checksum available."""
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(b"fake package")
            temp_path = Path(f.name)

        try:
            # Should return True when no checksum available
            result = PackageVerifier.verify_package(
                temp_path, "unknown_package", "1.0.0"
            )
            assert result is True
        finally:
            temp_path.unlink()

    def test_verify_package_placeholder_checksum(self):
        """Test package verification with placeholder checksum."""
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(b"fake package")
            temp_path = Path(f.name)

        try:
            # Should return True for placeholder checksums
            result = PackageVerifier.verify_package(
                temp_path, "torch_npu", "2.4.0.post2"
            )
            assert result is True
        finally:
            temp_path.unlink()

    def test_verify_package_explicit_checksum(self):
        """Test package verification with explicit checksum."""
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(b"package content")
            temp_path = Path(f.name)

        try:
            correct_checksum = ChecksumVerifier.calculate(temp_path)
            result = PackageVerifier.verify_package(
                temp_path, "test_package", "1.0.0", checksum=correct_checksum
            )
            assert result is True
        finally:
            temp_path.unlink()

    def test_calculate_package_checksum(self):
        """Test calculating package checksum."""
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(b"test package data")
            temp_path = Path(f.name)

        try:
            checksum = PackageVerifier.calculate_package_checksum(temp_path)
            assert len(checksum) == 64  # SHA256 hex length
        finally:
            temp_path.unlink()
