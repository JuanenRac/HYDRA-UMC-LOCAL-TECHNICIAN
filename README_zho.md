<!-- =============================================================================
HYDRA-UMC-LOCAL-TECHNICIAN - Local, policy-gated maintenance assistant
Copyright (C) JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
GPL-3.0-or-later - see LICENSE
============================================================================= -->

<p align="center">
  <img src="images/HYDRA_UMC_BANNER.svg" alt="HYDRA-UMC-LOCAL-TECHNICIAN banner" width="100%">
</p>

# 🤖 HYDRA-UMC-LOCAL-TECHNICIAN

<p align="center"><a href="README.md">🇺🇸 English</a> | <a href="README_spa.md">🇪🇸 Español</a> | <a href="README_fra.md">🇫🇷 Français</a> | <a href="README_ita.md">🇮🇹 Italiano</a> | <a href="README_deu.md">🇩🇪 Deutsch</a> | 🇨🇳 <b>简体中文</b> | <a href="README_jpn.md">🇯🇵 日本語</a> | <a href="README_por.md">🇵🇹 Português</a></p>

### 🛡️ 由策略限权的本地 AI 技术员

<p align="center">
  <img src="https://img.shields.io/badge/License-GPL%203.0--or--later-blue.svg" alt="GPL 3.0 or later">
  <img src="https://img.shields.io/badge/Language-Python%203.11%2B-blue.svg" alt="Language">
  <img src="https://img.shields.io/badge/Core-stdlib%20only-brightgreen.svg" alt="Core">
  <img src="https://img.shields.io/badge/Phase-1%2C%203%20%26%204%20of%206%20complete-367BF5.svg" alt="Phase">
  <img src="https://img.shields.io/badge/Tests-315%20passing-2ea44f.svg" alt="Tests">
  <img src="https://img.shields.io/badge/Version-0.1.7-0f6cbd.svg" alt="Version">
  <img src="https://img.shields.io/badge/Maturity-functional-0F6CBD.svg" alt="Maturity">
</p>

---

- **第 5 阶段 - 只读本地 API 与网页（第二部分）。** `serve`（`webapi.py`、`webui/`）展示技术员已经产出的内容：工具注册表、数据目录中的 ToolResult、EvidenceBundle 和 MaintenanceProposal 文件、各项目的清单，以及已列入白名单的知识来源的文档索引。它只响应 GET（其他方法一律返回 405），除非另行指定否则只绑定 `127.0.0.1`，绑定到其他地址时要求至少 24 个字符的 Bearer 令牌；通过列出文件夹来查找条目（绝不拼接请求路径），像 CLI 一样对每个响应做脱敏，并限制所有大小。单页界面不需要任何来自互联网的资源，提供英语、西班牙语、德语、法语、意大利语、日语、中文和葡萄牙（欧洲）葡萄牙语。详见 [docs/WEB_API.md](docs/WEB_API.md)。

**诚实核查 - 今天真正能运行的部分：** 风险等级策略(`policy/risk_levels.py`)、固定的工具白名单(`policy/tool_matrix.py`)、五个契约验证器(`contracts.py` + `contracts/*.schema.json`)、注入防御边界(`knowledge/trust.py`、`knowledge/redaction.py`)、本地 TF-IDF 知识索引(`knowledge/index.py`，第 1 阶段)、全部 10 个已声明的 OBSERVE 工具都有真实的处理程序(`orchestrator/dispatch.py` + `orchestrator/allowlist.py`：`service.status`、`storage.usage`、`network.port_status`、`network.connectivity`、`system.temperature`、`manifest.read`、`logs.read`、`process.list`、`update.pending`、`knowledge.search`)，真实的 `EvidenceBundle`/`MaintenanceProposal` 构建(`escalation/evidence.py`、`escalation/proposal.py`，第 4 阶段)，以及覆盖以上全部内容的真实 CLI(`tools list`/`tools call`/`escalation evidence`/`escalation propose`，第 5 阶段自身的第一个切片)，都经过测试(`tests/unit/` 和 `tests/adversarial/` 中共 315 个测试外加 149 个子测试全部通过)——第 1、3、4 阶段均已完成，第 5 阶段已启动。`update.pending` 需要可选依赖 `hydra-umc-updater`(`update-check` extra)才能真正查询 GitHub，没有它时会诚实降级(`available: false`)。本仓库中任何地方仍不存在推理引擎，也没有与 HYDRA-UMC-SERVER 的集成，本代码中也没有任何地方能对 `MaintenanceProposal` 采取行动——下方路线图中的第 2 阶段，以及第 5 阶段的其余部分（与 HYDRA-UMC-SERVER 集成的 API，以及语音）仍完全是愿景，背后没有任何代码。具体已交付的内容请见 `CHANGELOG.md`。

**带签名的结果。** `ToolResult` 现在会写明生成它的 `tool`,并且在配置了本地密钥时(`HYDRA_UMC_LOCAL_TECHNICIAN_RESULT_KEY`,或指向仓库之外某个文件的 `..._FILE`,16 个字符或更长),带有对整个结果规范化 JSON 的 HMAC-SHA256 `signature`。构建证据包时会拒绝未签名、被伪造或被冒充为其他工具的结果;没有密钥时与以前一样不签名也不拒绝。这两个字段在契约中是可选的,因此以前的结果仍然有效。

---

> **安全与安防现状:**本生态系统不是经认证的安全系统。目前尚无硬件 E-STOP 通路,没有由固件强制执行的限位或联锁,也没有经过验证的运动指令;固件映像使用 CRC-32 和 Ed25519 签名校验,发布构建会拒绝已公开的开发密钥(中继之后的工具头和扩展板仍运行 URTC 的引导程序,它们使用共享密钥的 HMAC-SHA256 而不是签名);TLS 与双向 TLS 均为可选项,默认关闭;自制电路板尚未组装或测试。在依赖此处任何说法来保障人身安全之前,请先阅读[安全基线](https://github.com/JuanenRac/HYDRA-UMC-DOCS/blob/main/docs/SECURITY_BASELINE.md)和[威胁模型](https://github.com/JuanenRac/HYDRA-UMC-DOCS/blob/main/docs/THREAT_MODEL.md)。

---

## 📋 速览

| | |
|---|---|
| 版本 | `0.1.7` |
| 成熟度 | 可用 |
| 测试 | 315 (`python -m pytest -q tests`) |
| 技术栈 | Python 3.11+ / JSON Schema / HailoRT GenAI (optional, later phase) / systemd (cm5 role, Linux only) |
| 目标 | HYDRA-UMC 工作单元的 Raspberry Pi CM5 |
| 真实硬件 | 尚未：此版本没有在真实硬件上运行的记录 |

**跳转：** [概述](#-概述) · [架构](#-架构) · [快速开始](#-快速开始) · [测试](#-测试) · [仓库结构](#-仓库结构) · [相关项目](#-相关项目)

## 🚦 项目状态

每一行是本仓库的一个部分，灯号表示它今天做到了哪一步。内容依据仓库能够展示的证据（测试、构建、运行），而不是计划。

🟢 已完成并验证 · 🟡 可用，有已知限制 · 🟠 部分完成或尚未验证 · 🔴 未完成或不可用

| 领域 | 状态 | 在这里的含义 |
|---|---|---|
| 软件 | 🟡 | 主要用途可用；上面的诚实性检查列出了仍然缺少的内容 |
| 测试 | 🟢 | 315 项自动测试，每次变更都会运行 |
| 真实硬件 | 🔴 | 尚未：此版本没有在真实硬件上运行的记录 |
| 文档 | 🟢 | 八种语言的 README，每次变更都会与清单核对 |

## 🎯 概述

HYDRA-UMC-LOCAL-TECHNICIAN 是为 HYDRA-UMC 生态系统自身量身打造的专用本地
AI：它观察、解释、诊断并为生态系统自己的服务和节点提出维护建议 - 它绝不会
训练一个新的基础模型，也绝不会通过生成文本来采取行动。它的目标平台是 CM5，
一旦安装则使用 Hailo-10H 加速器,但第 0 阶段两者皆不需要：本次交付中的一切
都是纯 Python 代码,验证的也都是纯数据。

**不可协商的原则：** AI 永远不会因生成一段回复而获得权限。策略、权限与人工
确认决定每一个真实动作 - 绝不是模型自己说的话。

本次交付带来了八个真实、且各自独立有用的部分：

1. **风险等级策略**（`policy/risk_levels.py`）- 六个有序等级，从
   `INFORM` 到 `PHYSICAL_ACTION`，每一级都有真实、经过测试的策略（是否可以
   读取工具、是否可以变更、是否需要确认、是否已实现）。最高的两级仅为合约
   完整性而声明 - 在本代码库中确实没有任何地方实现它们。
2. **工具矩阵**（`policy/tool_matrix.py`）- 十个真实的 `OBSERVE` 等级工具
   名称组成的固定白名单。不在此字典中的工具名称永远无法被调用,就这么简单 -
   全部 10 个都已连接到真实的处理程序(见下方第 5、6 点)。
3. **真实合约**（`contracts/*.schema.json` + `contracts.py`）-
   `ToolRequest`、`ToolResult`、`MaintenanceProposal`、`EvidenceBundle`
   和 `PatchVerificationReport`，每一份都有一份规范性的 JSON Schema 文件，
   以及一个从中逐字段复制而来、仅使用标准库的 Python 校验器。
4. **注入防御边界**（`knowledge/trust.py` + `knowledge/redaction.py`）-
   不可信内容（一份 README、一行日志、一条提交信息）总是被包装为
   `UntrustedText`，这是一种没有任何方法能产生工具调用的类型。在本代码库中
   构造 `ToolRequest` 的唯一真实方式,接受的是已经分好类型、已经分离好的字
   段 - 在该对象存在之前，就会拒绝任何未注册或未实现的工具名称。
5. **工具编排器**（`orchestrator/dispatch.py` + `orchestrator/allowlist.py`，
   第 3 阶段）- `dispatch_tool_request()` 真实执行一个已经过校验的
   `ToolRequest`，并返回一个真实的 `ToolResult`：`service.status`（真实的
   `systemctl is-active`）、`storage.usage`（`shutil.disk_usage`）、
   `network.port_status`（一次真实的套接字探测）、`network.connectivity`
   （一次真实的 HTTP GET 请求，报告该端点自身真实的状态码 - 这与
   `network.port_status` 是真正不同的检查，与 HYDRA-UMC-OPS-AGENT 自身
   `inventory.py` 在纯 TCP 连接与真实健康检查 GET 之间所做的区分完全相同）、
   `system.temperature`（真实的 Linux 热区 sysfs 路径）、`manifest.read`
   （真实读取 `hydra-umc.project.json`）、`logs.read`（对白名单中某个日志
   文件的、经脱敏处理的有限截尾读取）、`process.list`（针对
   `/proc/<pid>/cmdline` 的真实、白名单化子字符串匹配），以及
   `update.pending`（复用 HYDRA-UMC-UPDATER 自身真实的 GitHub 发现与版本
   比较逻辑，属可选依赖）。这些工具没有一个会直接接受原始的
   路径/主机/端口/URL/单元名/模式 - 只会通过一个固定的 `OrchestratorConfig`
   解析一个简短的符号化名称，因此一份被投毒文档自身的文本永远无法指定任意
   真实目标，只能指定一个已在白名单中的名称。
   处理器返回的内容在边界处受到限制并经过脱敏：进程命令行、知识摘录和证据包中的日志行都会经过与 `logs.read` 相同的机密脱敏，`manifest.read` 只返回四个短字符串，`network.connectivity` 只报告重定向而不跟随它。
6. **可检索知识索引**（`knowledge/index.py`，第 1 阶段）- 一个真实的本地
   TF-IDF 搜索引擎(tokenize/build_index/search)，未经改动地移植自
   HYDRA-UMC-DOCS-QA 自身已测试的 `index.py`，并新增了针对 Markdown 来源
   （按标题切分的片段）和 JSON 来源（每份文件作为一个整体片段 - 清单或合约
   schema 永远不会在对象中途被有意义地拆分）的有限摄取功能。作为第十个工具
   `knowledge.search` 接入，通过 `orchestrator/allowlist.py` 新增的
   `resolve_knowledge_source()`：调用方只能指定一个已在白名单中的符号化
   来源，永远不能是原始路径，并且每一条返回的真实匹配结果在离开处理程序前
   都仍然被包装为 `UntrustedText`。即使是一个合法在白名单中的根目录，遍历
   本身也受到限制（文件数量、单文件大小）- 绝不盲目，绝不遍历整块磁盘。
7. **升级上报：证据与提案**（`escalation/`，第 4 阶段）-
   `evidence.assemble_evidence_bundle()` 将一批已经执行、已经通过校验的
   真实 `ToolResult` 转换为一份真实、符合契约的 `EvidenceBundle`，采用
   与 HYDRA-UMC-OPS-AGENT 自身 `incident.py` 相同的模式：纯粹从已观测
   数据中推导，绝不调用 AI。`proposal.propose_maintenance()` 是
   `MaintenanceProposal` 的真实构造器/校验器 - 刻意不是一个生成器，因为
   目前仍不存在推理引擎，而本项目自身不可协商的原则排除了编造诊断的
   可能。今天只有人工操作员能提供 `diagnosis`/`steps`/`rollback`；这个
   模块新增的唯一真实防护措施是：`citedEvidence` 中的每一条都必须与某
   个真实的、已观测工具结果自身的 `evidence` 字段逐字匹配，否则该提案
   会被直接拒绝。`confirmationRequired` 绝不是调用方可设置的 - 它始终
   完全等于 `policy/risk_levels.py` 自身策略中对该提案所声明风险等级已
   经规定的值。本代码中还没有任何地方能对 `MaintenanceProposal` 采取
   行动。
8. **CLI 界面**（`cli.py`，第 5 阶段自身的第一个真实切片）-
   `tools list`/`tools call` 和 `escalation evidence`/`escalation
   propose` 首次为上述每一部分提供了真实的命令行（此前每一部分都只能
   从测试中触及）。不新增任何自身权限：`tools call` 通过每个测试早已
   调用的同一个 `build_tool_request_from_model_output()` 构建
   `ToolRequest`，并通过同一个 `dispatch_tool_request()` 执行它 - 仍然
   只能触及 OBSERVE 级工具，因为本代码中任何地方都没有实现高于
   OBSERVE 的内容。`--config` 从一个 JSON 文件加载真实的
   `OrchestratorConfig`（省略时回退到 `default_config()`）；命令行本身
   依旧无法直接指定原始的路径/主机/端口。

```
$ hydra-umc-local-technician contracts validate tests/fixtures/tool_request.valid.json --contract ToolRequest
VALID: tests/fixtures/tool_request.valid.json (ToolRequest)

$ hydra-umc-local-technician contracts validate tests/fixtures/tool_request.invalid.json --contract ToolRequest
INVALID: tests/fixtures/tool_request.invalid.json (ToolRequest): ...
```

本次交付没有默认/无参数调用方式，也没有图形界面 - 完整、真实的命令界面参见
[docs/CLI_REFERENCE.md](docs/CLI_REFERENCE.md)。

## 🧩 在 HYDRA-UMC 中的角色

**HYDRA-UMC-LOCAL-TECHNICIAN** 是生态系统的本地维护助手：它观察、解释并提出建议，模型生成的文本永远不是行动的授权。它的工具在允许列表内且只读，发现的内容会作为证据和建议交给人或 `HYDRA-UMC-OPS-AGENT`。

## 🏛️ 架构

<p align="center">
  <img src="images/architecture.svg" alt="HYDRA-UMC-LOCAL-TECHNICIAN architecture" width="100%">
</p>

### 架构与设计决策

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
- **机密信息脱敏是一份共享副本。** `knowledge/redaction.py` 是 HYDRA-UMC-SDK 维护的脱敏实现(`tools/canonical/redaction.py`),与运维代理的完全一致,并用同一组共享用例(`tests/redaction_vectors.json`)检验。
- **每个工具请求都可以审计。** 使用 `--audit-log 路径`(或 `HYDRA_UMC_LOCAL_TECHNICIAN_AUDIT_LOG`,或配置文件中的 `auditLog`)后,每个请求在执行前、其结果在执行后都会经脱敏写入只追加的 JSONL 日志,每行用 SHA-256 与上一行链接,并按大小轮转。无法记录的请求不会被执行;`audit-verify 路径` 用于检查链。默认关闭。
- **`PRIVILEGED_CHANGE` 和 `PHYSICAL_ACTION` 仍未实现。** 这是一道刻意且
  永久的关卡，直到出现专门的设计、独立的授权路径,以及对于物理动作而言的
  真实联锁装置为止 - 这不是留待日后补上的疏漏。
- **知识检索是有限且白名单化的，绝不盲目。** `knowledge.search` 只会索引
  一个已在白名单中的根目录(`orchestrator/allowlist.py` 的
  `resolve_knowledge_source()`)，遍历本身也受到真实的文件数量与单文件大小
  上限约束 - "绝不会盲目地在整块磁盘上训练"这一点，即使对一个运维人员已经
  判定为安全的根目录也同样成立。
- **本次交付只声明、检索与校验 - 尚未采取任何行动。** 本仓库中的任何地方
  都还不存在推理引擎、超出 OBSERVE 级别的真实工具执行,也没有与
  HYDRA-UMC-SERVER 的集成。

## 🚀 快速开始

需要 Python 3.11 或更高版本。

```bash
./build.sh  # Linux, macOS (build.bat on Windows)
./run.sh contracts validate tests/fixtures/tool_request.valid.json --contract ToolRequest
./run.sh --version
```

## 🧪 测试

运行 `python -m pytest -q tests` 会执行 315 个自动测试。 不需要硬件，也不需要这台机器以外的任何东西。

CI 运行 `HYDRA_UMC_CI=1 python tools/ci_validate.py`，检查清单、文档、八个 README 和图片。

## 🏗️ 构建与发布

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

## 📂 仓库结构

<p align="center">
  <img src="images/repository-structure.svg" alt="Repository structure of HYDRA-UMC-LOCAL-TECHNICIAN" width="100%">
</p>

<details>
<summary>目录树的文本版本</summary>

```text
HYDRA-UMC-LOCAL-TECHNICIAN/
├── src/hydra_umc_local_technician/   源代码
│   ├── policy/                       工具矩阵、风险等级、执行模式
│   ├── knowledge/                    索引、信任级别、脱敏
│   ├── orchestrator/                 第 3 阶段 + 第 1 阶段 - 全部 10 个真实的 OBSERVE 工具处理程序，已完成
│   ├── escalation/                   第 4 阶段 - 真实的 EvidenceBundle 组装 + MaintenanceProposal 构建，已完成
│   ├── contracts.py                  五份最小合约的真实、仅标准库校验器
│   ├── cli.py                        第 5 阶段 - contracts validate、tools list/call、escalation evidence/propose、--version, serve
│   ├── webapi.py                     只读本地 API：仅 GET，默认回环地址，非回环需令牌，已脱敏并限制大小
│   └── webui/                        可离线使用的单页界面：index.html、app.js、app.css 与八种语言的 i18n/
├── contracts/                        五份合约的规范性 JSON Schema 文件（draft 2020-12）
├── tests/                            自动测试
├── docs/                             项目文档
├── tools/                            项目工具和 CI 检查
├── images/                           媒体资源与应用图标
├── .github/                          CI 工作流和 Issue 模板
├── build.sh / build.bat              虚拟环境 + 可编辑安装 + 编译检查 + 测试
├── run.sh / run.bat                  转发一条真实的 CLI 命令
├── bump_version.py                   显式提升版本
├── bump_manifest_version.py          将 hydra-umc.project.json 的版本与原生版本同步（--sync）
├── CHANGELOG.md                      每个版本的变更
├── build-test.sh                     不修改内容的构建检查
├── hydra-umc.project.json            清单：版本、成熟度、系列
├── pyproject.toml                    包的元数据
└── test.sh                           运行测试
```

</details>

## 🗺️ 路线图与已知限制

**当前已知限制**

本版本交付了第 0 阶段、第 1 阶段、第 3 阶段和第 4 阶段。剩余部分，按阶段顺序：

- **第 1 阶段 - 可检索知识（已完成）。** 一个本地的、带版本管理的索引，
  涵盖已批准的文档、清单、合约和运维手册 - 绝不会盲目地在整块磁盘上训练。
  `knowledge/index.py` 未经改动地移植了 HYDRA-UMC-DOCS-QA 自身已测试的
  TF-IDF 搜索，并新增了针对 Markdown 和 JSON 来源的有限、白名单化摄取，
  作为第十个 OBSERVE 级工具 `knowledge.search` 接入。
- **第 2 阶段 - 本地推理引擎。** 一个与 Hailo-10H 兼容的小型 LLM（候选：
  Qwen2.5-1.5B-Instruct、Qwen2.5-Coder-1.5B、Qwen3-1.7B-Instruct），只有
  在验证了真实的 Hailo 兼容性、延迟、语言质量、功耗和许可证之后才会真正
  选定。
- **第 3 阶段 - 工具编排器（已完成：已声明的 9 个中的 9 个）。** 确定性代码，将
  全部真实的 `OBSERVE` 级工具处理程序接入 `TOOL_MATRIX`，并在每次调用时
  强制执行策略。`service.status`、`storage.usage`、`network.port_status`、
  `network.connectivity`、`system.temperature`、`manifest.read`、`logs.read`、`process.list` 和 `update.pending` 现已
  真实实现(`orchestrator/dispatch.py`)。
- **第 4 阶段 - 提案与证据（已完成）。** 真实构建 `MaintenanceProposal`
  和 `EvidenceBundle`（`escalation/`），向 HYDRA-UMC-DEV-SERVER 未来的
  Developer Node 角色升级。`evidence.assemble_evidence_bundle()` 从已
  观测的 `ToolResult` 推导出一份真实的证据包；`proposal.propose_maintenance()`
  会校验并印证人工提供的提案与真实证据是否相符 - 绝不会自行生成，因为
  目前仍不存在推理引擎。本代码中还没有任何地方能对 `MaintenanceProposal`
  采取行动。
- **第 5 阶段 - 用户界面（已启动：CLI 切片）。** 一个集成到
  HYDRA-UMC-SERVER/Studio 中的本地 API，然后是一个 CLI，再然后是语音 -
  绝不会绕过第 0 阶段已经建立的策略与确认边界。CLI 切片现在已是真实的：
  `tools list`/`tools call` 和 `escalation evidence`/`escalation
  propose`（`cli.py`）通过同样已测试、已受策略约束的代码触及上述每一个
  真实部分，刻意将范围限定在这一个仓库内部。与 HYDRA-UMC-SERVER 集成的
  API 以及语音仍是留待未来交付的、独立的跨仓库工作。

第 2 阶段，以及第 5 阶段的其余部分，目前均尚未存在于本仓库中 - 剩余各阶段明确包含与排除的内容
参见
[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)，各阶段必须持续遵守的安全
不变量参见 [docs/SECURITY_MODEL.md](docs/SECURITY_MODEL.md)。

## 🌍 语言

本 README 和仓库文档提供八种语言：英语、西班牙语、德语、法语、意大利语、日语、中文和葡萄牙语（葡萄牙）。它们同时编写，并由 CI 检查八个文件拥有相同的章节和相同的链接。 本仓库没有自己的界面或消息目录，因此没有需要翻译的界面文字。

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
- **[HYDRA-UMC](https://github.com/JuanenRac/HYDRA-UMC)** — 机器人手臂主板设计——CM5 主机 + 双核 STM32H745,目标是通过 CAN-OTA/SPI-OTA 协调最多 8 条工具臂(固件处于早期阶段,尚无已组装的电路板)。
- **[HYDRA-UMC-OS](https://github.com/JuanenRac/HYDRA-UMC-OS)** — 为 CM5 打造的可复现 Raspberry Pi OS 产品层：只读代理、经过验证的配置/档案、WiFi 首次接触配网。

*核心后端与客户端*
- **[HYDRA-UMC-STUDIO](https://github.com/JuanenRac/HYDRA-UMC-STUDIO)** — 具备实时多机器人 3D 可视化的网页控制面板。
- **[HYDRA-UMC-SUITE](https://github.com/JuanenRac/HYDRA-UMC-SUITE)** — 可同时管理多台服务器的桌面（PySide6）群控指挥中心。
- **[HYDRA-UMC-ANDROID-CONTROL](https://github.com/JuanenRac/HYDRA-UMC-ANDROID-CONTROL)** — 原生 Android 控制应用，具备生物识别登录和配对的 Wear OS 伴侣应用。
- **[HYDRA-UMC-IOS-CONTROL](https://github.com/JuanenRac/HYDRA-UMC-IOS-CONTROL)** — iOS/iPadOS 控制应用（Flutter），具备实时 WebSocket 同步。
- **[HYDRA-UMC-DSI](https://github.com/JuanenRac/HYDRA-UMC-DSI)** — 板载 7 寸 DSI 触摸屏的原生触控 UI，直接嵌入 CM5 本身。
- **[HYDRA-UMC-EDITOR-URDF](https://github.com/JuanenRac/HYDRA-UMC-EDITOR-URDF)** — 桌面版图形化 URDF 创建/编辑器，将完成的模型推送到 STUDIO 自身的目录中。
- **[HYDRA-UMC-EDITOR-STL](https://github.com/JuanenRac/HYDRA-UMC-EDITOR-STL)** — 桌面 STL 模型编辑器，在 HYDRA-UMC-EDITOR-URDF 编辑的同一模型目录中变换/替换/移除/添加真实部件。
- **[HYDRA-UMC-BRIDGE-AMR](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-AMR)** — 通过 VDA 5050 MQTT 发布者为 AGV/AMR 车队提供的协调边界(仅针对仿真车队测试)。
- **[HYDRA-UMC-BRIDGE-CNC](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-CNC)** — 具备 GRBL 状态/控制字节访问能力的高层 CNC 单元协调器(仅针对模拟器测试)。
- **[HYDRA-UMC-BRIDGE-DROIDS](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-DROIDS)** — 面向足式/人形机器人的协调边界,带有 Boston Dynamics Spot 指令发送器(仅针对模拟器测试)。
- **[HYDRA-UMC-BRIDGE-LASER](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-LASER)** — 读取 3 路钥匙/外壳/联锁 GPIO 信号的激光单元协调器(仅针对模拟芯片测试;无法使激光器上膛或发射)。
- **[HYDRA-UMC-BRIDGE-OPENPNP](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-OPENPNP)** — 针对 OpenPnP 贴片作业的安全高层级板件流程协调器。
- **[HYDRA-UMC-BRIDGE-PRINTER3D](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-PRINTER3D)** — 针对 Moonraker/Klipper 3D 打印机的安全协调边界，具备真实受控的任务命令。
- **[HYDRA-UMC-BRIDGE-ROS2](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-ROS2)** — 带有惰性导入 rclpy ROS 2 传输层的协调器(尚未在 ROS 2 环境中运行)。
- **[HYDRA-UMC-BRIDGE-UAV](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-UAV)** — 面向搭载摄像头的无人机的协调边界,带有 MAVLink 指令发送器(仅针对模拟器测试)。

*URTC 工具平台*
- **[URTC](https://github.com/JuanenRac/URTC)** — 实体 Universal Robot Tool Controller 电路板固件，通过 CAN 总线支持 25 种以上工具档案。
- **[URTC-FLASHER](https://github.com/JuanenRac/URTC-FLASHER)** — 用于烧录 URTC 板卡的桌面图形化工具，支持 CAN-OTA 及完整芯片级 SWD/JTAG。
- **[URTC-TESTER](https://github.com/JuanenRac/URTC-TESTER)** — 面向 URTC 板卡的桌面实时 CAN 总线诊断工具，每个工具档案一个面板。
- **[URTC-WEB-STUDIO](https://github.com/JuanenRac/URTC-WEB-STUDIO)** — 通过 Web Serial API 实现的、无需本地安装的浏览器版 URTC-TESTER 替代方案。
- **[URTC-GATEWAY](https://github.com/JuanenRac/URTC-GATEWAY)** — URTC CAN 总线前的网关：允许的标识符列表、速率限制和会话密钥；软件已在计算机上测试，尚未在真实总线上测试。

*视觉 AI 节点（Hailo-8）*
- **[HYDRA-UMC-VISION-NODE](https://github.com/JuanenRac/HYDRA-UMC-VISION-NODE)** — Hailo-8 视觉流水线的集成中心，具备真实的分阶段硬件就绪检查。
- **[HYDRA-UMC-DETECTION-HEF](https://github.com/JuanenRac/HYDRA-UMC-DETECTION-HEF)** — 真实的已编译模型注册表，具备 Hailo 架构/校验和安全加载验证。
- **[HYDRA-UMC-VISION-STREAMER](https://github.com/JuanenRac/HYDRA-UMC-VISION-STREAMER)** — 真实的 GStreamer 流水线 + MediaMTX 配置生成器，具备真实的 HailoRT 集成边界。
- **[HYDRA-UMC-VISUAL-SERVOING-API](https://github.com/JuanenRac/HYDRA-UMC-VISUAL-SERVOING-API)** — 以区域状态为授权条件的 Position-Based Visual Servoing 修正律;尚无摄像头位姿估计。
- **[HYDRA-UMC-SAFETY-ZONES](https://github.com/JuanenRac/HYDRA-UMC-SAFETY-ZONES)** — 从文件读取物体位置的 v0 区域入侵、校准新鲜度与 E-STOP 请求逻辑;没有检测器为其供数,也尚未连接任何物理 E-STOP。

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
- **[HYDRA-UMC-HIL-BRIDGE](https://github.com/JuanenRac/HYDRA-UMC-HIL-BRIDGE)** — 在仿真与真实硬件之间带有软件碰撞联锁的硬件在环路由器(未在真实硬件上测试)。
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
- **[HYDRA-UMC-WATCH](https://github.com/JuanenRac/HYDRA-UMC-WATCH)** — 带有触觉提醒模式与配对手机语音中继的 WearOS 伴侣应用(尚未在实体手表上运行)。
- **[HYDRA-UMC-CONNECTOR-HUB](https://github.com/JuanenRac/HYDRA-UMC-CONNECTOR-HUB)** — 外部适配器能力目录，设计上仅支持 GET。
- **[HYDRA-UMC-OS-REBUILDER](https://github.com/JuanenRac/HYDRA-UMC-OS-REBUILDER)** — 从源码构建全新的 CM5 镜像，是 "Ecosystem Operations" 系列的另一个兄弟项目。
- **[HYDRA-UMC-UPDATER](https://github.com/JuanenRac/HYDRA-UMC-UPDATER)** —— 发现、克隆并更新本生态系统中每个仓库的管理类桌面工具。
- **[URTC-SMART-RACK](https://github.com/JuanenRac/URTC-SMART-RACK)** — 用于板卡安装机架的固件，具备真实的工具 ID 解码与 Smart Idle 预热逻辑。
- **[URTC-VISION-TOOL](https://github.com/JuanenRac/URTC-VISION-TOOL)** — 固件加上一个真实的 Python 视觉伴侣程序，用于热成像/RGB 检测工具头。

## 📚 文档

更多阅读：

* **[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)** — 目的、五个目标组成部分、目标架构，以及生态系统关系。
* **[docs/CLI_REFERENCE.md](docs/CLI_REFERENCE.md)** — 每个子命令、其参数标志，以及退出码合约。
* **[docs/CONTRACTS.md](docs/CONTRACTS.md)** — 五份合约逐字段的真实结构。
* [生态系统的安全基线](https://github.com/JuanenRac/HYDRA-UMC-DOCS/blob/main/docs/SECURITY_BASELINE.md)
* [生态系统的威胁模型](https://github.com/JuanenRac/HYDRA-UMC-DOCS/blob/main/docs/THREAT_MODEL.md)
* [本仓库的更新日志](CHANGELOG.md)
* [本仓库的许可证](LICENSE.md)

## 🤝 参与贡献与社区

* 提交 pull request 之前，请运行 `HYDRA_UMC_CI=1 py -3 tools/ci_validate.py`（或 `HYDRA_UMC_CI=1 python3 tools/ci_validate.py`）：它必须输出 `CI_VALIDATION=PASS`。此检查不要运行 `build.sh` 或 `build.bat`；构建不是检查。
* 八个 README 由 HYDRA-UMC-DOCS 中的同一个源生成；请勿手工编辑。修改源文件，再用 `tools/make_readmes.py` 重新生成。
* 不要在 README 中声称尚未运行过的内容：属实时请写“仅模拟”或“尚未在硬件上试过”。
* 请参阅 [CONTRIBUTING.md](CONTRIBUTING.md)、[行为准则](CODE_OF_CONDUCT.md)、[SECURITY.md](SECURITY.md) 和 [SUPPORT.md](SUPPORT.md)。

## 👤 作者

**JuanenRac (Electro Hobby 3D)** · electrohobby3d@gmail.com

## 📜 许可证

GPL-3.0-or-later - [LICENSE](LICENSE).
