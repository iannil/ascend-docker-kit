# Ascend Docker Kit (ADK)

A DevOps toolkit for Huawei Ascend NPU environments that automates Docker environment configuration and resolves CANN/driver/framework version compatibility issues.

[![Python](https://img.shields.io/badge/Python-3.8%2B-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-Apache%202.0-green)](LICENSE)

[中文文档](README.zh-CN.md)

---

## Overview

In Ascend NPU environments, complex dependencies exist between CANN versions, driver versions, and PyTorch/MindSpore versions. ADK solves this problem through the following core features:

- **Compatibility Matrix**: Structures scattered version compatibility information from Huawei's official documentation into a single source of truth
- **Environment Analyzer**: Automatically detects host environment (NPU model, driver version, OS)
- **Smart Recommendations**: Automatically recommends compatible CANN and framework versions based on current environment

## Features

| Feature | Description |
| --------- | ------------- |
| Environment Detection | Auto-detect NPU model (910A/910B/310P), driver version, OS distribution |
| Compatibility Validation | Verify if current environment supports target CANN version |
| Version Recommendation | Recommend optimal CANN and framework combinations based on driver version |
| Framework Configuration | Get torch_npu version and installation method for PyTorch/MindSpore |

### Supported Environments

**NPU Models**: Atlas 910A / 910B / 910B2 / 910B3 / 310P / 310
**Operating Systems**: Ubuntu 20.04/22.04/24.04, openEuler 22.03/24.03, Kylin V10
**CPU Architectures**: x86_64, aarch64

## Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/iannil/ascend-docker-kit.git
cd ascend-docker-kit

# Install dependencies
pip install -r requirements.txt
```

### Basic Usage

#### 1. Detect Host Environment

```python
from adk_core import EnvironmentAnalyzer

# Auto-detect environment
env = EnvironmentAnalyzer.analyze()

print(f"OS: {env.os_name}")
print(f"CPU Architecture: {env.arch}")
print(f"NPU Model: {env.npu_type}")
print(f"NPU Count: {env.npu_count}")
print(f"Driver Version: {env.driver_version}")
```

Example output:

```
OS: ubuntu22.04
CPU Architecture: x86_64
NPU Model: 910B
NPU Count: 8
Driver Version: 24.1.rc1
```

#### 2. Validate Environment Compatibility

```python
from adk_core import EnvironmentAnalyzer, CompatibilityResolver

# Detect environment
env = EnvironmentAnalyzer.analyze()

# Load compatibility matrix
resolver = CompatibilityResolver.from_yaml('data/compatibility.yaml')

# Validate compatibility
result = resolver.validate_environment(env)

if result.valid:
    print(f"Compatible CANN versions: {result.compatible_cann_versions}")
else:
    print(f"Errors: {result.errors}")
```

#### 3. Query Framework Configuration

```python
from adk_core import CompatibilityResolver

resolver = CompatibilityResolver.from_yaml('data/compatibility.yaml')

# Get PyTorch configuration for CANN 8.0.0
config = resolver.get_framework_config("8.0.0", "pytorch")

print(f"PyTorch Version: {config.version}")
print(f"torch_npu Version: {config.torch_npu_version}")
print(f"Supported Python Versions: {config.python_versions}")
print(f"Download URL: {config.whl_url}")
```

#### 4. Get Recommended Versions

```python
from adk_core import CompatibilityResolver

resolver = CompatibilityResolver.from_yaml('data/compatibility.yaml')

# Get recommended CANN version based on driver version
recommended = resolver.get_recommended_cann(
    driver_version="24.1.0",
    os_name="ubuntu22.04",
    npu_type="910B"
)

print(f"Recommended CANN Version: {recommended}")  # 8.0.0
```

### Shell Script Detection

You can also use the shell script to detect NPU information directly:

```bash
bash scripts/check_npu.sh
```

JSON output:

```json
{
  "status": "ok",
  "driver_version": "24.1.rc1",
  "npu_count": 8,
  "npus": [{"id": 0, "type": "910B"}, {"id": 1, "type": "910B"}]
}
```

## API Reference

### EnvironmentAnalyzer

Environment detector for detecting host environment information.

| Method | Description | Return Value |
| -------- | ------------- | -------------- |
| `analyze()` | Full environment detection | `EnvironmentInfo` |
| `analyze_safe()` | Safe mode (no exceptions) | `(EnvironmentInfo, List[str])` |
| `detect_os()` | Detect operating system | `str` |
| `detect_arch()` | Detect CPU architecture | `str` |
| `detect_npu()` | Detect NPU information | `Dict` |

### CompatibilityResolver

Compatibility resolver for querying version compatibility information.

| Method | Description |
| -------- | ------------- |
| `from_yaml(path)` | Create instance from YAML file |
| `list_cann_versions()` | List all CANN versions |
| `find_compatible_cann(driver_version)` | Find compatible CANN versions |
| `get_recommended_cann(driver_version)` | Get recommended CANN version |
| `validate_environment(env)` | Validate environment compatibility |
| `get_framework_config(cann_version, framework)` | Get framework configuration |

### Data Models

```python
class EnvironmentInfo:
    driver_version: str   # NPU driver version
    os_name: str          # Operating system (e.g., ubuntu22.04)
    npu_type: str         # NPU model (e.g., 910B)
    arch: str             # CPU architecture (x86_64/aarch64)
    npu_count: int        # Number of NPUs
    firmware_version: Optional[str]  # Firmware version

class ValidationResult:
    valid: bool                        # Whether valid
    compatible_cann_versions: List[str]  # List of compatible CANN versions
    errors: List[str]                  # Error messages
    warnings: List[str]                # Warning messages
```

### Exception Classes

| Exception | Description |
| ----------- | ------------- |
| `EnvironmentDetectionError` | Environment detection failed |
| `DriverNotInstalledError` | NPU driver not installed |
| `NPUNotDetectedError` | No NPU device detected |
| `VersionNotFoundError` | Version not found |
| `DriverIncompatibleError` | Driver version incompatible |
| `OSNotSupportedError` | Operating system not supported |
| `NPUNotSupportedError` | NPU model not supported |

## Project Structure

```
ascend-docker-kit/
├── adk_core/                    # Core library
│   ├── __init__.py              # Module exports
│   ├── analyzer.py              # Environment analyzer
│   ├── matrix.py                # Compatibility resolver
│   ├── models.py                # Data models
│   ├── exceptions.py            # Exception definitions
│   └── version.py               # Version utilities
├── data/
│   └── compatibility.yaml       # Compatibility matrix data
├── scripts/
│   └── check_npu.sh             # NPU detection script
├── tests/                       # Unit tests
│   ├── test_analyzer.py
│   └── test_matrix.py
├── docs/                        # Documentation
├── requirements.txt             # Dependencies
└── README.md
```

## Compatibility Matrix

Compatibility data is stored in `data/compatibility.yaml`, containing the following CANN versions:

| CANN Version | Min Driver Version | PyTorch | MindSpore | Status |
| -------------- | ------------------- | --------- | ----------- | -------- |
| 8.0.0 | 24.1.rc1 | 2.4.0 | 2.3.0 | Stable |
| 8.0.0rc3 | 24.1.rc1 | 2.3.1 | 2.2.14 | RC |
| 7.0.0 | 23.0.3 | 2.1.0 | 2.2.0 | Stable |
| 6.3.0 | 22.0.4 | 1.11.0 | 1.10.1 | Deprecated |

## Development Guide

### Running Tests

```bash
# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run tests
pytest tests/ -v
```

### Adding New CANN Versions

Edit `data/compatibility.yaml` to add new version configuration:

```yaml
cann_versions:
  "8.1.0":
    min_driver_version: "24.2.0"
    supported_os:
      - ubuntu22.04
      - ubuntu24.04
    supported_npu:
      - 910B
      - 910B3
    supported_arch:
      - x86_64
      - aarch64
    frameworks:
      pytorch:
        version: "2.5.0"
        torch_npu_version: "2.5.0.post1"
        python_versions: ["3.9", "3.10", "3.11"]
    deprecated: false
```

## Roadmap

**Overall Progress: ~50%**

### Phase 1: Core Layer ✅ Completed
- [x] **Compatibility Matrix Library** - `matrix.py` (428 lines, 23 tests passed)
- [x] **Environment Analyzer** - `analyzer.py` (408 lines, 36 tests passed)
- [x] **Data Models** - Pydantic v2 type definitions
- [x] **Exception Handling** - 11 custom exception classes
- [x] **Version Utilities** - PEP 440 compliant version comparison
- [x] **NPU Detection Script** - `scripts/check_npu.sh` (JSON output)

### Phase 2: Build Layer 🚧 In Progress
- [ ] **Image Build Generator** - Dockerfile rendering with Jinja2 templates
- [ ] **Dockerfile Templates** - base, CANN, PyTorch/MindSpore multi-stage builds
- [ ] **CANN Installation Script** - Silent installation automation
- [ ] **Run Parameter Generator** - Docker run command generation with device mapping

### Phase 3: User Interface 📋 Planned
- [ ] **CLI Tool** - Command-line interface with Click
- [ ] **Examples** - Ready-to-use PyTorch/MindSpore configurations

## Contributing

Issues and Pull Requests are welcome.

1. Fork this repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Create a Pull Request

## License

This project is licensed under the Apache 2.0 License. See the [LICENSE](LICENSE) file for details.

## Resources

- [Huawei Ascend Official Website](https://www.hiascend.com/)
- [CANN Documentation](https://www.hiascend.com/document)
- [Ascend PyTorch](https://gitee.com/ascend/pytorch)

## Acknowledgments

Thanks to the Huawei Ascend team for providing official documentation and technical support.
