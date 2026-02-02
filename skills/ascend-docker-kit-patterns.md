---
name: ascend-docker-kit-patterns
description: Coding patterns extracted from ascend-docker-kit repository
version: 1.0.0
source: local-git-analysis
analyzed_commits: 6
---

# Ascend Docker Kit Patterns

## Project Overview

Ascend Docker Kit (ADK) is a DevOps toolkit for Huawei Ascend NPU environments. It automates Docker environment configuration, connecting infrastructure (NPU drivers/firmware) with upper-layer frameworks (PyTorch/MindSpore).

**Tech Stack:** Python (core logic) + Shell (system detection) + Jinja2 (Dockerfile templates)

**Language Convention:** Communication and documentation in Chinese; generated code in English.

## Code Architecture

```
ascend-docker-kit/
├── adk.py                  # CLI entry point
├── adk_core/               # Core library (all Python modules)
│   ├── __init__.py         # Public API exports
│   ├── analyzer.py         # Environment detection (npu-smi info parsing)
│   ├── checksum.py         # Package integrity verification
│   ├── exceptions.py       # Custom exception hierarchy
│   ├── generator.py        # Jinja2 Dockerfile rendering
│   ├── matrix.py           # CANN compatibility matrix resolver
│   ├── models.py           # Pydantic data models
│   └── version.py          # Version comparison utilities
├── data/
│   └── compatibility.yaml  # Single source of truth for versions
├── templates/              # Jinja2 Dockerfile templates
│   ├── Dockerfile.base.j2
│   ├── Dockerfile.cann.j2
│   └── Dockerfile.pytorch.j2
├── scripts/                # Shell helper scripts
│   ├── install_cann.sh     # Silent CANN installation
│   └── check_npu.sh        # Container startup self-check
├── tests/                  # Unit tests (pytest)
│   ├── test_analyzer.py
│   ├── test_matrix.py
│   └── test_edge_cases.py
└── examples/               # Ready-to-use examples
    ├── pytorch-2.4-910b/
    └── mindspore-2.3-910b/
```

### Module Organization

- **High cohesion, low coupling**: Each module has a single responsibility
- **200-400 lines typical**: `exceptions.py` (~170 lines), `models.py` (~190 lines)
- **Stable public API**: All exports through `adk_core/__init__.py`

## Commit Conventions

This project uses **mixed commit message styles** (not yet standardized):
- Some use `feat:` prefix (e.g., `feat: update roadmap`)
- Most use descriptive messages in Chinese/English mixed

**Recommendation**: Adopt conventional commits going forward:
- `feat:` - New features
- `fix:` - Bug fixes
- `refactor:` - Code refactoring
- `docs:` - Documentation updates
- `test:` - Test updates
- `chore:` - Maintenance tasks

## Coding Style

### Python Conventions

1. **Module-level documentation**: Each module starts with a docstring describing its purpose
2. **Type hints**: Extensive use of `typing` module for function signatures
3. **Pydantic models**: Use `pydantic` for data validation and schema definition
4. **Exception hierarchy**: Custom exceptions in `exceptions.py` for domain-specific errors

```python
# Typical module structure
"""
ADK Module Name

Brief description of module purpose.
"""

from typing import Any, Dict, List, Optional
from pydantic import ValidationError

from .exceptions import CustomException
from .models import DataModel

class ClassName:
    """Brief class description."""

    def method_name(self, param: str) -> Result:
        """Brief method description."""
        # Implementation
```

### Imports Organization

```python
# 1. Standard library
from pathlib import Path
from typing import Any, Dict, List

# 2. Third-party
import yaml
from pydantic import ValidationError

# 3. Local imports (relative)
from .exceptions import ConfigurationError
from .models import CompatibilityMatrix
```

### Error Handling Pattern

```python
try:
    result = risky_operation()
    return result
except ValidationError as e:
    raise ConfigurationError(f"Invalid configuration: {e}")
except FileNotFoundError:
    raise ConfigurationError(f"File not found: {path}")
```

## Testing Patterns

### Test Structure

- **Framework**: pytest
- **Test location**: `tests/` directory
- **Naming**: `test_<module>.py` pattern
- **Coverage target**: 80%+

### Test Organization

```python
"""Tests for ADK Core Module Name."""

import pytest
from pathlib import Path

from adk_core import (
    ClassUnderTest,
    ExceptionToTest,
)

class TestFeatureGroup:
    """Tests for related functionality."""

    @pytest.fixture
    def setup_data(self):
        """Create test data."""
        return test_value

    def test_specific_behavior(self, setup_data):
        """Test that specific behavior works correctly."""
        assert setup_data.expected_result()
```

### Common Test Patterns

- Use `pytest.raises` for exception testing
- Use `@pytest.fixture` for reusable test data
- Group related tests in classes
- Test both success and failure paths

## Documentation Conventions

### Folder Structure

```
docs/
├── design/              # Technical design documents
├── progress/            # Work-in-progress (dated)
├── reports/             # Acceptance reports (dated)
├── reports/completed/   # Completed work (dated)
├── standards/           # Documentation standards
└── templates/           # Document templates
```

### Naming Conventions

- **Progress files**: `YYYY-MM-DD- description.md`
- **Report files**: `YYYY-MM-DD-acceptance.md`
- **Completed files**: `YYYY-MM-DD-topic.md`

### Progress Tracking

- Save progress **during** development with timestamps
- Move completed work to `reports/completed/`
- Update `PROJECT-STATUS.md` for overall project status

## Key Design Constraints

1. **CANN packages require Huawei login**: Assume `.run` packages are pre-downloaded to `packages/`
2. **torch_npu version matching**: Must strictly match PyTorch version; use locked whl URLs from `compatibility.yaml`
3. **Training vs Inference images**:
   - Training: Full compiler/headers (~10GB+)
   - Inference: Use `--target inference` for minimal runtime (~3GB)

## Common Workflows

### Adding a New NPU Support

1. Update `data/compatibility.yaml` with new NPU info
2. Add test cases in `tests/test_matrix.py`
3. Update documentation in `docs/progress/`

### Adding a New Framework

1. Add framework config to `compatibility.yaml`
2. Create new Jinja2 template in `templates/`
3. Update `generator.py` to render new template
4. Add example in `examples/`
5. Write tests

### Version Update Process

1. Update `data/compatibility.yaml` with new versions
2. Run `pytest` to verify compatibility checks
3. Update examples with new versions
4. Update documentation

## Data-Driven Configuration

The project uses YAML as a single source of truth:

```yaml
# data/compatibility.yaml structure
version: "1.0.0"
last_updated: "YYYY-MM-DD"

cann_versions:
  "8.0.0":
    min_driver_version: "24.1.rc1"
    supported_os: ["ubuntu20.04", "ubuntu22.04"]
    supported_npu: ["910B", "910B2", "310P"]
    frameworks:
      pytorch:
        version: "2.4.0"
        torch_npu_version: "2.4.0.post2"
```

## Release Conventions

- **Release directory**: `/release`
- **Rust services**: `/release/rust`
- **Production standard**: All release artifacts must be production-ready
- **Include**: Full release + delta release, first-time + update releases

## Important Notes

1. **LLM-Friendly Design**: Consistent structure, clear boundaries, explicit types
2. **Immutability**: Prefer creating new objects over mutation
3. **Small commits**: Use `IMPLEMENTATION_PLAN.md` and small commits for context
4. **Backup before bulk changes**: Copy files to `/backup` relative path before batch operations
