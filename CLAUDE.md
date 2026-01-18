# CLAUDE.md

本文件为 Claude Code (claude.ai/code) 在本仓库中工作时提供指导。

## 项目概述

Ascend Docker Kit (ADK) 是华为昇腾 NPU 环境的 DevOps 工具包。它通过自动化 Docker 环境配置，连接基础设施（NPU 驱动/固件）与上层应用（PyTorch/MindSpore）。

技术栈： Python（核心逻辑）+ Shell（系统探测）+ Dockerfile 模板（Jinja2）

## 关键设计约束

- CANN 安装包需要华为账号登录下载；假设用户已将 `.run` 包预先下载到本地 `packages/` 目录
- `torch_npu` 必须与 PyTorch 版本严格匹配；使用 `compatibility.yaml` 中锁定的 whl URL
- 训练镜像包含编译器/头文件（约 10GB+）；推理镜像使用 `--target inference` 实现最小化运行时（约 3GB）

## 项目指南

- 语言约定：交流与文档使用中文；生成的代码使用英文；文档放在 `docs` 且使用 Markdown。
- 发布约定：
  - 发布固定在 `/release` 文件夹，如 rust 服务固定发布在 `/release/rust` 文件夹。
  - 发布的成果物必须且始终以生产环境为标准，要包含所有发布生产所应该包含的文件或数据（包含全量发布与增量发布，首次发布与非首次发布）。
- 文档约定：
  - 每次修改都必须延续上一次的进展，每次修改的进展都必须保存在对应的 `docs` 文件夹下的文档中。
  - 执行修改过程中，进展随时保存文档，带上实际修改的时间，便于追溯修改历史。
  - 未完成的修改，文档保存在 `/docs/progress` 文件夹下。
  - 已完成的修改，文档保存在 `/docs/reports/completed` 文件夹下。
  - 对修改进行验收，文档保存在 `/docs/reports` 文件夹下。
  - 对重复的、冗余的、不能体现实际情况的文档或文档内容，要保持更新和调整。
  - 文档模板和命名规范可以参考 `/docs/standards` 和 `docs/templates` 文件夹下的内容。
- 数据约定：数据固定在`/data`文件夹下

### 面向大模型的可改写性（LLM Friendly）

- 一致的分层与目录：相同功能在各应用/包中遵循相同结构与命名，使检索与大范围重构更可控。
- 明确边界与单一职责：函数/类保持单一职责；公共模块暴露极少稳定接口；避免隐式全局状态。
- 显式类型与契约优先：导出 API 均有显式类型；运行时与编译时契约一致（zod schema 即类型源）。
- 声明式配置：将重要行为转为数据驱动（配置对象 + `as const`/`satisfies`），减少分支与条件散落。
- 可搜索性：统一命名（如 `parseXxx`、`assertNever`、`safeJsonParse`、`createXxxService`），降低 LLM 与人类的检索成本。
- 小步提交与计划：通过 `IMPLEMENTATION_PLAN.md` 和小步提交让模型理解上下文、意图与边界。
- 变更安全策略：批量程序性改动前先将原文件备份至 `/backup` 相对路径；若错误数异常上升，立即回滚备份。

## 架构

项目由四个核心模块组成：

1. 兼容性矩阵库 (`adk_core/matrix.py`)：将 CANN 版本映射到驱动要求、操作系统支持和框架版本。使用 `data/compatibility.yaml` 作为单一事实来源。

2. 环境诊断器 (`adk_core/analyzer.py`)：通过 `npu-smi info` 探测宿主机环境，检测 NPU 型号（910A/910B/310P）、驱动版本、固件版本、操作系统发行版和架构。

3. 镜像构建生成器 (`adk_core/generator.py`)：使用 Jinja2 模板渲染 Dockerfile，采用多阶段构建（base → CANN → framework）。

4. 运行参数生成器：生成 `docker run` 参数，包括设备映射（`/dev/davinci*`、`/dev/hisi_hdc`）、共享内存设置和卷挂载。

## 项目结构

```
ascend-docker-kit/
├── adk.py                  # CLI 入口
├── adk_core/
│   ├── matrix.py           # 兼容性逻辑
│   ├── analyzer.py         # 环境探测
│   └── generator.py        # Dockerfile 渲染
├── data/
│   └── compatibility.yaml  # 版本兼容性矩阵
├── templates/              # Jinja2 Dockerfile 模板
│   ├── Dockerfile.base.j2
│   ├── Dockerfile.cann.j2
│   └── Dockerfile.pytorch.j2
├── scripts/                # Shell 辅助脚本
│   ├── install_cann.sh     # CANN 静默安装脚本
│   └── check_npu.sh        # 容器启动自检脚本
└── examples/               # 开箱即用示例
```
