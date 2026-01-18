# 项目状态总览

> **最后更新**：2026-01-18
> **项目阶段**：设计阶段

## 项目简介

Ascend Docker Kit (ADK) 是华为昇腾 NPU 环境的 DevOps 工具包，通过自动化 Docker 环境配置，连接基础设施（NPU 驱动/固件）与上层应用（PyTorch/MindSpore）。

## 模块实现状态

| 模块 | 路径 | 状态 | 说明 |
| ------ | ------ | ------ | ------ |
| CLI 入口 | `adk.py` | 未实现 | 命令行接口主入口 |
| 兼容性矩阵库 | `adk_core/matrix.py` | 未实现 | CANN 版本映射逻辑 |
| 环境诊断器 | `adk_core/analyzer.py` | 未实现 | 宿主机 NPU 环境探测 |
| 镜像构建生成器 | `adk_core/generator.py` | 未实现 | Dockerfile 渲染引擎 |
| 兼容性数据 | `data/compatibility.yaml` | 未实现 | 版本兼容性矩阵数据 |
| Base 模板 | `templates/Dockerfile.base.j2` | 未实现 | 基础镜像模板 |
| CANN 模板 | `templates/Dockerfile.cann.j2` | 未实现 | CANN 安装模板 |
| PyTorch 模板 | `templates/Dockerfile.pytorch.j2` | 未实现 | PyTorch 框架模板 |
| CANN 安装脚本 | `scripts/install_cann.sh` | 未实现 | CANN 静默安装脚本 |
| NPU 检测脚本 | `scripts/check_npu.sh` | 未实现 | 容器启动自检脚本 |
| 示例代码 | `examples/` | 未实现 | 开箱即用示例 |

## 目录结构对照

### 计划结构 vs 实际结构

```
ascend-docker-kit/
├── adk.py                  # [未实现] CLI 入口
├── adk_core/               # [未实现] 核心模块目录
│   ├── matrix.py           # [未实现] 兼容性逻辑
│   ├── analyzer.py         # [未实现] 环境探测
│   └── generator.py        # [未实现] Dockerfile 渲染
├── data/                   # [未实现] 数据目录
│   └── compatibility.yaml  # [未实现] 版本兼容性矩阵
├── templates/              # [未实现] Jinja2 模板目录
│   ├── Dockerfile.base.j2
│   ├── Dockerfile.cann.j2
│   └── Dockerfile.pytorch.j2
├── scripts/                # [未实现] Shell 脚本目录
│   ├── install_cann.sh
│   └── check_npu.sh
├── examples/               # [未实现] 示例目录
├── docs/                   # [已创建] 文档目录
│   ├── standards/          # [已创建] 文档标准
│   ├── templates/          # [已创建] 文档模板
│   ├── progress/           # [已创建] 进度记录
│   └── reports/completed/  # [已创建] 完成报告
├── README.md               # [已完成] 技术方案设计
└── CLAUDE.md               # [已完成] 工作指南
```

## 已完成工作

### 文档与规划

| 文件 | 说明 |
| ------ | ------ |
| `README.md` | 项目技术方案设计，包含架构说明和使用指南 |
| `CLAUDE.md` | Claude Code 工作指南，定义项目约定和规范 |
| `docs/standards/documentation-guide.md` | 文档规范指南 |
| `docs/templates/progress-template.md` | 进度文档模板 |
| `docs/templates/report-template.md` | 完成报告模板 |
| `docs/progress/2026-01-18-project-initialization.md` | 项目初始化进度记录 |

## 代码清理状态

| 检查项 | 状态 | 说明 |
| -------- | ------ | ------ |
| 冗余代码 | 无需清理 | 项目尚无代码实现 |
| 过期脚本 | 无需清理 | 项目尚无脚本实现 |
| 无效测试 | 无需清理 | 项目尚无测试用例 |
| 过期文档 | 无需清理 | 文档体系刚建立 |

## 下一步行动建议

### 优先级 1：核心数据层

1. 创建 `data/compatibility.yaml` - 定义 CANN、驱动、框架版本兼容性矩阵
2. 实现 `adk_core/matrix.py` - 解析和查询兼容性数据

### 优先级 2：环境探测

3. 实现 `adk_core/analyzer.py` - 探测宿主机 NPU 环境
4. 创建 `scripts/check_npu.sh` - NPU 状态检测脚本

### 优先级 3：镜像生成

5. 创建 `templates/` 目录下的 Jinja2 模板
6. 实现 `adk_core/generator.py` - Dockerfile 渲染引擎
7. 创建 `scripts/install_cann.sh` - CANN 安装脚本

### 优先级 4：CLI 与示例

8. 实现 `adk.py` - 命令行接口
9. 创建 `examples/` - 使用示例

## 版本信息

- **当前版本**：0.0.0（未发布）
- **目标版本**：0.1.0（MVP）
- **Python 版本**：3.8+
- **依赖**：Jinja2、PyYAML、Click（计划中）
