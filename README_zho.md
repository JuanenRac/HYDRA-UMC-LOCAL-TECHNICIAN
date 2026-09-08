<p align="center">
  <img src="images/HYDRA_UMC_BANNER.svg" alt="HYDRA-UMC-LOCAL-TECHNICIAN 横幅" width="100%">
</p>

# 🤖 HYDRA-UMC-LOCAL-TECHNICIAN

<p align="center"><a href="README.md">🇺🇸 English</a> | <a href="README_spa.md">🇪🇸 Español</a> | <a href="README_fra.md">🇫🇷 Français</a> | <a href="README_ita.md">🇮🇹 Italiano</a> | <a href="README_deu.md">🇩🇪 Deutsch</a> | 🇨🇳 <b>简体中文</b> | <a href="README_jpn.md">🇯🇵 日本語</a></p>

### 🛡️ 由策略限权的本地 AI 技术员

<p align="center">
  <img src="https://img.shields.io/badge/许可证-GPL%203.0-blue.svg" alt="GPL 3.0">
  <img src="https://img.shields.io/badge/语言-Python%203.11%2B-blue.svg" alt="Python">
  <img src="https://img.shields.io/badge/核心-仅标准库-brightgreen.svg" alt="仅标准库核心">
  <img src="https://img.shields.io/badge/阶段-0%2F6-367BF5.svg" alt="第 0 阶段（共 6 阶段）">
</p>

> **状态：v0.0.1，脚手架阶段 - 六阶段计划中的第 0 阶段（清单与安全基线）。**
> 本次交付定义了真实的风险等级策略（`policy/risk_levels.py`）、一份固定的
> 工具白名单（`policy/tool_matrix.py`）、未来每一次工具调用都必须校验通过的
> 五份真实最小合约（`contracts/*.schema.json` + `contracts.py`）、从
> HYDRA-UMC-OPS-AGENT 自身已测试的 `log_redaction.py` 移植而来的真实密钥/
> 敏感信息脱敏功能，以及本次第 0 阶段自身字面意义上的退出标准：一个真实的
> 对抗性测试，证明恶意的被检索文档永远无法触发工具调用或泄露密钥。目前尚不
> 存在推理引擎、RAG 索引、真实的工具执行，也没有与 HYDRA-UMC-SERVER 的集成 -
> 参见 [docs/CLI_REFERENCE.md](docs/CLI_REFERENCE.md) 了解今天真实存在的命令
> 界面范围。

---

## 1. 🛠️ 技术概览

HYDRA-UMC-LOCAL-TECHNICIAN 是为 HYDRA-UMC 生态系统自身量身打造的专用本地
AI：它观察、解释、诊断并为生态系统自己的服务和节点提出维护建议 - 它绝不会
训练一个新的基础模型，也绝不会通过生成文本来采取行动。它的目标平台是 CM5，
一旦安装则使用 Hailo-10H 加速器,但第 0 阶段两者皆不需要：本次交付中的一切
都是纯 Python 代码,验证的也都是纯数据。

**不可协商的原则：** AI 永远不会因生成一段回复而获得权限。策略、权限与人工
确认决定每一个真实动作 - 绝不是模型自己说的话。

本次交付（第 0 阶段）带来了四个真实、且各自独立有用的部分：

1. **风险等级策略**（`policy/risk_levels.py`）- 六个有序等级，从
   `INFORM` 到 `PHYSICAL_ACTION`，每一级都有真实、经过测试的策略（是否可以
   读取工具、是否可以变更、是否需要确认、是否已实现）。最高的两级仅为合约
   完整性而声明 - 在本代码库中确实没有任何地方实现它们。
2. **工具矩阵**（`policy/tool_matrix.py`）- 九个真实的 `OBSERVE` 等级工具
   名称组成的固定白名单。不在此字典中的工具名称永远无法被调用,就这么简单 -
   而其中每一个名称在本次交付中仍然是 `implemented=False`。
3. **真实合约**（`contracts/*.schema.json` + `contracts.py`）-
   `ToolRequest`、`ToolResult`、`MaintenanceProposal`、`EvidenceBundle`
   和 `PatchVerificationReport`，逐字段从本项目自己的私有开发计划中复制而
   来，每一份都有一份规范性的 JSON Schema 文件，以及一个与之对应的、仅使用
   标准库的 Python 校验器。
4. **注入防御边界**（`knowledge/trust.py` + `knowledge/redaction.py`）-
   不可信内容（一份 README、一行日志、一条提交信息）总是被包装为
   `UntrustedText`，这是一种没有任何方法能产生工具调用的类型。在本代码库中
   构造 `ToolRequest` 的唯一真实方式,接受的是已经分好类型、已经分离好的字
   段 - 在该对象存在之前，就会拒绝任何未注册或未实现的工具名称。

```
$ hydra-umc-local-technician contracts validate tests/fixtures/tool_request.valid.json --contract ToolRequest
VALID: tests/fixtures/tool_request.valid.json (ToolRequest)

$ hydra-umc-local-technician contracts validate tests/fixtures/tool_request.invalid.json --contract ToolRequest
INVALID: tests/fixtures/tool_request.invalid.json (ToolRequest): ...
```

本次交付没有默认/无参数调用方式，也没有图形界面 - 完整、真实的命令界面参见
[docs/CLI_REFERENCE.md](docs/CLI_REFERENCE.md)。

## 2. 🧱 架构与设计决策

- **AI 永远不会因生成一段回复而获得权限。** 本次交付的每一个设计决策都是为
  了保护这一条原则而存在 - 完整模型参见
  [docs/SECURITY_MODEL.md](docs/SECURITY_MODEL.md)。
- **工具必须先注册，才有可能被调用。** `policy/tool_matrix.py` 的
  `TOOL_MATRIX` 是完整且固定的清单；`lookup_tool()` 返回 `None` 意味着无
  条件拒绝，绝不是去猜测一个默认风险等级的情形。
- **不可信内容永远不能变成一条命令。** 这种防御是架构层面的（一种没有任何
  方法能产生工具的类型），而不是一个试图识别"看起来像指令"文本的过滤器 -
  面对一次坚决的提示注入，那种过滤器注定输掉这场游戏。参见
  `tests/adversarial/test_injection_defense.py`，这是第 0 阶段自身字面意义
  上的退出标准。
- **合约的规范性来源是它的 JSON Schema 文件。** `contracts.py` 中的字段
  清单与校验器都是逐字段从 `contracts/*.schema.json` 复制而来，遵循与
  HYDRA-UMC-SDK 自身 `validation.py` 相同的约定 - 而不是第二个独立的真相
  来源。
- **密钥脱敏复用了已经测试过的代码。** `knowledge/redaction.py` 是对
  HYDRA-UMC-OPS-AGENT 自身已测试的 `log_redaction.py` 逐字节移植的结果
  （只有头部注释不同）- 这里的底层问题（在不使用模糊启发式规则的前提下识
  别真实的、常见的密钥形态）与那边完全相同。
- **`PRIVILEGED_CHANGE` 和 `PHYSICAL_ACTION` 仍未实现。** 这是一道刻意且
  永久的关卡，直到出现专门的设计、独立的授权路径,以及对于物理动作而言的
  真实联锁装置为止 - 这不是留待日后补上的疏漏。
- **本次交付只声明与校验 - 尚未采取任何行动。** 本仓库中的任何地方都还不
  存在推理引擎、RAG 索引、真实的工具执行,也没有与 HYDRA-UMC-SERVER 的集成。

## 📂 目录结构

```
HYDRA-UMC-LOCAL-TECHNICIAN/
├── src/hydra_umc_local_technician/
│   ├── policy/
│   │   ├── risk_levels.py    # RiskLevel + RiskLevelPolicy：六个等级，每级真实策略
│   │   └── tool_matrix.py    # TOOL_MATRIX：固定且真实的工具白名单（9 个 OBSERVE 级名称）
│   ├── knowledge/
│   │   ├── redaction.py      # 真实的密钥脱敏，移植自 HYDRA-UMC-OPS-AGENT
│   │   └── trust.py          # UntrustedText + build_tool_request_from_model_output()：注入防御边界
│   ├── contracts.py           # 五份最小合约的真实、仅标准库校验器
│   └── cli.py                 # contracts validate 子命令 + --version
├── contracts/                  # 五份合约的规范性 JSON Schema 文件（draft 2020-12）
├── tests/
│   ├── unit/                   # 上述每个模块的真实测试
│   ├── adversarial/            # test_injection_defense.py - 第 0 阶段自身字面意义上的退出标准
│   └── fixtures/                # 每份合约的有效/无效 JSON 测试样例
├── docs/
│   ├── ARCHITECTURE.md         # 目的、五个目标组成部分、目标架构、生态系统关系
│   ├── SECURITY_MODEL.md       # 六个风险等级、数据/密钥规则、注入防御
│   ├── CLI_REFERENCE.md        # contracts validate、参数标志、退出码
│   └── CONTRACTS.md            # 五份合约逐字段的真实结构
├── images/                      # 媒体资源与应用图标
├── build.sh / build.bat        # 虚拟环境 + 可编辑安装 + 编译检查 + 测试
├── build-test.sh / .bat        # 仅不产生变更的构建校验
├── run.sh / run.bat            # 转发一条真实的 CLI 命令
├── bump_version.py             # 整个生态系统的"里程表式"版本递增（pyproject.toml + __init__.py）
└── bump_manifest_version.py    # 将 hydra-umc.project.json 的版本与原生版本同步（--sync）
```

## ⚙️ 构建与运行指南

```bash
chmod +x build.sh   # 只需一次
./build.sh          # 创建 .venv，pip install -e ".[dev]"，编译检查 + 测试
./run.sh contracts validate tests/fixtures/tool_request.valid.json --contract ToolRequest
./run.sh --version
```

在 Windows 上：先 `build.bat`，再 `run.bat contracts validate ...` /
`run.bat --version`。`build-test.sh`/`.bat` 执行的是与本项目自身 CI
工作流相同的、不产生变更的 Python 语法编译检查，不会改动项目版本号或
CHANGELOG - 它并**不**运行测试套件；要运行完整的本地测试套件，请执行
`./build.sh`/`build.bat`（或直接执行 `pytest tests/`）。

**故障排查**

- `contracts validate` 以退出码 `1` 和 `INVALID: ...` 结束：请阅读该消息 -
  它会指明具体是哪个字段以及原因，而不只是说"有些东西失败了"。每份合约的
  真实预期结构参见 [docs/CONTRACTS.md](docs/CONTRACTS.md)。
- `tests/adversarial/` 中的某个测试失败：这正是第 0 阶段自身字面意义上的
  退出标准 - 请将那里的任何失败都当作注入防御边界的真实退化，绝不要把它当
  作一个应该放宽的测试。

## 🚀 路线图

本版本只交付第 0 阶段。剩余部分，按本项目自身私有开发计划的顺序：

- **第 1 阶段 - 可检索知识。** 一个本地的、带版本管理的索引，涵盖已批准的
  文档、清单、合约和运维手册 - 绝不会盲目地在整块磁盘上训练。
- **第 2 阶段 - 本地推理引擎。** 一个与 Hailo-10H 兼容的小型 LLM（候选：
  Qwen2.5-1.5B-Instruct、Qwen2.5-Coder-1.5B、Qwen3-1.7B-Instruct），只有
  在验证了真实的 Hailo 兼容性、延迟、语言质量、功耗和许可证之后才会真正
  选定。
- **第 3 阶段 - 工具编排器。** 确定性代码，将首批真实的 `OBSERVE` 级工具
  处理程序接入 `TOOL_MATRIX`，并在每次调用时强制执行策略。
- **第 4 阶段 - 提案与证据。** 真实生成 `MaintenanceProposal` 和
  `EvidenceBundle`，向 HYDRA-UMC-DEV-SERVER 未来的 Developer Node 角色升级。
- **第 5 阶段 - 用户界面。** 一个集成到 HYDRA-UMC-SERVER/Studio 中的本地
  API，然后是一个 CLI，再然后是语音 - 绝不会绕过第 0 阶段已经建立的策略与
  确认边界。

以上内容目前均尚未存在于本仓库中 - 各阶段明确包含与排除的内容参见
[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)，各阶段必须持续遵守的安全
不变量参见 [docs/SECURITY_MODEL.md](docs/SECURITY_MODEL.md)。

## 🔗 相关项目

本项目是同一作者（JuanenRac / Electro Hobby 3D）HYDRA-UMC 机器人生态系统
的一部分。值得了解一下，因为某个请求实际上可能与以下这些项目有关，而不是
本仓库。

**直接相关**
- **[HYDRA-UMC-COGNITIVE-NODE](https://github.com/JuanenRac/HYDRA-UMC-COGNITIVE-NODE)** — 本项目自身的父项目：Hailo-10 认知流水线的集成中心，该技术员未来的推理引擎将运行在其上。
- **[HYDRA-UMC-OPS-AGENT](https://github.com/JuanenRac/HYDRA-UMC-OPS-AGENT)** — 拥有维护事件生命周期（证据、诊断、人工批准的变更、金丝雀部署、验证）；本技术员自身的 `knowledge/redaction.py` 是对其已测试的 `log_redaction.py` 的直接移植，未来某个阶段会向它升级真实的证据包，绝不会绕过它自身的审批流程。
- **[HYDRA-UMC-DEV-SERVER](https://github.com/JuanenRac/HYDRA-UMC-DEV-SERVER)** — 未来的 Developer Node，后续阶段会向其发送真实的 `EvidenceBundle` 以供研究、测试并准备一份经审查的补丁 - 绝不是一条直接、自动的打补丁通道。
- **[HYDRA-UMC-SDK](https://github.com/JuanenRac/HYDRA-UMC-SDK)** — 将定义共享的、带版本管理的合约，一旦这些合约也存在于那里，本项目自身本地的 `contracts/*.schema.json` 就会与之协调统一。
- **[HYDRA-UMC-SERVER](https://github.com/JuanenRac/HYDRA-UMC-SERVER)** — 未来经过认证的入口点，将承载本技术员自身的端点、会话、角色与审计轨迹。

**生态系统的其他部分**

*核心硬件与平台*
- **[HYDRA-UMC](https://github.com/JuanenRac/HYDRA-UMC)** — 机械臂的实体主板：CM5 主机 + 双核 STM32H745，通过 CAN-OTA/SPI-OTA 编排最多 8 条工具臂。
- **[HYDRA-UMC-OS](https://github.com/JuanenRac/HYDRA-UMC-OS)** — 为 CM5 打造的可复现 Raspberry Pi OS 产品层：只读代理、经过验证的配置/档案、WiFi 首次接触配网。

*核心后端与客户端*
- **[HYDRA-UMC-STUDIO](https://github.com/JuanenRac/HYDRA-UMC-STUDIO)** — 具备实时多机器人 3D 可视化的网页控制面板。
- **[HYDRA-UMC-SUITE](https://github.com/JuanenRac/HYDRA-UMC-SUITE)** — 可同时管理多台服务器的桌面（PySide6）群控指挥中心。
- **[HYDRA-UMC-ANDROID-CONTROL](https://github.com/JuanenRac/HYDRA-UMC-ANDROID-CONTROL)** — 原生 Android 控制应用，具备生物识别登录和配对的 Wear OS 伴侣应用。
- **[HYDRA-UMC-IOS-CONTROL](https://github.com/JuanenRac/HYDRA-UMC-IOS-CONTROL)** — iOS/iPadOS 控制应用（Flutter），具备实时 WebSocket 同步。
- **[HYDRA-UMC-DSI](https://github.com/JuanenRac/HYDRA-UMC-DSI)** — 板载 7 寸 DSI 触摸屏的原生触控 UI，直接嵌入 CM5 本身。
- **[HYDRA-UMC-EDITOR-URDF](https://github.com/JuanenRac/HYDRA-UMC-EDITOR-URDF)** — 桌面版图形化 URDF 创建/编辑器，将完成的模型推送到 STUDIO 自身的目录中。
- **[HYDRA-UMC-BRIDGE-AMR](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-AMR)** — 通过真实的 VDA 5050 MQTT 发布者实现的 AGV/AMR 车队协调边界。
- **[HYDRA-UMC-BRIDGE-CNC](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-CNC)** — 高层级 CNC 单元协调器，具备真实的 GRBL 状态/控制字节访问能力。
- **[HYDRA-UMC-BRIDGE-DROIDS](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-DROIDS)** — 腿足/人形机器人的协调边界，具备真实的 Boston Dynamics Spot 命令发送器。
- **[HYDRA-UMC-BRIDGE-LASER](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-LASER)** — 激光单元安全协调器，读取 3 个真实的钥匙/围栏/联锁 GPIO 安全装置。
- **[HYDRA-UMC-BRIDGE-OPENPNP](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-OPENPNP)** — 针对 OpenPnP 贴片作业的安全高层级板件流程协调器。
- **[HYDRA-UMC-BRIDGE-PRINTER3D](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-PRINTER3D)** — 针对 Moonraker/Klipper 3D 打印机的安全协调边界，具备真实受控的任务命令。
- **[HYDRA-UMC-BRIDGE-ROS2](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-ROS2)** — 安全协调器，具备真实的、惰性导入的 rclpy ROS 2 传输层。
- **[HYDRA-UMC-BRIDGE-UAV](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-UAV)** — 配备摄像头的无人机协调边界，具备真实的 MAVLink 命令发送器。

*URTC 工具平台*
- **[URTC](https://github.com/JuanenRac/URTC)** — 实体 Universal Robot Tool Controller 电路板固件，通过 CAN 总线支持 25 种以上工具档案。
- **[URTC-FLASHER](https://github.com/JuanenRac/URTC-FLASHER)** — 用于烧录 URTC 板卡的桌面图形化工具，支持 CAN-OTA 及完整芯片级 SWD/JTAG。
- **[URTC-TESTER](https://github.com/JuanenRac/URTC-TESTER)** — 面向 URTC 板卡的桌面实时 CAN 总线诊断工具，每个工具档案一个面板。
- **[URTC-WEB-STUDIO](https://github.com/JuanenRac/URTC-WEB-STUDIO)** — 通过 Web Serial API 实现的、无需本地安装的浏览器版 URTC-TESTER 替代方案。

*视觉 AI 节点（Hailo-8）*
- **[HYDRA-UMC-VISION-NODE](https://github.com/JuanenRac/HYDRA-UMC-VISION-NODE)** — Hailo-8 视觉流水线的集成中心，具备真实的分阶段硬件就绪检查。
- **[HYDRA-UMC-DETECTION-HEF](https://github.com/JuanenRac/HYDRA-UMC-DETECTION-HEF)** — 真实的已编译模型注册表，具备 Hailo 架构/校验和安全加载验证。
- **[HYDRA-UMC-VISION-STREAMER](https://github.com/JuanenRac/HYDRA-UMC-VISION-STREAMER)** — 真实的 GStreamer 流水线 + MediaMTX 配置生成器，具备真实的 HailoRT 集成边界。
- **[HYDRA-UMC-VISUAL-SERVOING-API](https://github.com/JuanenRac/HYDRA-UMC-VISUAL-SERVOING-API)** — 真实的基于位置的视觉伺服校正律，根据上游区域状态进行安全门控。
- **[HYDRA-UMC-SAFETY-ZONES](https://github.com/JuanenRac/HYDRA-UMC-SAFETY-ZONES)** — 真实的区域入侵检查与 E-STOP 请求，强制执行标定时效性。

*认知 AI 节点（Hailo-10）*
- **[HYDRA-UMC-VLA-ENGINE](https://github.com/JuanenRac/HYDRA-UMC-VLA-ENGINE)** — 面向视觉-语言-动作模型的真实动作令牌编解码与轨迹生成。
- **[HYDRA-UMC-VOICE-UI](https://github.com/JuanenRac/HYDRA-UMC-VOICE-UI)** — 真实的语音前端（VAD + 意图解析器），具备受限且需确认的 Watch 中继。
- **[HYDRA-UMC-SEMANTIC-PLANNER](https://github.com/JuanenRac/HYDRA-UMC-SEMANTIC-PLANNER)** — 基于规则的真实任务分解，以及针对 MCU 错误代码的语义化错误恢复。
- **[HYDRA-UMC-DOCS-QA](https://github.com/JuanenRac/HYDRA-UMC-DOCS-QA)** — 仅使用标准库的真实 TF-IDF 文档检索，覆盖本生态系统自身的 Markdown 文档。

*编排与集群*
- **[HYDRA-UMC-ORCHESTRATOR](https://github.com/JuanenRac/HYDRA-UMC-ORCHESTRATOR)** — 集成中心，具备真实的 gRPC/Protobuf 健康报告合约与任务状态机。
- **[HYDRA-UMC-JOB-DISPATCHER](https://github.com/JuanenRac/HYDRA-UMC-JOB-DISPATCHER)** — 基于真实 HTTP API 的、带去重功能的真实优先级任务队列。
- **[HYDRA-UMC-NODE-HEALING](https://github.com/JuanenRac/HYDRA-UMC-NODE-HEALING)** — 基于 gRPC 的真实车队健康看门狗，具备自身的重试/退避机制及身份不匹配检测。
- **[HYDRA-UMC-PATH-PLANNER-3D](https://github.com/JuanenRac/HYDRA-UMC-PATH-PLANNER-3D)** — 基于 RRT 的真实 3D 路径规划器，具备真实的障碍物/工作空间碰撞验证。
- **[HYDRA-UMC-SWARM-SYNC](https://github.com/JuanenRac/HYDRA-UMC-SWARM-SYNC)** — 真实的 CRDT LWW-Element-Map 状态同步，针对多单元收敛进行了属性化测试。

*数字孪生与仿真*
- **[HYDRA-UMC-TWIN](https://github.com/JuanenRac/HYDRA-UMC-TWIN)** — 数字孪生引擎的集成中心，具备真实的版本兼容性同步合约。
- **[HYDRA-UMC-HIL-BRIDGE](https://github.com/JuanenRac/HYDRA-UMC-HIL-BRIDGE)** — 真实的硬件在环安全联锁装置，在仿真与真实硬件之间路由命令。
- **[HYDRA-UMC-PHYSICS-REPLICA](https://github.com/JuanenRac/HYDRA-UMC-PHYSICS-REPLICA)** — 基于真实 URDF 子集的真实正向运动学与关节限位验证。
- **[HYDRA-UMC-SYNTHETIC-DATA-GEN](https://github.com/JuanenRac/HYDRA-UMC-SYNTHETIC-DATA-GEN)** — 真实的 2D 场景程序化生成器，具备 YOLO/COCO 标注导出功能。

*数据与分析*
- **[HYDRA-UMC-DATALAKE](https://github.com/JuanenRac/HYDRA-UMC-DATALAKE)** — 基于 sqlite3 的真实时间序列存储，具备真实的写入/查询 HTTP API。
- **[HYDRA-UMC-ANOMALY-DETECTOR](https://github.com/JuanenRac/HYDRA-UMC-ANOMALY-DETECTOR)** — 基于 FFT + 统计基线的真实异常检测器，具备漂移监测。
- **[HYDRA-UMC-PRODUCTION-REPORTS](https://github.com/JuanenRac/HYDRA-UMC-PRODUCTION-REPORTS)** — 基于 DATALAKE 历史数据的真实 OEE/可用性计算，具备可复现的 CSV 导出。
- **[HYDRA-UMC-TELEMETRY-COLLECTOR](https://github.com/JuanenRac/HYDRA-UMC-TELEMETRY-COLLECTOR)** — 真实的 CAN/WebSocket 数据摄取流水线，写入 DATALAKE，具备序列去重。

*工业网关*
- **[HYDRA-UMC-GATEWAY-INDUSTRIAL](https://github.com/JuanenRac/HYDRA-UMC-GATEWAY-INDUSTRIAL)** — 中继至工业协议的集成中心，具备真实的命令白名单/背压层。
- **[HYDRA-UMC-OPCUA-SERVER](https://github.com/JuanenRac/HYDRA-UMC-OPCUA-SERVER)** — 真实的 OPC-UA 地址空间，通过真实的二进制协议客户端会话进行验证。
- **[HYDRA-UMC-MQTT-BROKER](https://github.com/JuanenRac/HYDRA-UMC-MQTT-BROKER)** — 真实的 MQTT 代理，具备可选的按客户端身份验证与主题 ACL。
- **[HYDRA-UMC-MTCONNECT-ADAPTER](https://github.com/JuanenRac/HYDRA-UMC-MTCONNECT-ADAPTER)** — 真实的 MTConnect `/probe` 与 `/current` XML 端点，具备降级模式输出。

*配套工具*
- **[HYDRA-UMC-DASHBOARD-AI](https://github.com/JuanenRac/HYDRA-UMC-DASHBOARD-AI)** — 基于 DATALAKE/ANOMALY-DETECTOR 的智能摘要与异常高亮面板，具备诚实的统计回退机制。
- **[HYDRA-UMC-TOOL-CLI](https://github.com/JuanenRac/HYDRA-UMC-TOOL-CLI)** — 车队 CLI，具备真实且稳定的退出码合约，是 HYDRA-UMC-SERVER 自身 API 的真实在线客户端。
- **[HYDRA-UMC-WATCH](https://github.com/JuanenRac/HYDRA-UMC-WATCH)** — WearOS 伴侣应用，具备真实的触觉提醒和配对手机语音中继功能。
- **[HYDRA-UMC-CONNECTOR-HUB](https://github.com/JuanenRac/HYDRA-UMC-CONNECTOR-HUB)** — 外部适配器能力目录，设计上仅支持 GET。
- **[HYDRA-UMC-OS-REBUILDER](https://github.com/JuanenRac/HYDRA-UMC-OS-REBUILDER)** — 从源码构建全新的 CM5 镜像，是 "Ecosystem Operations" 系列的另一个兄弟项目。
- **[URTC-SMART-RACK](https://github.com/JuanenRac/URTC-SMART-RACK)** — 用于板卡安装机架的固件，具备真实的工具 ID 解码与 Smart Idle 预热逻辑。
- **[URTC-VISION-TOOL](https://github.com/JuanenRac/URTC-VISION-TOOL)** — 固件加上一个真实的 Python 视觉伴侣程序，用于热成像/RGB 检测工具头。

---

## 📚 文档与社区

- **[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)** — 目的、五个目标组成部分、目标架构，以及生态系统关系。
- **[docs/SECURITY_MODEL.md](docs/SECURITY_MODEL.md)** — 六个风险等级、数据/密钥规则，以及真实且经过测试的注入防御边界。
- **[docs/CLI_REFERENCE.md](docs/CLI_REFERENCE.md)** — 每个子命令、其参数标志，以及退出码合约。
- **[docs/CONTRACTS.md](docs/CONTRACTS.md)** — 五份合约逐字段的真实结构。
- **[CONTRIBUTING.md](CONTRIBUTING.md)** — 提交拉取请求所需的技术栈与编码规范。
- **[CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)** — 本社区所期望的行为准则。
- **[SECURITY.md](SECURITY.md)** — 如何报告漏洞，以及本项目真实的安全重点领域。
- **[SUPPORT.md](SUPPORT.md)** — 在哪里提问和报告错误。

## 👤 作者
**JuanenRac** (Electro Hobby 3D)
📧 electrohobby3d@gmail.com
📺 [youtube.com/@electrohobby3d](https://youtube.com/@electrohobby3d)

## 📜 许可证

GPL-3.0（软件）/ CC BY-SA 4.0（文档）- 详见 [LICENSE.md](LICENSE.md)。
