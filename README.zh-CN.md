# Ascend Docker Kit (ADK)

华为昇腾 NPU 环境的 DevOps 工具包，自动化 Docker 环境配置，解决 CANN/驱动/框架版本兼容性问题。

[![Python](https://img.shields.io/badge/Python-3.8%2B-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-Apache%202.0-green)](LICENSE)

---

## 项目简介

在昇腾 NPU 环境中，CANN 版本、驱动版本、PyTorch/MindSpore 版本之间存在复杂的依赖关系。ADK 通过以下核心功能解决这个问题：

- **兼容性矩阵库**：将华为官方文档中分散的版本兼容信息结构化为单一数据源
- **环境诊断器**：自动探测宿主机环境（NPU 型号、驱动版本、操作系统）
- **智能推荐**：根据当前环境自动推荐兼容的 CANN 和框架版本

## 功能特性

| 功能 | 描述 |
| ------ | ------ |
| 环境探测 | 自动检测 NPU 型号（910A/910B/310P）、驱动版本、OS 发行版 |
| 兼容性验证 | 校验当前环境是否支持目标 CANN 版本 |
| 版本推荐 | 根据驱动版本推荐最佳 CANN 和框架组合 |
| 框架配置 | 获取 PyTorch/MindSpore 对应的 torch_npu 版本和安装方式 |

### 支持的环境

**NPU 型号**：Atlas 910A / 910B / 910B2 / 910B3 / 310P / 310
**操作系统**：Ubuntu 20.04/22.04/24.04、openEuler 22.03/24.03、Kylin V10
**CPU 架构**：x86_64、aarch64

## 快速开始

### 安装

```bash
# 克隆仓库
git clone https://github.com/iannil/ascend-docker-kit.git
cd ascend-docker-kit

# 安装依赖
pip install -r requirements.txt
```

### 基本使用

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

# 探测环境
env = EnvironmentAnalyzer.analyze()

# 加载兼容性矩阵
resolver = CompatibilityResolver.from_yaml('data/compatibility.yaml')

# 验证兼容性
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
print(f"下载地址: {config.whl_url}")
```

#### 4. 获取推荐版本

```python
from adk_core import CompatibilityResolver

resolver = CompatibilityResolver.from_yaml('data/compatibility.yaml')

# 根据驱动版本获取推荐的 CANN 版本
recommended = resolver.get_recommended_cann(
    driver_version="24.1.0",
    os_name="ubuntu22.04",
    npu_type="910B"
)

print(f"推荐 CANN 版本: {recommended}")  # 8.0.0
```

### Shell 脚本探测

也可以直接使用 Shell 脚本探测 NPU 信息：

```bash
bash scripts/check_npu.sh
```

输出 JSON 格式：

```json
{
  "status": "ok",
  "driver_version": "24.1.rc1",
  "npu_count": 8,
  "npus": [{"id": 0, "type": "910B"}, {"id": 1, "type": "910B"}]
}
```

## API 参考

### EnvironmentAnalyzer

环境探测器，用于检测宿主机环境信息。

| 方法 | 描述 | 返回值 |
| ------ | ------ | -------- |
| `analyze()` | 完整环境探测 | `EnvironmentInfo` |
| `analyze_safe()` | 安全模式（不抛异常） | `(EnvironmentInfo, List[str])` |
| `detect_os()` | 检测操作系统 | `str` |
| `detect_arch()` | 检测 CPU 架构 | `str` |
| `detect_npu()` | 检测 NPU 信息 | `Dict` |

### CompatibilityResolver

兼容性查询器，用于查询版本兼容性信息。

| 方法 | 描述 |
| ------ | ------ |
| `from_yaml(path)` | 从 YAML 文件创建实例 |
| `list_cann_versions()` | 列出所有 CANN 版本 |
| `find_compatible_cann(driver_version)` | 查找兼容的 CANN 版本 |
| `get_recommended_cann(driver_version)` | 获取推荐的 CANN 版本 |
| `validate_environment(env)` | 验证环境兼容性 |
| `get_framework_config(cann_version, framework)` | 获取框架配置 |

### 数据模型

```python
class EnvironmentInfo:
    driver_version: str   # NPU 驱动版本
    os_name: str          # 操作系统（如 ubuntu22.04）
    npu_type: str         # NPU 型号（如 910B）
    arch: str             # CPU 架构（x86_64/aarch64）
    npu_count: int        # NPU 数量
    firmware_version: Optional[str]  # 固件版本

class ValidationResult:
    valid: bool                        # 是否有效
    compatible_cann_versions: List[str]  # 兼容的 CANN 版本列表
    errors: List[str]                  # 错误信息
    warnings: List[str]                # 警告信息
```

### 异常类

| 异常 | 描述 |
| ------ | ------ |
| `EnvironmentDetectionError` | 环境探测失败 |
| `DriverNotInstalledError` | NPU 驱动未安装 |
| `NPUNotDetectedError` | 未检测到 NPU 设备 |
| `VersionNotFoundError` | 版本不存在 |
| `DriverIncompatibleError` | 驱动版本不兼容 |
| `OSNotSupportedError` | 操作系统不支持 |
| `NPUNotSupportedError` | NPU 型号不支持 |

## 项目结构

```
ascend-docker-kit/
├── adk_core/                    # 核心库
│   ├── __init__.py              # 模块导出
│   ├── analyzer.py              # 环境诊断器
│   ├── matrix.py                # 兼容性查询
│   ├── models.py                # 数据模型
│   ├── exceptions.py            # 异常定义
│   └── version.py               # 版本工具
├── data/
│   └── compatibility.yaml       # 兼容性矩阵数据
├── scripts/
│   └── check_npu.sh             # NPU 检测脚本
├── tests/                       # 单元测试
│   ├── test_analyzer.py
│   └── test_matrix.py
├── docs/                        # 文档
├── requirements.txt             # 依赖
└── README.md
```

## 兼容性矩阵

兼容性数据存储在 `data/compatibility.yaml`，包含以下 CANN 版本：

| CANN 版本 | 最低驱动版本 | PyTorch | MindSpore | 状态 |
| ---------- | ------------- | --------- | ----------- | ------ |
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

编辑 `data/compatibility.yaml`，添加新版本配置：

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

**整体进度：约 50%**

### 第一阶段：核心层 ✅ 已完成
- [x] **兼容性矩阵库** - `matrix.py`（428 行，23 个测试通过）
- [x] **环境诊断器** - `analyzer.py`（408 行，36 个测试通过）
- [x] **数据模型** - Pydantic v2 类型定义
- [x] **异常处理** - 11 个自定义异常类
- [x] **版本工具** - PEP 440 版本比较
- [x] **NPU 检测脚本** - `scripts/check_npu.sh`（JSON 输出）

### 第二阶段：构建层 🚧 进行中
- [ ] **镜像构建生成器** - Jinja2 模板渲染 Dockerfile
- [ ] **Dockerfile 模板** - base、CANN、PyTorch/MindSpore 多阶段构建
- [ ] **CANN 安装脚本** - 静默安装自动化
- [ ] **运行参数生成器** - docker run 命令生成（设备映射）

### 第三阶段：用户界面 📋 计划中
- [ ] **CLI 工具** - Click 命令行接口
- [ ] **示例代码** - 开箱即用的 PyTorch/MindSpore 配置

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

## 致谢

感谢华为昇腾团队提供的官方文档和技术支持。
