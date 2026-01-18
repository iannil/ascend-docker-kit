# ADK 技术方案设计文档

这是 `ascend-docker-kit` (ADK) 的详细技术方案设计。

该方案的设计原则是：轻量级、无侵入、自动化、知识代码化。我们不重新发明轮子（如重写 Docker），而是通过封装最佳实践，屏蔽底层的复杂性。

---

## 1. 项目定位与架构总览

* 项目名称：Ascend Docker Kit (ADK)
* 定位：华为昇腾环境下的 DevOps 瑞士军刀，连接基础设施（NPU 驱动/固件）与上层应用（PyTorch/MindSpore）的中间件工具。
* 开发语言：Python (核心逻辑) + Shell (底层探测) + Dockerfile (模板)

### 架构图

```mermaid
graph TD
    User[用户/运维人员] --> CLI[ADK CLI (命令行入口)]

    subgraph "Core Modules (核心模块)"
        CLI --> Analyzer[环境诊断器 (Analyzer)]
        CLI --> Matrix[兼容性矩阵库 (Matrix DB)]
        CLI --> Generator[镜像构建生成器 (Builder)]
        CLI --> Runtime[运行参数生成器 (Runtime Helper)]
    end

    subgraph "Infrastructure (底层设施)"
        Analyzer --读取--> Host[宿主机 (npu-smi/OS)]
        Matrix --校验--> Driver[驱动/固件版本]
    end

    subgraph "Output (交付物)"
        Generator --渲染--> Dockerfile[标准化 Dockerfile]
        Runtime --生成--> Cmd[最佳实践启动命令]
    end
```

---

## 2. 核心模块详细设计

### 2.1 兼容性矩阵数据库 (Matrix DB)

痛点解决：解决"不知道哪个版本的 PyTorch 配合哪个版本的 CANN，又需要哪个版本的驱动"的排列组合噩梦。

* 设计实现：
  * 维护一个 `compatibility.yaml` 文件，作为单一事实来源（Single Source of Truth）。
  * 该文件将华为官方分散的文档结构化。

* 数据结构示例：

    ```yaml
    # compatibility.yaml
    cann_versions:
      "7.0.RC1":
        min_driver_version: "23.0.rc1"
        supported_os: ["ubuntu20.04", "euler2.8"]
        frameworks:
          pytorch:
            version: "2.1.0"
            torch_npu_version: "2.1.0.post3"
            python: "3.9"
          mindspore:
            version: "2.2.0"
    ```

### 2.2 环境诊断器 (Host Analyzer)

痛点解决：防止用户在错误的驱动上强行安装不兼容的 CANN 版本，导致构建失败或运行时报错。

* 功能逻辑：
    1. 探测硬件：调用 `npu-smi info` 解析输出，获取 NPU 型号（910A/910B/310P）、Driver Version、Firmware Version。
    2. 探测系统：检测 OS 发行版（Ubuntu/CentOS/EulerOS）及架构（aarch64/x86_64）。
    3. 匹配校验：将探测结果与 `Matrix DB` 比对。
    4. 输出建议：如果当前驱动过旧，直接输出："当前驱动 22.0.0，构建 PyTorch 2.1 需要驱动 >= 23.0.0，请先升级驱动。"

### 2.3 镜像构建生成器 (Image Builder)

痛点解决：解决 Dockerfile 编写困难，依赖包缺失（如 `libsox`, `gcc`, `openssl`）导致编译失败的问题。

* 设计实现：
  * 采用 Jinja2 模板引擎 管理 Dockerfile。
  * 多阶段构建 (Multi-stage Build) 策略：
    * *Stage 1 (Base)*: 基础 OS，配置国内源（华为云/阿里云），安装系统级依赖（HCCL 依赖等）。
    * *Stage 2 (CANN)*: 自动拷贝并静默安装 CANN Toolkit。
    * *Stage 3 (Framework)*: 安装 PyTorch/MindSpore 及对应的 Adapter (`torch_npu`)。
  * 构建上下文自动准备：
    * CLI 会检查当前目录是否有必要的 `.run` 安装包。如果没有，提供 `wget` 下载链接（如果官方有公开链接）或提示用户下载路径。

* CLI 交互示例：

    ```bash
    $ adk build init --framework pytorch --version 2.1 --type train
    > 检测到宿主机驱动: 23.0.rc1 (Atlas 800T A2)
    > 已自动匹配 CANN 版本: 7.0.RC1
    > 生成 Dockerfile... OK
    > 生成 build.sh... OK
    ```

### 2.4 运行参数生成器 (Runtime Helper)

痛点解决：`docker run` 参数极其复杂，经常忘记挂载设备、忘记设置共享内存导致 NCCL 通信失败。

* 设计实现：
  * 支持两种运行时模式：
        1. Ascend Docker Runtime (推荐): 自动生成 `--gpus all` 或华为特定的 runtime 参数。
        2. Native Mapping (兜底): 如果没装 runtime，自动遍历 `/dev/davinci*` 和 `/dev/hisi_hdc` 等设备文件，生成 `--device ...` 列表。
  * 最佳实践注入：
    * 自动添加 `--shm-size=32g` (解决分布式训练通信内存不足)。
    * 自动添加 `--ulimit memlock=-1` (解决内存锁定限制)。
    * 自动挂载 `/usr/local/Ascend/driver` (如果需要容器内调用驱动库)。

---

## 3. 目录结构设计 (Repository Layout)

```text
ascend-docker-kit/
├── adk.py                  # CLI 入口
├── adk_core/
│   ├── matrix.py           # 兼容性逻辑
│   ├── analyzer.py         # 环境探测
│   └── generator.py        # Dockerfile 渲染
├── data/
│   └── compatibility.yaml  # 核心版本矩阵
├── templates/              # Dockerfile 模板
│   ├── Dockerfile.base.j2
│   ├── Dockerfile.cann.j2
│   └── Dockerfile.pytorch.j2
├── scripts/                # 辅助 Shell 脚本
│   ├── install_cann.sh     # 容器内静默安装脚本
│   └── check_npu.sh        # 容器启动时的自检脚本
├── examples/               # 生成好的开箱即用示例
│   ├── pytorch-2.1-910b/
│   └── mindspore-2.2-910a/
└── README.md
```

---

## 4. 关键技术难点与解决方案

### 难点 A：CANN 包的下载权限问题

* 问题：华为很多 CANN 包下载需要登录账号，无法在 Dockerfile 中直接 `RUN wget ...`。
* 方案：本地代理模式。
  * ADK 默认假设用户已将 `.run` 包下载到本地 `packages/` 目录。
  * 构建时，ADK 会启动一个临时的 Python HTTP Server，或者在 Dockerfile 中使用 `COPY` 指令将本地包复制进去安装，安装完后在同一层 `RUN rm` 清理，以减小镜像体积。

### 难点 B：PyTorch 与 torch_npu 的版本强绑定

* 问题：`pip install torch` 默认拉取的是 CUDA 版本，且 `torch_npu` 必须与 `torch` 版本严格一致（精确到 commit id 级别的情况时有发生）。
* 方案：锁定 whl 源。
  * 模板中不使用默认 pip 源。
  * 直接指向华为官方的 S3 镜像源或清华源的特定链接。
  * 在 `compatibility.yaml` 中硬编码 whl 的下载 URL，确保绝对兼容。

### 难点 C：推理与训练镜像的差异

* 问题：训练镜像很大（包含编译器、头文件），推理镜像需要极简。
* 方案：Target 分离。
  * 利用 Docker 的 `FROM ... AS builder` 和 `FROM ... AS runtime`。
  * ADK CLI 支持参数 `--target inference`，只拷贝必要的 `.so` 动态库和 Python 包，丢弃 GCC 和头文件，将镜像大小从 10GB+ 压缩到 3GB 左右。

---

## 5. 推广与开源策略 (GTM)

1. 首发场景：针对 DeepSeek / Llama3 / Qwen 等热门大模型在昇腾上的微调场景。提供一个 *One-Click Script*，直接生成能跑通 Llama3 微调的 Docker 环境。
2. 文档策略：
    * 提供《昇腾 Docker 避坑指南》（Markdown 电子书），将 ADK 作为解决方案植入。
    * 列出"十大常见报错"以及 ADK 如何自动解决它们。
3. 社区互动：
    * 在 Gitee（主阵地）和 GitHub 同步发布。
    * 提交 Issue 给 `Ascend/pytorch` 官方仓库，推荐作为非官方的 Quick Start 工具。

---

## 6. 总结

`ascend-docker-kit` 的核心价值在于"消除不确定性"。

在信创和智算中心建设的大潮中，工程师最怕的就是"环境配了一周，代码还没跑起来"。ADK 通过将专家的环境配置经验固化为代码（Infrastructure as Code），为用户提供了一个开箱即用、确定性高的容器化环境，这正是当前市场最急缺的"止痛药"。
