# Ascend Docker Kit (ADK)

A DevOps toolkit for Huawei Ascend NPU environments that automates Docker environment configuration and resolves complex CANN/driver/framework version compatibility issues.

[![Python](https://img.shields.io/badge/Python-3.8%2B-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-Apache%202.0-green)](LICENSE)

[中文文档](README.zh-CN.md)

---

## Why ADK?

In Ascend NPU environments, complex dependencies exist between CANN versions, driver versions, and PyTorch/MindSpore versions. A wrong combination can lead to cryptic errors or silent failures. ADK solves this problem by:

- **Structuring Compatibility Data**: Converting scattered Huawei documentation into a single source of truth
- **Auto-detecting Environment**: Probing host NPU model, driver version, and OS automatically
- **Smart Recommendations**: Suggesting compatible CANN and framework versions for your setup
- **Generating Docker Builds**: Creating ready-to-use Dockerfiles with proper multi-stage builds

## Features

| Feature | Description |
|---------|-------------|
| Environment Detection | Auto-detect NPU model (910A/910B/310P), driver version, OS distribution |
| Compatibility Validation | Verify if current environment supports target CANN version |
| Version Recommendation | Recommend optimal CANN and framework combinations based on driver |
| Dockerfile Generation | Generate multi-stage Dockerfiles for training/inference |
| CLI Interface | Full-featured command-line tool for all operations |

### Supported Environments

| Category | Supported Values |
|----------|------------------|
| **NPU Models** | Atlas 910A, 910B, 910B2, 910B3, 310P, 310 |
| **Operating Systems** | Ubuntu 20.04/22.04/24.04, openEuler 22.03/24.03, Kylin V10 |
| **CPU Architectures** | x86_64, aarch64 |
| **Frameworks** | PyTorch (with torch_npu), MindSpore |

## Installation

```bash
# Clone the repository
git clone https://github.com/iannil/ascend-docker-kit.git
cd ascend-docker-kit

# Install dependencies
pip install -r requirements.txt
```

## Quick Start

### CLI Usage

ADK provides a comprehensive CLI for all operations:

```bash
# Show help
python adk.py --help

# Diagnose current environment
python adk.py diagnose
python adk.py diagnose --validate  # With compatibility check
python adk.py diagnose --json      # JSON output

# Query CANN versions
python adk.py query cann           # List all versions
python adk.py query cann 8.0.0     # Details for specific version
python adk.py query cann --all     # Include deprecated versions

# Query framework configuration
python adk.py query framework 8.0.0 pytorch
python adk.py query framework 8.0.0 mindspore

# Validate environment for specific CANN version
python adk.py validate 8.0.0

# Generate Dockerfile and build scripts
python adk.py build init \
  --cann 8.0.0 \
  --framework pytorch \
  --target train \
  --python 3.10 \
  -o ./build
```

### Python API

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

env = EnvironmentAnalyzer.analyze()
resolver = CompatibilityResolver.from_yaml('data/compatibility.yaml')

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
```

#### 4. Generate Dockerfile

```python
from adk_core import DockerfileGenerator, CompatibilityResolver
from adk_core.generator import BuildTarget, FrameworkType

resolver = CompatibilityResolver.from_yaml('data/compatibility.yaml')
generator = DockerfileGenerator(resolver)

context = generator.create_context(
    cann_version="8.0.0",
    framework=FrameworkType.PYTORCH,
    target=BuildTarget.TRAIN,
    python_version="3.10"
)

output = generator.generate(context)
generator.write_output(output, "./build/")
```

### Shell Script Detection

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

## Examples

Ready-to-use examples are provided in the `examples/` directory:

### PyTorch 2.4 + 910B

```bash
cd examples/pytorch-2.4-910b

# Build the image
docker build -t pytorch-910b:2.4 .

# Run container with NPU access
./run.sh

# Verify NPU inside container
python test_npu.py
```

### MindSpore 2.3 + 910B

```bash
cd examples/mindspore-2.3-910b

# Build and run
docker build -t mindspore-910b:2.3 .
./run.sh
python test_npu.py
```

## CLI Reference

### Global Options

```bash
python adk.py [OPTIONS] COMMAND

Options:
  --version              Show version
  --matrix PATH          Path to compatibility matrix file
  --help                 Show help message
```

### Commands

| Command | Description |
|---------|-------------|
| `diagnose` | Detect and display host environment information |
| `validate CANN_VERSION` | Check if environment supports a CANN version |
| `query cann [VERSION]` | List CANN versions or show details for one |
| `query framework CANN FRAMEWORK` | Show framework config for CANN version |
| `build init` | Generate Dockerfile and build scripts |

### Build Command Options

```bash
python adk.py build init [OPTIONS]

Options:
  --cann VERSION         CANN version (required)
  --framework TYPE       pytorch or mindspore (required)
  --target TYPE          train or inference (default: train)
  --python VERSION       Python version (default: auto-detect)
  -o, --output PATH      Output directory (default: current)
  --auto-detect          Auto-detect environment settings
  --no-china-mirror      Disable China mirror for pip
```

## API Reference

### EnvironmentAnalyzer

| Method | Description | Return |
|--------|-------------|--------|
| `analyze()` | Full environment detection | `EnvironmentInfo` |
| `analyze_safe()` | Safe mode (no exceptions) | `(EnvironmentInfo, List[str])` |
| `detect_os()` | Detect operating system | `str` |
| `detect_arch()` | Detect CPU architecture | `str` |
| `detect_npu()` | Detect NPU information | `Dict` |

### CompatibilityResolver

| Method | Description |
|--------|-------------|
| `from_yaml(path)` | Create instance from YAML file |
| `list_cann_versions()` | List all CANN versions |
| `get_cann_requirements(version)` | Get requirements for CANN version |
| `find_compatible_cann(driver)` | Find compatible CANN versions |
| `validate_environment(env)` | Validate environment compatibility |
| `get_framework_config(cann, framework)` | Get framework configuration |

### DockerfileGenerator

| Method | Description |
|--------|-------------|
| `create_context(...)` | Create build context |
| `generate(context)` | Generate Dockerfile content |
| `write_output(output, path)` | Write files to directory |

### Data Models

```python
class EnvironmentInfo:
    driver_version: str       # NPU driver version
    os_name: str              # Operating system (e.g., ubuntu22.04)
    npu_type: str             # NPU model (e.g., 910B)
    arch: str                 # CPU architecture (x86_64/aarch64)
    npu_count: int            # Number of NPUs
    firmware_version: Optional[str]

class ValidationResult:
    valid: bool
    compatible_cann_versions: List[str]
    errors: List[str]
    warnings: List[str]
```

### Exception Classes

All exceptions inherit from `ADKError` and include a `suggestions` list.

| Exception | Raised When |
|-----------|-------------|
| `EnvironmentDetectionError` | `/etc/os-release` missing or unreadable |
| `DriverNotInstalledError` | `npu-smi` command not found |
| `NPUNotDetectedError` | No NPU devices found |
| `ConfigurationError` | YAML file invalid or missing |
| `VersionNotFoundError` | CANN version not in matrix |
| `DriverIncompatibleError` | Driver version outside supported range |
| `OSNotSupportedError` | OS not supported by CANN version |
| `NPUNotSupportedError` | NPU model not supported |
| `FrameworkNotFoundError` | Framework not available for CANN version |

## Project Structure

```
ascend-docker-kit/
├── adk.py                       # CLI entry point
├── adk_core/                    # Core library
│   ├── __init__.py              # Module exports
│   ├── analyzer.py              # Environment analyzer
│   ├── matrix.py                # Compatibility resolver
│   ├── generator.py             # Dockerfile generator
│   ├── models.py                # Data models (Pydantic v2)
│   ├── exceptions.py            # Exception definitions
│   └── version.py               # Version utilities
├── data/
│   └── compatibility.yaml       # Compatibility matrix data
├── templates/                   # Jinja2 Dockerfile templates
│   ├── Dockerfile.base.j2
│   ├── Dockerfile.cann.j2
│   └── Dockerfile.pytorch.j2
├── scripts/
│   ├── check_npu.sh             # NPU detection script
│   └── install_cann.sh          # CANN silent installation
├── examples/                    # Ready-to-use examples
│   ├── pytorch-2.4-910b/
│   └── mindspore-2.3-910b/
├── tests/                       # Unit tests
├── docs/                        # Documentation
├── pyproject.toml               # Project configuration
└── requirements.txt             # Dependencies
```

## Compatibility Matrix

The compatibility data in `data/compatibility.yaml` includes:

| CANN Version | Min Driver | PyTorch | MindSpore | Status |
|--------------|------------|---------|-----------|--------|
| 8.0.0 | 24.1.rc1 | 2.4.0 | 2.3.0 | Stable |
| 8.0.0rc3 | 24.1.rc1 | 2.3.1 | 2.2.14 | RC |
| 7.0.0 | 23.0.3 | 2.1.0 | 2.2.0 | Stable |
| 6.3.0 | 22.0.4 | 1.11.0 | 1.10.1 | Deprecated |

## Development

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

Edit `data/compatibility.yaml`:

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

### Completed ✅

- **Core Layer**: Compatibility matrix, environment analyzer, data models
- **Build Layer**: Dockerfile generator, Jinja2 templates (PyTorch & MindSpore), CLI interface
- **Examples**: PyTorch and MindSpore ready-to-use configurations
- **Quality**: 90+ test cases, type annotations, exception handling

### Planned 📋

- [ ] Integration tests on real NPU hardware
- [ ] PyPI package distribution
- [ ] GUI tool for visual configuration

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
- [Ascend MindSpore](https://www.mindspore.cn/)

## Acknowledgments

Thanks to the Huawei Ascend team for providing official documentation and technical support.
