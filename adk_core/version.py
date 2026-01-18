"""
ADK Version Utilities

Version comparison utilities based on PEP 440 for CANN, driver, and framework versions.
"""

from typing import List, Optional

from packaging.version import Version, InvalidVersion


def parse_version(version_str: str) -> Version:
    """
    Parse a version string into a Version object.

    Args:
        version_str: Version string (e.g., "8.0.0", "24.0.0.rc1", "2.4.0.post2")

    Returns:
        Parsed Version object

    Raises:
        InvalidVersion: If the version string is invalid
    """
    return Version(version_str)


def is_version_valid(version_str: str) -> bool:
    """
    Check if a version string is valid according to PEP 440.

    Args:
        version_str: Version string to validate

    Returns:
        True if valid, False otherwise
    """
    try:
        parse_version(version_str)
        return True
    except InvalidVersion:
        return False


def compare_versions(v1: str, v2: str) -> int:
    """
    Compare two version strings.

    Args:
        v1: First version string
        v2: Second version string

    Returns:
        -1 if v1 < v2, 0 if v1 == v2, 1 if v1 > v2
    """
    version1 = parse_version(v1)
    version2 = parse_version(v2)

    if version1 < version2:
        return -1
    elif version1 > version2:
        return 1
    return 0


def is_compatible(current: str, minimum_required: str) -> bool:
    """
    Check if the current version meets the minimum requirement.

    Args:
        current: Current version string
        minimum_required: Minimum required version string

    Returns:
        True if current >= minimum_required
    """
    return compare_versions(current, minimum_required) >= 0


def find_latest_compatible(
    available_versions: List[str],
    max_version: Optional[str] = None,
    min_version: Optional[str] = None,
) -> Optional[str]:
    """
    Find the latest version from a list that satisfies optional constraints.

    Args:
        available_versions: List of available version strings
        max_version: Maximum allowed version (inclusive)
        min_version: Minimum required version (inclusive)

    Returns:
        The latest compatible version, or None if no version matches
    """
    valid_versions: List[str] = []

    for v in available_versions:
        if not is_version_valid(v):
            continue

        if min_version and not is_compatible(v, min_version):
            continue

        if max_version and compare_versions(v, max_version) > 0:
            continue

        valid_versions.append(v)

    if not valid_versions:
        return None

    return max(valid_versions, key=lambda x: parse_version(x))


def sort_versions(versions: List[str], reverse: bool = False) -> List[str]:
    """
    Sort a list of version strings.

    Args:
        versions: List of version strings
        reverse: If True, sort in descending order

    Returns:
        Sorted list of version strings
    """
    valid = [(v, parse_version(v)) for v in versions if is_version_valid(v)]
    valid.sort(key=lambda x: x[1], reverse=reverse)
    return [v[0] for v in valid]


def get_major_minor(version_str: str) -> str:
    """
    Extract major.minor from a version string.

    Args:
        version_str: Version string (e.g., "8.0.0.rc1")

    Returns:
        Major.minor string (e.g., "8.0")
    """
    v = parse_version(version_str)
    return f"{v.major}.{v.minor}"
