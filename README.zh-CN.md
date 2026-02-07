# Ascend Docker Kit (ADK)

华为昇腾 NPU 环境的 DevOps 工具包，自动化 Docker 环境配置，解决 CANN/驱动/框架版本兼容性问题。

[![Python](https://img.shields.io/badge/Python-3.8%2B-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-Apache%202.0-green)](LICENSE)

[English](README.md)

---

## 为什么需要 ADK？

在昇腾 NPU 环境中，CANN 版本、驱动版本、PyTorch/MindSpore 版本之间存在复杂的依赖关系。错误的组合会导致难以排查的错误或静默失败。ADK 通过以下方式解决这个问题：

- **结构化兼容性数据**：将华为官方文档中分散的信息整合为单一数据源
- **自动探测环境**：自动检测宿主机 NPU 型号、驱动版本和操作系统
- **智能推荐**：根据当前环境推荐兼容的 CANN 和框架版本
- **生成 Docker 构建**：创建即用的多阶段构建 Dockerfile

## 功能特性

| 功能 | 描述 |
|------|------|
| 环境探测 | 自动检测 NPU 型号（910A/910B/310P）、驱动版本、OS 发行版 |
| 兼容性验证 | 校验当前环境是否支持目标 CANN 版本 |
| 版本推荐 | 根据驱动版本推荐最佳 CANN 和框架组合 |
| Dockerfile 生成 | 生成用于训练/推理的多阶段构建 Dockerfile |
| CLI 接口 | 功能完整的命令行工具 |

### 支持的环境

| 类别 | 支持的值 |
|------|----------|
| **NPU 型号** | Atlas 910A, 910B, 910B2, 910B3, 310P, 310 |
| **操作系统** | Ubuntu 20.04/22.04/24.04, openEuler 22.03/24.03, Kylin V10 |
| **CPU 架构** | x86_64, aarch64 |
| **框架** | PyTorch (含 torch_npu), MindSpore |

## 安装

```bash
# 克隆仓库
git clone https://github.com/iannil/ascend-docker-kit.git
cd ascend-docker-kit

# 安装依赖
pip install -r requirements.txt
```

## 快速开始

### CLI 使用

ADK 提供了完整的命令行接口：

```bash
# 显示帮助
python adk.py --help

# 诊断当前环境
python adk.py diagnose
python adk.py diagnose --validate  # 含兼容性检查
python adk.py diagnose --json      # JSON 输出

# 查询 CANN 版本
python adk.py query cann           # 列出所有版本
python adk.py query cann 8.0.0     # 查看特定版本详情
python adk.py query cann --all     # 包含已废弃版本

# 查询框架配置
python adk.py query framework 8.0.0 pytorch
python adk.py query framework 8.0.0 mindspore

# 验证环境是否支持特定 CANN 版本
python adk.py validate 8.0.0

# 生成 Dockerfile 和构建脚本
python adk.py build init \
  --cann 8.0.0 \
  --framework pytorch \
  --target train \
  --python 3.10 \
  -o ./build
```

### Python API

#### 1. 探测宿主机环境

```python
from adk_core import EnvironmentAnalyzer

# 自动探测环境
env = EnvironmentAnalyzer.analyze()

print(f"操作系统: {env.os_name}")
print(f"CPU 架构: {env.arch}")
print(f"NPU 型号: {env.npu_type}")
print(f"NPU 数量: {env.npu_count}")
print(f"驱动版本: {env.driver_version}")
```

输出示例：

```
操作系统: ubuntu22.04
CPU 架构: x86_64
NPU 型号: 910B
NPU 数量: 8
驱动版本: 24.1.rc1
```

#### 2. 验证环境兼容性

```python
from adk_core import EnvironmentAnalyzer, CompatibilityResolver

env = EnvironmentAnalyzer.analyze()
resolver = CompatibilityResolver.from_yaml('data/compatibility.yaml')

result = resolver.validate_environment(env)

if result.valid:
    print(f"兼容的 CANN 版本: {result.compatible_cann_versions}")
else:
    print(f"错误: {result.errors}")
```

#### 3. 查询框架配置

```python
from adk_core import CompatibilityResolver

resolver = CompatibilityResolver.from_yaml('data/compatibility.yaml')

# 获取 CANN 8.0.0 的 PyTorch 配置
config = resolver.get_framework_config("8.0.0", "pytorch")

print(f"PyTorch 版本: {config.version}")
print(f"torch_npu 版本: {config.torch_npu_version}")
print(f"支持的 Python 版本: {config.python_versions}")
```

#### 4. 生成 Dockerfile

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

### Shell 脚本探测

```bash
bash scripts/check_npu.sh
```

JSON 输出：

```json
{
  "status": "ok",
  "driver_version": "24.1.rc1",
  "npu_count": 8,
  "npus": [{"id": 0, "type": "910B"}, {"id": 1, "type": "910B"}]
}
```

## 示例项目

`examples/` 目录下提供了即用示例：

### PyTorch 2.4 + 910B

```bash
cd examples/pytorch-2.4-910b

# 构建镜像
docker build -t pytorch-910b:2.4 .

# 运行容器并挂载 NPU
./run.sh

# 在容器内验证 NPU
python test_npu.py
```

### MindSpore 2.3 + 910B

```bash
cd examples/mindspore-2.3-910b

# 构建并运行
docker build -t mindspore-910b:2.3 .
./run.sh
python test_npu.py
```

## CLI 参考

### 全局选项

```bash
python adk.py [OPTIONS] COMMAND

选项:
  --version              显示版本
  --matrix PATH          指定兼容性矩阵文件路径
  --help                 显示帮助信息
```

### 命令列表

| 命令 | 描述 |
|------|------|
| `diagnose` | 检测并显示宿主机环境信息 |
| `validate CANN_VERSION` | 检查环境是否支持指定 CANN 版本 |
| `query cann [VERSION]` | 列出 CANN 版本或显示某版本详情 |
| `query framework CANN FRAMEWORK` | 显示 CANN 版本的框架配置 |
| `build init` | 生成 Dockerfile 和构建脚本 |

### Build 命令选项

```bash
python adk.py build init [OPTIONS]

选项:
  --cann VERSION         CANN 版本（必需）
  --framework TYPE       pytorch 或 mindspore（必需）
  --target TYPE          train 或 inference（默认: train）
  --python VERSION       Python 版本（默认: 自动检测）
  -o, --output PATH      输出目录（默认: 当前目录）
  --auto-detect          自动检测环境配置
  --no-china-mirror      禁用国内 pip 镜像
```

## API 参考

### EnvironmentAnalyzer

| 方法 | 描述 | 返回值 |
|------|------|--------|
| `analyze()` | 完整环境探测 | `EnvironmentInfo` |
| `analyze_safe()` | 安全模式（不抛异常） | `(EnvironmentInfo, List[str])` |
| `detect_os()` | 检测操作系统 | `str` |
| `detect_arch()` | 检测 CPU 架构 | `str` |
| `detect_npu()` | 检测 NPU 信息 | `Dict` |

### CompatibilityResolver

| 方法 | 描述 |
|------|------|
| `from_yaml(path)` | 从 YAML 文件创建实例 |
| `list_cann_versions()` | 列出所有 CANN 版本 |
| `get_cann_requirements(version)` | 获取 CANN 版本的要求 |
| `find_compatible_cann(driver)` | 查找兼容的 CANN 版本 |
| `validate_environment(env)` | 验证环境兼容性 |
| `get_framework_config(cann, framework)` | 获取框架配置 |

### DockerfileGenerator

| 方法 | 描述 |
|------|------|
| `create_context(...)` | 创建构建上下文 |
| `generate(context)` | 生成 Dockerfile 内容 |
| `write_output(output, path)` | 将文件写入目录 |

### 数据模型

```python
class EnvironmentInfo:
    driver_version: str       # NPU 驱动版本
    os_name: str              # 操作系统（如 ubuntu22.04）
    npu_type: str             # NPU 型号（如 910B）
    arch: str                 # CPU 架构（x86_64/aarch64）
    npu_count: int            # NPU 数量
    firmware_version: Optional[str]

class ValidationResult:
    valid: bool
    compatible_cann_versions: List[str]
    errors: List[str]
    warnings: List[str]
```

### 异常类

所有异常继承自 `ADKError`，并包含 `suggestions` 列表。

| 异常 | 触发条件 |
|------|----------|
| `EnvironmentDetectionError` | `/etc/os-release` 缺失或不可读 |
| `DriverNotInstalledError` | 找不到 `npu-smi` 命令 |
| `NPUNotDetectedError` | 未检测到 NPU 设备 |
| `ConfigurationError` | YAML 文件无效或缺失 |
| `VersionNotFoundError` | CANN 版本不在矩阵中 |
| `DriverIncompatibleError` | 驱动版本超出支持范围 |
| `OSNotSupportedError` | 操作系统不支持该 CANN 版本 |
| `NPUNotSupportedError` | NPU 型号不支持 |
| `FrameworkNotFoundError` | 框架不可用于该 CANN 版本 |

## 项目结构

```
ascend-docker-kit/
├── adk.py                       # CLI 入口
├── adk_core/                    # 核心库
│   ├── __init__.py              # 模块导出
│   ├── analyzer.py              # 环境诊断器
│   ├── matrix.py                # 兼容性查询
│   ├── generator.py             # Dockerfile 生成器
│   ├── models.py                # 数据模型（Pydantic v2）
│   ├── exceptions.py            # 异常定义
│   └── version.py               # 版本工具
├── data/
│   └── compatibility.yaml       # 兼容性矩阵数据
├── templates/                   # Jinja2 Dockerfile 模板
│   ├── Dockerfile.base.j2
│   ├── Dockerfile.cann.j2
│   └── Dockerfile.pytorch.j2
├── scripts/
│   ├── check_npu.sh             # NPU 检测脚本
│   └── install_cann.sh          # CANN 静默安装
├── examples/                    # 即用示例
│   ├── pytorch-2.4-910b/
│   └── mindspore-2.3-910b/
├── tests/                       # 单元测试
├── docs/                        # 文档
├── pyproject.toml               # 项目配置
└── requirements.txt             # 依赖
```

## 兼容性矩阵

`data/compatibility.yaml` 中的兼容性数据包括：

| CANN 版本 | 最低驱动版本 | PyTorch | MindSpore | 状态 |
|-----------|--------------|---------|-----------|------|
| 8.0.0 | 24.1.rc1 | 2.4.0 | 2.3.0 | 稳定版 |
| 8.0.0rc3 | 24.1.rc1 | 2.3.1 | 2.2.14 | RC 版 |
| 7.0.0 | 23.0.3 | 2.1.0 | 2.2.0 | 稳定版 |
| 6.3.0 | 22.0.4 | 1.11.0 | 1.10.1 | 已废弃 |

## 开发指南

### 运行测试

```bash
# 创建虚拟环境
python3 -m venv .venv
source .venv/bin/activate

# 安装依赖
pip install -r requirements.txt

# 运行测试
pytest tests/ -v
```

### 添加新的 CANN 版本

编辑 `data/compatibility.yaml`：

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

## 路线图

### 已完成 ✅

- **核心层**：兼容性矩阵、环境诊断器、数据模型
- **构建层**：Dockerfile 生成器、Jinja2 模板（PyTorch 和 MindSpore）、CLI 接口
- **示例**：PyTorch 和 MindSpore 即用配置
- **质量保证**：90+ 测试用例、类型注解、异常处理

### 计划中 📋

- [ ] 真实 NPU 硬件的集成测试
- [ ] PyPI 包发布
- [ ] 可视化配置的 GUI 工具

## 贡献指南

欢迎提交 Issue 和 Pull Request。

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/amazing-feature`)
3. 提交更改 (`git commit -m 'Add amazing feature'`)
4. 推送到分支 (`git push origin feature/amazing-feature`)
5. 创建 Pull Request

## 许可证

本项目采用 Apache 2.0 许可证。详见 [LICENSE](LICENSE) 文件。

## 相关资源

- [华为昇腾官网](https://www.hiascend.com/)
- [CANN 文档](https://www.hiascend.com/document)
- [Ascend PyTorch](https://gitee.com/ascend/pytorch)
- [Ascend MindSpore](https://www.mindspore.cn/)

## 致谢

感谢华为昇腾团队提供的官方文档和技术支持。
