"""
ADK Checksum Verification

Provides checksum verification for downloaded packages to ensure integrity.
"""

import hashlib
from pathlib import Path
from typing import Dict, Optional

from .exceptions import ADKError


class ChecksumError(ADKError):
    """Raised when checksum verification fails."""

    def __init__(self, file_path: str, expected: str, actual: str):
        self.file_path = file_path
        self.expected = expected
        self.actual = actual
        message = f"Checksum mismatch for {file_path}: expected {expected[:16]}..., got {actual[:16]}..."
        super().__init__(
            message,
            suggestions=[
                "Re-download the file from the official source",
                "Verify the checksum value in compatibility.yaml",
                "Check for file corruption or incomplete download",
            ],
        )


class ChecksumVerifier:
    """Verify file checksums using various algorithms."""

    SUPPORTED_ALGORITHMS = ["sha256", "sha512", "md5"]

    @classmethod
    def calculate(
        cls, file_path: Path, algorithm: str = "sha256", chunk_size: int = 8192
    ) -> str:
        """
        Calculate checksum of a file.

        Args:
            file_path: Path to the file
            algorithm: Hash algorithm (sha256, sha512, md5)
            chunk_size: Read chunk size in bytes

        Returns:
            Hexadecimal checksum string
        """
        if algorithm not in cls.SUPPORTED_ALGORITHMS:
            raise ValueError(f"Unsupported algorithm: {algorithm}")

        hasher = hashlib.new(algorithm)
        with open(file_path, "rb") as f:
            while chunk := f.read(chunk_size):
                hasher.update(chunk)
        return hasher.hexdigest()

    @classmethod
    def verify(
        cls,
        file_path: Path,
        expected_checksum: str,
        algorithm: str = "sha256",
    ) -> bool:
        """
        Verify file checksum.

        Args:
            file_path: Path to the file
            expected_checksum: Expected checksum value
            algorithm: Hash algorithm

        Returns:
            True if checksum matches

        Raises:
            ChecksumError: If checksum doesn't match
            FileNotFoundError: If file doesn't exist
        """
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        actual_checksum = cls.calculate(file_path, algorithm)

        if actual_checksum.lower() != expected_checksum.lower():
            raise ChecksumError(str(file_path), expected_checksum, actual_checksum)

        return True

    @classmethod
    def verify_batch(
        cls,
        files: Dict[Path, str],
        algorithm: str = "sha256",
    ) -> Dict[str, bool]:
        """
        Verify checksums for multiple files.

        Args:
            files: Dict mapping file paths to expected checksums
            algorithm: Hash algorithm

        Returns:
            Dict mapping file paths to verification results
        """
        results = {}
        for file_path, expected in files.items():
            try:
                cls.verify(file_path, expected, algorithm)
                results[str(file_path)] = True
            except (ChecksumError, FileNotFoundError):
                results[str(file_path)] = False
        return results


class PackageVerifier:
    """Verify CANN and framework package checksums."""

    # Known checksums for common packages (example data)
    # In production, these would come from compatibility.yaml
    KNOWN_CHECKSUMS: Dict[str, Dict[str, str]] = {
        # Format: "package_name": {"version": "sha256_checksum"}
        "torch_npu": {
            "2.4.0.post2": "placeholder_checksum_to_be_updated",
        },
    }

    @classmethod
    def verify_package(
        cls,
        package_path: Path,
        package_name: str,
        version: str,
        checksum: Optional[str] = None,
    ) -> bool:
        """
        Verify a package file.

        Args:
            package_path: Path to the package file
            package_name: Name of the package
            version: Package version
            checksum: Optional explicit checksum (overrides known checksums)

        Returns:
            True if verification passes or no checksum available

        Raises:
            ChecksumError: If checksum doesn't match
        """
        expected = checksum

        # Try to get from known checksums if not provided
        if expected is None:
            package_checksums = cls.KNOWN_CHECKSUMS.get(package_name, {})
            expected = package_checksums.get(version)

        # If no checksum available, skip verification with warning
        if expected is None or expected.startswith("placeholder"):
            return True

        return ChecksumVerifier.verify(package_path, expected)

    @classmethod
    def calculate_package_checksum(cls, package_path: Path) -> str:
        """
        Calculate checksum for a package file.

        Useful for generating checksums to add to compatibility.yaml.

        Args:
            package_path: Path to the package file

        Returns:
            SHA256 checksum string
        """
        return ChecksumVerifier.calculate(package_path, "sha256")
